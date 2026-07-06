"""Physics-aware robust decision metrics for thin-film designs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np

from .paths import output_file
from .plotting import AMBER, BLUE, GREEN, INK, MUTED, RED, apply_plot_style, save_publication_figure, style_axis
from .figure_audit import audit_missing_values, build_figure_audit, write_figure_audit


METRIC_SCHEMAS: dict[str, dict[str, dict[str, float | str]]] = {
    "ar": {
        "R_design": {"direction": "min", "good": 0.01, "bad": 0.10, "weight": 1.2},
        "R_band_mean": {"direction": "min", "good": 0.03, "bad": 0.12, "weight": 1.0},
        "R_band_max": {"direction": "min", "good": 0.08, "bad": 0.25, "weight": 0.8},
    },
    "reflector": {
        "R_design": {"direction": "max", "good": 0.99, "bad": 0.85, "weight": 1.2},
        "R_local_min": {"direction": "max", "good": 0.95, "bad": 0.70, "weight": 1.0},
        "high_R_fraction": {"direction": "max", "good": 0.70, "bad": 0.10, "weight": 0.8},
    },
    "filter": {
        "T_peak": {"direction": "max", "good": 0.90, "bad": 0.40, "weight": 1.2},
        "relative_peak_shift": {"direction": "min", "good": 0.002, "bad": 0.05, "weight": 1.0},
        "T_local_offband_p95": {"direction": "min", "good": 0.10, "bad": 0.60, "weight": 0.8},
    },
    "pdrc": {
        "A_solar_avg": {"direction": "min", "good": 0.10, "bad": 0.30, "weight": 1.0},
        "epsilon_8_13_avg": {"direction": "max", "good": 0.85, "bad": 0.50, "weight": 1.0},
        "cooling_score": {"direction": "max", "good": 0.70, "bad": 0.20, "weight": 1.2},
    },
}


def infer_device_class(case_id: str) -> str:
    key = str(case_id).lower()
    if any(term in key for term in ("pdrc", "cooling")):
        return "pdrc"
    if any(term in key for term in ("fp_", "filter", "wdm", "bandpass")):
        return "filter"
    if any(term in key for term in ("reflector", "mirror", "bragg", "quarter_wave_stack")):
        return "reflector"
    return "ar"


def _at(x: np.ndarray, y: np.ndarray, target: float) -> float:
    return float(np.interp(float(target), x, y))


def _fwhm(x: np.ndarray, y: np.ndarray) -> float:
    peak = int(np.argmax(y))
    half = float(np.min(y) + 0.5 * (np.max(y) - np.min(y)))
    above = y >= half
    left = peak
    right = peak
    while left > 0 and above[left - 1]:
        left -= 1
    while right < y.size - 1 and above[right + 1]:
        right += 1
    return float(x[right] - x[left]) if right > left else 0.0


def compute_device_metrics(
    case_id: str,
    wavelength: Sequence[float],
    R: Sequence[float],
    T: Sequence[float],
    A: Sequence[float],
    *,
    design_wavelength: float,
    extra_metrics: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Compute metrics appropriate to the physical device class."""
    wl = np.asarray(wavelength, dtype=float)
    r = np.asarray(R, dtype=float)
    t = np.asarray(T, dtype=float)
    device_class = infer_device_class(case_id)
    if device_class == "pdrc":
        values = dict(extra_metrics or {})
        return {"device_class": device_class, "metrics": values}
    if device_class == "ar":
        values = {"R_design": _at(wl, r, design_wavelength), "R_band_mean": float(np.mean(r)), "R_band_max": float(np.max(r))}
    elif device_class == "reflector":
        local = np.abs(wl - design_wavelength) <= 0.10 * design_wavelength
        if not np.any(local):
            local = np.ones_like(wl, dtype=bool)
        values = {
            "R_design": _at(wl, r, design_wavelength),
            "R_local_min": float(np.min(r[local])),
            "high_R_fraction": float(np.mean(r[local] >= 0.95)),
        }
    else:
        peak_idx = int(np.argmax(t))
        width = _fwhm(wl, t)
        exclusion = max(2.0 * width, 0.02 * design_wavelength)
        local = np.abs(wl - design_wavelength) <= 0.10 * design_wavelength
        offband = local & (np.abs(wl - float(wl[peak_idx])) > exclusion)
        values = {
            "T_peak": float(t[peak_idx]),
            "relative_peak_shift": abs(float(wl[peak_idx]) - design_wavelength) / design_wavelength,
            "T_local_offband_p95": float(np.quantile(t[offband], 0.95)) if np.any(offband) else float(np.min(t)),
            "FWHM": width,
        }
    return {"device_class": device_class, "metrics": values}


