from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import matplotlib.pyplot as plt
import numpy as np

from .education import LayerSpec, multilayer_rt_spectrum, simulate_report_case
from .io import load_spectrum_csv
from .paths import output_file
from .validation import build_standard_teaching_validation_cases, export_standard_teaching_validation_bundle

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

MAIN_RED = "#c94f2d"
REF_BLUE = "#1d4ed8"
ERR_GOLD = "#b7791f"
TARGET_GREEN = "#0f766e"
GRID_COLOR = "#d7dde5"
TEXT_DARK = "#223046"
PANEL_BG = "#f7f8fb"

STABILITY_PROFILES: Dict[str, Dict[str, float]] = {
    "strict": {
        "resolution_mae_limit": 5e-3,
        "resolution_lambda0_error_limit_nm": 0.5,
        "resolution_feature_shift_limit_nm": 0.5,
        "noise_mae_limit": 5e-3,
        "noise_lambda0_error_std_limit_nm": 0.5,
        "noise_feature_shift_std_limit_nm": 0.5,
    },
    "competition_balanced": {
        "resolution_mae_limit": 1e-2,
        "resolution_lambda0_error_limit_nm": 1.0,
        "resolution_feature_shift_limit_nm": 1.0,
        "noise_mae_limit": 1e-2,
        "noise_lambda0_error_std_limit_nm": 1.0,
        "noise_feature_shift_std_limit_nm": 1.0,
    },
    "loose": {
        "resolution_mae_limit": 2e-2,
        "resolution_lambda0_error_limit_nm": 2.0,
        "resolution_feature_shift_limit_nm": 2.0,
        "noise_mae_limit": 2e-2,
        "noise_lambda0_error_std_limit_nm": 2.0,
        "noise_feature_shift_std_limit_nm": 2.0,
    },
}

SELECTOR_CN = {
    "all": "全层",
    "high": "高折层",
    "low": "低折层",
    "cavity": "腔层",
}


