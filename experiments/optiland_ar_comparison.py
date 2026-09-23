r"""Native Optiland comparison of a bare lens and a PyThinFilm-designed AR lens.

The experiment intentionally stays outside the production ``thinfilm`` package.
It uses PyThinFilm to define and validate a quarter-wave AR layer, maps the same
layer into Optiland, and compares two otherwise identical imaging systems using
Optiland's native Matplotlib and VTK visualization paths.

Run with the isolated Optiland environment::

    ..\optiland\.venv\Scripts\python.exe experiments\optiland_ar_comparison.py
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
from matplotlib.colors import LogNorm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.optiland_poc import _json_ready, _load_optiland, _save_3d_png
from thinfilm.education import (
    LayerSpec,
    build_single_ar_layers,
    multilayer_rt_spectrum,
)


DESIGN_WAVELENGTH_NM = 550.0
N_AIR = 1.0
N_GLASS = 1.52
N_AR = float(np.sqrt(N_AIR * N_GLASS))


def _design_specs() -> tuple[list[LayerSpec], dict[str, Any]]:
    """Create the AR design through PyThinFilm's teaching-design functions."""
    layers = build_single_ar_layers(DESIGN_WAVELENGTH_NM, complex(N_AR))
    layer = layers[0]
    return layers, {
        "design": "single_layer_quarter_wave_ar",
        "source": "PyThinFilm thinfilm.education.build_single_ar_layers",
        "wavelength_nm": DESIGN_WAVELENGTH_NM,
        "incident_index": N_AIR,
        "substrate_index": N_GLASS,
        "layer_index": float(np.real(layer.n)),
        "layer_thickness_nm": float(layer.thickness_nm),
    }


def _make_front_coatings(api: dict[str, Any]) -> tuple[Any, Any, dict[str, Any]]:
    """Build bare-Fresnel and AR front-surface coatings."""
    _, design = _design_specs()
    air = api["IdealMaterial"](n=N_AIR)
    glass = api["IdealMaterial"](n=N_GLASS)
    ar_material = api["IdealMaterial"](n=N_AR)
    bare = api["ThinFilmCoating"](air, glass, layers=[])
    ar = api["ThinFilmCoating"](
        air,
        glass,
        layers=[(ar_material, design["layer_thickness_nm"], "PyThinFilm AR")],
    )
    return bare, ar, design


def _build_lens(api: dict[str, Any], front_coating: Any, name: str) -> Any:
    """Create the same singlet geometry with a selectable front coating."""
    air = api["IdealMaterial"](n=N_AIR)
    glass = api["IdealMaterial"](n=N_GLASS)
    rear_fresnel = api["ThinFilmCoating"](glass, air, layers=[])

    optic = api["Optic"](name=name)
    optic.surfaces.add(index=0, radius=np.inf, thickness=np.inf, material=air)
    optic.surfaces.add(
        index=1,
        radius=40.0,
        thickness=4.0,
        material=glass,
        is_stop=True,
        coating=front_coating,
    )
    optic.surfaces.add(
        index=2,
        radius=-40.0,
        thickness=37.0,
        material=air,
        coating=rear_fresnel,
    )
    optic.surfaces.add(index=3, material=air)
    optic.set_aperture(aperture_type="EPD", value=10.0)
    optic.fields.set_type(field_type="angle")
    optic.fields.add(y=0.0)
    optic.wavelengths.add(value=DESIGN_WAVELENGTH_NM / 1000.0, is_primary=True)
    optic.updater.set_polarization(api["PolarizationState"](is_polarized=False))
    return optic


def _stack_grid(stack: Any, wavelengths_nm: np.ndarray, angles_deg: np.ndarray) -> dict[str, Any]:
    """Evaluate s/p power coefficients over wavelength and AOI grids."""
    return {
        pol: stack.compute_rtRAT_nm_deg(wavelengths_nm, angles_deg, pol)
        for pol in ("s", "p")
    }


def _center_value(data: dict[str, Any], key: str, index: int) -> float:
    """Read one wavelength/angle cell from an Optiland TMM result."""
    return float(np.asarray(data[key])[index, 0])


