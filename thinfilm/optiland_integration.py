"""Optional bridge from PyThinFilm material/stack data to Optiland systems.

The module intentionally does not import Optiland at import time.  PyThinFilm
therefore keeps its existing dependency set, while callers that have Optiland
installed (or provide a source checkout) can build a sequential optical system
using PyThinFilm's real-material n/k tables.

All public input units are explicit:

* wavelength: micrometres (matching Optiland's sequential-system API)
* surface radius and spacing: millimetres
* coating layer thickness: nanometres (matching PyThinFilm's stack model)
"""

from __future__ import annotations

import importlib
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .materials import (
    canonical_material_name,
    load_real_material,
    material_complex_index,
)


class OptilandUnavailableError(RuntimeError):
    """Raised when the optional Optiland runtime cannot be loaded."""


@dataclass(frozen=True)
class CoatingLayerInput:
    """One isotropic coating layer supplied to Optiland."""

    material_id: str
    thickness_nm: float
    label: str = ""

    def __post_init__(self) -> None:
        if not str(self.material_id).strip():
            raise ValueError("coating material_id must not be empty")
        object.__setattr__(self, "material_id", canonical_material_name(self.material_id))
        if not math.isfinite(float(self.thickness_nm)) or self.thickness_nm <= 0:
            raise ValueError("coating thickness_nm must be finite and positive")


@dataclass(frozen=True)
class CoatingStackInput:
    """Material-resolved coating attached to one sequential surface."""

    incident_material_id: str
    substrate_material_id: str
    layers: tuple[CoatingLayerInput, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not str(self.incident_material_id).strip():
            raise ValueError("incident_material_id must not be empty")
        if not str(self.substrate_material_id).strip():
            raise ValueError("substrate_material_id must not be empty")
        object.__setattr__(
            self,
            "incident_material_id",
            canonical_material_name(self.incident_material_id),
        )
        object.__setattr__(
            self,
            "substrate_material_id",
            canonical_material_name(self.substrate_material_id),
        )
        object.__setattr__(self, "layers", tuple(self.layers))


@dataclass(frozen=True)
class SequentialSurfaceInput:
    """One Optiland sequential surface with an explicit transmitted material.

    ``radius_mm=None`` represents a plane. ``thickness_mm=None`` leaves the
    Optiland default unchanged; the string ``"infinity"`` represents an
    infinite object distance without emitting non-standard JSON ``Infinity``.
    """

    material_id: str
    radius_mm: float | None = None
    thickness_mm: float | str | None = None
    is_stop: bool = False
    coating: CoatingStackInput | None = None

    def __post_init__(self) -> None:
        if not str(self.material_id).strip():
            raise ValueError("surface material_id must not be empty")
        object.__setattr__(self, "material_id", canonical_material_name(self.material_id))
        if self.radius_mm is not None and not math.isfinite(float(self.radius_mm)):
            raise ValueError("radius_mm must be finite or None for a plane")
        if isinstance(self.thickness_mm, str):
            if self.thickness_mm != "infinity":
                raise ValueError('string thickness_mm must be "infinity"')
        elif self.thickness_mm is not None:
            value = float(self.thickness_mm)
            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    'thickness_mm must be finite and non-negative, "infinity", or None'
                )