def normalize_metric(value: float, *, direction: str, good: float, bad: float) -> float:
    """Map a physical metric to [0,1], with 1 meeting the good target."""
    value = float(value)
    if direction == "max":
        raw = (value - bad) / (good - bad)
    elif direction == "min":
        raw = (bad - value) / (bad - good)
    else:
        raise ValueError("direction must be 'min' or 'max'")
    return float(np.clip(raw, 0.0, 1.0))


def score_device_metrics(device_class: str, metrics: Mapping[str, float]) -> dict[str, Any]:
    """Return an interpretable weighted geometric score and weakest metric."""
    schema = METRIC_SCHEMAS[str(device_class)]
    components: dict[str, float] = {}
    weights: list[float] = []
    values: list[float] = []
    for name, rule in schema.items():
        if name not in metrics or not np.isfinite(float(metrics[name])):
            components[name] = 0.0
        else:
            components[name] = normalize_metric(float(metrics[name]), direction=str(rule["direction"]), good=float(rule["good"]), bad=float(rule["bad"]))
        weights.append(float(rule["weight"]))
        values.append(max(components[name], 1e-6))
    score = float(np.exp(np.average(np.log(values), weights=weights)))
    weakest = "all_targets_met" if all(value >= 1.0 - 1e-12 for value in components.values()) else min(components, key=components.get)
    weakest_score = 1.0 if weakest == "all_targets_met" else components[weakest]
    return {"score": score, "components": components, "weakest_metric": weakest, "weakest_score": weakest_score}