def _style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor(PANEL_BG)
    ax.grid(True, alpha=0.35, color=GRID_COLOR, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#c9d2dc")
    ax.tick_params(colors=TEXT_DARK)
    ax.xaxis.label.set_color(TEXT_DARK)
    ax.yaxis.label.set_color(TEXT_DARK)
    ax.title.set_color(TEXT_DARK)


def _default_case_quantity(case_id: str) -> str:
    key = str(case_id).strip().lower()
    if "fp_" in key:
        return "T"
    return "R"


def _reference_kind_to_quantity(y_kind: str) -> str | None:
    key = str(y_kind).strip().lower()
    if "trans" in key:
        return "T"
    if "abs" in key:
        return "A"
    if "reflect" in key:
        return "R"
    return None


def _pick_quantity(case_id: str, reference_kind: str, quantity: str | None) -> str:
    if quantity is not None:
        return str(quantity).strip().upper()
    ref_quantity = _reference_kind_to_quantity(reference_kind)
    if ref_quantity is not None:
        return ref_quantity
    return _default_case_quantity(case_id)


def _series_for_quantity(result: Dict[str, Any], quantity: str) -> np.ndarray:
    key = str(quantity).strip().upper()
    if key not in {"R", "T", "A"}:
        raise ValueError("quantity must be 'R', 'T', or 'A'.")
    return np.asarray(result[key], dtype=float)


def _resample_pair(
    x1_nm: np.ndarray,
    y1: np.ndarray,
    x2_nm: np.ndarray,
    y2: np.ndarray,
    n_grid: int = 600,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x_min = max(float(np.min(x1_nm)), float(np.min(x2_nm)))
    x_max = min(float(np.max(x1_nm)), float(np.max(x2_nm)))
    if x_max <= x_min:
        raise ValueError("Theory and reference curves do not overlap in wavelength.")
    grid = np.linspace(x_min, x_max, max(int(n_grid), 80))
    return grid, np.interp(grid, x1_nm, y1), np.interp(grid, x2_nm, y2)


def _error_metrics(theory: np.ndarray, reference: np.ndarray) -> Dict[str, float]:
    diff = np.asarray(theory, dtype=float) - np.asarray(reference, dtype=float)
    return {
        "mae": float(np.mean(np.abs(diff))),
        "rmse": float(np.sqrt(np.mean(diff ** 2))),
        "max_abs_error": float(np.max(np.abs(diff))),
        "mean_bias": float(np.mean(diff)),
    }


def _feature_mode(case_id: str, quantity: str) -> str:
    key = str(case_id).strip().lower()
    q = str(quantity).strip().upper()
    if q == "T":
        return "max"
    if "high_reflector" in key or "beamsplitter" in key:
        return "max"
    return "min"


def _default_feature_window_nm(case_id: str, quantity: str) -> float:
    key = str(case_id).strip().lower()
    q = str(quantity).strip().upper()
    if "fp_" in key or q == "T":
        return 20.0
    if "high_reflector" in key:
        return 30.0
    return 25.0


def _feature_summary(
    case_id: str,
    quantity: str,
    x_nm: np.ndarray,
    y: np.ndarray,
    *,
    anchor_nm: float | None = None,
    window_nm: float | None = None,
) -> Dict[str, float]:
    mode = _feature_mode(case_id, quantity)
    x_use = np.asarray(x_nm, dtype=float)
    y_use = np.asarray(y, dtype=float)
    if anchor_nm is not None:
        local_window = float(window_nm if window_nm is not None else _default_feature_window_nm(case_id, quantity))
        mask = np.abs(x_use - float(anchor_nm)) <= local_window
        if int(np.count_nonzero(mask)) >= 3:
            x_local = x_use[mask]
            y_local = y_use[mask]
        else:
            x_local = x_use
            y_local = y_use
    else:
        x_local = x_use
        y_local = y_use
    if mode == "max":
        idx = int(np.argmax(y_local))
        feature_label = "峰位"
    else:
        idx = int(np.argmin(y_local))
        feature_label = "谷位"
    return {
        "feature_label": feature_label,
        "feature_wavelength_nm": float(x_local[idx]),
        "feature_value": float(y_local[idx]),
    }


def _estimate_native_step_nm(x_nm: np.ndarray) -> float:
    x = np.asarray(x_nm, dtype=float)
    if len(x) < 2:
        return 0.0
    diffs = np.diff(x)
    diffs = diffs[np.abs(diffs) > 1e-12]
    if len(diffs) == 0:
        return 0.0
    return float(np.median(diffs))


def _layers_from_result(result: Dict[str, Any]) -> List[LayerSpec]:
    layers: List[LayerSpec] = []
    for item in result.get("layers", []):
        layers.append(
            LayerSpec(
                str(item["name"]),
                complex(float(item["n_real"]), float(item["n_imag"])),
                float(item["thickness_nm"]),
            )
        )
    return layers


def _scaled_layers(
    layers: Sequence[LayerSpec],
    scale: float,
    selector: str = "all",
) -> List[LayerSpec]:
    key = str(selector).strip().lower()

    def matches(name: str) -> bool:
        base = str(name).strip().upper()
        if key == "all":
            return True
        if key == "high":
            return base.startswith("H")
        if key == "low":
            return base.startswith("L")
        if key == "cavity":
            return base.startswith("C") or base.startswith("2L") or base.startswith("2H")
        return False

    scaled: List[LayerSpec] = []
    for layer in layers:
        thickness = float(layer.thickness_nm) * float(scale) if matches(layer.name) else float(layer.thickness_nm)
        scaled.append(LayerSpec(layer.name, layer.n, thickness))
    return scaled


def _rerun_from_result(
    base_result: Dict[str, Any],
    *,
    theta_deg: float | None = None,
    layers: Sequence[LayerSpec] | None = None,
) -> Dict[str, Any]:
    active_layers = list(layers) if layers is not None else _layers_from_result(base_result)
    theta = float(base_result["theta_deg"]) if theta_deg is None else float(theta_deg)
    spectrum = multilayer_rt_spectrum(
        wavelengths_nm=np.asarray(base_result["wavelength_nm"], dtype=float),
        layers=active_layers,
        n_incident=complex(base_result["n_incident"]),
        n_substrate=complex(base_result["n_substrate"]),
        theta0_deg=theta,
        pol=str(base_result["pol"]),
    )
    return {
        "wavelength_nm": np.asarray(spectrum["wavelength_nm"], dtype=float),
        "R": np.asarray(spectrum["R"], dtype=float),
        "T": np.asarray(spectrum["T"], dtype=float),
        "A": np.asarray(spectrum["A"], dtype=float),
        "theta_deg": theta,
        "layers": active_layers,
    }


def _sample_curve_by_step(x_nm: np.ndarray, y: np.ndarray, step_nm: float) -> tuple[np.ndarray, np.ndarray]:
    step_nm = float(step_nm)
    if step_nm <= 0.0:
        raise ValueError("step_nm must be positive.")
    x_start = float(np.min(x_nm))
    x_stop = float(np.max(x_nm))
    sample_x = np.arange(x_start, x_stop + 0.5 * step_nm, step_nm, dtype=float)
    sample_y = np.interp(sample_x, x_nm, y)
    return sample_x, sample_y


def _compare_curve_to_theory(
    case_id: str,
    quantity: str,
    theory_result: Dict[str, Any],
    reference_x_nm: np.ndarray,
    reference_y: np.ndarray,
    n_grid: int = 600,
    *,
    feature_anchor_nm: float | None = None,
    feature_window_nm: float | None = None,
) -> Dict[str, float]:
    theory_x = np.asarray(theory_result["wavelength_nm"], dtype=float)
    theory_y = _series_for_quantity(theory_result, quantity)
    grid_nm, theory_i, reference_i = _resample_pair(theory_x, theory_y, reference_x_nm, reference_y, n_grid=n_grid)
    metrics = _error_metrics(theory_i, reference_i)
    lambda0_nm = float(theory_result["lambda0_nm"])
    theory_at_lambda0 = float(np.interp(lambda0_nm, grid_nm, theory_i))
    reference_at_lambda0 = float(np.interp(lambda0_nm, grid_nm, reference_i))
    feature = _feature_summary(
        case_id,
        quantity,
        reference_x_nm,
        reference_y,
        anchor_nm=feature_anchor_nm,
        window_nm=feature_window_nm,
    )
    return {
        "lambda_min_nm": float(grid_nm[0]),
        "lambda_max_nm": float(grid_nm[-1]),
        "num_points": int(len(reference_x_nm)),
        "theory_at_lambda0": theory_at_lambda0,
        "reference_at_lambda0": reference_at_lambda0,
        "lambda0_error": theory_at_lambda0 - reference_at_lambda0,
        **feature,
        **metrics,
    }


def analyze_reference_resolution(
    case_id: str,
    reference_csv: Path | str,
    *,
    y_selector: int | str | None = None,
    quantity: str | None = None,
    sample_steps_nm: Sequence[float] = (0.5, 1.0, 2.0, 5.0),
    n_grid: int = 600,
    reference_label: str = "COMSOL",
    **case_overrides: Any,
) -> Dict[str, Any]:
    ref_spec = load_spectrum_csv(Path(reference_csv), y_selector=y_selector)
    active_quantity = _pick_quantity(case_id, ref_spec.y_kind, quantity)
    theory_result = simulate_report_case(case_id, **case_overrides)

    base_x = np.asarray(ref_spec.x_nm, dtype=float)
    base_y = np.asarray(ref_spec.y, dtype=float)
    base_summary = _compare_curve_to_theory(case_id, active_quantity, theory_result, base_x, base_y, n_grid=n_grid)
    native_step_nm = _estimate_native_step_nm(base_x)

    rows: List[Dict[str, float | str]] = [
        {
            "mode": "native",
            "sampling_step_nm": native_step_nm,
            "feature_shift_nm": 0.0,
            "value_at_lambda0_shift": 0.0,
            **base_summary,
        }
    ]

    for step_nm in sample_steps_nm:
        sampled_x, sampled_y = _sample_curve_by_step(base_x, base_y, float(step_nm))
        sampled_summary = _compare_curve_to_theory(
            case_id,
            active_quantity,
            theory_result,
            sampled_x,
            sampled_y,
            n_grid=n_grid,
            feature_anchor_nm=float(base_summary["feature_wavelength_nm"]),
        )
        rows.append(
            {
                "mode": "resampled",
                "sampling_step_nm": float(step_nm),
                "feature_shift_nm": float(sampled_summary["feature_wavelength_nm"]) - float(base_summary["feature_wavelength_nm"]),
                "value_at_lambda0_shift": float(sampled_summary["reference_at_lambda0"]) - float(base_summary["reference_at_lambda0"]),
                **sampled_summary,
            }
        )

    return {
        "analysis_type": "resolution",
        "case_id": str(case_id),
        "title_cn": str(theory_result.get("title_cn") or case_id),
        "title_en": str(theory_result.get("title_en") or case_id),
        "quantity": active_quantity,
        "lambda0_nm": float(theory_result["lambda0_nm"]),
        "reference_label": str(reference_label),
        "reference_csv": str(Path(reference_csv)),
        "native_step_nm": native_step_nm,
        "rows": rows,
    }


def analyze_reference_noise(
    case_id: str,
    reference_csv: Path | str,
    *,
    y_selector: int | str | None = None,
    quantity: str | None = None,
    noise_sigmas: Sequence[float] = (1e-4, 5e-4, 1e-3, 5e-3),
    repeats: int = 20,
    seed: int = 20260505,
    n_grid: int = 600,
    reference_label: str = "COMSOL",
    **case_overrides: Any,
) -> Dict[str, Any]:
    ref_spec = load_spectrum_csv(Path(reference_csv), y_selector=y_selector)
    active_quantity = _pick_quantity(case_id, ref_spec.y_kind, quantity)
    theory_result = simulate_report_case(case_id, **case_overrides)

    base_x = np.asarray(ref_spec.x_nm, dtype=float)
    base_y = np.asarray(ref_spec.y, dtype=float)
    base_summary = _compare_curve_to_theory(case_id, active_quantity, theory_result, base_x, base_y, n_grid=n_grid)

    rng = np.random.default_rng(int(seed))
    rows: List[Dict[str, float | str]] = []
    example_curves: Dict[str, Dict[str, List[float]]] = {}

    for sigma in noise_sigmas:
        sigma_val = float(sigma)
        metric_rows: List[Dict[str, float]] = []
        first_curve_x: np.ndarray | None = None
        first_curve_y: np.ndarray | None = None
        for idx in range(max(int(repeats), 1)):
            noisy_y = np.clip(base_y + rng.normal(0.0, sigma_val, size=len(base_y)), 0.0, 1.0)
            noisy_summary = _compare_curve_to_theory(
                case_id,
                active_quantity,
                theory_result,
                base_x,
                noisy_y,
                n_grid=n_grid,
                feature_anchor_nm=float(base_summary["feature_wavelength_nm"]),
            )
            metric_rows.append(
                {
                    "mae": float(noisy_summary["mae"]),
                    "rmse": float(noisy_summary["rmse"]),
                    "max_abs_error": float(noisy_summary["max_abs_error"]),
                    "mean_bias": float(noisy_summary["mean_bias"]),
                    "lambda0_error": float(noisy_summary["lambda0_error"]),
                    "feature_shift_nm": float(noisy_summary["feature_wavelength_nm"]) - float(base_summary["feature_wavelength_nm"]),
                    "value_at_lambda0_shift": float(noisy_summary["reference_at_lambda0"]) - float(base_summary["reference_at_lambda0"]),
                }
            )
            if idx == 0:
                first_curve_x = base_x.copy()
                first_curve_y = noisy_y.copy()

        metric_array = {key: np.asarray([row[key] for row in metric_rows], dtype=float) for key in metric_rows[0]}
        rows.append(
            {
                "noise_sigma": sigma_val,
                "repeats": int(repeats),
                "mae_mean": float(np.mean(metric_array["mae"])),
                "mae_std": float(np.std(metric_array["mae"])),
                "rmse_mean": float(np.mean(metric_array["rmse"])),
                "rmse_std": float(np.std(metric_array["rmse"])),
                "max_abs_error_mean": float(np.mean(metric_array["max_abs_error"])),
                "mean_bias_mean": float(np.mean(metric_array["mean_bias"])),
                "mean_bias_std": float(np.std(metric_array["mean_bias"])),
                "lambda0_error_mean": float(np.mean(metric_array["lambda0_error"])),
                "lambda0_error_std": float(np.std(metric_array["lambda0_error"])),
                "feature_shift_nm_mean": float(np.mean(metric_array["feature_shift_nm"])),
                "feature_shift_nm_std": float(np.std(metric_array["feature_shift_nm"])),
                "value_at_lambda0_shift_mean": float(np.mean(metric_array["value_at_lambda0_shift"])),
                "value_at_lambda0_shift_std": float(np.std(metric_array["value_at_lambda0_shift"])),
            }
        )
        if first_curve_x is not None and first_curve_y is not None:
            example_curves[f"{sigma_val:.12g}"] = {
                "wavelength_nm": [float(x) for x in first_curve_x],
                "y": [float(y) for y in first_curve_y],
            }

    return {
        "analysis_type": "noise",
        "case_id": str(case_id),
        "title_cn": str(theory_result.get("title_cn") or case_id),
        "title_en": str(theory_result.get("title_en") or case_id),
        "quantity": active_quantity,
        "lambda0_nm": float(theory_result["lambda0_nm"]),
        "reference_label": str(reference_label),
        "reference_csv": str(Path(reference_csv)),
        "base_summary": base_summary,
        "rows": rows,
        "example_curves": example_curves,
    }


def analyze_theoretical_angle_sensitivity(
    case_id: str,
    *,
    theta_values_deg: Sequence[float] = (0.0, 1.0, 2.0, 3.0, 5.0),
    quantity: str | None = None,
    **case_overrides: Any,
) -> Dict[str, Any]:
    base_result = simulate_report_case(case_id, **case_overrides)
    active_quantity = _default_case_quantity(case_id) if quantity is None else str(quantity).strip().upper()
    base_x = np.asarray(base_result["wavelength_nm"], dtype=float)
    base_y = _series_for_quantity(base_result, active_quantity)
    base_feature = _feature_summary(case_id, active_quantity, base_x, base_y)

    rows: List[Dict[str, float]] = []
    for theta_deg in theta_values_deg:
        perturbed = _rerun_from_result(base_result, theta_deg=float(theta_deg))
        perturbed_y = np.asarray(perturbed[active_quantity], dtype=float)
        metrics = _error_metrics(base_y, perturbed_y)
        feature = _feature_summary(
            case_id,
            active_quantity,
            base_x,
            perturbed_y,
            anchor_nm=float(base_feature["feature_wavelength_nm"]),
        )
        lambda0_nm = float(base_result["lambda0_nm"])
        rows.append(
            {
                "theta_deg": float(theta_deg),
                "mae": float(metrics["mae"]),
                "rmse": float(metrics["rmse"]),
                "max_abs_error": float(metrics["max_abs_error"]),
                "mean_bias": float(metrics["mean_bias"]),
                "lambda0_shift": float(np.interp(lambda0_nm, base_x, perturbed_y) - np.interp(lambda0_nm, base_x, base_y)),
                "feature_shift_nm": float(feature["feature_wavelength_nm"]) - float(base_feature["feature_wavelength_nm"]),
                "feature_value_shift": float(feature["feature_value"]) - float(base_feature["feature_value"]),
            }
        )

    return {
        "analysis_type": "angle",
        "case_id": str(case_id),
        "title_cn": str(base_result.get("title_cn") or case_id),
        "title_en": str(base_result.get("title_en") or case_id),
        "quantity": active_quantity,
        "lambda0_nm": float(base_result["lambda0_nm"]),
        "base_theta_deg": float(base_result["theta_deg"]),
        "base_feature": base_feature,
        "rows": rows,
    }


def analyze_theoretical_thickness_sensitivity(
    case_id: str,
    *,
    scale_values: Sequence[float] = (0.98, 0.99, 0.995, 1.0, 1.005, 1.01, 1.02),
    selector: str = "all",
    quantity: str | None = None,
    **case_overrides: Any,
) -> Dict[str, Any]:
    base_result = simulate_report_case(case_id, **case_overrides)
    active_quantity = _default_case_quantity(case_id) if quantity is None else str(quantity).strip().upper()
    base_x = np.asarray(base_result["wavelength_nm"], dtype=float)
    base_y = _series_for_quantity(base_result, active_quantity)
    base_layers = _layers_from_result(base_result)
    base_feature = _feature_summary(case_id, active_quantity, base_x, base_y)

    rows: List[Dict[str, float]] = []
    for scale in scale_values:
        perturbed_layers = _scaled_layers(base_layers, float(scale), selector=selector)
        perturbed = _rerun_from_result(base_result, layers=perturbed_layers)
        perturbed_y = np.asarray(perturbed[active_quantity], dtype=float)
        metrics = _error_metrics(base_y, perturbed_y)
        feature = _feature_summary(
            case_id,
            active_quantity,
            base_x,
            perturbed_y,
            anchor_nm=float(base_feature["feature_wavelength_nm"]),
        )
        lambda0_nm = float(base_result["lambda0_nm"])
        rows.append(
            {
                "scale": float(scale),
                "relative_error_percent": (float(scale) - 1.0) * 100.0,
                "mae": float(metrics["mae"]),
                "rmse": float(metrics["rmse"]),
                "max_abs_error": float(metrics["max_abs_error"]),
                "mean_bias": float(metrics["mean_bias"]),
                "lambda0_shift": float(np.interp(lambda0_nm, base_x, perturbed_y) - np.interp(lambda0_nm, base_x, base_y)),
                "feature_shift_nm": float(feature["feature_wavelength_nm"]) - float(base_feature["feature_wavelength_nm"]),
                "feature_value_shift": float(feature["feature_value"]) - float(base_feature["feature_value"]),
            }
        )

    return {
        "analysis_type": "thickness",
        "case_id": str(case_id),
        "title_cn": str(base_result.get("title_cn") or case_id),
        "title_en": str(base_result.get("title_en") or case_id),
        "quantity": active_quantity,
        "lambda0_nm": float(base_result["lambda0_nm"]),
        "selector": str(selector),
        "base_feature": base_feature,
        "rows": rows,
    }


def export_resolution_analysis(
    result: Dict[str, Any],
    *,
    prefix: str = "teaching_resolution",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    stem = f"{prefix}_{result['case_id']}"
    rows = list(result["rows"])

    csv_path = output_file(f"{stem}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        headers = [
            "mode",
            "sampling_step_nm",
            "num_points",
            "mae",
            "rmse",
            "max_abs_error",
            "mean_bias",
            "lambda0_error",
            "feature_wavelength_nm",
            "feature_value",
            "feature_shift_nm",
            "value_at_lambda0_shift",
        ]
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(
                ",".join(
                    [
                        str(row["mode"]),
                        f"{float(row['sampling_step_nm']):.12g}",
                        str(int(row["num_points"])),
                        f"{float(row['mae']):.12g}",
                        f"{float(row['rmse']):.12g}",
                        f"{float(row['max_abs_error']):.12g}",
                        f"{float(row['mean_bias']):.12g}",
                        f"{float(row['lambda0_error']):.12g}",
                        f"{float(row['feature_wavelength_nm']):.12g}",
                        f"{float(row['feature_value']):.12g}",
                        f"{float(row['feature_shift_nm']):.12g}",
                        f"{float(row['value_at_lambda0_shift']):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{stem}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2))
    step_rows = [row for row in rows if str(row["mode"]) == "resampled"]
    x = np.asarray([float(row["sampling_step_nm"]) for row in step_rows], dtype=float)
    mae = np.asarray([float(row["mae"]) for row in step_rows], dtype=float)
    rmse = np.asarray([float(row["rmse"]) for row in step_rows], dtype=float)
    lambda0_err = np.asarray([float(row["lambda0_error"]) for row in step_rows], dtype=float)
    feature_shift = np.asarray([float(row["feature_shift_nm"]) for row in step_rows], dtype=float)

    for ax in axes.ravel():
        _style_axis(ax)

    axes[0, 0].plot(x, mae, marker="o", color=MAIN_RED, linewidth=2.2)
    axes[0, 0].set_title("分辨率 vs 平均绝对误差")
    axes[0, 0].set_xlabel("采样步长 (nm)")
    axes[0, 0].set_ylabel("MAE")

    axes[0, 1].plot(x, rmse, marker="o", color=REF_BLUE, linewidth=2.2)
    axes[0, 1].set_title("分辨率 vs 均方根误差")
    axes[0, 1].set_xlabel("采样步长 (nm)")
    axes[0, 1].set_ylabel("RMSE")

    axes[1, 0].plot(x, lambda0_err, marker="o", color=TARGET_GREEN, linewidth=2.2)
    axes[1, 0].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[1, 0].set_title("分辨率 vs 中心点误差")
    axes[1, 0].set_xlabel("采样步长 (nm)")
    axes[1, 0].set_ylabel("误差")

    axes[1, 1].plot(x, feature_shift, marker="o", color=ERR_GOLD, linewidth=2.2)
    axes[1, 1].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[1, 1].set_title("分辨率 vs 特征位置偏移")
    axes[1, 1].set_xlabel("采样步长 (nm)")
    axes[1, 1].set_ylabel("偏移 (nm)")

    fig.suptitle(f"{result['title_cn']} | 分辨率影响分析", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{stem}_analysis.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["analysis_png"] = str(png_path)
    return saved


def export_noise_analysis(
    result: Dict[str, Any],
    *,
    prefix: str = "teaching_noise",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    stem = f"{prefix}_{result['case_id']}"
    rows = list(result["rows"])

    csv_path = output_file(f"{stem}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        headers = [
            "noise_sigma",
            "repeats",
            "mae_mean",
            "mae_std",
            "rmse_mean",
            "rmse_std",
            "max_abs_error_mean",
            "mean_bias_mean",
            "mean_bias_std",
            "lambda0_error_mean",
            "lambda0_error_std",
            "feature_shift_nm_mean",
            "feature_shift_nm_std",
            "value_at_lambda0_shift_mean",
            "value_at_lambda0_shift_std",
        ]
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(
                ",".join(
                    [
                        f"{float(row['noise_sigma']):.12g}",
                        str(int(row["repeats"])),
                        f"{float(row['mae_mean']):.12g}",
                        f"{float(row['mae_std']):.12g}",
                        f"{float(row['rmse_mean']):.12g}",
                        f"{float(row['rmse_std']):.12g}",
                        f"{float(row['max_abs_error_mean']):.12g}",
                        f"{float(row['mean_bias_mean']):.12g}",
                        f"{float(row['mean_bias_std']):.12g}",
                        f"{float(row['lambda0_error_mean']):.12g}",
                        f"{float(row['lambda0_error_std']):.12g}",
                        f"{float(row['feature_shift_nm_mean']):.12g}",
                        f"{float(row['feature_shift_nm_std']):.12g}",
                        f"{float(row['value_at_lambda0_shift_mean']):.12g}",
                        f"{float(row['value_at_lambda0_shift_std']):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{stem}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    sigma = np.asarray([float(row["noise_sigma"]) for row in rows], dtype=float)
    mae_mean = np.asarray([float(row["mae_mean"]) for row in rows], dtype=float)
    mae_std = np.asarray([float(row["mae_std"]) for row in rows], dtype=float)
    lambda0_mean = np.asarray([float(row["lambda0_error_mean"]) for row in rows], dtype=float)
    lambda0_std = np.asarray([float(row["lambda0_error_std"]) for row in rows], dtype=float)
    feature_shift_mean = np.asarray([float(row["feature_shift_nm_mean"]) for row in rows], dtype=float)
    feature_shift_std = np.asarray([float(row["feature_shift_nm_std"]) for row in rows], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2))
    for ax in axes.ravel():
        _style_axis(ax)
        ax.set_xscale("log")

    axes[0, 0].errorbar(sigma, mae_mean, yerr=mae_std, marker="o", color=MAIN_RED, linewidth=2.0, capsize=3)
    axes[0, 0].set_title("噪声 vs 平均绝对误差")
    axes[0, 0].set_xlabel("噪声标准差")
    axes[0, 0].set_ylabel("MAE")

    axes[0, 1].errorbar(sigma, lambda0_mean, yerr=lambda0_std, marker="o", color=TARGET_GREEN, linewidth=2.0, capsize=3)
    axes[0, 1].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[0, 1].set_title("噪声 vs 中心点误差")
    axes[0, 1].set_xlabel("噪声标准差")
    axes[0, 1].set_ylabel("误差")

    axes[1, 0].errorbar(sigma, feature_shift_mean, yerr=feature_shift_std, marker="o", color=ERR_GOLD, linewidth=2.0, capsize=3)
    axes[1, 0].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[1, 0].set_title("噪声 vs 特征位置偏移")
    axes[1, 0].set_xlabel("噪声标准差")
    axes[1, 0].set_ylabel("偏移 (nm)")

    axes[1, 1].plot(result["base_summary"]["feature_wavelength_nm"], result["base_summary"]["feature_value"], marker="o", color=MAIN_RED)
    axes[1, 1].set_title("基准特征点")
    axes[1, 1].set_xlabel("波长 (nm)")
    axes[1, 1].set_ylabel(str(result["quantity"]))

    fig.suptitle(f"{result['title_cn']} | 噪声敏感性分析", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{stem}_analysis.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["analysis_png"] = str(png_path)
    return saved


def export_angle_sensitivity_analysis(
    result: Dict[str, Any],
    *,
    prefix: str = "teaching_angle",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    stem = f"{prefix}_{result['case_id']}"
    rows = list(result["rows"])

    csv_path = output_file(f"{stem}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        headers = [
            "theta_deg",
            "mae",
            "rmse",
            "max_abs_error",
            "mean_bias",
            "lambda0_shift",
            "feature_shift_nm",
            "feature_value_shift",
        ]
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(
                ",".join(
                    [
                        f"{float(row['theta_deg']):.12g}",
                        f"{float(row['mae']):.12g}",
                        f"{float(row['rmse']):.12g}",
                        f"{float(row['max_abs_error']):.12g}",
                        f"{float(row['mean_bias']):.12g}",
                        f"{float(row['lambda0_shift']):.12g}",
                        f"{float(row['feature_shift_nm']):.12g}",
                        f"{float(row['feature_value_shift']):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{stem}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    theta = np.asarray([float(row["theta_deg"]) for row in rows], dtype=float)
    mae = np.asarray([float(row["mae"]) for row in rows], dtype=float)
    lambda0_shift = np.asarray([float(row["lambda0_shift"]) for row in rows], dtype=float)
    feature_shift = np.asarray([float(row["feature_shift_nm"]) for row in rows], dtype=float)
    feature_value_shift = np.asarray([float(row["feature_value_shift"]) for row in rows], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2))
    for ax in axes.ravel():
        _style_axis(ax)

    axes[0, 0].plot(theta, mae, marker="o", color=MAIN_RED, linewidth=2.2)
    axes[0, 0].set_title("入射角误差 vs MAE")
    axes[0, 0].set_xlabel("入射角 (°)")
    axes[0, 0].set_ylabel("MAE")

    axes[0, 1].plot(theta, lambda0_shift, marker="o", color=TARGET_GREEN, linewidth=2.2)
    axes[0, 1].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[0, 1].set_title("入射角误差 vs 中心点变化")
    axes[0, 1].set_xlabel("入射角 (°)")
    axes[0, 1].set_ylabel("变化")

    axes[1, 0].plot(theta, feature_shift, marker="o", color=ERR_GOLD, linewidth=2.2)
    axes[1, 0].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[1, 0].set_title("入射角误差 vs 特征位置偏移")
    axes[1, 0].set_xlabel("入射角 (°)")
    axes[1, 0].set_ylabel("偏移 (nm)")

    axes[1, 1].plot(theta, feature_value_shift, marker="o", color=REF_BLUE, linewidth=2.2)
    axes[1, 1].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[1, 1].set_title("入射角误差 vs 特征值变化")
    axes[1, 1].set_xlabel("入射角 (°)")
    axes[1, 1].set_ylabel("变化")

    fig.suptitle(f"{result['title_cn']} | 入射角误差分析", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{stem}_analysis.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["analysis_png"] = str(png_path)
    return saved


def export_thickness_sensitivity_analysis(
    result: Dict[str, Any],
    *,
    prefix: str = "teaching_thickness",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    selector = str(result.get("selector", "all"))
    stem = f"{prefix}_{result['case_id']}_{selector}"
    rows = list(result["rows"])

    csv_path = output_file(f"{stem}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        headers = [
            "scale",
            "relative_error_percent",
            "mae",
            "rmse",
            "max_abs_error",
            "mean_bias",
            "lambda0_shift",
            "feature_shift_nm",
            "feature_value_shift",
        ]
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(
                ",".join(
                    [
                        f"{float(row['scale']):.12g}",
                        f"{float(row['relative_error_percent']):.12g}",
                        f"{float(row['mae']):.12g}",
                        f"{float(row['rmse']):.12g}",
                        f"{float(row['max_abs_error']):.12g}",
                        f"{float(row['mean_bias']):.12g}",
                        f"{float(row['lambda0_shift']):.12g}",
                        f"{float(row['feature_shift_nm']):.12g}",
                        f"{float(row['feature_value_shift']):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{stem}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    x = np.asarray([float(row["relative_error_percent"]) for row in rows], dtype=float)
    mae = np.asarray([float(row["mae"]) for row in rows], dtype=float)
    lambda0_shift = np.asarray([float(row["lambda0_shift"]) for row in rows], dtype=float)
    feature_shift = np.asarray([float(row["feature_shift_nm"]) for row in rows], dtype=float)
    feature_value_shift = np.asarray([float(row["feature_value_shift"]) for row in rows], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2))
    for ax in axes.ravel():
        _style_axis(ax)
        ax.axvline(0.0, color="#666666", linewidth=1.0, alpha=0.85)

    axes[0, 0].plot(x, mae, marker="o", color=MAIN_RED, linewidth=2.2)
    axes[0, 0].set_title("厚度误差 vs MAE")
    axes[0, 0].set_xlabel("厚度相对误差 (%)")
    axes[0, 0].set_ylabel("MAE")

    axes[0, 1].plot(x, lambda0_shift, marker="o", color=TARGET_GREEN, linewidth=2.2)
    axes[0, 1].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[0, 1].set_title("厚度误差 vs 中心点变化")
    axes[0, 1].set_xlabel("厚度相对误差 (%)")
    axes[0, 1].set_ylabel("变化")

    axes[1, 0].plot(x, feature_shift, marker="o", color=ERR_GOLD, linewidth=2.2)
    axes[1, 0].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[1, 0].set_title("厚度误差 vs 特征位置偏移")
    axes[1, 0].set_xlabel("厚度相对误差 (%)")
    axes[1, 0].set_ylabel("偏移 (nm)")

    axes[1, 1].plot(x, feature_value_shift, marker="o", color=REF_BLUE, linewidth=2.2)
    axes[1, 1].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[1, 1].set_title("厚度误差 vs 特征值变化")
    axes[1, 1].set_xlabel("厚度相对误差 (%)")
    axes[1, 1].set_ylabel("变化")

    selector_cn = {
        "all": "全层",
        "high": "高折层",
        "low": "低折层",
        "cavity": "腔层",
    }.get(selector, selector)
    fig.suptitle(f"{result['title_cn']} | {selector_cn}厚度误差分析", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{stem}_analysis.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["analysis_png"] = str(png_path)
    return saved


def export_standard_sensitivity_bundle(
    single_ar_csv: Path | str,
    fp_single_csv: Path | str,
    high_reflector_csv: Path | str,
    *,
    prefix: str = "teaching_sensitivity_standard",
    reference_label: str = "COMSOL",
    sample_steps_nm: Sequence[float] = (0.5, 1.0, 2.0, 5.0),
    noise_sigmas: Sequence[float] = (1e-4, 5e-4, 1e-3, 5e-3),
    noise_repeats: int = 20,
    noise_seed: int = 20260505,
) -> Dict[str, Any]:
    cases = build_standard_teaching_validation_cases(
        single_ar_csv=single_ar_csv,
        fp_single_csv=fp_single_csv,
        high_reflector_csv=high_reflector_csv,
        reference_label=reference_label,
    )

    resolution_results: Dict[str, Dict[str, Any]] = {}
    noise_results: Dict[str, Dict[str, Any]] = {}
    resolution_files: Dict[str, Dict[str, str]] = {}
    noise_files: Dict[str, Dict[str, str]] = {}

    for item in cases:
        case_id = str(item["case_id"])
        overrides = dict(item.get("overrides", {}))
        resolution_results[case_id] = analyze_reference_resolution(
            case_id=case_id,
            reference_csv=item["reference_csv"],
            y_selector=item.get("y_selector"),
            quantity=item.get("quantity"),
            sample_steps_nm=sample_steps_nm,
            reference_label=reference_label,
            **overrides,
        )
        resolution_files[case_id] = export_resolution_analysis(
            resolution_results[case_id],
            prefix=f"{prefix}_resolution",
        )

        noise_results[case_id] = analyze_reference_noise(
            case_id=case_id,
            reference_csv=item["reference_csv"],
            y_selector=item.get("y_selector"),
            quantity=item.get("quantity"),
            noise_sigmas=noise_sigmas,
            repeats=noise_repeats,
            seed=noise_seed,
            reference_label=reference_label,
            **overrides,
        )
        noise_files[case_id] = export_noise_analysis(
            noise_results[case_id],
            prefix=f"{prefix}_noise",
        )

    manifest_path = output_file(f"{prefix}_manifest.json")
    manifest = {
        "reference_label": reference_label,
        "sample_steps_nm": [float(x) for x in sample_steps_nm],
        "noise_sigmas": [float(x) for x in noise_sigmas],
        "noise_repeats": int(noise_repeats),
        "resolution": {
            case_id: {
                "result": resolution_results[case_id],
                "files": resolution_files[case_id],
            }
            for case_id in resolution_results
        },
        "noise": {
            case_id: {
                "result": noise_results[case_id],
                "files": noise_files[case_id],
            }
            for case_id in noise_results
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "resolution_results": resolution_results,
        "noise_results": noise_results,
        "resolution_files": resolution_files,
        "noise_files": noise_files,
        "manifest": str(manifest_path),
    }


def export_standard_system_error_bundle(
    *,
    prefix: str = "teaching_system_error_standard",
    angle_values_deg: Sequence[float] = (0.0, 1.0, 2.0, 3.0, 5.0),
    thickness_scale_values: Sequence[float] = (0.98, 0.99, 0.995, 1.0, 1.005, 1.01, 1.02),
) -> Dict[str, Any]:
    case_configs = [
        (
            "single_ar",
            {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.52,
                "n_low": 1.38,
            },
        ),
        (
            "fp_single_halfwave",
            {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.0,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 4,
            },
        ),
        (
            "high_reflector",
            {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.5215,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 6,
            },
        ),
    ]

    angle_results: Dict[str, Dict[str, Any]] = {}
    thickness_results: Dict[str, Dict[str, Any]] = {}
    angle_files: Dict[str, Dict[str, str]] = {}
    thickness_files: Dict[str, Dict[str, str]] = {}

    for case_id, overrides in case_configs:
        angle_results[case_id] = analyze_theoretical_angle_sensitivity(
            case_id,
            theta_values_deg=angle_values_deg,
            **overrides,
        )
        angle_files[case_id] = export_angle_sensitivity_analysis(
            angle_results[case_id],
            prefix=f"{prefix}_angle",
        )

        thickness_results[case_id] = analyze_theoretical_thickness_sensitivity(
            case_id,
            scale_values=thickness_scale_values,
            selector="all",
            **overrides,
        )
        thickness_files[case_id] = export_thickness_sensitivity_analysis(
            thickness_results[case_id],
            prefix=f"{prefix}_thickness",
        )

    manifest_path = output_file(f"{prefix}_manifest.json")
    manifest = {
        "angle_values_deg": [float(x) for x in angle_values_deg],
        "thickness_scale_values": [float(x) for x in thickness_scale_values],
        "angle": {
            case_id: {"result": angle_results[case_id], "files": angle_files[case_id]}
            for case_id in angle_results
        },
        "thickness": {
            case_id: {"result": thickness_results[case_id], "files": thickness_files[case_id]}
            for case_id in thickness_results
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "angle_results": angle_results,
        "thickness_results": thickness_results,
        "angle_files": angle_files,
        "thickness_files": thickness_files,
        "manifest": str(manifest_path),
    }


def export_layerwise_thickness_error_bundle(
    *,
    prefix: str = "teaching_layerwise_thickness",
    thickness_scale_values: Sequence[float] = (0.98, 0.99, 0.995, 1.0, 1.005, 1.01, 1.02),
) -> Dict[str, Any]:
    case_configs = {
        "single_ar": {
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.52,
                "n_low": 1.38,
            },
            "selectors": ["low"],
        },
        "fp_single_halfwave": {
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.0,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 4,
            },
            "selectors": ["high", "low", "cavity"],
        },
        "high_reflector": {
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.5215,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 6,
            },
            "selectors": ["high", "low"],
        },
    }

    results: Dict[str, Dict[str, Dict[str, Any]]] = {}
    files: Dict[str, Dict[str, Dict[str, str]]] = {}
    for case_id, config in case_configs.items():
        results[case_id] = {}
        files[case_id] = {}
        for selector in config["selectors"]:
            result = analyze_theoretical_thickness_sensitivity(
                case_id,
                scale_values=thickness_scale_values,
                selector=selector,
                **dict(config["overrides"]),
            )
            results[case_id][selector] = result
            files[case_id][selector] = export_thickness_sensitivity_analysis(
                result,
                prefix=prefix,
            )

    manifest_path = output_file(f"{prefix}_manifest.json")
    manifest = {
        "thickness_scale_values": [float(x) for x in thickness_scale_values],
        "results": {
            case_id: {
                selector: {
                    "result": results[case_id][selector],
                    "files": files[case_id][selector],
                }
                for selector in results[case_id]
            }
            for case_id in results
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "results": results,
        "files": files,
        "manifest": str(manifest_path),
    }


def summarize_layerwise_thickness_sensitivity(
    bundle: Dict[str, Any],
) -> Dict[str, Any]:
    selector_cn = {
        "all": "全层",
        "high": "高折层",
        "low": "低折层",
        "cavity": "腔层",
    }
    rows: List[Dict[str, Any]] = []
    results = dict(bundle.get("results", {}))
    for case_id, selector_map in results.items():
        for selector, result in selector_map.items():
            rows_data = list(result.get("rows", []))
            worst = max(rows_data, key=lambda row: abs(float(row["relative_error_percent"]))) if rows_data else None
            title_cn = str(result.get("title_cn") or case_id)
            rows.append(
                {
                    "case_id": case_id,
                    "title_cn": title_cn,
                    "selector": selector,
                    "selector_cn": selector_cn.get(selector, selector),
                    "worst_test_percent": None if worst is None else float(worst["relative_error_percent"]),
                    "mae_at_worst": None if worst is None else float(worst["mae"]),
                    "lambda0_shift_at_worst": None if worst is None else float(worst["lambda0_shift"]),
                    "feature_shift_nm_at_worst": None if worst is None else float(worst["feature_shift_nm"]),
                }
            )
    return {
        "summary_type": "layerwise_thickness",
        "rows": rows,
    }


def export_layerwise_thickness_summary(
    summary: Dict[str, Any],
    *,
    prefix: str = "teaching_layerwise_thickness",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    rows = list(summary.get("rows", []))

    csv_path = output_file(f"{prefix}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "case_id,title_cn,selector,selector_cn,worst_test_percent,mae_at_worst,lambda0_shift_at_worst,feature_shift_nm_at_worst\n"
        )
        for row in rows:
            f.write(
                ",".join(
                    [
                        str(row["case_id"]),
                        str(row["title_cn"]),
                        str(row["selector"]),
                        str(row["selector_cn"]),
                        "" if row["worst_test_percent"] is None else f"{float(row['worst_test_percent']):.12g}",
                        "" if row["mae_at_worst"] is None else f"{float(row['mae_at_worst']):.12g}",
                        "" if row["lambda0_shift_at_worst"] is None else f"{float(row['lambda0_shift_at_worst']):.12g}",
                        "" if row["feature_shift_nm_at_worst"] is None else f"{float(row['feature_shift_nm_at_worst']):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    labels = [f"{row['title_cn']}-{row['selector_cn']}" for row in rows]
    feature_shift = np.asarray([
        0.0 if row["feature_shift_nm_at_worst"] is None else abs(float(row["feature_shift_nm_at_worst"]))
        for row in rows
    ], dtype=float)
    mae_vals = np.asarray([
        0.0 if row["mae_at_worst"] is None else float(row["mae_at_worst"])
        for row in rows
    ], dtype=float)
    x = np.arange(len(labels), dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
    for ax in axes:
        _style_axis(ax)

    axes[0].bar(x, mae_vals, color=MAIN_RED, width=0.56)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=20, ha="right")
    axes[0].set_title("分层厚度误差下的 MAE", fontweight="semibold")
    axes[0].set_ylabel("MAE")

    axes[1].bar(x, feature_shift, color=ERR_GOLD, width=0.56)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=20, ha="right")
    axes[1].set_title("分层厚度误差下的特征偏移", fontweight="semibold")
    axes[1].set_ylabel("nm")

    fig.suptitle("分层厚度误差敏感性总览", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{prefix}_overview.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["overview_png"] = str(png_path)
    return saved


def export_refined_layer_tolerance_bundle(
    *,
    prefix: str = "teaching_refined_layer_tolerance",
    thickness_scale_values: Sequence[float] = (0.99, 0.9925, 0.995, 0.9975, 1.0, 1.0025, 1.005, 1.0075, 1.01),
) -> Dict[str, Any]:
    case_configs = {
        "single_ar": {
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.52,
                "n_low": 1.38,
            },
            "selector": "low",
        },
        "fp_single_halfwave": {
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.0,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 4,
            },
            "selector": "low",
        },
        "high_reflector": {
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.5215,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 6,
            },
            "selector": "high",
        },
    }

    results: Dict[str, Dict[str, Any]] = {}
    files: Dict[str, Dict[str, str]] = {}
    for case_id, config in case_configs.items():
        result = analyze_theoretical_thickness_sensitivity(
            case_id,
            scale_values=thickness_scale_values,
            selector=str(config["selector"]),
            **dict(config["overrides"]),
        )
        results[case_id] = result
        files[case_id] = export_thickness_sensitivity_analysis(
            result,
            prefix=prefix,
        )

    manifest_path = output_file(f"{prefix}_manifest.json")
    manifest = {
        "thickness_scale_values": [float(x) for x in thickness_scale_values],
        "results": {
            case_id: {
                "result": results[case_id],
                "files": files[case_id],
            }
            for case_id in results
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "results": results,
        "files": files,
        "manifest": str(manifest_path),
    }


def summarize_refined_layer_tolerance(
    bundle: Dict[str, Any],
    *,
    mae_limit: float = 1e-2,
    lambda0_value_shift_limit: float = 1e-2,
    feature_shift_limit_nm: float = 1.0,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    results = dict(bundle.get("results", {}))
    for case_id, result in results.items():
        case_rows = list(result.get("rows", []))
        passed_rows = [
            row
            for row in case_rows
            if float(row["mae"]) <= float(mae_limit)
            and abs(float(row["lambda0_shift"])) <= float(lambda0_value_shift_limit)
            and abs(float(row["feature_shift_nm"])) <= float(feature_shift_limit_nm)
        ]
        title_cn = str(result.get("title_cn") or case_id)
        selector = str(result.get("selector", "all"))
        selector_cn = SELECTOR_CN.get(selector, selector)

        if passed_rows:
            min_scale_row = min(passed_rows, key=lambda row: float(row["scale"]))
            max_scale_row = max(passed_rows, key=lambda row: float(row["scale"]))
            best_row = min(
                passed_rows,
                key=lambda row: (
                    abs(float(row["feature_shift_nm"])),
                    float(row["mae"]),
                    abs(float(row["lambda0_shift"])),
                ),
            )
            recommended_min_percent = float(min_scale_row["relative_error_percent"])
            recommended_max_percent = float(max_scale_row["relative_error_percent"])
            recommended_min_scale = float(min_scale_row["scale"])
            recommended_max_scale = float(max_scale_row["scale"])
        else:
            best_row = min(
                case_rows,
                key=lambda row: (
                    abs(float(row["feature_shift_nm"])),
                    float(row["mae"]),
                    abs(float(row["lambda0_shift"])),
                ),
            ) if case_rows else None
            recommended_min_percent = None
            recommended_max_percent = None
            recommended_min_scale = None
            recommended_max_scale = None

        rows.append(
            {
                "case_id": case_id,
                "title_cn": title_cn,
                "selector": selector,
                "selector_cn": selector_cn,
                "passed_count": len(passed_rows),
                "recommended_min_percent": recommended_min_percent,
                "recommended_max_percent": recommended_max_percent,
                "recommended_min_scale": recommended_min_scale,
                "recommended_max_scale": recommended_max_scale,
                "best_test_percent": None if best_row is None else float(best_row["relative_error_percent"]),
                "best_test_scale": None if best_row is None else float(best_row["scale"]),
                "best_test_mae": None if best_row is None else float(best_row["mae"]),
                "best_test_lambda0_shift": None if best_row is None else float(best_row["lambda0_shift"]),
                "best_test_feature_shift_nm": None if best_row is None else float(best_row["feature_shift_nm"]),
            }
        )

    return {
        "summary_type": "refined_layer_tolerance",
        "criteria": {
            "mae_limit": float(mae_limit),
            "lambda0_value_shift_limit": float(lambda0_value_shift_limit),
            "feature_shift_limit_nm": float(feature_shift_limit_nm),
        },
        "rows": rows,
    }


def export_refined_layer_tolerance_summary(
    summary: Dict[str, Any],
    *,
    prefix: str = "teaching_refined_layer_tolerance",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    rows = list(summary.get("rows", []))

    csv_path = output_file(f"{prefix}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "case_id,title_cn,selector,selector_cn,passed_count,"
            "recommended_min_percent,recommended_max_percent,recommended_min_scale,recommended_max_scale,"
            "best_test_percent,best_test_scale,best_test_mae,best_test_lambda0_shift,best_test_feature_shift_nm\n"
        )
        for row in rows:
            f.write(
                ",".join(
                    [
                        str(row["case_id"]),
                        str(row["title_cn"]),
                        str(row["selector"]),
                        str(row["selector_cn"]),
                        str(int(row["passed_count"])),
                        "" if row["recommended_min_percent"] is None else f"{float(row['recommended_min_percent']):.12g}",
                        "" if row["recommended_max_percent"] is None else f"{float(row['recommended_max_percent']):.12g}",
                        "" if row["recommended_min_scale"] is None else f"{float(row['recommended_min_scale']):.12g}",
                        "" if row["recommended_max_scale"] is None else f"{float(row['recommended_max_scale']):.12g}",
                        "" if row["best_test_percent"] is None else f"{float(row['best_test_percent']):.12g}",
                        "" if row["best_test_scale"] is None else f"{float(row['best_test_scale']):.12g}",
                        "" if row["best_test_mae"] is None else f"{float(row['best_test_mae']):.12g}",
                        "" if row["best_test_lambda0_shift"] is None else f"{float(row['best_test_lambda0_shift']):.12g}",
                        "" if row["best_test_feature_shift_nm"] is None else f"{float(row['best_test_feature_shift_nm']):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}_summary.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        criteria = dict(summary.get("criteria", {}))
        f.write("精细分层厚度容差总结\n")
        f.write("=" * 72 + "\n")
        f.write(
            f"判据: MAE <= {criteria.get('mae_limit')} | "
            f"中心点幅值偏差 <= {criteria.get('lambda0_value_shift_limit')} | "
            f"特征位置偏移 <= {criteria.get('feature_shift_limit_nm')} nm\n\n"
        )
        for row in rows:
            f.write(f"{row['title_cn']} | {row['selector_cn']}\n")
            if row["passed_count"] > 0:
                f.write(
                    f"  推荐容差区间: {float(row['recommended_min_percent']):+.3f}% ~ "
                    f"{float(row['recommended_max_percent']):+.3f}%\n"
                )
            else:
                f.write("  推荐容差区间: 当前测试点内未找到满足判据的区间\n")
            f.write(
                f"  最佳测试点: {float(row['best_test_percent']):+.3f}% | "
                f"MAE={float(row['best_test_mae']):.6g} | "
                f"中心点幅值偏差={float(row['best_test_lambda0_shift']):+.6g} | "
                f"特征位置偏移={float(row['best_test_feature_shift_nm']):+.3f} nm\n\n"
            )
    saved["txt"] = str(txt_path)

    labels = [f"{row['title_cn']}-{row['selector_cn']}" for row in rows]
    y = np.arange(len(labels), dtype=float)
    centers = np.asarray([
        0.0 if row["recommended_min_percent"] is None or row["recommended_max_percent"] is None
        else (float(row["recommended_min_percent"]) + float(row["recommended_max_percent"])) / 2.0
        for row in rows
    ], dtype=float)
    lower_err = np.asarray([
        0.0 if row["recommended_min_percent"] is None or row["recommended_max_percent"] is None
        else centers[i] - float(row["recommended_min_percent"])
        for i, row in enumerate(rows)
    ], dtype=float)
    upper_err = np.asarray([
        0.0 if row["recommended_min_percent"] is None or row["recommended_max_percent"] is None
        else float(row["recommended_max_percent"]) - centers[i]
        for i, row in enumerate(rows)
    ], dtype=float)
    mae_vals = np.asarray([
        0.0 if row["best_test_mae"] is None else float(row["best_test_mae"])
        for row in rows
    ], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8))
    for ax in axes:
        _style_axis(ax)

    axes[0].errorbar(
        centers,
        y,
        xerr=np.vstack([lower_err, upper_err]),
        fmt="o",
        color=TARGET_GREEN,
        ecolor=TARGET_GREEN,
        elinewidth=2.0,
        capsize=4,
    )
    axes[0].axvline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(labels)
    axes[0].set_xlabel("允许厚度相对误差 (%)")
    axes[0].set_title("最敏感层允许容差区间", fontweight="semibold")

    axes[1].barh(y, mae_vals, color=MAIN_RED, height=0.56)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels(labels)
    axes[1].set_xlabel("MAE")
    axes[1].set_title("最佳测试点误差水平", fontweight="semibold")

    fig.suptitle("精细分层厚度容差总览", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{prefix}_overview.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["overview_png"] = str(png_path)
    return saved


def export_standard_refined_angle_bundle(
    *,
    prefix: str = "teaching_refined_angle_standard",
) -> Dict[str, Any]:
    case_configs = {
        "single_ar": {
            "theta_values_deg": (0.0, 0.2, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0),
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.52,
                "n_low": 1.38,
            },
        },
        "fp_single_halfwave": {
            "theta_values_deg": (0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5),
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.0,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 4,
            },
        },
        "high_reflector": {
            "theta_values_deg": (0.0, 0.2, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0),
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.5215,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 6,
            },
        },
    }

    results: Dict[str, Dict[str, Any]] = {}
    files: Dict[str, Dict[str, str]] = {}
    for case_id, config in case_configs.items():
        result = analyze_theoretical_angle_sensitivity(
            case_id,
            theta_values_deg=config["theta_values_deg"],
            **dict(config["overrides"]),
        )
        results[case_id] = result
        files[case_id] = export_angle_sensitivity_analysis(
            result,
            prefix=prefix,
        )

    manifest_path = output_file(f"{prefix}_manifest.json")
    manifest = {
        "results": {
            case_id: {
                "theta_values_deg": [float(x) for x in case_configs[case_id]["theta_values_deg"]],
                "result": results[case_id],
                "files": files[case_id],
            }
            for case_id in results
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "results": results,
        "files": files,
        "manifest": str(manifest_path),
    }


def summarize_refined_angle_tolerance(
    bundle: Dict[str, Any],
    *,
    mae_limit: float = 1e-2,
    lambda0_value_shift_limit: float = 1e-2,
    feature_shift_limit_nm: float = 1.0,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    results = dict(bundle.get("results", {}))
    for case_id, result in results.items():
        case_rows = list(result.get("rows", []))
        passed_rows = [
            row
            for row in case_rows
            if float(row["mae"]) <= float(mae_limit)
            and abs(float(row["lambda0_shift"])) <= float(lambda0_value_shift_limit)
            and abs(float(row["feature_shift_nm"])) <= float(feature_shift_limit_nm)
        ]
        title_cn = str(result.get("title_cn") or case_id)

        if passed_rows:
            max_row = max(passed_rows, key=lambda row: float(row["theta_deg"]))
            best_row = min(
                passed_rows,
                key=lambda row: (
                    abs(float(row["feature_shift_nm"])),
                    float(row["mae"]),
                    abs(float(row["lambda0_shift"])),
                ),
            )
            recommended_max_theta_deg = float(max_row["theta_deg"])
        else:
            best_row = min(
                case_rows,
                key=lambda row: (
                    abs(float(row["feature_shift_nm"])),
                    float(row["mae"]),
                    abs(float(row["lambda0_shift"])),
                ),
            ) if case_rows else None
            recommended_max_theta_deg = None

        rows.append(
            {
                "case_id": case_id,
                "title_cn": title_cn,
                "passed_count": len(passed_rows),
                "recommended_max_theta_deg": recommended_max_theta_deg,
                "best_test_theta_deg": None if best_row is None else float(best_row["theta_deg"]),
                "best_test_mae": None if best_row is None else float(best_row["mae"]),
                "best_test_lambda0_shift": None if best_row is None else float(best_row["lambda0_shift"]),
                "best_test_feature_shift_nm": None if best_row is None else float(best_row["feature_shift_nm"]),
            }
        )

    return {
        "summary_type": "refined_angle_tolerance",
        "criteria": {
            "mae_limit": float(mae_limit),
            "lambda0_value_shift_limit": float(lambda0_value_shift_limit),
            "feature_shift_limit_nm": float(feature_shift_limit_nm),
        },
        "rows": rows,
    }


def export_refined_angle_tolerance_summary(
    summary: Dict[str, Any],
    *,
    prefix: str = "teaching_refined_angle_tolerance",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    rows = list(summary.get("rows", []))

    csv_path = output_file(f"{prefix}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "case_id,title_cn,passed_count,recommended_max_theta_deg,"
            "best_test_theta_deg,best_test_mae,best_test_lambda0_shift,best_test_feature_shift_nm\n"
        )
        for row in rows:
            f.write(
                ",".join(
                    [
                        str(row["case_id"]),
                        str(row["title_cn"]),
                        str(int(row["passed_count"])),
                        "" if row["recommended_max_theta_deg"] is None else f"{float(row['recommended_max_theta_deg']):.12g}",
                        "" if row["best_test_theta_deg"] is None else f"{float(row['best_test_theta_deg']):.12g}",
                        "" if row["best_test_mae"] is None else f"{float(row['best_test_mae']):.12g}",
                        "" if row["best_test_lambda0_shift"] is None else f"{float(row['best_test_lambda0_shift']):.12g}",
                        "" if row["best_test_feature_shift_nm"] is None else f"{float(row['best_test_feature_shift_nm']):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}_summary.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        criteria = dict(summary.get("criteria", {}))
        f.write("精细角度误差容差总结\n")
        f.write("=" * 72 + "\n")
        f.write(
            f"判据: MAE <= {criteria.get('mae_limit')} | "
            f"中心点幅值偏差 <= {criteria.get('lambda0_value_shift_limit')} | "
            f"特征位置偏移 <= {criteria.get('feature_shift_limit_nm')} nm\n\n"
        )
        for row in rows:
            f.write(f"{row['title_cn']}\n")
            if row["passed_count"] > 0:
                f.write(f"  推荐最大入射角误差: ±{float(row['recommended_max_theta_deg']):.3f}°\n")
            else:
                f.write("  推荐最大入射角误差: 当前测试点内未找到满足判据的范围\n")
            f.write(
                f"  最佳测试点: {float(row['best_test_theta_deg']):.3f}° | "
                f"MAE={float(row['best_test_mae']):.6g} | "
                f"中心点幅值偏差={float(row['best_test_lambda0_shift']):+.6g} | "
                f"特征位置偏移={float(row['best_test_feature_shift_nm']):+.3f} nm\n\n"
            )
    saved["txt"] = str(txt_path)

    labels = [str(row["title_cn"]) for row in rows]
    y = np.arange(len(labels), dtype=float)
    angle_vals = np.asarray([
        0.0 if row["recommended_max_theta_deg"] is None else float(row["recommended_max_theta_deg"])
        for row in rows
    ], dtype=float)
    mae_vals = np.asarray([
        0.0 if row["best_test_mae"] is None else float(row["best_test_mae"])
        for row in rows
    ], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8))
    for ax in axes:
        _style_axis(ax)

    axes[0].barh(y, angle_vals, color=TARGET_GREEN, height=0.56)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(labels)
    axes[0].set_xlabel("允许最大入射角误差 (°)")
    axes[0].set_title("精细角度容差", fontweight="semibold")

    axes[1].barh(y, mae_vals, color=MAIN_RED, height=0.56)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels(labels)
    axes[1].set_xlabel("MAE")
    axes[1].set_title("最佳测试点误差水平", fontweight="semibold")

    fig.suptitle("精细角度容差总览", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{prefix}_overview.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["overview_png"] = str(png_path)
    return saved


def export_standard_refined_tolerance_bundle(
    *,
    prefix: str = "teaching_refined_tolerance_standard",
) -> Dict[str, Any]:
    case_configs = {
        "single_ar": {
            "selector": "low",
            "scale_values": (
                0.994, 0.995, 0.996, 0.997, 0.998, 0.999,
                1.0,
                1.001, 1.002, 1.003, 1.004, 1.005, 1.006,
            ),
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.52,
                "n_low": 1.38,
            },
        },
        "fp_single_halfwave": {
            "selector": "low",
            "scale_values": (
                0.9975, 0.9980, 0.9985, 0.9990, 0.9995,
                1.0,
                1.0005, 1.0010, 1.0015, 1.0020, 1.0025,
            ),
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.0,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 4,
            },
        },
        "high_reflector": {
            "selector": "high",
            "scale_values": (
                0.9925, 0.9930, 0.9935, 0.9940, 0.9945, 0.9950,
                0.9975, 1.0, 1.0025,
                1.0050, 1.0055, 1.0060, 1.0065, 1.0070, 1.0075,
            ),
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.5215,
                "n_low": 1.45,
                "n_high_2": 2.10,
                "periods": 6,
            },
        },
    }

    results: Dict[str, Dict[str, Any]] = {}
    files: Dict[str, Dict[str, str]] = {}
    for case_id, config in case_configs.items():
        result = analyze_theoretical_thickness_sensitivity(
            case_id,
            scale_values=config["scale_values"],
            selector=str(config["selector"]),
            **dict(config["overrides"]),
        )
        results[case_id] = result
        files[case_id] = export_thickness_sensitivity_analysis(
            result,
            prefix=prefix,
        )

    manifest_path = output_file(f"{prefix}_manifest.json")
    manifest = {
        "results": {
            case_id: {
                "selector": case_configs[case_id]["selector"],
                "scale_values": [float(x) for x in case_configs[case_id]["scale_values"]],
                "result": results[case_id],
                "files": files[case_id],
            }
            for case_id in results
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "results": results,
        "files": files,
        "manifest": str(manifest_path),
    }


def summarize_overall_performance_table(
    validation_bundle: Dict[str, Any],
    stability_summary: Dict[str, Any],
    system_error_bundle: Dict[str, Any],
    layerwise_thickness_summary: Dict[str, Any] | None = None,
    refined_tolerance_summary: Dict[str, Any] | None = None,
    refined_angle_summary: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    validation_map = {
        str(item["case_id"]): item
        for item in validation_bundle.get("results", [])
    }
    stability_map = dict(stability_summary.get("case_summaries", {}))
    angle_map = dict(system_error_bundle.get("angle_results", {}))
    thickness_map = dict(system_error_bundle.get("thickness_results", {}))
    layerwise_rows = list((layerwise_thickness_summary or {}).get("rows", []))
    refined_rows = list((refined_tolerance_summary or {}).get("rows", []))
    refined_angle_rows = list((refined_angle_summary or {}).get("rows", []))
    layerwise_map: Dict[str, List[Dict[str, Any]]] = {}
    for row in layerwise_rows:
        layerwise_map.setdefault(str(row["case_id"]), []).append(row)
    refined_map = {str(row["case_id"]): row for row in refined_rows}
    refined_angle_map = {str(row["case_id"]): row for row in refined_angle_rows}
    case_ids = sorted(set(validation_map) | set(stability_map) | set(angle_map) | set(thickness_map))

    performance_rows = summarize_performance_conclusions(validation_bundle, stability_summary)["rows"]
    performance_map = {str(item["case_id"]): item for item in performance_rows}

    rows: List[Dict[str, Any]] = []
    for case_id in case_ids:
        validation_item = validation_map.get(case_id, {})
        validation_summary = validation_item.get("summary", {})
        stability_item = stability_map.get(case_id, {})
        angle_rows = list(angle_map.get(case_id, {}).get("rows", []))
        thickness_rows = list(thickness_map.get(case_id, {}).get("rows", []))

        max_angle_row = max(angle_rows, key=lambda row: abs(float(row["theta_deg"]))) if angle_rows else None
        max_thickness_row = max(
            thickness_rows,
            key=lambda row: abs(float(row["relative_error_percent"])),
        ) if thickness_rows else None
        layerwise_candidates = layerwise_map.get(case_id, [])
        most_sensitive_layer = max(
            layerwise_candidates,
            key=lambda row: abs(float(row["mae_at_worst"])) if row.get("mae_at_worst") is not None else -1.0,
        ) if layerwise_candidates else None
        refined_item = refined_map.get(case_id)
        refined_angle_item = refined_angle_map.get(case_id)

        title_cn = str(
            validation_item.get("title_cn")
            or stability_item.get("title_cn")
            or angle_map.get(case_id, {}).get("title_cn")
            or thickness_map.get(case_id, {}).get("title_cn")
            or case_id
        )

        rows.append(
            {
                "case_id": case_id,
                "title_cn": title_cn,
                "quantity": str(validation_item.get("quantity", "")),
                "validation_mae": float(validation_summary.get("mae", np.nan)),
                "validation_rmse": float(validation_summary.get("rmse", np.nan)),
                "validation_lambda0_error": float(validation_summary.get("lambda0_error", np.nan)),
                "max_stable_sampling_step_nm": stability_item.get("resolution", {}).get("max_stable_sampling_step_nm"),
                "max_stable_noise_sigma": stability_item.get("noise", {}).get("max_stable_noise_sigma"),
                "angle_max_test_deg": None if max_angle_row is None else float(max_angle_row["theta_deg"]),
                "angle_mae_at_max_test": None if max_angle_row is None else float(max_angle_row["mae"]),
                "angle_feature_shift_nm_at_max_test": None if max_angle_row is None else float(max_angle_row["feature_shift_nm"]),
                "thickness_max_test_percent": None if max_thickness_row is None else float(max_thickness_row["relative_error_percent"]),
                "thickness_mae_at_max_test": None if max_thickness_row is None else float(max_thickness_row["mae"]),
                "thickness_feature_shift_nm_at_max_test": None if max_thickness_row is None else float(max_thickness_row["feature_shift_nm"]),
                "most_sensitive_layer_cn": None if most_sensitive_layer is None else str(most_sensitive_layer["selector_cn"]),
                "most_sensitive_layer_mae": None if most_sensitive_layer is None else float(most_sensitive_layer["mae_at_worst"]),
                "most_sensitive_layer_feature_shift_nm": None if most_sensitive_layer is None else float(most_sensitive_layer["feature_shift_nm_at_worst"]),
                "refined_tolerance_min_percent": None if refined_item is None else refined_item.get("recommended_min_percent"),
                "refined_tolerance_max_percent": None if refined_item is None else refined_item.get("recommended_max_percent"),
                "refined_tolerance_best_mae": None if refined_item is None else refined_item.get("best_test_mae"),
                "refined_angle_max_deg": None if refined_angle_item is None else refined_angle_item.get("recommended_max_theta_deg"),
                "refined_angle_best_mae": None if refined_angle_item is None else refined_angle_item.get("best_test_mae"),
                "status_cn": str(performance_map.get(case_id, {}).get("status_cn", "")),
            }
        )

    return {
        "summary_type": "overall_performance_table",
        "profile": stability_summary.get("profile"),
        "rows": rows,
    }


def export_overall_performance_table(
    summary: Dict[str, Any],
    *,
    prefix: str = "teaching_overall_performance",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    rows = list(summary.get("rows", []))

    csv_path = output_file(f"{prefix}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "case_id,title_cn,quantity,validation_mae,validation_rmse,validation_lambda0_error,"
            "max_stable_sampling_step_nm,max_stable_noise_sigma,"
            "angle_max_test_deg,angle_mae_at_max_test,angle_feature_shift_nm_at_max_test,"
            "thickness_max_test_percent,thickness_mae_at_max_test,thickness_feature_shift_nm_at_max_test,"
            "most_sensitive_layer_cn,most_sensitive_layer_mae,most_sensitive_layer_feature_shift_nm,"
            "refined_tolerance_min_percent,refined_tolerance_max_percent,refined_tolerance_best_mae,"
            "refined_angle_max_deg,refined_angle_best_mae,status_cn\n"
        )
        for row in rows:
            fields = [
                str(row["case_id"]),
                str(row["title_cn"]),
                str(row["quantity"]),
                f"{float(row['validation_mae']):.12g}",
                f"{float(row['validation_rmse']):.12g}",
                f"{float(row['validation_lambda0_error']):.12g}",
                "" if row["max_stable_sampling_step_nm"] is None else f"{float(row['max_stable_sampling_step_nm']):.12g}",
                "" if row["max_stable_noise_sigma"] is None else f"{float(row['max_stable_noise_sigma']):.12g}",
                "" if row["angle_max_test_deg"] is None else f"{float(row['angle_max_test_deg']):.12g}",
                "" if row["angle_mae_at_max_test"] is None else f"{float(row['angle_mae_at_max_test']):.12g}",
                "" if row["angle_feature_shift_nm_at_max_test"] is None else f"{float(row['angle_feature_shift_nm_at_max_test']):.12g}",
                "" if row["thickness_max_test_percent"] is None else f"{float(row['thickness_max_test_percent']):.12g}",
                "" if row["thickness_mae_at_max_test"] is None else f"{float(row['thickness_mae_at_max_test']):.12g}",
                "" if row["thickness_feature_shift_nm_at_max_test"] is None else f"{float(row['thickness_feature_shift_nm_at_max_test']):.12g}",
                "" if row["most_sensitive_layer_cn"] is None else str(row["most_sensitive_layer_cn"]),
                "" if row["most_sensitive_layer_mae"] is None else f"{float(row['most_sensitive_layer_mae']):.12g}",
                "" if row["most_sensitive_layer_feature_shift_nm"] is None else f"{float(row['most_sensitive_layer_feature_shift_nm']):.12g}",
                "" if row["refined_tolerance_min_percent"] is None else f"{float(row['refined_tolerance_min_percent']):.12g}",
                "" if row["refined_tolerance_max_percent"] is None else f"{float(row['refined_tolerance_max_percent']):.12g}",
                "" if row["refined_tolerance_best_mae"] is None else f"{float(row['refined_tolerance_best_mae']):.12g}",
                "" if row["refined_angle_max_deg"] is None else f"{float(row['refined_angle_max_deg']):.12g}",
                "" if row["refined_angle_best_mae"] is None else f"{float(row['refined_angle_best_mae']):.12g}",
                str(row["status_cn"]),
            ]
            f.write(",".join(fields) + "\n")
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}_summary.txt")
    lines = [
        "综合性能指标总表",
        "=" * 80,
    ]
    for row in rows:
        step_text = "未通过" if row["max_stable_sampling_step_nm"] is None else f"{float(row['max_stable_sampling_step_nm']):.3f} nm"
        noise_text = "未通过" if row["max_stable_noise_sigma"] is None else f"{float(row['max_stable_noise_sigma']):.6g}"
        angle_text = "无" if row["angle_max_test_deg"] is None else f"{float(row['angle_max_test_deg']):.3f}°"
        thickness_text = "无" if row["thickness_max_test_percent"] is None else f"{float(row['thickness_max_test_percent']):+.3f}%"
        layer_text = "无" if row["most_sensitive_layer_cn"] is None else str(row["most_sensitive_layer_cn"])
        lines.extend(
            [
                f"{row['title_cn']} ({row['case_id']})",
                f"  验证MAE = {float(row['validation_mae']):.4e}",
                f"  验证RMSE = {float(row['validation_rmse']):.4e}",
                f"  验证中心点误差 = {float(row['validation_lambda0_error']):+.4e}",
                f"  最大稳定采样步长 = {step_text}",
                f"  最大稳定噪声标准差 = {noise_text}",
                f"  最大角度测试点 = {angle_text}",
                f"  厚度最大测试点 = {thickness_text}",
                f"  最敏感层 = {layer_text}",
                f"  结论 = {row['status_cn']}",
                "",
            ]
        )
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    labels = [str(row["title_cn"]) for row in rows]
    mae_vals = np.asarray([float(row["validation_mae"]) for row in rows], dtype=float)
    angle_vals = np.asarray([
        0.0 if row["angle_feature_shift_nm_at_max_test"] is None else abs(float(row["angle_feature_shift_nm_at_max_test"]))
        for row in rows
    ], dtype=float)
    thickness_vals = np.asarray([
        0.0 if row["most_sensitive_layer_feature_shift_nm"] is None else abs(float(row["most_sensitive_layer_feature_shift_nm"]))
        for row in rows
    ], dtype=float)
    x = np.arange(len(labels), dtype=float)

    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.6))
    for ax in axes:
        _style_axis(ax)

    axes[0].bar(x, mae_vals, color=MAIN_RED, width=0.56)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=12, ha="right")
    axes[0].set_title("验证误差", fontweight="semibold")
    axes[0].set_ylabel("MAE")

    axes[1].bar(x, angle_vals, color=TARGET_GREEN, width=0.56)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=12, ha="right")
    axes[1].set_title("最大角度测试下特征偏移", fontweight="semibold")
    axes[1].set_ylabel("nm")

    axes[2].bar(x, thickness_vals, color=ERR_GOLD, width=0.56)
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels, rotation=12, ha="right")
    axes[2].set_title("最敏感层厚度误差下特征偏移", fontweight="semibold")
    axes[2].set_ylabel("nm")

    fig.suptitle("三类结构综合性能总览", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{prefix}_overview.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["overview_png"] = str(png_path)
    return saved


def export_competition_ready_summary(
    overall_summary: Dict[str, Any],
    *,
    prefix: str = "teaching_competition_ready",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    rows = list(overall_summary.get("rows", []))

    json_path = output_file(f"{prefix}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(overall_summary, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}_summary.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("教学薄膜平台验证与性能指标总结\n")
        f.write("=" * 80 + "\n")
        f.write("当前总结基于三类标准结构：单层减反膜、F-P 单半波滤光片、高反膜。\n")
        f.write("已完成理论- COMSOL 对照、分辨率影响、噪声敏感性、角度误差、厚度误差以及最敏感层容差分析。\n\n")
        for row in rows:
            f.write(f"{row['title_cn']}\n")
            f.write(f"  验证误差: MAE={float(row['validation_mae']):.6g}, RMSE={float(row['validation_rmse']):.6g}\n")
            if row.get("max_stable_sampling_step_nm") is not None:
                f.write(f"  稳定采样步长: 最大 {float(row['max_stable_sampling_step_nm']):.3g} nm\n")
            if row.get("max_stable_noise_sigma") is not None:
                f.write(f"  稳定噪声水平: 最大 sigma={float(row['max_stable_noise_sigma']):.3g}\n")
            if row.get("refined_angle_max_deg") is not None:
                f.write(f"  推荐最大入射角误差: ±{float(row['refined_angle_max_deg']):.3f}°\n")
            if row.get("most_sensitive_layer_cn") is not None:
                f.write(f"  最敏感层: {row['most_sensitive_layer_cn']}\n")
            if row.get("refined_tolerance_min_percent") is not None and row.get("refined_tolerance_max_percent") is not None:
                f.write(
                    f"  最敏感层精细容差: {float(row['refined_tolerance_min_percent']):+.3f}% ~ "
                    f"{float(row['refined_tolerance_max_percent']):+.3f}%\n"
                )
            f.write(f"  综合状态: {row['status_cn']}\n\n")
    saved["txt"] = str(txt_path)
    return saved


def export_final_delivery_bundle(
    *,
    single_ar_csv: Path | str,
    fp_single_csv: Path | str,
    high_reflector_csv: Path | str,
    prefix: str = "teaching_final_delivery",
    reference_label: str = "COMSOL",
) -> Dict[str, Any]:
    validation = export_standard_teaching_validation_bundle(
        single_ar_csv=single_ar_csv,
        fp_single_csv=fp_single_csv,
        high_reflector_csv=high_reflector_csv,
        prefix=f"{prefix}_validation",
        reference_label=reference_label,
    )

    sensitivity = export_standard_sensitivity_bundle(
        single_ar_csv=single_ar_csv,
        fp_single_csv=fp_single_csv,
        high_reflector_csv=high_reflector_csv,
        prefix=f"{prefix}_sensitivity",
        reference_label=reference_label,
    )
    stability = summarize_sensitivity_stability(sensitivity, profile="competition_balanced")
    stability_files = export_sensitivity_stability_summary(stability, prefix=f"{prefix}_stability")

    system_error = export_standard_system_error_bundle(prefix=f"{prefix}_system_error")
    layerwise = export_layerwise_thickness_error_bundle(prefix=f"{prefix}_layerwise")
    layerwise_summary = summarize_layerwise_thickness_sensitivity(layerwise)
    layerwise_files = export_layerwise_thickness_summary(layerwise_summary, prefix=f"{prefix}_layerwise")

    refined_thickness = export_standard_refined_tolerance_bundle(prefix=f"{prefix}_refined_thickness")
    refined_thickness_summary = summarize_refined_layer_tolerance(
        refined_thickness,
        mae_limit=2e-2,
        lambda0_value_shift_limit=2e-2,
        feature_shift_limit_nm=2.0,
    )
    refined_thickness_files = export_refined_layer_tolerance_summary(
        refined_thickness_summary,
        prefix=f"{prefix}_refined_thickness",
    )

    refined_angle = export_standard_refined_angle_bundle(prefix=f"{prefix}_refined_angle")
    refined_angle_summary = summarize_refined_angle_tolerance(
        refined_angle,
        mae_limit=2e-2,
        lambda0_value_shift_limit=2e-2,
        feature_shift_limit_nm=2.0,
    )
    refined_angle_files = export_refined_angle_tolerance_summary(
        refined_angle_summary,
        prefix=f"{prefix}_refined_angle",
    )

    overall = summarize_overall_performance_table(
        validation,
        stability,
        system_error,
        layerwise_thickness_summary=layerwise_summary,
        refined_tolerance_summary=refined_thickness_summary,
        refined_angle_summary=refined_angle_summary,
    )
    overall_files = export_overall_performance_table(overall, prefix=f"{prefix}_overall")
    competition_files = export_competition_ready_summary(overall, prefix=f"{prefix}_competition")

    manifest = {
        "reference_label": reference_label,
        "inputs": {
            "single_ar_csv": str(Path(single_ar_csv)),
            "fp_single_csv": str(Path(fp_single_csv)),
            "high_reflector_csv": str(Path(high_reflector_csv)),
        },
        "validation_manifest": validation["manifest"],
        "stability_files": stability_files,
        "layerwise_files": layerwise_files,
        "refined_thickness_files": refined_thickness_files,
        "refined_angle_files": refined_angle_files,
        "overall_files": overall_files,
        "competition_files": competition_files,
    }
    manifest_path = output_file(f"{prefix}_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    index_path = output_file(f"{prefix}_index.txt")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("教学薄膜平台最终交付总包索引\n")
        f.write("=" * 80 + "\n")
        f.write(f"单层减反膜 CSV: {Path(single_ar_csv)}\n")
        f.write(f"F-P 滤光片 CSV: {Path(fp_single_csv)}\n")
        f.write(f"高反膜 CSV: {Path(high_reflector_csv)}\n\n")
        f.write(f"验证总包: {validation['manifest']}\n")
        f.write(f"稳定性总结: {stability_files['json']}\n")
        f.write(f"分层厚度总结: {layerwise_files['json']}\n")
        f.write(f"精细厚度容差: {refined_thickness_files['json']}\n")
        f.write(f"精细角度容差: {refined_angle_files['json']}\n")
        f.write(f"综合性能总表: {overall_files['json']}\n")
        f.write(f"竞赛口径总结: {competition_files['txt']}\n")
    return {
        "manifest": str(manifest_path),
        "index": str(index_path),
        "overall_summary": overall,
        "overall_files": overall_files,
        "competition_files": competition_files,
    }


def summarize_sensitivity_stability(
    sensitivity_bundle: Dict[str, Any],
    *,
    profile: str | None = None,
    resolution_mae_limit: float = 1e-2,
    resolution_lambda0_error_limit_nm: float = 1.0,
    resolution_feature_shift_limit_nm: float = 1.0,
    noise_mae_limit: float = 1e-2,
    noise_lambda0_error_std_limit_nm: float = 1.0,
    noise_feature_shift_std_limit_nm: float = 1.0,
) -> Dict[str, Any]:
    if profile is not None:
        profile_key = str(profile).strip().lower()
        if profile_key not in STABILITY_PROFILES:
            raise ValueError(f"Unsupported stability profile: {profile}")
        selected = STABILITY_PROFILES[profile_key]
        resolution_mae_limit = float(selected["resolution_mae_limit"])
        resolution_lambda0_error_limit_nm = float(selected["resolution_lambda0_error_limit_nm"])
        resolution_feature_shift_limit_nm = float(selected["resolution_feature_shift_limit_nm"])
        noise_mae_limit = float(selected["noise_mae_limit"])
        noise_lambda0_error_std_limit_nm = float(selected["noise_lambda0_error_std_limit_nm"])
        noise_feature_shift_std_limit_nm = float(selected["noise_feature_shift_std_limit_nm"])

    resolution_results = dict(sensitivity_bundle.get("resolution_results", {}))
    noise_results = dict(sensitivity_bundle.get("noise_results", {}))
    cases = sorted(set(resolution_results.keys()) | set(noise_results.keys()))

    case_summaries: Dict[str, Dict[str, Any]] = {}
    for case_id in cases:
        resolution_rows = list(resolution_results.get(case_id, {}).get("rows", []))
        noise_rows = list(noise_results.get(case_id, {}).get("rows", []))

        resolution_pass_rows = [
            row
            for row in resolution_rows
            if str(row.get("mode")) == "resampled"
            and float(row["mae"]) <= float(resolution_mae_limit)
            and abs(float(row["lambda0_error"])) <= float(resolution_lambda0_error_limit_nm)
            and abs(float(row["feature_shift_nm"])) <= float(resolution_feature_shift_limit_nm)
        ]
        max_resolution_step_nm = (
            max(float(row["sampling_step_nm"]) for row in resolution_pass_rows)
            if resolution_pass_rows
            else None
        )

        noise_pass_rows = [
            row
            for row in noise_rows
            if float(row["mae_mean"]) <= float(noise_mae_limit)
            and float(row["lambda0_error_std"]) <= float(noise_lambda0_error_std_limit_nm)
            and float(row["feature_shift_nm_std"]) <= float(noise_feature_shift_std_limit_nm)
        ]
        max_noise_sigma = (
            max(float(row["noise_sigma"]) for row in noise_pass_rows)
            if noise_pass_rows
            else None
        )

        title_cn = ""
        if case_id in resolution_results:
            title_cn = str(resolution_results[case_id].get("title_cn") or "")
        if not title_cn and case_id in noise_results:
            title_cn = str(noise_results[case_id].get("title_cn") or "")

        case_summaries[case_id] = {
            "case_id": case_id,
            "title_cn": title_cn,
            "resolution": {
                "max_stable_sampling_step_nm": max_resolution_step_nm,
                "passed_steps_nm": [float(row["sampling_step_nm"]) for row in resolution_pass_rows],
                "criteria": {
                    "mae_limit": float(resolution_mae_limit),
                    "lambda0_error_limit_nm": float(resolution_lambda0_error_limit_nm),
                    "feature_shift_limit_nm": float(resolution_feature_shift_limit_nm),
                },
            },
            "noise": {
                "max_stable_noise_sigma": max_noise_sigma,
                "passed_sigmas": [float(row["noise_sigma"]) for row in noise_pass_rows],
                "criteria": {
                    "mae_mean_limit": float(noise_mae_limit),
                    "lambda0_error_std_limit_nm": float(noise_lambda0_error_std_limit_nm),
                    "feature_shift_std_limit_nm": float(noise_feature_shift_std_limit_nm),
                },
            },
        }

    return {
        "summary_type": "stability",
        "profile": None if profile is None else str(profile),
        "case_summaries": case_summaries,
        "criteria": {
            "resolution_mae_limit": float(resolution_mae_limit),
            "resolution_lambda0_error_limit_nm": float(resolution_lambda0_error_limit_nm),
            "resolution_feature_shift_limit_nm": float(resolution_feature_shift_limit_nm),
            "noise_mae_limit": float(noise_mae_limit),
            "noise_lambda0_error_std_limit_nm": float(noise_lambda0_error_std_limit_nm),
            "noise_feature_shift_std_limit_nm": float(noise_feature_shift_std_limit_nm),
        },
    }


def summarize_performance_conclusions(
    validation_bundle: Dict[str, Any],
    stability_summary: Dict[str, Any],
) -> Dict[str, Any]:
    validation_results = list(validation_bundle.get("results", []))
    validation_map = {str(item["case_id"]): item for item in validation_results}
    stability_map = dict(stability_summary.get("case_summaries", {}))
    cases = sorted(set(validation_map.keys()) | set(stability_map.keys()))

    rows: List[Dict[str, Any]] = []
    for case_id in cases:
        validation_item = validation_map.get(case_id, {})
        validation_summary = validation_item.get("summary", {})
        stability_item = stability_map.get(case_id, {})
        title_cn = str(
            validation_item.get("title_cn")
            or stability_item.get("title_cn")
            or case_id
        )
        max_step = stability_item.get("resolution", {}).get("max_stable_sampling_step_nm")
        max_noise = stability_item.get("noise", {}).get("max_stable_noise_sigma")

        if max_step is not None and max_noise is not None:
            status_cn = "分辨率与噪声均稳定"
        elif max_step is not None:
            status_cn = "分辨率稳定，噪声较敏感"
        elif max_noise is not None:
            status_cn = "噪声稳定，分辨率较敏感"
        else:
            status_cn = "对分辨率与噪声均较敏感"

        rows.append(
            {
                "case_id": case_id,
                "title_cn": title_cn,
                "quantity": str(validation_item.get("quantity", "")),
                "mae": float(validation_summary.get("mae", np.nan)),
                "rmse": float(validation_summary.get("rmse", np.nan)),
                "max_abs_error": float(validation_summary.get("max_abs_error", np.nan)),
                "lambda0_error": float(validation_summary.get("lambda0_error", np.nan)),
                "max_stable_sampling_step_nm": None if max_step is None else float(max_step),
                "max_stable_noise_sigma": None if max_noise is None else float(max_noise),
                "status_cn": status_cn,
            }
        )

    return {
        "summary_type": "performance_conclusion",
        "profile": stability_summary.get("profile"),
        "rows": rows,
    }


def export_performance_conclusions(
    summary: Dict[str, Any],
    *,
    prefix: str = "teaching_performance_conclusion",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    rows = list(summary.get("rows", []))

    csv_path = output_file(f"{prefix}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "case_id,title_cn,quantity,mae,rmse,max_abs_error,lambda0_error,"
            "max_stable_sampling_step_nm,max_stable_noise_sigma,status_cn\n"
        )
        for row in rows:
            f.write(
                ",".join(
                    [
                        str(row["case_id"]),
                        str(row["title_cn"]),
                        str(row["quantity"]),
                        f"{float(row['mae']):.12g}",
                        f"{float(row['rmse']):.12g}",
                        f"{float(row['max_abs_error']):.12g}",
                        f"{float(row['lambda0_error']):.12g}",
                        "" if row["max_stable_sampling_step_nm"] is None else f"{float(row['max_stable_sampling_step_nm']):.12g}",
                        "" if row["max_stable_noise_sigma"] is None else f"{float(row['max_stable_noise_sigma']):.12g}",
                        str(row["status_cn"]),
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}_summary.txt")
    lines = [
        "性能指标与稳定区间结论",
        "=" * 80,
    ]
    for row in rows:
        step_text = "未通过" if row["max_stable_sampling_step_nm"] is None else f"{float(row['max_stable_sampling_step_nm']):.3f} nm"
        noise_text = "未通过" if row["max_stable_noise_sigma"] is None else f"{float(row['max_stable_noise_sigma']):.6g}"
        lines.extend(
            [
                f"{row['title_cn']} ({row['case_id']})",
                f"  MAE = {float(row['mae']):.4e}",
                f"  RMSE = {float(row['rmse']):.4e}",
                f"  最大误差 = {float(row['max_abs_error']):.4e}",
                f"  中心点误差 = {float(row['lambda0_error']):+.4e}",
                f"  最大稳定采样步长 = {step_text}",
                f"  最大稳定噪声标准差 = {noise_text}",
                f"  结论 = {row['status_cn']}",
                "",
            ]
        )
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    labels = [str(row["title_cn"]) for row in rows]
    maes = np.asarray([float(row["mae"]) for row in rows], dtype=float)
    max_steps = np.asarray(
        [0.0 if row["max_stable_sampling_step_nm"] is None else float(row["max_stable_sampling_step_nm"]) for row in rows],
        dtype=float,
    )
    noise_sigmas = np.asarray(
        [0.0 if row["max_stable_noise_sigma"] is None else float(row["max_stable_noise_sigma"]) for row in rows],
        dtype=float,
    )
    x = np.arange(len(labels), dtype=float)

    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.6))
    for ax in axes:
        _style_axis(ax)

    axes[0].bar(x, maes, color=MAIN_RED, width=0.56)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=12, ha="right")
    axes[0].set_title("验证误差水平", fontweight="semibold")
    axes[0].set_ylabel("MAE")

    axes[1].bar(x, max_steps, color=REF_BLUE, width=0.56)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=12, ha="right")
    axes[1].set_title("最大稳定采样步长", fontweight="semibold")
    axes[1].set_ylabel("nm")

    axes[2].bar(x, noise_sigmas, color=ERR_GOLD, width=0.56)
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels, rotation=12, ha="right")
    axes[2].set_title("最大稳定噪声标准差", fontweight="semibold")
    axes[2].set_ylabel("噪声σ")

    fig.suptitle("三类结构性能结论总览", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{prefix}_overview.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["overview_png"] = str(png_path)
    return saved


def export_sensitivity_stability_summary(
    summary: Dict[str, Any],
    *,
    prefix: str = "teaching_sensitivity_stability",
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    case_rows = list(summary.get("case_summaries", {}).values())

    csv_path = output_file(f"{prefix}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("case_id,title_cn,max_stable_sampling_step_nm,max_stable_noise_sigma\n")
        for row in case_rows:
            resolution_value = row["resolution"]["max_stable_sampling_step_nm"]
            noise_value = row["noise"]["max_stable_noise_sigma"]
            f.write(
                ",".join(
                    [
                        str(row["case_id"]),
                        str(row["title_cn"]),
                        "" if resolution_value is None else f"{float(resolution_value):.12g}",
                        "" if noise_value is None else f"{float(noise_value):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}_summary.txt")
    lines = [
        "敏感性稳定区间总结",
        "=" * 80,
    ]
    for row in case_rows:
        resolution_value = row["resolution"]["max_stable_sampling_step_nm"]
        noise_value = row["noise"]["max_stable_noise_sigma"]
        resolution_text = "未通过" if resolution_value is None else f"{float(resolution_value):.3f} nm"
        noise_text = "未通过" if noise_value is None else f"{float(noise_value):.6g}"
        lines.extend(
            [
                f"{row['title_cn']} ({row['case_id']})",
                f"  最大稳定采样步长: {resolution_text}",
                f"  最大稳定噪声标准差: {noise_text}",
                "",
            ]
        )
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    labels = [str(row["title_cn"] or row["case_id"]) for row in case_rows]
    resolution_vals = [
        np.nan if row["resolution"]["max_stable_sampling_step_nm"] is None else float(row["resolution"]["max_stable_sampling_step_nm"])
        for row in case_rows
    ]
    noise_vals = [
        np.nan if row["noise"]["max_stable_noise_sigma"] is None else float(row["noise"]["max_stable_noise_sigma"])
        for row in case_rows
    ]
    x = np.arange(len(labels), dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    for ax in axes:
        _style_axis(ax)

    axes[0].bar(x, np.nan_to_num(np.asarray(resolution_vals, dtype=float), nan=0.0), color=REF_BLUE, width=0.56)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=12, ha="right")
    axes[0].set_title("最大稳定采样步长", fontweight="semibold")
    axes[0].set_ylabel("nm")

    axes[1].bar(x, np.nan_to_num(np.asarray(noise_vals, dtype=float), nan=0.0), color=ERR_GOLD, width=0.56)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=12, ha="right")
    axes[1].set_title("最大稳定噪声标准差", fontweight="semibold")
    axes[1].set_ylabel("噪声σ")

    fig.suptitle("三类结构稳定区间总览", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    png_path = output_file(f"{prefix}_overview.png")
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["overview_png"] = str(png_path)
    return saved
