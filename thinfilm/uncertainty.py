from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .api import fit_two_angle
from . import config as cfg
from . import io as io_module
from .io import load_spectrum_csv
from .paths import OUTPUT_DIR, output_file

MAIN_RED = "#c94f2d"
REF_BLUE = "#1d4ed8"
ERR_GOLD = "#b7791f"
TARGET_GREEN = "#0f766e"
GRID_COLOR = "#d7dde5"
TEXT_DARK = "#223046"
PANEL_BG = "#f7f8fb"


def _style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor(PANEL_BG)
    ax.grid(True, alpha=0.35, color=GRID_COLOR, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#c9d2dc")
    ax.tick_params(colors=TEXT_DARK)
    ax.xaxis.label.set_color(TEXT_DARK)
    ax.yaxis.label.set_color(TEXT_DARK)
    ax.title.set_color(TEXT_DARK)


def _write_synthetic_reflectance_csv(
    path: Path,
    wavelength_nm: np.ndarray,
    reflectance: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "wavelength_nm": np.asarray(wavelength_nm, dtype=float),
            "总反射率": np.asarray(reflectance, dtype=float),
        }
    )
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _resample_curve(
    wavelength_nm: np.ndarray,
    reflectance: np.ndarray,
    step_nm: float,
) -> tuple[np.ndarray, np.ndarray]:
    wl = np.asarray(wavelength_nm, dtype=float)
    rv = np.asarray(reflectance, dtype=float)
    if step_nm <= 0:
        return wl.copy(), rv.copy()
    grid = np.arange(float(wl[0]), float(wl[-1]) + 0.5 * step_nm, float(step_nm))
    if len(grid) < 5:
        grid = np.linspace(float(wl[0]), float(wl[-1]), 5)
    return grid, np.interp(grid, wl, rv)


def _fit_from_spec_objects(
    spec1: Any,
    spec2: Any,
    *,
    fit_theta1_deg: float,
    fit_theta2_deg: float,
    data_theta1_deg: float,
    data_theta2_deg: float,
    pol: str,
    sample_id: str,
    fit_grid_step_nm: float | None,
) -> Dict[str, Any]:
    if fit_grid_step_nm is None:
        raise ValueError("fit_grid_step_nm must not be None in _fit_from_spec_objects.")
    wl1, r1 = _resample_curve(spec1.x_nm, spec1.y, float(fit_grid_step_nm))
    wl2, r2 = _resample_curve(spec2.x_nm, spec2.y, float(fit_grid_step_nm))
    return _fit_from_synthetic_curves(
        wl1,
        r1,
        data_theta1_deg,
        wl2,
        r2,
        data_theta2_deg,
        fit_theta1_deg=fit_theta1_deg,
        fit_theta2_deg=fit_theta2_deg,
        pol=pol,
        sample_id=sample_id,
    )


def _fit_from_synthetic_curves(
    wavelength1_nm: np.ndarray,
    reflectance1: np.ndarray,
    theta1_deg: float,
    wavelength2_nm: np.ndarray,
    reflectance2: np.ndarray,
    theta2_deg: float,
    *,
    fit_theta1_deg: float,
    fit_theta2_deg: float,
    pol: str,
    sample_id: str,
) -> Dict[str, Any]:
    tmp_dir = OUTPUT_DIR / "_uncertainty_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    csv1 = tmp_dir / f"{sample_id}_angle1.csv"
    csv2 = tmp_dir / f"{sample_id}_angle2.csv"
    _write_synthetic_reflectance_csv(csv1, wavelength1_nm, reflectance1)
    _write_synthetic_reflectance_csv(csv2, wavelength2_nm, reflectance2)
    original_selector_1 = getattr(io_module, "FIT_Y_SELECTOR_0DEG", None)
    original_selector_2 = getattr(io_module, "FIT_Y_SELECTOR_2DEG", None)
    io_module.FIT_Y_SELECTOR_0DEG = "总反射率"
    io_module.FIT_Y_SELECTOR_2DEG = "总反射率"
    try:
        return fit_two_angle(
            csv_angle1=csv1,
            csv_angle2=csv2,
            theta1_deg=float(fit_theta1_deg),
            theta2_deg=float(fit_theta2_deg),
            pol=pol,
            y_selector_angle1="总反射率",
            y_selector_angle2="总反射率",
            save_plots=False,
            sample_id=sample_id,
        )
    finally:
        io_module.FIT_Y_SELECTOR_0DEG = original_selector_1
        io_module.FIT_Y_SELECTOR_2DEG = original_selector_2


