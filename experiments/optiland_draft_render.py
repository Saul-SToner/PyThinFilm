"""Render one current PyThinFilm free-design draft through Optiland."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.optiland_ar_comparison import _psf_and_mtf, _spot_data, _trace_snapshot
from experiments.optiland_poc import _json_ready, _save_3d_png
from experiments.optiland_sampling import sample_spectrum
from thinfilm.materials import load_real_material
from thinfilm.optiland_integration import (
    CoatingLayerInput,
    CoatingStackInput,
    OptilandBridge,
    make_teaching_system_input,
)


def _draft_material_ids(draft: dict[str, Any]) -> list[str]:
    return [
        str(draft.get("incident_material_id", "Air")),
        str(draft.get("substrate_material_id", "N-BK7")),
        *[
            str(layer["material_id"])
            for layer in draft.get("layers", [])
            if layer.get("enabled", True)
        ],
    ]


def _plot_spot(spot: dict[str, np.ndarray], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    ax.scatter(spot["x_mm"], spot["y_mm"], c=spot["intensity"], s=13, cmap="viridis")
    ax.set_xlabel("像面 X（mm）")
    ax.set_ylabel("像面 Y（mm）")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.set_title("Optiland 光斑图")
    fig.tight_layout()
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _plot_psf(image: dict[str, Any], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    ax.imshow(image["psf_normalized"], origin="lower", cmap="magma", vmin=0, vmax=1)
    ax.set_xlabel("像面采样")
    ax.set_ylabel("像面采样")
    ax.set_title("Optiland 归一化 FFT PSF")
    fig.tight_layout()
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _plot_mtf(image: dict[str, Any], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(image["mtf_frequency_tangential_cycles_per_mm"], image["mtf_tangential"], label="子午方向")
    ax.plot(image["mtf_frequency_sagittal_cycles_per_mm"], image["mtf_sagittal"], label="弧矢方向")
    ax.set_xlabel("空间频率（cycles/mm）")
    ax.set_ylabel("归一化 MTF")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend()
    ax.set_title("Optiland FFT MTF")
    fig.tight_layout()
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _unpolarized_front_transmittance(bridge: OptilandBridge, stack: CoatingStackInput, wavelength_nm: float) -> float:
    """Evaluate the actual Optiland coating transmittance at normal incidence."""
    coating = bridge.build_coating(stack)
    values = []
    for polarization in ("s", "p"):
        result = coating.stack.compute_rtRAT_nm_deg(
            np.asarray([wavelength_nm], dtype=float),
            np.asarray([0.0], dtype=float),
            polarization,
        )
        values.append(float(np.asarray(result["T"], dtype=float).reshape(-1)[0]))
    return float(np.mean(values))


def _plot_energy_comparison(
    bare_trace: dict[str, Any],
    coated_trace: dict[str, Any],
    bare_front_transmittance: float,
    coated_front_transmittance: float,
    output: Path,
) -> dict[str, float]:
    """Plot Optiland coating transmission and final traced ray weights."""
    bare_exit = float(np.mean(np.asarray(bare_trace["exit_intensity"], dtype=float)))
    coated_exit = float(np.mean(np.asarray(coated_trace["exit_intensity"], dtype=float)))
    # Optiland updates polarized ray intensity only after the full trace;
    # surface snapshots retain the pre-update weights. Use actual endpoints.
    bare_relative = np.asarray([1.0, bare_exit])
    coated_relative = np.asarray([1.0, coated_exit])

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    surface_index = np.arange(len(bare_relative))
    ax.plot(surface_index, bare_relative, "o--", color="#64748b", label="裸表面")
    ax.plot(surface_index, coated_relative, "o-", color="#0f766e", linewidth=2.2, label="当前镀膜")
    ax.set_xlabel("能量检查点")
    ax.set_ylabel("相对平均光线权重")
    ax.set_ylim(bottom=0)
    ax.set_xticks(surface_index, ['入射', '接收面'])
    ax.grid(alpha=0.22)
    ax.legend(loc="best")
    ax.set_title("Optiland 系统能量传递")
    fig.tight_layout()
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)

    return {
        "bare_relative_throughput": bare_exit,
        "coated_relative_throughput": coated_exit,
        "throughput_gain": coated_exit - bare_exit,
    }


def _weighted_irradiance_histogram(
    spot: dict[str, np.ndarray],
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    target_mean_weight: float,
) -> np.ndarray:
    x = np.asarray(spot["x_mm"], dtype=float)
    y = np.asarray(spot["y_mm"], dtype=float)
    weight = np.asarray(spot["intensity"], dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weight) & (weight >= 0)
    if np.any(valid):
        current_mean = float(np.mean(weight[valid]))
        if current_mean > 0:
            weight = weight * (target_mean_weight / current_mean)
    histogram, _, _ = np.histogram2d(x[valid], y[valid], bins=(x_edges, y_edges), weights=weight[valid])
    return histogram.T


def _plot_detector_comparison(
    bare_spot: dict[str, np.ndarray],
    coated_spot: dict[str, np.ndarray],
    bare_mean_exit_weight: float,
    coated_mean_exit_weight: float,
    output: Path,
) -> dict[str, float]:
    """Plot a truthful relative irradiance map from Optiland image-plane rays.

    This is a weighted sequential-ray histogram, not an absolute W/mm² NSQ
    detector result.  The distinction is carried into the JSON contract/UI.
    """
    all_x = np.concatenate((np.asarray(bare_spot["x_mm"]), np.asarray(coated_spot["x_mm"]))).astype(float)
    all_y = np.concatenate((np.asarray(bare_spot["y_mm"]), np.asarray(coated_spot["y_mm"]))).astype(float)
    finite_x, finite_y = all_x[np.isfinite(all_x)], all_y[np.isfinite(all_y)]
    x_min, x_max = (float(np.min(finite_x)), float(np.max(finite_x))) if finite_x.size else (-1.0, 1.0)
    y_min, y_max = (float(np.min(finite_y)), float(np.max(finite_y))) if finite_y.size else (-1.0, 1.0)
    x_pad = max((x_max - x_min) * 0.06, 1e-6)
    y_pad = max((y_max - y_min) * 0.06, 1e-6)
    x_edges = np.linspace(x_min - x_pad, x_max + x_pad, 49)
    y_edges = np.linspace(y_min - y_pad, y_max + y_pad, 49)
    bare_map = _weighted_irradiance_histogram(bare_spot, x_edges, y_edges, bare_mean_exit_weight)
    coated_map = _weighted_irradiance_histogram(coated_spot, x_edges, y_edges, coated_mean_exit_weight)
    vmax = max(float(np.max(bare_map)), float(np.max(coated_map)), 1e-15)

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.1), sharex=True, sharey=True)
    extent = [x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]]
    for ax, image_data, title in zip(axes, (bare_map, coated_map), ("裸表面", "当前镀膜")):
        image = ax.imshow(image_data, origin="lower", extent=extent, cmap="magma", vmin=0, vmax=vmax, aspect="equal")
        ax.set_title(title)
        ax.set_xlabel("像面 X（mm）")
    axes[0].set_ylabel("像面 Y（mm）")
    colorbar = fig.colorbar(image, ax=axes, fraction=0.035, pad=0.04)
    colorbar.set_label("相对辐照度")
    fig.suptitle("Optiland 像面探测器对照")
    fig.subplots_adjust(left=0.08, right=0.91, bottom=0.14, top=0.84, wspace=0.16)
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)

    bare_total = float(np.sum(bare_map))
    coated_total = float(np.sum(coated_map))
    return {
        "bare_detector_relative_energy": bare_total,
        "coated_detector_relative_energy": coated_total,
        "detector_relative_energy_gain": coated_total - bare_total,
        "coated_detector_peak_relative_irradiance": float(np.max(coated_map)),
    }


def _stack_spectrum(stack: Any, wavelengths_nm: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return unpolarized R/T/A from an Optiland ThinFilmStack."""
    values: dict[str, list[np.ndarray]] = {"R": [], "T": [], "A": []}
    angles = np.asarray([0.0], dtype=float)
    for polarization in ("s", "p"):
        result = stack.compute_rtRAT_nm_deg(wavelengths_nm, angles, polarization)
        for key in values:
            values[key].append(np.asarray(result[key], dtype=float).reshape(-1))
    return tuple(np.mean(np.stack(values[key]), axis=0) for key in ("R", "T", "A"))