def _trace_snapshot(optic: Any, api: dict[str, Any], wavelength_nm: float = DESIGN_WAVELENGTH_NM, field: tuple[float, float] = (0.0, 0.0)) -> dict[str, Any]:
    """Trace an identical pupil grid and copy all per-surface numerical data."""
    be = api["be"]
    rays = optic.trace(
        Hx=field[0],
        Hy=field[1],
        wavelength=wavelength_nm / 1000.0,
        num_rays=32,
        distribution="uniform",
    )
    return {
        "x": be.to_numpy(optic.surfaces.x).copy(),
        "y": be.to_numpy(optic.surfaces.y).copy(),
        "z": be.to_numpy(optic.surfaces.z).copy(),
        "L": be.to_numpy(optic.surfaces.L).copy(),
        "M": be.to_numpy(optic.surfaces.M).copy(),
        "N": be.to_numpy(optic.surfaces.N).copy(),
        "intensity_by_surface": be.to_numpy(optic.surfaces.intensity).copy(),
        "exit_intensity": be.to_numpy(rays.i).copy(),
    }


def _max_finite_difference(left: np.ndarray, right: np.ndarray) -> float:
    """Return maximum finite absolute difference between matching arrays."""
    difference = np.abs(np.asarray(left) - np.asarray(right))
    finite = np.isfinite(difference)
    return float(np.max(difference[finite])) if np.any(finite) else 0.0


def _raw_psf(psf: Any, api: dict[str, Any]) -> np.ndarray:
    """Recover a relative absolute-energy PSF before Optiland normalization."""
    be = api["be"]
    total = np.zeros((psf.grid_size, psf.grid_size), dtype=float)
    for pupil in psf.pupils:
        pupil_np = np.asarray(be.to_numpy(pupil))
        before = (psf.grid_size - pupil_np.shape[0]) // 2
        after = before + (psf.grid_size - pupil_np.shape[0]) % 2
        padded = np.pad(pupil_np, ((before, after), (before, after)))
        amplitude = np.fft.fftshift(np.fft.fft2(padded))
        total += np.abs(amplitude) ** 2
    return total


def _spot_data(
    optic: Any,
    api: dict[str, Any],
    wavelength_nm: float = DESIGN_WAVELENGTH_NM,
    field: tuple[float, float] = (0.0, 0.0),
) -> dict[str, np.ndarray]:
    """Calculate native Optiland spot coordinates and ray weights."""
    be = api["be"]
    analysis = api["SpotDiagram"](
        optic,
        fields=[field],
        wavelengths=[wavelength_nm / 1000.0],
        num_rings=8,
    )
    data = analysis.data[0][0]
    return {
        "x_mm": be.to_numpy(data.x),
        "y_mm": be.to_numpy(data.y),
        "intensity": be.to_numpy(data.intensity),
    }


def _psf_and_mtf(
    optic: Any,
    api: dict[str, Any],
    wavelength_nm: float = DESIGN_WAVELENGTH_NM,
    field: tuple[float, float] = (0.0, 0.0),
) -> dict[str, Any]:
    """Calculate native vectorial FFT PSF and MTF numerical arrays."""
    from optiland.mtf import FFTMTF
    from optiland.psf import FFTPSF

    be = api["be"]
    psf = FFTPSF(
        optic,
        field=field,
        wavelength=wavelength_nm / 1000.0,
        num_rays=32,
        grid_size=128,
    )
    raw = _raw_psf(psf, api)
    normalized = raw / max(float(np.max(raw)), np.finfo(float).tiny)

    mtf = FFTMTF(
        optic,
        fields=[field],
        wavelength=wavelength_nm / 1000.0,
        num_rays=32,
        grid_size=128,
    )
    return {
        "psf_native": be.to_numpy(psf.psf),
        "psf_normalized": normalized,
        "psf_absolute_relative_units": raw,
        "psf_peak_absolute_relative_units": float(np.max(raw)),
        "psf_integrated_absolute_relative_units": float(np.sum(raw)),
        "mtf_frequency_tangential_cycles_per_mm": be.to_numpy(mtf.freq_tang[0]),
        "mtf_frequency_sagittal_cycles_per_mm": be.to_numpy(mtf.freq_sag[0]),
        "mtf_tangential": be.to_numpy(mtf.mtf[0][0]),
        "mtf_sagittal": be.to_numpy(mtf.mtf[0][1]),
    }


