r"""Compare a bare N-BK7 lens with a real MgF2 AR-coated lens in Optiland.

PyThinFilm remains the source of material dispersion and coating design.  The
same wavelength-dependent n/k tables are exposed to Optiland through a small
``BaseMaterial`` adapter, so both engines evaluate the same physical stack.

Run with the isolated Optiland environment::

    ..\optiland\.venv\Scripts\python.exe experiments\optiland_real_material_ar_comparison.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.optiland_ar_comparison import (
    DESIGN_WAVELENGTH_NM,
    _center_value,
    _max_finite_difference,
    _plot_aoi,
    _plot_mtf,
    _plot_psf_absolute,
    _plot_psf_normalized,
    _plot_spectrum,
    _plot_spot,
    _psf_and_mtf,
    _save_layouts,
    _spot_data,
    _trace_snapshot,
)
from experiments.optiland_poc import _json_ready
from thinfilm.education import (
    LayerSpec,
    multilayer_rt_spectrum_real_materials,
    simulate_report_design_real_materials,
)
from thinfilm.materials import load_real_material, material_complex_index
from thinfilm.optiland_integration import (
    CoatingLayerInput,
    CoatingStackInput,
    OptilandBridge,
    make_singlet_system_input,
)


INCIDENT_MATERIAL = "Air"
LAYER_MATERIAL = "MgF2"
SUBSTRATE_MATERIAL = "N-BK7"
WAVELENGTHS_NM = np.linspace(400.0, 700.0, 151)
ANGLES_DEG = np.linspace(0.0, 60.0, 121)


def _design() -> tuple[LayerSpec, dict[str, Any]]:
    """Design one quarter-wave MgF2 layer using real n at 550 nm."""
    result = simulate_report_design_real_materials(
        "single_ar",
        material_map={
            "n_incident": INCIDENT_MATERIAL,
            "n_low": LAYER_MATERIAL,
            "n_substrate": SUBSTRATE_MATERIAL,
        },
        wavelengths_nm=WAVELENGTHS_NM,
        lambda0_nm=DESIGN_WAVELENGTH_NM,
        theta_deg=0.0,
        pol="p",
        out_of_range_policy="error",
    )
    row = result["layers"][0]
    layer = LayerSpec(
        str(row["name"]),
        complex(float(row["n_real"]), float(row["n_imag"])),
        float(row["thickness_nm"]),
    )
    design_indices = result["design_indices_at_lambda0"]
    ideal_index = float(
        np.sqrt(
            design_indices["n_incident"]["n"]
            * design_indices["n_substrate"]["n"]
        )
    )
    datasets = {
        name: load_real_material(name)
        for name in (LAYER_MATERIAL, SUBSTRATE_MATERIAL)
    }
    return layer, {
        "design": "real_material_single_layer_quarter_wave_ar",
        "source": "PyThinFilm simulate_report_design_real_materials",
        "wavelength_nm": DESIGN_WAVELENGTH_NM,
        "incident_material": INCIDENT_MATERIAL,
        "layer_material": LAYER_MATERIAL,
        "substrate_material": SUBSTRATE_MATERIAL,
        "design_indices_at_lambda0": design_indices,
        "ideal_zero_reflection_layer_index": ideal_index,
        "actual_layer_index": float(np.real(layer.n)),
        "layer_index_mismatch_from_ideal": float(np.real(layer.n)) - ideal_index,
        "layer_thickness_nm": float(layer.thickness_nm),
        "material_sources": {
            name: {
                "source": dataset.source,
                "file": str(dataset.file),
                "valid_wavelength_nm": [
                    dataset.lambda_min_um * 1000.0,
                    dataset.lambda_max_um * 1000.0,
                ],
            }
            for name, dataset in datasets.items()
        },
    }


def _make_systems(
    bridge: OptilandBridge,
) -> tuple[Any, Any, Any, Any, dict[str, Any]]:
    """Build identical bare/coated singlets using dispersive materials."""
    layer, design = _design()
    bare_stack = CoatingStackInput(
        incident_material_id=INCIDENT_MATERIAL,
        substrate_material_id=SUBSTRATE_MATERIAL,
    )
    ar_stack = CoatingStackInput(
        incident_material_id=INCIDENT_MATERIAL,
        substrate_material_id=SUBSTRATE_MATERIAL,
        layers=(
            CoatingLayerInput(
                material_id=LAYER_MATERIAL,
                thickness_nm=layer.thickness_nm,
                label="Real MgF2",
            ),
        ),
    )
    bare_coating = bridge.build_coating(bare_stack)
    ar_coating = bridge.build_coating(ar_stack)
    bare_spec = make_singlet_system_input(
        name="Bare Real N-BK7 Singlet",
        glass_material_id=SUBSTRATE_MATERIAL,
        front_coating=bare_stack,
        wavelength_um=DESIGN_WAVELENGTH_NM / 1000.0,
    )
    ar_spec = make_singlet_system_input(
        name="Real MgF2 AR on N-BK7",
        glass_material_id=SUBSTRATE_MATERIAL,
        front_coating=ar_stack,
        wavelength_um=DESIGN_WAVELENGTH_NM / 1000.0,
    )
    design["system_inputs"] = {
        "bare": bare_spec.to_dict(),
        "ar": ar_spec.to_dict(),
    }

    return (
        bare_coating,
        ar_coating,
        bridge.build_system(bare_spec),
        bridge.build_system(ar_spec),
        design,
    )


def _stack_grid(stack: Any, wavelengths_nm: np.ndarray, angles_deg: np.ndarray) -> dict[str, Any]:
    return {
        pol: stack.compute_rtRAT_nm_deg(wavelengths_nm, angles_deg, pol)
        for pol in ("s", "p")
    }


def _pythinfilm_reference(
    wavelengths_nm: np.ndarray,
    layers: list[LayerSpec],
) -> dict[str, Any]:
    material_map = {
        "n_incident": INCIDENT_MATERIAL,
        "n_low": LAYER_MATERIAL,
        "n_substrate": SUBSTRATE_MATERIAL,
    }
    design_indices = {
        "n_incident": complex(
            np.asarray(material_complex_index(INCIDENT_MATERIAL, DESIGN_WAVELENGTH_NM))
        ),
        "n_low": complex(
            np.asarray(material_complex_index(LAYER_MATERIAL, DESIGN_WAVELENGTH_NM))
        ),
        "n_substrate": complex(
            np.asarray(material_complex_index(SUBSTRATE_MATERIAL, DESIGN_WAVELENGTH_NM))
        ),
    }
    return {
        pol: multilayer_rt_spectrum_real_materials(
            wavelengths_nm,
            layers,
            design_type="single_ar",
            material_map=material_map,
            role_fallback_indices=design_indices,
            theta0_deg=0.0,
            pol=pol,
            out_of_range_policy="error",
        )
        for pol in ("s", "p")
    }


def _plot_material_dispersion(output_path: Path) -> None:
    """Plot the exact PyThinFilm material data passed to Optiland."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharex=True)
    for material, color in ((LAYER_MATERIAL, "C0"), (SUBSTRATE_MATERIAL, "C1")):
        index = material_complex_index(
            material,
            WAVELENGTHS_NM,
            out_of_range_policy="error",
        )
        axes[0].plot(WAVELENGTHS_NM, np.real(index), color=color, label=material)
        axes[1].plot(WAVELENGTHS_NM, np.imag(index), color=color, label=material)
    axes[0].set_ylabel("Refractive index n")
    axes[1].set_ylabel("Extinction coefficient k")
    for axis in axes:
        axis.set_xlabel("Wavelength (nm)")
        axis.grid(alpha=0.25)
        axis.legend()
    fig.suptitle("PyThinFilm Material Data Used by Optiland")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def run_comparison(optiland_root: Path, output_dir: Path) -> Path:
    """Run the real-material coating and image-system comparison."""
    output_dir.mkdir(parents=True, exist_ok=True)
    bridge = OptilandBridge(optiland_root)
    api = bridge.api
    bare_coating, ar_coating, bare_lens, ar_lens, design = _make_systems(bridge)

    zero_angle = np.asarray([0.0])
    design_wavelength = np.asarray([DESIGN_WAVELENGTH_NM])
    bare_spectrum = _stack_grid(bare_coating.stack, WAVELENGTHS_NM, zero_angle)
    ar_spectrum = _stack_grid(ar_coating.stack, WAVELENGTHS_NM, zero_angle)
    bare_aoi = _stack_grid(bare_coating.stack, design_wavelength, ANGLES_DEG)
    ar_aoi = _stack_grid(ar_coating.stack, design_wavelength, ANGLES_DEG)

    layer = LayerSpec(
        "L",
        complex(design["actual_layer_index"], 0.0),
        design["layer_thickness_nm"],
    )
    py_bare = _pythinfilm_reference(WAVELENGTHS_NM, [])
    py_ar = _pythinfilm_reference(WAVELENGTHS_NM, [layer])

    center_index = int(np.argmin(np.abs(WAVELENGTHS_NM - DESIGN_WAVELENGTH_NM)))
    bare_trace = _trace_snapshot(bare_lens, api)
    ar_trace = _trace_snapshot(ar_lens, api)
    ray_coordinate_delta = max(
        _max_finite_difference(bare_trace[axis], ar_trace[axis])
        for axis in ("x", "y", "z")
    )
    ray_direction_delta = max(
        _max_finite_difference(bare_trace[axis], ar_trace[axis])
        for axis in ("L", "M", "N")
    )
    bare_spot = _spot_data(bare_lens, api)
    ar_spot = _spot_data(ar_lens, api)
    bare_image = _psf_and_mtf(bare_lens, api)
    ar_image = _psf_and_mtf(ar_lens, api)

    energy_errors: list[float] = []
    for dataset in (bare_spectrum, ar_spectrum, bare_aoi, ar_aoi):
        for pol in ("s", "p"):
            total = sum(np.asarray(dataset[pol][key]) for key in ("R", "T", "A"))
            energy_errors.append(float(np.max(np.abs(total - 1.0))))

    cross_engine_errors: list[float] = []
    for optiland_data, pythinfilm_data in (
        (bare_spectrum, py_bare),
        (ar_spectrum, py_ar),
    ):
        for pol in ("s", "p"):
            for key in ("R", "T", "A"):
                cross_engine_errors.append(
                    _max_finite_difference(
                        np.asarray(optiland_data[pol][key])[:, 0],
                        np.asarray(pythinfilm_data[pol][key]),
                    )
                )

    bare_r = 0.5 * sum(
        _center_value(bare_spectrum[pol], "R", center_index) for pol in ("s", "p")
    )
    ar_r = 0.5 * sum(
        _center_value(ar_spectrum[pol], "R", center_index) for pol in ("s", "p")
    )
    bare_t = 0.5 * sum(
        _center_value(bare_spectrum[pol], "T", center_index) for pol in ("s", "p")
    )
    ar_t = 0.5 * sum(
        _center_value(ar_spectrum[pol], "T", center_index) for pol in ("s", "p")
    )

    artifacts = _save_layouts(bare_lens, ar_lens, output_dir)
    plot_paths = {
        "material_dispersion": output_dir / "material_dispersion.png",
        "coating_spectrum": output_dir / "coating_spectrum.png",
        "coating_aoi_scan": output_dir / "coating_aoi_scan.png",
        "spot_comparison": output_dir / "spot_comparison.png",
        "psf_normalized_comparison": output_dir / "psf_normalized_comparison.png",
        "psf_absolute_comparison": output_dir / "psf_absolute_comparison.png",
        "mtf_comparison": output_dir / "mtf_comparison.png",
    }
    _plot_material_dispersion(plot_paths["material_dispersion"])
    _plot_spectrum(WAVELENGTHS_NM, bare_spectrum, ar_spectrum, plot_paths["coating_spectrum"])
    _plot_aoi(ANGLES_DEG, bare_aoi, ar_aoi, plot_paths["coating_aoi_scan"])
    _plot_spot(bare_spot, ar_spot, plot_paths["spot_comparison"])
    _plot_psf_normalized(
        bare_image["psf_normalized"],
        ar_image["psf_normalized"],
        plot_paths["psf_normalized_comparison"],
    )
    _plot_psf_absolute(
        bare_image["psf_absolute_relative_units"],
        ar_image["psf_absolute_relative_units"],
        bare_image["psf_integrated_absolute_relative_units"],
        ar_image["psf_integrated_absolute_relative_units"],
        plot_paths["psf_absolute_comparison"],
    )
    _plot_mtf(bare_image, ar_image, plot_paths["mtf_comparison"])
    artifacts.update({key: str(path) for key, path in plot_paths.items()})

    metrics = {
        "max_energy_conservation_error": max(energy_errors),
        "max_pythinfilm_optiland_rta_difference": max(cross_engine_errors),
        "center_wavelength_nm": DESIGN_WAVELENGTH_NM,
        "bare_front_reflectance": bare_r,
        "ar_front_reflectance": ar_r,
        "absolute_reflectance_reduction": bare_r - ar_r,
        "relative_reflectance_reduction": (bare_r - ar_r) / bare_r,
        "bare_front_transmittance": bare_t,
        "ar_front_transmittance": ar_t,
        "max_corresponding_ray_coordinate_delta_mm": ray_coordinate_delta,
        "max_corresponding_ray_direction_delta": ray_direction_delta,
        "bare_mean_exit_ray_weight": float(np.mean(bare_trace["exit_intensity"])),
        "ar_mean_exit_ray_weight": float(np.mean(ar_trace["exit_intensity"])),
        "bare_psf_integrated_relative_energy": bare_image[
            "psf_integrated_absolute_relative_units"
        ],
        "ar_psf_integrated_relative_energy": ar_image[
            "psf_integrated_absolute_relative_units"
        ],
        "max_normalized_psf_shape_delta": _max_finite_difference(
            bare_image["psf_normalized"], ar_image["psf_normalized"]
        ),
        "max_normalized_mtf_delta": max(
            _max_finite_difference(
                bare_image["mtf_tangential"], ar_image["mtf_tangential"]
            ),
            _max_finite_difference(
                bare_image["mtf_sagittal"], ar_image["mtf_sagittal"]
            ),
        ),
    }
    checks = {
        "energy_conservation": metrics["max_energy_conservation_error"] < 1e-10,
        "cross_engine_rta_agreement": (
            metrics["max_pythinfilm_optiland_rta_difference"] < 1e-10
        ),
        "real_mgf2_reduces_center_reflectance": ar_r < bare_r,
        "real_mgf2_increases_center_transmittance": ar_t > bare_t,
        "real_mgf2_is_not_ideal_zero_reflection": ar_r > 1e-5,
        "ray_geometry_unchanged": ray_coordinate_delta < 1e-12,
        "ray_directions_unchanged": ray_direction_delta < 1e-12,
        "finite_outputs": all(
            np.all(np.isfinite(np.asarray(array)))
            for array in (
                bare_spot["x_mm"],
                ar_spot["x_mm"],
                bare_image["psf_absolute_relative_units"],
                ar_image["psf_absolute_relative_units"],
                bare_image["mtf_tangential"],
                ar_image["mtf_tangential"],
            )
        ),
        "native_2d_outputs": all(
            Path(str(artifacts[key])).is_file()
            for key in ("layout_uncoated", "layout_coated")
        ),
        "native_3d_outputs": all(
            artifacts.get(key) is not None and Path(str(artifacts[key])).is_file()
            for key in ("system3d_uncoated", "system3d_coated")
        ),
    }
    result = {
        "schema_version": "0.1.0-real-material-native-comparison",
        "scope": {
            "renderer": "Optiland native Matplotlib 2D and off-screen VTK 3D",
            "material_provider": "PyThinFilm real n/k CSV library",
            "three_js": "not used",
            "zemax": "deferred and not used",
        },
        "source": {
            "pythinfilm_project": str(PROJECT_ROOT),
            "optiland_project": str(optiland_root.resolve()),
            "optiland_commit": "17610805",
        },
        "design": design,
        "metrics": metrics,
        "checks": checks,
        "interpretation": (
            "Real MgF2 is not the exact geometric-mean index required for zero "
            "reflection on N-BK7. The quarter-wave layer still reduces Fresnel "
            "loss substantially, while coating-dependent pupil weights change "
            "energy more than normalized PSF or MTF shape."
        ),
        "spectrum": {
            "wavelength_nm": WAVELENGTHS_NM,
            "bare": bare_spectrum,
            "ar": ar_spectrum,
            "pythinfilm_reference_bare": py_bare,
            "pythinfilm_reference_ar": py_ar,
        },
        "aoi_scan": {
            "wavelength_nm": DESIGN_WAVELENGTH_NM,
            "angle_deg": ANGLES_DEG,
            "bare": bare_aoi,
            "ar": ar_aoi,
        },
        "ray_trace": {"bare": bare_trace, "ar": ar_trace},
        "spot": {"bare": bare_spot, "ar": ar_spot},
        "psf_mtf": {"bare": bare_image, "ar": ar_image},
        "artifacts": artifacts,
    }
    result_path = output_dir / "comparison_result.json"
    result_path.write_text(
        json.dumps(_json_ready(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not all(checks.values()):
        failed = ", ".join(key for key, passed in checks.items() if not passed)
        raise RuntimeError(f"real-material comparison validation failed: {failed}")
    return result_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--optiland-root",
        type=Path,
        default=PROJECT_ROOT.parent / "optiland",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home()
        / "thinfilm_outputs"
        / "optiland_real_material_ar_comparison",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(run_comparison(args.optiland_root, args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