def _build_nsq_lens_scene(api: dict[str, Any], reflectance: float, transmittance: float, wavelength_um: float) -> Any:
    """Create a reproducible NSQ singlet scene using the current coating R/T."""
    nsq = importlib.import_module("optiland.nonsequential")
    coatings = importlib.import_module("optiland.coatings")
    coordinate_system = importlib.import_module("optiland.coordinate_system")
    scene = nsq.NSQScene()
    spectrum = nsq.Spectrum.monochromatic(wavelength_um)
    scene.add_source(
        "光源",
        coordinate_system.CoordinateSystem(z=-20.0),
        nsq.CollimatedSourceConfig(spectrum=spectrum, total_flux=1.0, aperture_radius=5.0),
    )
    scene.add_lens(
        "镜片",
        coordinate_system.CoordinateSystem(z=0.0),
        nsq.LensConfig(
            r1=40.0,
            r2=-40.0,
            thickness=4.0,
            material="N-BK7",
            front_aperture_radius=8.0,
            front=nsq.SurfaceConfig(
                coating=coatings.SimpleCoating(
                    reflectance=float(np.clip(reflectance, 0.0, 1.0)),
                    transmittance=float(np.clip(transmittance, 0.0, 1.0)),
                )
            ),
        ),
    )
    scene.add_detector(
        "像面",
        coordinate_system.CoordinateSystem(z=41.0),
        nsq.IrradianceDetectorConfig(width=12.0, height=12.0, num_pixels_x=96, num_pixels_y=96),
    )
    return scene