def _save_layouts(
    bare_lens: Any, ar_lens: Any, output_dir: Path
) -> dict[str, str | None]:
    """Save native Optiland 2D and off-screen VTK 3D layouts."""
    artifacts: dict[str, str | None] = {}
    for key, optic in (("uncoated", bare_lens), ("coated", ar_lens)):
        path_2d = output_dir / f"layout_{key}.png"
        figure, _ = optic.draw(num_rays=7, show=False, figsize=(10, 4))
        figure.savefig(path_2d, dpi=170, bbox_inches="tight")
        plt.close(figure)
        artifacts[f"layout_{key}"] = str(path_2d)

        path_3d = output_dir / f"system3d_{key}.png"
        try:
            _save_3d_png(optic, path_3d)
            artifacts[f"system3d_{key}"] = str(path_3d)
        except Exception as exc:  # VTK depends on the local graphics driver.
            artifacts[f"system3d_{key}"] = None
            artifacts[f"system3d_{key}_error"] = f"{type(exc).__name__}: {exc}"
    return artifacts


def _plot_spectrum(
    wavelengths_nm: np.ndarray,
    bare: dict[str, Any],
    ar: dict[str, Any],
    output_path: Path,
) -> None:
    """Plot normal-incidence coating R/T spectra."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True, sharey=True)
    for axis, pol in zip(axes, ("s", "p"), strict=True):
        axis.plot(wavelengths_nm, np.asarray(bare[pol]["R"])[:, 0], label="Bare R")
        axis.plot(wavelengths_nm, np.asarray(ar[pol]["R"])[:, 0], label="AR R")
        axis.plot(
            wavelengths_nm,
            np.asarray(bare[pol]["T"])[:, 0],
            "--",
            label="Bare T",
        )
        axis.plot(
            wavelengths_nm,
            np.asarray(ar[pol]["T"])[:, 0],
            "--",
            label="AR T",
        )
        axis.axvline(DESIGN_WAVELENGTH_NM, color="0.35", linestyle=":")
        axis.set_title(f"{pol.upper()} polarization, AOI = 0°")
        axis.set_xlabel("Wavelength (nm)")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Power coefficient")
    axes[1].legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
    fig.suptitle("Bare Fresnel Interface vs PyThinFilm Quarter-Wave AR")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _plot_aoi(
    angles_deg: np.ndarray,
    bare: dict[str, Any],
    ar: dict[str, Any],
    output_path: Path,
) -> None:
    """Plot s/p AOI dependence at the design wavelength."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)
    for pol, color in (("s", "C0"), ("p", "C1")):
        axes[0].plot(
            angles_deg,
            np.asarray(bare[pol]["R"])[0, :],
            color=color,
            linestyle="--",
            label=f"Bare {pol.upper()}",
        )
        axes[0].plot(
            angles_deg,
            np.asarray(ar[pol]["R"])[0, :],
            color=color,
            label=f"AR {pol.upper()}",
        )
        axes[1].plot(
            angles_deg,
            np.asarray(bare[pol]["T"])[0, :],
            color=color,
            linestyle="--",
            label=f"Bare {pol.upper()}",
        )
        axes[1].plot(
            angles_deg,
            np.asarray(ar[pol]["T"])[0, :],
            color=color,
            label=f"AR {pol.upper()}",
        )
    axes[0].set_title("Reflectance")
    axes[1].set_title("Transmittance")
    for axis in axes:
        axis.set_xlabel("AOI (deg)")
        axis.grid(alpha=0.25)
        axis.legend()
    axes[0].set_ylabel("Power coefficient")
    fig.suptitle(f"AOI Response at {DESIGN_WAVELENGTH_NM:.0f} nm")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _plot_spot(
    bare: dict[str, np.ndarray], ar: dict[str, np.ndarray], output_path: Path
) -> None:
    """Plot unchanged geometry and changed per-ray weights side by side."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharex=True, sharey=True)
    all_intensity = np.concatenate((bare["intensity"], ar["intensity"]))
    vmin, vmax = float(np.min(all_intensity)), float(np.max(all_intensity))
    for axis, title, data in zip(
        axes,
        ("Bare Fresnel", "PyThinFilm AR"),
        (bare, ar),
        strict=True,
    ):
        scatter = axis.scatter(
            data["x_mm"],
            data["y_mm"],
            c=data["intensity"],
            s=11,
            vmin=vmin,
            vmax=vmax,
        )
        axis.set_title(title)
        axis.set_xlabel("Image X (mm)")
        axis.set_aspect("equal")
        axis.grid(alpha=0.2)
    axes[0].set_ylabel("Image Y (mm)")
    fig.colorbar(scatter, ax=axes, label="Ray weight", shrink=0.85)
    fig.suptitle("Spot Coordinates and Coating-Dependent Weights")
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _plot_psf_normalized(
    bare: np.ndarray, ar: np.ndarray, output_path: Path
) -> None:
    """Plot PSF shapes after independent peak normalization."""
    difference = ar - bare
    limit = max(float(np.max(np.abs(difference))), 1e-12)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    axes[0].imshow(bare, origin="lower", cmap="magma", vmin=0, vmax=1)
    axes[0].set_title("Bare, peak-normalized")
    axes[1].imshow(ar, origin="lower", cmap="magma", vmin=0, vmax=1)
    axes[1].set_title("AR, peak-normalized")
    image = axes[2].imshow(
        difference,
        origin="lower",
        cmap="coolwarm",
        vmin=-limit,
        vmax=limit,
    )
    axes[2].set_title("AR − bare")
    for axis in axes:
        axis.set_xlabel("Image sample")
        axis.set_ylabel("Image sample")
    fig.colorbar(image, ax=axes[2], shrink=0.8, label="Normalized difference")
    fig.suptitle("Normalized Vectorial FFT PSF: Shape Comparison")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _plot_psf_absolute(
    bare: np.ndarray,
    ar: np.ndarray,
    bare_power: float,
    ar_power: float,
    output_path: Path,
) -> None:
    """Plot relative absolute-energy PSFs with one shared color scale."""
    positive = np.concatenate((bare[bare > 0], ar[ar > 0]))
    vmax = float(max(np.max(bare), np.max(ar)))
    vmin = max(float(np.percentile(positive, 20)), vmax * 1e-8)
    norm = LogNorm(vmin=vmin, vmax=vmax)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.1), sharex=True, sharey=True)
    image = axes[0].imshow(bare, origin="lower", cmap="magma", norm=norm)
    axes[0].set_title(f"Bare\nΣPSF = {bare_power:.4g}")
    axes[1].imshow(ar, origin="lower", cmap="magma", norm=norm)
    axes[1].set_title(f"AR\nΣPSF = {ar_power:.4g}")
    for axis in axes:
        axis.set_xlabel("Image sample")
        axis.set_ylabel("Image sample")
    fig.colorbar(image, ax=axes, shrink=0.82, label="Relative absolute energy")
    fig.suptitle("Vectorial FFT PSF: Shared Absolute-Energy Scale")
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _plot_mtf(bare: dict[str, Any], ar: dict[str, Any], output_path: Path) -> None:
    """Plot native normalized MTF without requiring an improvement."""
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for label, data, linestyle in (("Bare", bare, "--"), ("AR", ar, "-")):
        ax.plot(
            data["mtf_frequency_tangential_cycles_per_mm"],
            data["mtf_tangential"],
            linestyle=linestyle,
            label=f"{label} tangential",
        )
        ax.plot(
            data["mtf_frequency_sagittal_cycles_per_mm"],
            data["mtf_sagittal"],
            linestyle=linestyle,
            label=f"{label} sagittal",
        )
    ax.set_xlabel("Spatial frequency (cycles/mm)")
    ax.set_ylabel("Normalized MTF")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend()
    ax.set_title("Native Optiland FFT MTF (Comparison Only)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def run_comparison(optiland_root: Path, output_dir: Path) -> Path:
    """Run the complete native Optiland AR comparison."""
    output_dir.mkdir(parents=True, exist_ok=True)
    api = _load_optiland(optiland_root)
    bare_coating, ar_coating, design = _make_front_coatings(api)
    bare_lens = _build_lens(api, bare_coating, "Bare Fresnel Singlet")
    ar_lens = _build_lens(api, ar_coating, "PyThinFilm AR Singlet")

    wavelengths_nm = np.linspace(400.0, 700.0, 151)
    angles_deg = np.linspace(0.0, 60.0, 121)
    zero_angle = np.asarray([0.0])
    design_wavelength = np.asarray([DESIGN_WAVELENGTH_NM])

    bare_spectrum = _stack_grid(bare_coating.stack, wavelengths_nm, zero_angle)
    ar_spectrum = _stack_grid(ar_coating.stack, wavelengths_nm, zero_angle)
    bare_aoi = _stack_grid(bare_coating.stack, design_wavelength, angles_deg)
    ar_aoi = _stack_grid(ar_coating.stack, design_wavelength, angles_deg)

    py_layers, _ = _design_specs()
    py_bare = {
        pol: multilayer_rt_spectrum(
            wavelengths_nm, [], N_AIR, N_GLASS, 0.0, pol
        )
        for pol in ("s", "p")
    }
    py_ar = {
        pol: multilayer_rt_spectrum(
            wavelengths_nm, py_layers, N_AIR, N_GLASS, 0.0, pol
        )
        for pol in ("s", "p")
    }

    center_index = int(np.argmin(np.abs(wavelengths_nm - DESIGN_WAVELENGTH_NM)))
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

    energy_errors = []
    for dataset in (bare_spectrum, ar_spectrum, bare_aoi, ar_aoi):
        for pol in ("s", "p"):
            total = (
                np.asarray(dataset[pol]["R"])
                + np.asarray(dataset[pol]["T"])
                + np.asarray(dataset[pol]["A"])
            )
            energy_errors.append(float(np.max(np.abs(total - 1.0))))

    cross_engine_errors = []
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
        "coating_spectrum": output_dir / "coating_spectrum.png",
        "coating_aoi_scan": output_dir / "coating_aoi_scan.png",
        "spot_comparison": output_dir / "spot_comparison.png",
        "psf_normalized_comparison": output_dir / "psf_normalized_comparison.png",
        "psf_absolute_comparison": output_dir / "psf_absolute_comparison.png",
        "mtf_comparison": output_dir / "mtf_comparison.png",
    }
    _plot_spectrum(wavelengths_nm, bare_spectrum, ar_spectrum, plot_paths["coating_spectrum"])
    _plot_aoi(angles_deg, bare_aoi, ar_aoi, plot_paths["coating_aoi_scan"])
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

    psf_shape_delta = _max_finite_difference(
        bare_image["psf_normalized"], ar_image["psf_normalized"]
    )
    mtf_delta = max(
        _max_finite_difference(
            bare_image["mtf_tangential"], ar_image["mtf_tangential"]
        ),
        _max_finite_difference(
            bare_image["mtf_sagittal"], ar_image["mtf_sagittal"]
        ),
    )

    metrics = {
        "max_energy_conservation_error": max(energy_errors),
        "max_pythinfilm_optiland_rta_difference": max(cross_engine_errors),
        "center_wavelength_nm": DESIGN_WAVELENGTH_NM,
        "bare_front_reflectance": bare_r,
        "ar_front_reflectance": ar_r,
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
        "max_normalized_psf_shape_delta": psf_shape_delta,
        "max_normalized_mtf_delta": mtf_delta,
    }
    checks = {
        "energy_conservation": metrics["max_energy_conservation_error"] < 1e-10,
        "cross_engine_rta_agreement": (
            metrics["max_pythinfilm_optiland_rta_difference"] < 1e-10
        ),
        "ar_reduces_center_reflectance": ar_r < bare_r,
        "ar_increases_center_transmittance": ar_t > bare_t,
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
            Path(artifacts[key]).is_file()
            for key in ("layout_uncoated", "layout_coated")
        ),
        "native_3d_outputs": all(
            artifacts.get(key) is not None and Path(str(artifacts[key])).is_file()
            for key in ("system3d_uncoated", "system3d_coated")
        ),
    }

    result = {
        "schema_version": "0.1.0-native-comparison",
        "scope": {
            "renderer": "Optiland native Matplotlib 2D and off-screen VTK 3D",
            "three_js": "not used",
            "zemax": "deferred and not used",
        },
        "source": {
            "pythinfilm_project": str(Path(__file__).resolve().parents[1]),
            "optiland_project": str(optiland_root.resolve()),
            "optiland_commit": "17610805",
        },
        "design": design,
        "metrics": metrics,
        "checks": checks,
        "interpretation": (
            "The coating changes power and pupil weighting but not refractive ray "
            "geometry. Spot coordinates and normalized PSF/MTF may therefore be "
            "nearly unchanged; this is a valid physical result, not a failed AR design."
        ),
        "spectrum": {
            "wavelength_nm": wavelengths_nm,
            "bare": bare_spectrum,
            "ar": ar_spectrum,
            "pythinfilm_reference_bare": py_bare,
            "pythinfilm_reference_ar": py_ar,
        },
        "aoi_scan": {
            "wavelength_nm": DESIGN_WAVELENGTH_NM,
            "angle_deg": angles_deg,
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
        raise RuntimeError(f"AR comparison validation failed: {failed}")
    return result_path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--optiland-root",
        type=Path,
        default=project_root.parent / "optiland",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "thinfilm_outputs" / "optiland_ar_comparison",
    )
    return parser.parse_args()


def main() -> int:
    """Run the comparison CLI."""
    args = parse_args()
    print(run_comparison(args.optiland_root, args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