def robust_interval(samples: Sequence[float], *, confidence: float = 0.90) -> dict[str, float]:
    """Summarize an ensemble without reducing it to a single optimum."""
    arr = np.asarray(samples, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {key: float("nan") for key in ("median", "lower", "upper", "minimum", "maximum")}
    alpha = 0.5 * (1.0 - confidence)
    return {
        "median": float(np.median(arr)),
        "lower": float(np.quantile(arr, alpha)),
        "upper": float(np.quantile(arr, 1.0 - alpha)),
        "minimum": float(np.min(arr)),
        "maximum": float(np.max(arr)),
    }


def pass_probability(samples: Sequence[float], *, direction: str, threshold: float) -> float:
    arr = np.asarray(samples, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    passed = arr >= threshold if direction == "max" else arr <= threshold
    return float(np.mean(passed))


def pareto_front_indices(rows: Sequence[Mapping[str, float]], objectives: Mapping[str, str]) -> list[int]:
    """Return non-dominated candidate indices for mixed min/max objectives."""
    if not objectives:
        return list(range(len(rows)))
    names = list(objectives)
    transformed = np.asarray([
        [float(row[name]) * (1.0 if objectives[name] == "max" else -1.0) for name in names]
        for row in rows
    ], dtype=float)
    front: list[int] = []
    for idx, point in enumerate(transformed):
        dominated = any(np.all(other >= point) and np.any(other > point) for j, other in enumerate(transformed) if j != idx)
        if not dominated:
            front.append(idx)
    return front


def build_decision_record(
    *,
    case_id: str,
    title: str,
    wavelength: Sequence[float],
    R: Sequence[float],
    T: Sequence[float],
    A: Sequence[float],
    design_wavelength: float,
    score_samples: Sequence[float] | None = None,
    extra_metrics: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    computed = compute_device_metrics(case_id, wavelength, R, T, A, design_wavelength=design_wavelength, extra_metrics=extra_metrics)
    scored = score_device_metrics(computed["device_class"], computed["metrics"])
    interval = robust_interval(score_samples if score_samples is not None else [scored["score"]])
    robustness = float(interval["lower"])
    return {
        "case_id": case_id,
        "title": title,
        "device_class": computed["device_class"],
        "metrics": computed["metrics"],
        "component_scores": scored["components"],
        "performance_score": scored["score"],
        "robustness_score": robustness,
        "score_interval": interval,
        "weakest_metric": scored["weakest_metric"],
    }


def sample_score_uncertainty(
    *,
    case_id: str,
    wavelength: Sequence[float],
    R: Sequence[float],
    T: Sequence[float],
    A: Sequence[float],
    design_wavelength: float,
    response_sigma: float,
    wavelength_sigma: float,
    samples: int = 300,
    seed: int = 0,
) -> list[float]:
    """Propagate declared response and wavelength-registration uncertainty."""
    wl = np.asarray(wavelength, dtype=float)
    curves = [np.asarray(values, dtype=float) for values in (R, T, A)]
    rng = np.random.default_rng(seed)
    scores: list[float] = []
    for _ in range(max(1, int(samples))):
        shifted_wl = wl + float(rng.normal(0.0, float(wavelength_sigma)))
        perturbed = [np.clip(curve + rng.normal(0.0, float(response_sigma), curve.size), 0.0, 1.0) for curve in curves]
        computed = compute_device_metrics(
            case_id, shifted_wl, perturbed[0], perturbed[1], perturbed[2], design_wavelength=design_wavelength
        )
        scores.append(score_device_metrics(computed["device_class"], computed["metrics"])["score"])
    return scores


def export_decision_analysis(records: Sequence[Mapping[str, Any]], *, prefix: str = "design_decision") -> dict[str, str]:
    """Export decision table, robust score chart, and Pareto map."""
    rows = [dict(row) for row in records]
    json_path = output_file(f"{prefix}_summary.json")
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = output_file(f"{prefix}_summary.csv")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "title", "device_class", "performance_score", "robustness_score", "weakest_metric", "pareto"])
        writer.writeheader()
        front = set(pareto_front_indices(rows, {"performance_score": "max", "robustness_score": "max"}))
        for idx, row in enumerate(rows):
            writer.writerow({**{key: row.get(key, "") for key in writer.fieldnames}, "pareto": idx in front})
    apply_plot_style()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    labels = [str(row["title"]) for row in rows]
    y = np.arange(len(rows))
    scores = np.asarray([float(row["performance_score"]) for row in rows])
    robust = np.asarray([float(row["robustness_score"]) for row in rows])
    axes[0].barh(y, scores, color=BLUE, height=0.58, label="名义性能")
    axes[0].scatter(robust, y, color=AMBER, marker="|", s=180, linewidths=2.4, label="稳健下界")
    axes[0].set_yticks(y, labels)
    axes[0].set_xlim(0, 1.02)
    axes[0].set_xlabel("判据归一化评分")
    axes[0].set_title("名义性能（蓝）与稳健下界（金）")
    style_axis(axes[0])
    front = set(pareto_front_indices(rows, {"performance_score": "max", "robustness_score": "max"}))
    colors = [GREEN if idx in front else MUTED for idx in range(len(rows))]
    axes[1].scatter(scores, robust, c=colors, s=75, edgecolors="white")
    for idx, row in enumerate(rows):
        if robust[idx] > 0.98:
            x_text, y_text, ha = scores[idx] - 0.03, 1.00, "right"
        elif robust[idx] > 0.85:
            x_text, y_text, ha = scores[idx] - 0.04, robust[idx] - 0.08, "right"
        elif robust[idx] > 0.2:
            x_text, y_text, ha = scores[idx] + 0.02, robust[idx] + 0.05, "left"
        else:
            x_text, y_text, ha = scores[idx] - 0.04, robust[idx] + 0.08, "right"
        axes[1].text(x_text, y_text, str(row["title"]), fontsize=7, ha=ha, va="center")
    axes[1].plot([0, 1], [0, 1], linestyle=":", color=MUTED, linewidth=1)
    axes[1].set_xlim(-0.02, 1.06)
    axes[1].set_ylim(-0.02, 1.04)
    axes[1].set_xlabel("名义性能评分")
    axes[1].set_ylabel("稳健评分下界")
    axes[1].set_title("Pareto 非支配候选（绿色标记）")
    style_axis(axes[1])
    assumption = rows[0].get("uncertainty_assumptions", {}) if rows else {}
    subtitle = ""
    if assumption:
        subtitle = (
            f"\n声明不确定性：响应 σ={float(assumption.get('response_sigma', 0)):.4g}，"
            f"波长 σ={float(assumption.get('wavelength_sigma_nm', 0)):.3g} nm，"
            f"样本数={int(assumption.get('samples', 0))}"
        )
    fig.suptitle(f"跨器件物理判据归一化决策{subtitle}", fontsize=14, fontweight="semibold", color=INK)
    fig.tight_layout(rect=[0.0, 0.04, 1.0, 0.88])
    png_path = output_file(f"{prefix}_overview.png")
    save_publication_figure(fig, png_path)
    plt.close(fig)
    audit = build_figure_audit(
        figure_id=f"{prefix}_overview",
        title="跨器件物理判据归一化决策",
        evidence_level="theory",
        checks=[audit_missing_values([row.get("performance_score") for row in rows]), audit_missing_values([row.get("robustness_score") for row in rows])],
    )
    audit_path = output_file(f"{prefix}_figure_audit.json")
    return {"json": str(json_path), "csv": str(csv_path), "png": str(png_path), "audit_json": write_figure_audit(audit_path, audit)}