def _trace_nsq_ghost(api: dict[str, Any], reflectance: float, transmittance: float, wavelength_um: float) -> dict[str, Any]:
    """Separate direct and multi-bounce detector flux using matched NSQ traces."""
    scene = _build_nsq_lens_scene(api, reflectance, transmittance, wavelength_um)
    direct = scene.trace(num_rays=120_000, max_depth=3, seed=2026)
    full = scene.trace(num_rays=120_000, max_depth=10, seed=2026, record_paths=1200)
    direct_detector = direct.detectors["像面"]
    full_detector = full.detectors["像面"]
    direct_map = np.asarray(direct_detector.irradiance, dtype=float)
    full_map = np.asarray(full_detector.irradiance, dtype=float)
    ghost_map = np.maximum(full_map - direct_map, 0.0)
    ghost_flux = max(float(full_detector.total_flux - direct_detector.total_flux), 0.0)
    return {
        "direct_flux": float(direct_detector.total_flux),
        "full_flux": float(full_detector.total_flux),
        "ghost_flux": ghost_flux,
        "ghost_fraction": ghost_flux / max(float(full_detector.total_flux), 1e-15),
        "ghost_map": ghost_map,
        "flux_conservation_error": float(full.flux_conservation_error),
        "recorded_path_events": int(len(full.ray_paths["events"])) if full.ray_paths else 0,
    }


def _plot_ghost_comparison(bare: dict[str, Any], coated: dict[str, Any], output: Path) -> dict[str, float]:
    vmax = max(float(np.max(bare["ghost_map"])), float(np.max(coated["ghost_map"])), 1e-15)
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.5), layout="constrained")
    for ax, result, title in zip(axes[:2], (bare, coated), ("裸表面鬼像", "当前镀膜鬼像")):
        image = ax.imshow(result["ghost_map"], origin="lower", cmap="inferno", vmin=0, vmax=vmax)
        ax.set_title(title)
        ax.set_xlabel("探测器像素 X")
        ax.set_ylabel("探测器像素 Y")
    colorbar = fig.colorbar(image, ax=axes[:2], fraction=0.035, pad=0.03)
    colorbar.set_label("W/mm²", fontsize=8)
    bars = axes[2].bar(["裸表面", "当前镀膜"], [bare["ghost_fraction"] * 100, coated["ghost_fraction"] * 100], color=["#64748b", "#0f766e"])
    axes[2].set_ylabel("功率占比（%）")
    axes[2].set_title("多次反射鬼像功率")
    axes[2].grid(axis="y", alpha=0.2)
    for bar in bars:
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():.4f}%", ha="center", va="bottom", fontsize=8)
    fig.suptitle("Optiland NSQ 鬼像与杂散光对照")
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return {
        "bare_ghost_power_fraction": float(bare["ghost_fraction"]),
        "coated_ghost_power_fraction": float(coated["ghost_fraction"]),
        "ghost_suppression_ratio": (1.0 - float(coated["ghost_fraction"]) / float(bare["ghost_fraction"])) if bare["ghost_flux"] > 3 * bare.get("ghost_flux_standard_error", 0) else None,
        "nsq_flux_conservation_error": max(float(bare["flux_conservation_error"]), float(coated["flux_conservation_error"])),
    }