def _row_from_fit(
    axis_name: str,
    axis_value: float,
    fit_result: Dict[str, Any],
    true_thickness_nm: float | None,
) -> Dict[str, Any]:
    d_fit = float(fit_result["d_fit_corrected_nm"])
    row = {
        "axis_name": axis_name,
        "axis_value": float(axis_value),
        "d_fit_corrected_nm": d_fit,
        "theta2_fit_deg": float(fit_result["theta2_fit_deg"]),
        "best_objective": float(fit_result["best_objective"]),
    }
    if true_thickness_nm is not None:
        row["thickness_error_nm"] = d_fit - float(true_thickness_nm)
        row["abs_thickness_error_nm"] = abs(row["thickness_error_nm"])
    return row


def _stability_interval(
    rows: Sequence[Dict[str, Any]],
    *,
    error_key: str = "abs_thickness_error_nm",
    threshold: float = 1.0,
) -> Dict[str, float] | None:
    usable = [
        row for row in rows
        if error_key in row and float(row[error_key]) <= float(threshold)
    ]
    if not usable:
        return None
    vals = sorted(float(row["axis_value"]) for row in usable)
    return {"min": vals[0], "max": vals[-1], "width": vals[-1] - vals[0]}


def run_inversion_uncertainty_analysis(
    csv_angle1: Path | str,
    csv_angle2: Path | str,
    *,
    theta1_deg: float,
    theta2_deg: float,
    pol: str = "s",
    true_thickness_nm: float | None = None,
    theta1_offsets_deg: Sequence[float] = (-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20),
    theta2_offsets_deg: Sequence[float] = (-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20),
    noise_sigmas: Sequence[float] = (0.0, 0.002, 0.005, 0.010),
    resolution_steps_nm: Sequence[float] = (0.0, 1.0, 2.0, 5.0),
    y_selector_angle1: int | str | None = None,
    y_selector_angle2: int | str | None = None,
    sample_id: str = "uncertainty_case",
    noise_seed: int = 42,
    fit_grid_step_nm: float | None = None,
) -> Dict[str, Any]:
    """Run thickness-inversion uncertainty sweeps for angle, noise, and resolution."""

    selector1 = cfg.FIT_Y_SELECTOR_ANGLE1 if y_selector_angle1 is None else y_selector_angle1
    selector2 = cfg.FIT_Y_SELECTOR_ANGLE2 if y_selector_angle2 is None else y_selector_angle2

    spec1 = load_spectrum_csv(Path(csv_angle1), y_selector=selector1)
    spec2 = load_spectrum_csv(Path(csv_angle2), y_selector=selector2)
    rng = np.random.default_rng(int(noise_seed))

    if fit_grid_step_nm is None:
        base = fit_two_angle(
            csv_angle1=Path(csv_angle1),
            csv_angle2=Path(csv_angle2),
            theta1_deg=float(theta1_deg),
            theta2_deg=float(theta2_deg),
            pol=pol,
            y_selector_angle1=selector1,
            y_selector_angle2=selector2,
            save_plots=False,
            sample_id=f"{sample_id}_baseline",
        )
    else:
        base = _fit_from_spec_objects(
            spec1,
            spec2,
            fit_theta1_deg=float(theta1_deg),
            fit_theta2_deg=float(theta2_deg),
            data_theta1_deg=float(theta1_deg),
            data_theta2_deg=float(theta2_deg),
            pol=pol,
            sample_id=f"{sample_id}_baseline",
            fit_grid_step_nm=float(fit_grid_step_nm),
        )

    theta1_rows: List[Dict[str, Any]] = []
    for offset in theta1_offsets_deg:
        if fit_grid_step_nm is None:
            fit_result = fit_two_angle(
                csv_angle1=Path(csv_angle1),
                csv_angle2=Path(csv_angle2),
                theta1_deg=float(theta1_deg + offset),
                theta2_deg=float(theta2_deg),
                pol=pol,
                y_selector_angle1=selector1,
                y_selector_angle2=selector2,
                save_plots=False,
                sample_id=f"{sample_id}_theta1_{offset:+.3f}",
            )
        else:
            fit_result = _fit_from_spec_objects(
                spec1,
                spec2,
                fit_theta1_deg=float(theta1_deg + offset),
                fit_theta2_deg=float(theta2_deg),
                data_theta1_deg=float(theta1_deg),
                data_theta2_deg=float(theta2_deg),
                pol=pol,
                sample_id=f"{sample_id}_theta1_{offset:+.3f}",
                fit_grid_step_nm=float(fit_grid_step_nm),
            )
        theta1_rows.append(_row_from_fit("theta1_offset_deg", float(offset), fit_result, true_thickness_nm))

    theta2_rows: List[Dict[str, Any]] = []
    for offset in theta2_offsets_deg:
        if fit_grid_step_nm is None:
            fit_result = fit_two_angle(
                csv_angle1=Path(csv_angle1),
                csv_angle2=Path(csv_angle2),
                theta1_deg=float(theta1_deg),
                theta2_deg=float(theta2_deg + offset),
                pol=pol,
                y_selector_angle1=selector1,
                y_selector_angle2=selector2,
                save_plots=False,
                sample_id=f"{sample_id}_theta2_{offset:+.3f}",
            )
        else:
            fit_result = _fit_from_spec_objects(
                spec1,
                spec2,
                fit_theta1_deg=float(theta1_deg),
                fit_theta2_deg=float(theta2_deg + offset),
                data_theta1_deg=float(theta1_deg),
                data_theta2_deg=float(theta2_deg),
                pol=pol,
                sample_id=f"{sample_id}_theta2_{offset:+.3f}",
                fit_grid_step_nm=float(fit_grid_step_nm),
            )
        theta2_rows.append(_row_from_fit("theta2_offset_deg", float(offset), fit_result, true_thickness_nm))

    noise_rows: List[Dict[str, Any]] = []
    for sigma in noise_sigmas:
        r1 = np.clip(np.asarray(spec1.y, dtype=float) + rng.normal(0.0, float(sigma), size=len(spec1.y)), 0.0, 1.0)
        r2 = np.clip(np.asarray(spec2.y, dtype=float) + rng.normal(0.0, float(sigma), size=len(spec2.y)), 0.0, 1.0)
        fit_result = _fit_from_synthetic_curves(
            spec1.x_nm,
            r1,
            float(theta1_deg),
            spec2.x_nm,
            r2,
            float(theta2_deg),
            fit_theta1_deg=float(theta1_deg),
            fit_theta2_deg=float(theta2_deg),
            pol=pol,
            sample_id=f"{sample_id}_noise_{sigma:.4f}",
        )
        noise_rows.append(_row_from_fit("noise_sigma", float(sigma), fit_result, true_thickness_nm))

    resolution_rows: List[Dict[str, Any]] = []
    for step_nm in resolution_steps_nm:
        wl1, r1 = _resample_curve(spec1.x_nm, spec1.y, float(step_nm))
        wl2, r2 = _resample_curve(spec2.x_nm, spec2.y, float(step_nm))
        fit_result = _fit_from_synthetic_curves(
            wl1,
            r1,
            float(theta1_deg),
            wl2,
            r2,
            float(theta2_deg),
            fit_theta1_deg=float(theta1_deg),
            fit_theta2_deg=float(theta2_deg),
            pol=pol,
            sample_id=f"{sample_id}_resolution_{step_nm:.3f}",
        )
        resolution_rows.append(_row_from_fit("resolution_step_nm", float(step_nm), fit_result, true_thickness_nm))

    theta2_stability = _stability_interval(theta2_rows)
    summary: Dict[str, Any] = {
        "sample_id": sample_id,
        "pol": str(pol),
        "theta1_deg": float(theta1_deg),
        "theta2_deg": float(theta2_deg),
        "true_thickness_nm": None if true_thickness_nm is None else float(true_thickness_nm),
        "baseline": {
            "d_fit_corrected_nm": float(base["d_fit_corrected_nm"]),
            "theta2_fit_deg": float(base["theta2_fit_deg"]),
            "best_objective": float(base["best_objective"]),
        },
        "theta1_sweep": theta1_rows,
        "theta2_sweep": theta2_rows,
        "noise_sweep": noise_rows,
        "resolution_sweep": resolution_rows,
        "stability": {
            "theta2_offset_deg_for_abs_error_le_1nm": theta2_stability,
        },
    }
    if true_thickness_nm is not None:
        summary["baseline"]["thickness_error_nm"] = float(base["d_fit_corrected_nm"]) - float(true_thickness_nm)
        summary["baseline"]["abs_thickness_error_nm"] = abs(summary["baseline"]["thickness_error_nm"])
    return summary