@dataclass(frozen=True)
class SequentialSystemInput:
    """Minimal serializable input model for an Optiland sequential system."""

    name: str
    surfaces: tuple[SequentialSurfaceInput, ...]
    wavelengths_um: tuple[float, ...]
    primary_wavelength_index: int = 0
    aperture_epd_mm: float = 10.0
    field_y_deg: float = 0.0
    unpolarized: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "surfaces", tuple(self.surfaces))
        object.__setattr__(self, "wavelengths_um", tuple(self.wavelengths_um))
        if not str(self.name).strip():
            raise ValueError("system name must not be empty")
        if len(self.surfaces) < 2:
            raise ValueError("a sequential system requires at least two surfaces")
        if not self.wavelengths_um:
            raise ValueError("at least one wavelength is required")
        if any(
            not math.isfinite(float(wavelength)) or wavelength <= 0
            for wavelength in self.wavelengths_um
        ):
            raise ValueError("wavelengths_um must contain finite positive values")
        if not 0 <= self.primary_wavelength_index < len(self.wavelengths_um):
            raise ValueError("primary_wavelength_index is outside wavelengths_um")
        if not math.isfinite(float(self.aperture_epd_mm)) or self.aperture_epd_mm <= 0:
            raise ValueError("aperture_epd_mm must be finite and positive")
        if not math.isfinite(float(self.field_y_deg)):
            raise ValueError("field_y_deg must be finite")
        self._validate_coating_boundaries()

    def _validate_coating_boundaries(self) -> None:
        for index, surface in enumerate(self.surfaces):
            coating = surface.coating
            if coating is None:
                continue
            if index == 0:
                raise ValueError("the object surface cannot carry a coating")
            previous_material = self.surfaces[index - 1].material_id
            if coating.incident_material_id != previous_material:
                raise ValueError(
                    f"surface {index} coating incident material "
                    f"{coating.incident_material_id!r} does not match previous "
                    f"medium {previous_material!r}"
                )
            if coating.substrate_material_id != surface.material_id:
                raise ValueError(
                    f"surface {index} coating substrate material "
                    f"{coating.substrate_material_id!r} does not match transmitted "
                    f"medium {surface.material_id!r}"
                )

    def material_ids(self) -> tuple[str, ...]:
        """Return every referenced material ID once, preserving first use order."""
        ordered: list[str] = []
        for surface in self.surfaces:
            candidates = [surface.material_id]
            if surface.coating is not None:
                candidates.extend(
                    [
                        surface.coating.incident_material_id,
                        surface.coating.substrate_material_id,
                    ]
                )
                candidates.extend(layer.material_id for layer in surface.coating.layers)
            for material_id in candidates:
                if material_id not in ordered:
                    ordered.append(material_id)
        return tuple(ordered)

    def validate_material_wavelength_ranges(self) -> None:
        """Reject a system wavelength outside any referenced material dataset."""
        for material_id in self.material_ids():
            dataset = load_real_material(material_id)
            for wavelength_um in self.wavelengths_um:
                if not dataset.lambda_min_um <= wavelength_um <= dataset.lambda_max_um:
                    raise ValueError(
                        f"{material_id} does not cover {wavelength_um:.6g} um; "
                        f"valid range is {dataset.lambda_min_um:.6g}-"
                        f"{dataset.lambda_max_um:.6g} um"
                    )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation with explicit unit field names."""
        return asdict(self)


def optiland_runtime_status(optiland_root: str | Path | None = None) -> dict[str, Any]:
    """Report whether the optional runtime can be loaded without building a system."""
    try:
        api = _load_optiland_api(optiland_root)
    except (ImportError, FileNotFoundError, OptilandUnavailableError) as exc:
        return {
            "available": False,
            "optiland_root": str(optiland_root) if optiland_root is not None else None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    module = api["module"]
    return {
        "available": True,
        "optiland_root": str(Path(module.__file__).resolve().parents[1]),
        "version": getattr(module, "__version__", None),
    }


def _load_optiland_api(optiland_root: str | Path | None = None) -> dict[str, Any]:
    if optiland_root is not None:
        root = Path(optiland_root).resolve()
        if not (root / "optiland" / "__init__.py").is_file():
            raise FileNotFoundError(f"Optiland source checkout not found: {root}")
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
    try:
        module = importlib.import_module("optiland")
        analysis = importlib.import_module("optiland.analysis")
        be = importlib.import_module("optiland.backend")
        coatings = importlib.import_module("optiland.coatings")
        materials_base = importlib.import_module("optiland.materials.base")
        optic_module = importlib.import_module("optiland.optic")
        rays = importlib.import_module("optiland.rays")
    except ImportError as exc:
        raise OptilandUnavailableError(
            "Optiland is optional. Install it or pass optiland_root pointing to a "
            "source checkout."
        ) from exc
    if optiland_root is not None and not getattr(sys, "frozen", False):
        imported_root = Path(module.__file__).resolve().parents[1]
        if imported_root != root:
            raise OptilandUnavailableError(
                f"Optiland is already imported from {imported_root}, not requested "
                f"checkout {root}. Start a fresh Python process to change runtimes."
            )
    return {
        "module": module,
        "be": be,
        "BaseMaterial": materials_base.BaseMaterial,
        "SpotDiagram": analysis.SpotDiagram,
        "ThinFilmCoating": coatings.ThinFilmCoating,
        "Optic": optic_module.Optic,
        "PolarizationState": rays.PolarizationState,
    }


class OptilandBridge:
    """Build Optiland objects while retaining PyThinFilm as material authority."""

    def __init__(self, optiland_root: str | Path | None = None):
        self.api = _load_optiland_api(optiland_root)
        self._material_type = self._create_material_type()
        self._materials: dict[str, Any] = {}

    def _create_material_type(self) -> type:
        be = self.api["be"]
        base_material = self.api["BaseMaterial"]

        class PyThinFilmTabulatedMaterial(base_material):
            """Optiland material evaluated from PyThinFilm's cached n/k tables."""

            def __init__(self, material_id: str):
                self.material_id = str(material_id)
                self.dataset = load_real_material(self.material_id)
                super().__init__()

            def _cache_state(self) -> tuple[str]:
                return (self.material_id,)

            @staticmethod
            def _return_like(values: np.ndarray, wavelength: Any) -> Any:
                converted = be.asarray(values)
                if not be.is_array_like(wavelength) and np.asarray(values).size == 1:
                    return converted.item()
                return converted

            def _complex_index(self, wavelength: Any) -> np.ndarray:
                wavelength_um = np.asarray(be.to_numpy(wavelength), dtype=float)
                return np.asarray(
                    material_complex_index(
                        self.material_id,
                        wavelength_um * 1000.0,
                        out_of_range_policy="error",
                    ),
                    dtype=complex,
                )

            def _calculate_n(self, wavelength: Any, **kwargs: Any) -> Any:
                return self._return_like(np.real(self._complex_index(wavelength)), wavelength)

            def _calculate_k(self, wavelength: Any, **kwargs: Any) -> Any:
                return self._return_like(np.imag(self._complex_index(wavelength)), wavelength)

            def to_dict(self) -> dict[str, Any]:
                result = super().to_dict()
                result.update(
                    {
                        "material_id": self.material_id,
                        "source": self.dataset.source,
                        "file": str(self.dataset.file),
                    }
                )
                return result

        return PyThinFilmTabulatedMaterial

    def material(self, material_id: str) -> Any:
        """Return one cached Optiland material backed by PyThinFilm data."""
        key = str(material_id)
        if key not in self._materials:
            self._materials[key] = self._material_type(key)
        return self._materials[key]

    def build_coating(self, stack: CoatingStackInput) -> Any:
        """Translate a coating input while preserving thickness in nanometres."""
        layers = [
            (
                self.material(layer.material_id),
                float(layer.thickness_nm),
                layer.label or layer.material_id,
            )
            for layer in stack.layers
        ]
        return self.api["ThinFilmCoating"](
            self.material(stack.incident_material_id),
            self.material(stack.substrate_material_id),
            layers=layers,
        )

    def build_system(self, spec: SequentialSystemInput) -> Any:
        """Validate and translate a minimal system input into ``Optic``."""
        spec.validate_material_wavelength_ranges()
        optic = self.api["Optic"](name=spec.name)
        for index, surface in enumerate(spec.surfaces):
            parameters: dict[str, Any] = {
                "index": index,
                "radius": np.inf if surface.radius_mm is None else surface.radius_mm,
                "material": self.material(surface.material_id),
            }
            if surface.thickness_mm == "infinity":
                parameters["thickness"] = np.inf
            elif surface.thickness_mm is not None:
                parameters["thickness"] = float(surface.thickness_mm)
            if surface.is_stop:
                parameters["is_stop"] = True
            if 0 < index < len(spec.surfaces) - 1:
                # Explicit clear diameter, shared with non-sequential geometry.
                parameters["aperture"] = 1.4 * float(spec.aperture_epd_mm)
            if surface.coating is not None:
                parameters["coating"] = self.build_coating(surface.coating)
            elif 0 < index < len(spec.surfaces) - 1:
                parameters["coating"] = self.build_coating(CoatingStackInput(
                    spec.surfaces[index - 1].material_id, surface.material_id))
            optic.surfaces.add(**parameters)

        optic.set_aperture(aperture_type="EPD", value=float(spec.aperture_epd_mm))
        optic.fields.set_type(field_type="angle")
        optic.fields.add(y=float(spec.field_y_deg))
        for index, wavelength_um in enumerate(spec.wavelengths_um):
            optic.wavelengths.add(
                value=float(wavelength_um),
                is_primary=index == spec.primary_wavelength_index,
            )
        optic.updater.set_polarization(
            self.api["PolarizationState"](is_polarized=not spec.unpolarized)
        )
        return optic