def _trace_spectral_detector(wavelengths_nm: np.ndarray, response: np.ndarray) -> dict[str, Any]:
    nsq = importlib.import_module("optiland.nonsequential")
    coordinate_system = importlib.import_module("optiland.coordinate_system")
    scene = nsq.NSQScene()
    quadrature = np.ones(len(response))
    quadrature[[0, -1]] = 0.5
    mean_response = max(float(np.sum(response * quadrature) / quadrature.sum()), 1e-12)
    scene.add_source(
        "宽带光源",
        coordinate_system.CoordinateSystem(z=-10.0),
        nsq.CollimatedSourceConfig(
            spectrum=nsq.Spectrum(wavelengths=wavelengths_nm / 1000.0, weights=np.maximum(response * quadrature, 1e-12)),
            total_flux=mean_response,
            aperture_radius=2.0,
        ),
    )
    scene.add_detector(
        "光谱探测器",
        coordinate_system.CoordinateSystem(z=10.0),
        nsq.SpectralDetectorConfig(
            width=8.0,
            height=8.0,
            num_pixels_x=16,
            num_pixels_y=16,
            wl_min=float(wavelengths_nm.min() / 1000.0 - 0.005),
            wl_max=float(wavelengths_nm.max() / 1000.0 + 0.005),
            num_bins=min(len(wavelengths_nm), 161),
            splat="bilinear",
        ),
    )
    result = scene.trace(num_rays=160_000, max_depth=3, seed=2026)
    detector = result.detectors["光谱探测器"]
    pixel_area = (8.0 / 16) * (8.0 / 16)
    spectral_flux = np.asarray(detector.irradiance, dtype=float).sum(axis=(0, 1)) * pixel_area
    return {
        "wavelengths_nm": np.asarray(detector.wavelengths, dtype=float) * 1000.0,
        "spectral_flux": spectral_flux,
        "total_flux": float(detector.total_flux),
        "flux_conservation_error": float(result.flux_conservation_error),
    }


def _color_metrics(wavelengths_nm: np.ndarray, response: np.ndarray) -> dict[str, Any]:
    color_core = importlib.import_module("optiland.colorimetry.core")
    xyz = tuple(float(value) for value in color_core.spectrum_to_xyz(wavelengths_nm.tolist(), response.tolist()))
    xyy = tuple(float(np.asarray(value)) for value in color_core.xyz_to_xyY(*xyz))
    srgb = tuple(int(np.asarray(value)) for value in color_core.xyz_to_srgb(*xyz))
    return {"xyz": xyz, "xyY": xyy, "srgb": srgb}