def export_inversion_uncertainty_analysis(
    result: Dict[str, Any],
    *,
    prefix: str = "inversion_uncertainty",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    sample_id = str(result.get("sample_id", "case"))
    stem = f"{prefix}_{sample_id}"

    def _rows_to_df(rows: Iterable[Dict[str, Any]]) -> pd.DataFrame:
        return pd.DataFrame(list(rows))

    if save_csv:
        paths = {
            "theta1_csv": output_file(f"{stem}_theta1.csv"),
            "theta2_csv": output_file(f"{stem}_theta2.csv"),
            "noise_csv": output_file(f"{stem}_noise.csv"),
            "resolution_csv": output_file(f"{stem}_resolution.csv"),
        }
        _rows_to_df(result["theta1_sweep"]).to_csv(paths["theta1_csv"], index=False, encoding="utf-8-sig")
        _rows_to_df(result["theta2_sweep"]).to_csv(paths["theta2_csv"], index=False, encoding="utf-8-sig")
        _rows_to_df(result["noise_sweep"]).to_csv(paths["noise_csv"], index=False, encoding="utf-8-sig")
        _rows_to_df(result["resolution_sweep"]).to_csv(paths["resolution_csv"], index=False, encoding="utf-8-sig")
        for key, path in paths.items():
            saved[key] = str(path)

    if save_json:
        json_path = output_file(f"{stem}_summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        saved["json"] = str(json_path)

    if save_txt:
        txt_path = output_file(f"{stem}_summary.txt")
        baseline = result["baseline"]
        lines = [
            "Inversion Uncertainty Summary",
            "=" * 80,
            f"sample_id              = {sample_id}",
            f"pol                    = {result['pol']}",
            f"theta1_deg             = {float(result['theta1_deg']):.6f}",
            f"theta2_deg             = {float(result['theta2_deg']):.6f}",
            f"d_fit_corrected_nm     = {float(baseline['d_fit_corrected_nm']):.6f}",
            f"theta2_fit_deg         = {float(baseline['theta2_fit_deg']):.6f}",
            f"best_objective         = {float(baseline['best_objective']):.12e}",
        ]
        if "thickness_error_nm" in baseline:
            lines.append(f"thickness_error_nm      = {float(baseline['thickness_error_nm']):+.6f}")
        stability = result.get("stability", {}).get("theta2_offset_deg_for_abs_error_le_1nm")
        if stability:
            lines.extend(
                [
                    "",
                    "Stable theta2-offset interval for |thickness error| <= 1 nm",
                    f"min_deg                = {float(stability['min']):+.6f}",
                    f"max_deg                = {float(stability['max']):+.6f}",
                    f"width_deg              = {float(stability['width']):.6f}",
                ]
            )
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        saved["txt"] = str(txt_path)

    if save_plot:
        fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.0))
        axes = axes.ravel()
        for ax in axes:
            _style_axis(ax)

        def _plot(ax: plt.Axes, rows: Sequence[Dict[str, Any]], x_key: str, title: str, xlabel: str) -> None:
            df = pd.DataFrame(list(rows))
            if df.empty:
                return
            ax.plot(df[x_key], df["d_fit_corrected_nm"], color=MAIN_RED, marker="o", linewidth=2.0)
            ax.set_title(title)
            ax.set_xlabel(xlabel)
            ax.set_ylabel("d_fit (nm)")
            if result.get("true_thickness_nm") is not None:
                ax.axhline(float(result["true_thickness_nm"]), color=TARGET_GREEN, linestyle=":", linewidth=1.3)

        _plot(axes[0], result["theta1_sweep"], "axis_value", "Theta1 Error Sensitivity", "theta1 offset (deg)")
        _plot(axes[1], result["theta2_sweep"], "axis_value", "Theta2 Error Sensitivity", "theta2 offset (deg)")
        _plot(axes[2], result["noise_sweep"], "axis_value", "Noise Sensitivity", "noise sigma")
        _plot(axes[3], result["resolution_sweep"], "axis_value", "Resolution Sensitivity", "resolution step (nm)")
        fig.suptitle("Thickness-Inversion Uncertainty Analysis", fontweight="semibold", color=TEXT_DARK)
        fig.tight_layout()
        png_path = output_file(f"{stem}_main.png")
        fig.savefig(png_path, dpi=180)
        plt.close(fig)
        saved["main_png"] = str(png_path)

        analysis_png = output_file(f"{stem}_analysis.png")
        fig2, axes2 = plt.subplots(1, 3, figsize=(11.5, 3.8))
        for ax in axes2:
            _style_axis(ax)

        baseline = result["baseline"]
        axes2[0].bar(
            ["d_fit", "theta2_fit"],
            [float(baseline["d_fit_corrected_nm"]), float(baseline["theta2_fit_deg"])],
            color=[MAIN_RED, REF_BLUE],
            alpha=0.92,
        )
        axes2[0].set_title("Baseline Fit")

        if result.get("true_thickness_nm") is not None:
            axes2[1].bar(
                ["Thickness error"],
                [float(baseline.get("thickness_error_nm", 0.0))],
                color=[ERR_GOLD],
                alpha=0.92,
            )
            axes2[1].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
            axes2[1].set_title("Baseline Error")
        else:
            axes2[1].text(0.5, 0.5, "No true thickness", ha="center", va="center", color=TEXT_DARK)
            axes2[1].set_title("Baseline Error")

        theta2_stability = result.get("stability", {}).get("theta2_offset_deg_for_abs_error_le_1nm")
        if theta2_stability:
            axes2[2].bar(
                ["min", "max", "width"],
                [
                    float(theta2_stability["min"]),
                    float(theta2_stability["max"]),
                    float(theta2_stability["width"]),
                ],
                color=[REF_BLUE, MAIN_RED, TARGET_GREEN],
                alpha=0.92,
            )
            axes2[2].set_title("Stable Theta2 Interval")
        else:
            axes2[2].text(0.5, 0.5, "No <=1 nm interval", ha="center", va="center", color=TEXT_DARK)
            axes2[2].set_title("Stable Theta2 Interval")

        fig2.suptitle("Uncertainty Summary", fontweight="semibold", color=TEXT_DARK)
        fig2.tight_layout()
        fig2.savefig(analysis_png, dpi=180)
        plt.close(fig2)
        saved["analysis_png"] = str(analysis_png)

    return saved