def make_singlet_system_input(
    *,
    name: str,
    incident_material_id: str = "Air",
    glass_material_id: str,
    front_coating: CoatingStackInput,
    wavelength_um: float,
    rear_radius_mm: float = -40.0,
    front_radius_mm: float = 40.0,
    center_thickness_mm: float = 4.0,
    image_distance_mm: float = 37.0,
    aperture_epd_mm: float = 10.0,
) -> SequentialSystemInput:
    """Create the reference singlet used by the Optiland integration examples."""
    rear_coating = CoatingStackInput(
        incident_material_id=glass_material_id,
        substrate_material_id=incident_material_id,
    )
    return SequentialSystemInput(
        name=name,
        surfaces=(
            SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
            SequentialSurfaceInput(
                material_id=glass_material_id,
                radius_mm=front_radius_mm,
                thickness_mm=center_thickness_mm,
                is_stop=True,
                coating=front_coating,
            ),
            SequentialSurfaceInput(
                material_id=incident_material_id,
                radius_mm=rear_radius_mm,
                thickness_mm=image_distance_mm,
                coating=rear_coating,
            ),
            SequentialSurfaceInput(material_id=incident_material_id),
        ),
        wavelengths_um=(float(wavelength_um),),
        aperture_epd_mm=float(aperture_epd_mm),
    )