def _plot_spectrum_color(
    wavelengths_nm: np.ndarray,
    bare_t: np.ndarray,
    coated_t: np.ndarray,
    bare_detector: dict[str, Any],
    coated_detector: dict[str, Any],
    bare_color: dict[str, Any] | None,
    coated_color: dict[str, Any] | None,
    color_unavailable_reason: str | None,
    output: Path,
) -> dict[str, float]:
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.8))
    axes[0].plot(wavelengths_nm, bare_t, "--", color="#64748b", label="裸表面 T(λ)")
    axes[0].plot(wavelengths_nm, coated_t, color="#0f766e", linewidth=2.0, label="当前镀膜 T(λ)")
    axes[0].set_xlabel("波长（nm）")
    axes[0].set_ylabel("透射率")
    axes[0].set_ylim(0, 1.03)
    axes[0].set_title("膜系光谱响应")
    axes[0].grid(alpha=0.2)
    axes[0].legend(fontsize=8)

    for detector, color, label, linestyle in ((bare_detector, "#64748b", "裸表面", "--"), (coated_detector, "#0f766e", "当前镀膜", "-")):
        flux = np.asarray(detector["spectral_flux"], dtype=float)
        axes[1].plot(detector["wavelengths_nm"], flux / max(float(np.max(flux)), 1e-15), linestyle, color=color, label=label)
    axes[1].set_xlabel("波长（nm）")
    axes[1].set_ylabel("归一化探测器光谱")
    axes[1].set_title("Optiland SpectralDetector")
    axes[1].grid(alpha=0.2)
    axes[1].legend(fontsize=8)

    axes[2].set_xlim(0, 1)
    axes[2].set_ylim(0, 1)
    axes[2].axis("off")
    if bare_color is not None and coated_color is not None:
        for y, label, data in ((0.64, "裸表面", bare_color), (0.24, "当前镀膜", coated_color)):
            rgb = np.asarray(data["srgb"], dtype=float) / 255.0
            axes[2].add_patch(plt.Rectangle((0.05, y), 0.28, 0.22, color=rgb, ec="#334155"))
            x, y_chroma, Y = data["xyY"]
            axes[2].text(0.39, y + 0.16, label, fontweight="bold", va="center")
            axes[2].text(0.39, y + 0.07, f"CIE xy=({x:.4f}, {y_chroma:.4f})\nsRGB={tuple(data['srgb'])}", fontsize=8, va="center")
        axes[2].set_title("CIE 1931 与 sRGB")
    else:
        axes[2].text(0.5, 0.56, "颜色暂不可计算", ha="center", va="center", fontsize=12, fontweight="bold")
        axes[2].text(0.5, 0.38, color_unavailable_reason or "材料光谱范围不足", ha="center", va="center", fontsize=8, color="#64748b", wrap=True)
        axes[2].set_title("颜色计算状态")
    fig.suptitle("Optiland 光谱与颜色响应")
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.16, top=0.80, wspace=0.34)
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return {
        "bare_spectral_detector_flux": float(bare_detector["total_flux"]),
        "coated_spectral_detector_flux": float(coated_detector["total_flux"]),
        "spectral_detector_gain": float(coated_detector["total_flux"] - bare_detector["total_flux"]),
        "spectral_flux_conservation_error": max(float(bare_detector["flux_conservation_error"]), float(coated_detector["flux_conservation_error"])),
    }


def run_render(optiland_root: Path, output_dir: Path, draft_path: Path) -> Path:
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    materials = _draft_material_ids(draft)
    wavelength_um = float(draft.get("probe_wavelength_nm", 550.0)) / 1000.0

    layers = tuple(
        CoatingLayerInput(
            material_id=str(layer["material_id"]),
            thickness_nm=float(layer["thickness_nm"]),
            label=str(layer.get("material_id", "layer")),
        )
        for layer in draft.get("layers", [])
        if layer.get("enabled", True)
    )
    front_stack = CoatingStackInput(
        incident_material_id=str(draft.get("incident_material_id", "Air")),
        substrate_material_id=str(draft.get("substrate_material_id", "N-BK7")),
        layers=layers,
    )
    bridge = OptilandBridge(optiland_root)
    template = str(draft.get("system_template", "single_lens_imaging"))
    from experiments.optiland_engineering_nsq import render_branch_result, trace_matched_ghost
    if template in {'folded_reflector','laser_expander','dbr_laser_cavity','dual_path_beamsplitter'}:
        return render_branch_result(bridge,front_stack,draft,output_dir)
    spec = make_teaching_system_input(
        template=template,
        name="Current PyThinFilm Draft",
        incident_material_id=front_stack.incident_material_id,
        glass_material_id=front_stack.substrate_material_id,
        front_coating=front_stack,
        wavelength_um=wavelength_um,
    )
    optic = bridge.build_system(spec)
    bare_stack = CoatingStackInput(
        incident_material_id=front_stack.incident_material_id,
        substrate_material_id=front_stack.substrate_material_id,
        layers=(),
    )
    bare_spec = make_teaching_system_input(
        template=template,
        name="Bare-surface Reference",
        incident_material_id=bare_stack.incident_material_id,
        glass_material_id=bare_stack.substrate_material_id,
        front_coating=bare_stack,
        wavelength_um=wavelength_um,
    )
    bare_optic = bridge.build_system(bare_spec)

    # Fix the same paraxial image plane for both comparisons. Windows have
    # no focusing power and retain their specified detector distance.
    imaging = any(surface.radius_mm is not None for surface in spec.surfaces)
    if imaging:
        if front_stack.incident_material_id == front_stack.substrate_material_id:
            raise ValueError('成像基线需要有折射能力的镜片材料，当前基底与入射介质相同。')
        bare_optic.updater.image_solve()
        optic.updater.image_solve()
    analysis_field = (0.0, 1.0) if spec.field_y_deg else (0.0, 0.0)

    output_dir.mkdir(parents=True, exist_ok=True)
    layout_path = output_dir / "layout_system.png"
    figure, _ = optic.draw(num_rays=7, show=False, figsize=(10, 4))
    figure.savefig(layout_path, dpi=170, bbox_inches="tight")
    plt.close(figure)
    system3d_path = output_dir / "system3d_system.png"
    _save_3d_png(optic, system3d_path)
    spot = _spot_data(optic, bridge.api, wavelength_um * 1000.0, analysis_field)
    bare_spot = _spot_data(bare_optic, bridge.api, wavelength_um * 1000.0, analysis_field)
    coated_trace = _trace_snapshot(optic, bridge.api, wavelength_um * 1000.0, analysis_field)
    bare_trace = _trace_snapshot(bare_optic, bridge.api, wavelength_um * 1000.0, analysis_field)
    bare_front_transmittance = _unpolarized_front_transmittance(bridge, bare_stack, wavelength_um * 1000.0)
    coated_front_transmittance = _unpolarized_front_transmittance(bridge, front_stack, wavelength_um * 1000.0)
    bare_mean_exit_weight = float(np.mean(np.asarray(bare_trace["exit_intensity"], dtype=float)))
    coated_mean_exit_weight = float(np.mean(np.asarray(coated_trace["exit_intensity"], dtype=float)))
    energy_path = output_dir / "energy_system.png"
    detector_path = output_dir / "detector_system.png"
    energy_metrics = _plot_energy_comparison(
        bare_trace,
        coated_trace,
        bare_front_transmittance,
        coated_front_transmittance,
        energy_path,
    )
    detector_metrics = _plot_detector_comparison(
        bare_spot,
        spot,
        bare_mean_exit_weight,
        coated_mean_exit_weight,
        detector_path,
    )
    material_datasets = [load_real_material(material) for material in dict.fromkeys(materials)]
    requested_spectrum = draft.get('spectrum', {'start_nm': 380.0, 'stop_nm': 780.0, 'points': 351})
    visible_start_nm = max(float(requested_spectrum['start_nm']), *(dataset.lambda_min_um * 1000.0 for dataset in material_datasets))
    visible_stop_nm = min(float(requested_spectrum['stop_nm']), *(dataset.lambda_max_um * 1000.0 for dataset in material_datasets))
    if visible_start_nm >= visible_stop_nm:
        raise ValueError(
            f"当前膜系材料没有共同可见光范围：{visible_start_nm:.1f}-{visible_stop_nm:.1f} nm"
        )
    spectral_start_nm = visible_start_nm
    spectral_stop_nm = visible_stop_nm
    bare_coating = bridge.build_coating(bare_stack)
    coated_coating = bridge.build_coating(front_stack)
    visible_wavelengths_nm, sampled, sampling = sample_spectrum(
        lambda wl: (*_stack_spectrum(bare_coating.stack, wl), *_stack_spectrum(coated_coating.stack, wl)),
        spectral_start_nm, spectral_stop_nm, requested_spectrum.get('points', 351))
    bare_r, bare_t, bare_a, coated_r, coated_t, coated_a = sampled
    probe_bare_r, probe_bare_t, _ = _stack_spectrum(bare_coating.stack, np.asarray([wavelength_um * 1000.0]))
    probe_coated_r, probe_coated_t, _ = _stack_spectrum(coated_coating.stack, np.asarray([wavelength_um * 1000.0]))

    ghost_path = output_dir / "ghost_stray_system.png"
    bare_ghost = {}; coated_ghost = {}; ghost_metrics = {}; ghost_error = None
    if imaging:
        try:
            bare_ghost = trace_matched_ghost(bridge,bare_spec,bare_optic,wavelength_um*1000)
            coated_ghost = trace_matched_ghost(bridge,spec,optic,wavelength_um*1000)
            ghost_metrics = _plot_ghost_comparison(bare_ghost, coated_ghost, ghost_path)
        except (ValueError, RuntimeError) as exc:
            ghost_error = str(exc)

    bare_spectral_detector = _trace_spectral_detector(visible_wavelengths_nm, bare_t)
    coated_spectral_detector = _trace_spectral_detector(visible_wavelengths_nm, coated_t)
    color_available = spectral_start_nm <= 380.0 and spectral_stop_nm >= 780.0
    color_unavailable_reason = None
    if color_available:
        color_wl = np.linspace(380, 780, 401)
        bare_color = _color_metrics(color_wl, _stack_spectrum(bare_coating.stack, color_wl)[1])
        coated_color = _color_metrics(color_wl, _stack_spectrum(coated_coating.stack, color_wl)[1])
    else:
        bare_color = None
        coated_color = None
        color_unavailable_reason = (
            f"当前材料共同有效范围为 {spectral_start_nm:.0f}–{spectral_stop_nm:.0f} nm；"
            "CIE 1931 计算要求完整覆盖 380–780 nm。"
        )
    spectrum_color_path = output_dir / "spectrum_color_system.png"
    spectral_metrics = _plot_spectrum_color(
        visible_wavelengths_nm,
        bare_t,
        coated_t,
        bare_spectral_detector,
        coated_spectral_detector,
        bare_color,
        coated_color,
        color_unavailable_reason,
        spectrum_color_path,
    )
    image = _psf_and_mtf(optic, bridge.api, wavelength_um * 1000.0, analysis_field)
    spot_path = output_dir / "spot_system.png"
    psf_path = output_dir / "psf_system.png"
    mtf_path = output_dir / "mtf_system.png"
    _plot_spot(spot, spot_path)
    _plot_psf(image, psf_path)
    _plot_mtf(image, mtf_path)
    artifacts = {
        "layout_system": str(layout_path),
        "system3d_system": str(system3d_path),
        "spot_system": str(spot_path),
        "psf_system": str(psf_path),
        "mtf_system": str(mtf_path),
        "energy_system": str(energy_path),
        "detector_system": str(detector_path),
        "ghost_stray_system": str(ghost_path),
        "spectrum_color_system": str(spectrum_color_path),
    }
    # Only publish successfully traced geometry-matched ghost results.
    if not ghost_metrics:
        artifacts.pop('ghost_stray_system')
    if not imaging:
        for key in ('spot_system', 'psf_system', 'mtf_system'):
            artifacts.pop(key)
    result = {
        "schema_version": "0.1.0-live-draft-optiland",
        "draft": draft,
        "system_template": template,
        "sampling": sampling,
        "analysis_conditions": {'wavelength_nm': wavelength_um * 1000.0, 'field_deg': spec.field_y_deg, 'normalized_field': analysis_field, 'image_plane': 'paraxial' if imaging else 'fixed_window_detector', 'coated_surface_indices': [i for i,s in enumerate(spec.surfaces) if s.coating and s.coating.layers]},
        "spectrum": {'wavelength_nm': visible_wavelengths_nm, 'bare_R': bare_r, 'bare_T': bare_t, 'coated_R': coated_r, 'coated_T': coated_t},
        "energy_residue": float(max(np.max(np.abs(bare_r+bare_t+bare_a-1)), np.max(np.abs(coated_r+coated_t+coated_a-1)))),
        "system_family": (
            "imaging" if template in {"single_lens_imaging", "multi_element_imaging", "complex_camera_lens", "phone_camera_module", "wide_angle_multi_element", "wide_field_camera", "photographic_lens", "camera_lens_coverglass", "dual_band_imager", "dispersive_lens", "wide_angle_window", "dual_path_beamsplitter"}
            else "spectral" if template in {"spectral_camera", "multispectral_imager", "dual_channel_spectral_imager", "spectrometer", "high_resolution_spectrometer", "sensor_prefilter", "wdm_receiver", "solar_cell_receiver", "low_e_window"}
            else "reflector" if template in {"folded_reflector", "laser_expander", "dbr_laser_cavity"}
            else "interface" if template in {"prism_coupled_tamm", "prism_coupled_tamm_scan", "tamm_absorption_probe", "polarized_phase_screen", "prism_coupled_tamm_window", "phase_interferometer"}
            else "thermal" if template in {"radiative_cooling_emitter", "photothermal_receiver", "photothermal_parameter_scan"}
            else "grating" if template == "grating_waveguide_coupler"
            else "baseline"
        ),
        "metrics": {
            "center_wavelength_nm": wavelength_um * 1000.0,
            "layer_count": len(layers),
            "psf_integrated_relative_energy": image["psf_integrated_absolute_relative_units"],
            **energy_metrics,
            **detector_metrics,
            **ghost_metrics,
            **spectral_metrics,
        },
        "analysis_groups": {
            "energy": {
                "ready": True,
                "source": "Optiland sequential per-surface ray weights",
                "units": "relative ray weight",
            },
            "detector": {
                "ready": True,
                "source": "Optiland weighted image-plane ray histogram",
                "units": "relative irradiance",
            },
            "ghost_stray": {
                "ready": bool(ghost_metrics),
                "reason": ghost_error,
                "source": "Optiland NSQ surfaces from the focused sequential system; unpolarized angular-bin coating",
                "units": "W/mm² and power fraction",
            },
            "spectrum_color": {
                "ready": True,
                "source": "Optiland SpectralDetector and CIE 1931 colorimetry driven by the current stack T(λ)",
                "units": "spectral flux, CIE XYZ/xyY and sRGB",
            },
        },
        "ghost_stray": {
            "probe_wavelength_nm": wavelength_um * 1000.0,
            "model_scope": "当前已调焦镜头逐面匹配；无偏振、单波长、0.5° 角度分箱；按实际反射事件分类鬼像，报告蒙特卡洛误差。",
            "bare": {key: value for key, value in bare_ghost.items() if key != "ghost_map"},
            "coated": {key: value for key, value in coated_ghost.items() if key != "ghost_map"},
        },
        "spectrum_color": {
            "wavelength_range_nm": [float(visible_wavelengths_nm[0]), float(visible_wavelengths_nm[-1])],
            "model_scope": "current stack T(λ) → Optiland SpectralDetector → CIE 1931 / sRGB",
            "color_available": color_available,
            "color_unavailable_reason": color_unavailable_reason,
            "bare": bare_color or {},
            "coated": coated_color or {},
        },
        "artifacts": artifacts,
        "spot": {"ray_count": int(len(spot["x_mm"]))},
        "psf_mtf": {
            "psf_shape": list(image["psf_normalized"].shape),
            "mtf_samples": int(len(image["mtf_tangential"])),
        },
        "material_sources": [
            {
                "material_id": material,
                "source": load_real_material(material).source,
            }
            for material in dict.fromkeys(materials)
        ],
        "interpretation": f"Optiland 当前使用 {template} 系统模板，由自由膜系草稿实时重建；改变材料、层序或厚度后，2D/3D 与系统级指标随下一次防抖计算更新。",
    }
    result_path = output_dir / "comparison_result.json"
    result_path.write_text(json.dumps(_json_ready(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return result_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--optiland-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--draft-json", type=Path, required=True)
    args = parser.parse_args()
    print(run_render(args.optiland_root, args.output_dir, args.draft_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