def make_teaching_system_input(
    *,
    template: str,
    name: str,
    incident_material_id: str = "Air",
    glass_material_id: str,
    front_coating: CoatingStackInput,
    wavelength_um: float,
) -> SequentialSystemInput:
    """Build one of the safe teaching templates used by the Optiland panel.

    These are deterministic teaching prescriptions, not optimized engineering
    designs. Unknown names fail explicitly instead of substituting a singlet.
    """
    imaging_templates = {
        "multi_element_imaging", "complex_camera_lens", "phone_camera_module",
        "wide_angle_multi_element", "wide_field_camera", "photographic_lens",
        "camera_lens_coverglass", "single_lens_imaging", "dual_band_imager",
        "dispersive_lens", "wide_angle_window", "dual_path_beamsplitter",
    }
    spectral_templates = {
        "spectral_camera", "multispectral_imager", "dual_channel_spectral_imager",
        "spectrometer", "high_resolution_spectrometer", "sensor_prefilter",
        "wdm_receiver", "solar_cell_receiver", "low_e_window",
    }
    reflector_templates = {
        "folded_reflector", "laser_expander", "dbr_laser_cavity",
    }
    interface_templates = {
        "prism_coupled_tamm", "prism_coupled_tamm_scan", "tamm_absorption_probe",
        "polarized_phase_screen", "prism_coupled_tamm_window", "phase_interferometer",
    }
    thermal_templates = {
        "radiative_cooling_emitter", "photothermal_receiver",
        "photothermal_parameter_scan",
    }
    grating_templates = {"grating_waveguide_coupler"}

    if template in imaging_templates:
        if template in {"single_lens_imaging", "camera_lens_coverglass", "wide_angle_window"}:
            return make_singlet_system_input(
                name=name,
                incident_material_id=incident_material_id,
                glass_material_id=glass_material_id,
                front_coating=front_coating,
                wavelength_um=wavelength_um,
            )
        # Keep the major teaching systems visibly distinct while remaining
        # deterministic and paraxial enough for a stable classroom baseline.
        if template == "phone_camera_module":
            rear_coating = CoatingStackInput(
                incident_material_id=glass_material_id,
                substrate_material_id=incident_material_id,
            )
            return SequentialSystemInput(
                name=name,
                surfaces=(
                    SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=32.0, thickness_mm=2.2, is_stop=True, coating=front_coating),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-28.0, thickness_mm=3.5, coating=rear_coating),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=48.0, thickness_mm=2.0),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-52.0, thickness_mm=8.0),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=70.0, thickness_mm=2.0),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-70.0, thickness_mm=24.0),
                    SequentialSurfaceInput(material_id=incident_material_id),
                ),
                wavelengths_um=(float(wavelength_um),),
                aperture_epd_mm=5.0,
            )
        if template in {"wide_angle_multi_element", "wide_field_camera"}:
            return SequentialSystemInput(
                name=name,
                surfaces=(
                    SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=28.0, thickness_mm=3.0, is_stop=True, coating=front_coating),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-24.0, thickness_mm=6.0),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=38.0, thickness_mm=3.0),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-38.0, thickness_mm=18.0),
                    SequentialSurfaceInput(material_id=incident_material_id),
                ),
                wavelengths_um=(float(wavelength_um),),
                aperture_epd_mm=10.0,
                field_y_deg=18.0,
            )
        if template == "complex_camera_lens":
            return SequentialSystemInput(
                name=name,
                surfaces=(
                    SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=55.0, thickness_mm=4.0, is_stop=True, coating=front_coating),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-55.0, thickness_mm=5.0),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=36.0, thickness_mm=3.0),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-36.0, thickness_mm=7.0),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=82.0, thickness_mm=3.0),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-82.0, thickness_mm=35.0),
                    SequentialSurfaceInput(material_id=incident_material_id),
                ),
                wavelengths_um=(float(wavelength_um),),
                aperture_epd_mm=9.0,
            )
        if template == "dual_band_imager":
            return SequentialSystemInput(
                name=name,
                surfaces=(
                    SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=45.0, thickness_mm=4.0, is_stop=True, coating=front_coating),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-45.0, thickness_mm=12.0),
                    SequentialSurfaceInput(material_id=glass_material_id, radius_mm=60.0, thickness_mm=3.0),
                    SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-60.0, thickness_mm=30.0),
                    SequentialSurfaceInput(material_id=incident_material_id),
                ),
                wavelengths_um=(float(wavelength_um),),
                aperture_epd_mm=7.0,
            )
        # Multi-element camera family: two coated/curved elements and an image
        # plane.  The construction remains sequential and deterministic.
        rear_coating = CoatingStackInput(
            incident_material_id=glass_material_id,
            substrate_material_id=incident_material_id,
        )
        return SequentialSystemInput(
            name=name,
            surfaces=(
                SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
                SequentialSurfaceInput(material_id=glass_material_id, radius_mm=42.0, thickness_mm=4.0, is_stop=True, coating=front_coating),
                SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-42.0, thickness_mm=8.0, coating=rear_coating),
                SequentialSurfaceInput(material_id=glass_material_id, radius_mm=65.0, thickness_mm=3.0),
                SequentialSurfaceInput(material_id=incident_material_id, radius_mm=-65.0, thickness_mm=42.0),
                SequentialSurfaceInput(material_id=incident_material_id),
            ),
            wavelengths_um=(float(wavelength_um),),
            aperture_epd_mm=8.0,
        )

    if template in spectral_templates:
        # Spectral systems use a coated entrance window and a detector plane;
        # the same sequential representation allows the panel to compare
        # spectral-film changes without inventing a separate ray engine.
        return SequentialSystemInput(
            name=name,
            surfaces=(
                SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
                SequentialSurfaceInput(material_id=glass_material_id, radius_mm=None, thickness_mm=5.0, is_stop=True, coating=front_coating),
                SequentialSurfaceInput(material_id=incident_material_id, radius_mm=None, thickness_mm=35.0),
                SequentialSurfaceInput(material_id=incident_material_id),
            ),
            wavelengths_um=(float(wavelength_um),),
            aperture_epd_mm=5.0,
        )

    if template in reflector_templates:
        return SequentialSystemInput(
            name=name,
            surfaces=(
                SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
                SequentialSurfaceInput(material_id=glass_material_id, radius_mm=None, thickness_mm=20.0, is_stop=True, coating=front_coating),
                SequentialSurfaceInput(material_id=incident_material_id, radius_mm=None, thickness_mm=20.0),
                SequentialSurfaceInput(material_id=glass_material_id, radius_mm=None, thickness_mm=20.0, coating=front_coating),
                SequentialSurfaceInput(material_id=incident_material_id),
            ),
            wavelengths_um=(float(wavelength_um),),
            aperture_epd_mm=6.0,
        )

    if template in interface_templates:
        return SequentialSystemInput(
            name=name,
            surfaces=(
                SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
                SequentialSurfaceInput(material_id=glass_material_id, radius_mm=None, thickness_mm=10.0, is_stop=True, coating=front_coating),
                SequentialSurfaceInput(material_id=glass_material_id, radius_mm=None, thickness_mm=15.0),
                SequentialSurfaceInput(material_id=incident_material_id),
            ),
            wavelengths_um=(float(wavelength_um),),
            aperture_epd_mm=4.0,
            field_y_deg=25.0,
        )

    if template in thermal_templates or template in grating_templates:
        return SequentialSystemInput(
            name=name,
            surfaces=(
                SequentialSurfaceInput(material_id=incident_material_id, thickness_mm="infinity"),
                SequentialSurfaceInput(material_id=glass_material_id, radius_mm=None, thickness_mm=5.0, is_stop=True, coating=front_coating),
                SequentialSurfaceInput(material_id=incident_material_id),
            ),
            wavelengths_um=(float(wavelength_um),),
            aperture_epd_mm=3.0,
        )

    raise ValueError(f"Unknown Optiland teaching template: {template}")


def referenced_material_records(
    spec: SequentialSystemInput,
) -> list[dict[str, Any]]:
    """Return provenance and valid ranges for every material in a system input."""
    rows: list[dict[str, Any]] = []
    for material_id in spec.material_ids():
        dataset = load_real_material(material_id)
        rows.append(
            {
                "material_id": material_id,
                "source": dataset.source,
                "file": str(dataset.file),
                "lambda_min_um": dataset.lambda_min_um,
                "lambda_max_um": dataset.lambda_max_um,
            }
        )
    return rows


__all__ = [
    "CoatingLayerInput",
    "CoatingStackInput",
    "OptilandBridge",
    "OptilandUnavailableError",
    "SequentialSurfaceInput",
    "SequentialSystemInput",
    "make_singlet_system_input",
    "make_teaching_system_input",
    "optiland_runtime_status",
    "referenced_material_records",
]
