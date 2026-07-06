"""PDRC COMSOL data analysis helpers.

This module keeps the research-facing PDRC data pipeline separate from the
teaching TMM presets in ``education.py``.  It is designed for COMSOL global
evaluation CSV files that export wavelength, one scanned thickness parameter,
R, T, and A.
"""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np

from .paths import output_file
from .plotting import AMBER, BLUE, CYAN, GREEN, INK, MUTED, RED, annotate_point, apply_plot_style, save_publication_figure, style_axis, style_colorbar
from .figure_audit import audit_source_files, build_figure_audit, write_figure_audit


_NUMBER_RE = re.compile(r"^[\s]*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)")


def _parse_comsol_number(value: Any) -> float:
    text = str(value or "").strip().replace("\ufeff", "")
    match = _NUMBER_RE.match(text)
    return float(match.group(1)) if match else float("nan")


def _find_header_line(lines: Sequence[str]) -> int:
    for idx, line in enumerate(lines):
        if line.startswith("%") and "abs(ewfd.S11)" in line:
            return idx
    raise ValueError("Could not find a COMSOL header line containing abs(ewfd.S11).")


def _find_column(headers: Sequence[str], selector: str) -> int:
    key = str(selector).strip().lower()
    for idx, header in enumerate(headers):
        if key in str(header).strip().lower():
            return idx
    raise ValueError(f"Could not find column selector '{selector}' in {list(headers)}")


def _normalize_list(value: str | Sequence[str]) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def _parameter_key(row: dict[str, Any]) -> tuple[float, ...]:
    if "parameter_key" in row:
        return tuple(float(item) for item in row["parameter_key"])
    return (float(row["parameter_nm"]),)


def _parameter_key_id(values: Sequence[float]) -> str:
    return "|".join(f"{float(item):.9g}" for item in values)


def load_pdrc_comsol_rows(
    csv_file: str | Path,
    *,
    parameter_selector: str | Sequence[str] = "d_TiO2",
) -> list[dict[str, Any]]:
    """Load one PDRC COMSOL global-evaluation CSV.

    Returns rows with normalized units:

    - ``parameter_nm``
    - ``lambda_um``
    - ``R``
    - ``T``
    - ``A``
    """
    path = Path(csv_file)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        lines = [line for line in f if line.strip()]

    header_idx = _find_header_line(lines)
    headers = [part.strip().lstrip("% ").strip() for part in lines[header_idx].strip().split(",")]

    parameter_selectors = _normalize_list(parameter_selector)
    if not parameter_selectors:
        raise ValueError("parameter_selector must contain at least one selector.")

    parameter_indices = [(selector, _find_column(headers, selector)) for selector in parameter_selectors]
    lambda_idx = _find_column(headers, "lam")
    r_idx = _find_column(headers, "abs(ewfd.S11)^2")
    t_idx = _find_column(headers, "abs(ewfd.S21)^2")
    a_idx = _find_column(headers, "1-abs(ewfd.S11)^2-abs(ewfd.S21)^2")

    rows: list[dict[str, Any]] = []
    for line in lines[header_idx + 1 :]:
        if line.startswith("%") or not line.strip():
            continue
        values = next(csv.reader([line]))
        if len(values) < len(headers):
            continue
        parameter_values_nm: list[float] = []
        parameters_nm: dict[str, float] = {}
        for selector, parameter_idx in parameter_indices:
            parameter_m = _parse_comsol_number(values[parameter_idx])
            parameter_nm = float(parameter_m) * 1e9
            parameter_values_nm.append(parameter_nm)
            parameters_nm[selector] = parameter_nm
        lambda_m = _parse_comsol_number(values[lambda_idx])
        reflectance = _parse_comsol_number(values[r_idx])
        transmittance = _parse_comsol_number(values[t_idx])
        absorptance = _parse_comsol_number(values[a_idx])
        if not all(
            math.isfinite(x)
            for x in [*parameter_values_nm, lambda_m, reflectance, transmittance, absorptance]
        ):
            continue
        rows.append(
            {
                "source_file": path.name,
                "parameter_nm": float(parameter_values_nm[0]),
                "parameters_nm": parameters_nm,
                "parameter_key": tuple(parameter_values_nm),
                "lambda_um": float(lambda_m) * 1e6,
                "R": float(reflectance),
                "T": float(transmittance),
                "A": float(absorptance),
            }
        )
    return rows


def merge_pdrc_comsol_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge duplicate parameter/wavelength rows, keeping the last value."""
    merged: dict[tuple[float, ...], dict[str, Any]] = {}
    for row in rows:
        key = (*[round(float(item), 9) for item in _parameter_key(row)], round(float(row["lambda_um"]), 9))
        merged[key] = dict(row)
    return sorted(merged.values(), key=lambda item: (*_parameter_key(item), float(item["lambda_um"])))


def _band_rows(rows: Sequence[dict[str, Any]], lower_um: float, upper_um: float) -> list[dict[str, Any]]:
    return [row for row in rows if lower_um <= float(row["lambda_um"]) <= upper_um]


def _nearest_value(rows: Sequence[dict[str, Any]], target_um: float, key: str = "A") -> float:
    if not rows:
        return float("nan")
    row = min(rows, key=lambda item: abs(float(item["lambda_um"]) - float(target_um)))
    return float(row[key])


def _solar_blackbody_weights(lambda_um: np.ndarray, *, temperature_k: float = 5778.0) -> np.ndarray:
    """Return relative solar spectral weights using a blackbody proxy.

    The absolute scale cancels in weighted averages, so the implementation uses
    a numerically stable Planck-shape expression and normalizes by its maximum.
    """
    lam_m = np.asarray(lambda_um, dtype=float) * 1e-6
    lam_m = np.clip(lam_m, 1e-12, None)
    c2 = 1.438776877e-2  # h*c/k in m*K
    exponent = np.clip(c2 / (lam_m * float(temperature_k)), 1e-9, 700.0)
    weights = 1.0 / (np.power(lam_m, 5) * np.expm1(exponent))
    weights = np.asarray(weights, dtype=float)
    max_weight = float(np.nanmax(weights)) if weights.size else 0.0
    if max_weight <= 0.0 or not math.isfinite(max_weight):
        return np.ones_like(lam_m, dtype=float)
    return weights / max_weight


def _load_solar_weight_csv(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Load an external solar spectrum CSV.

    Accepted wavelength columns include ``lambda_um``, ``wavelength_um``,
    ``lambda_nm`` or ``wavelength_nm``.  The weight column can be named
    ``weight``, ``irradiance`` or anything containing ``spectral``.
    """
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"solar weight CSV has no header: {csv_path}")
        fields = [str(name) for name in reader.fieldnames]
        normalized = {name: name.strip().lower() for name in fields}

        wavelength_col: str | None = None
        for name, key in normalized.items():
            if "lambda_um" in key or "wavelength_um" in key:
                wavelength_col = name
                wavelength_scale = 1.0
                break
            if "lambda_nm" in key or "wavelength_nm" in key:
                wavelength_col = name
                wavelength_scale = 1.0 / 1000.0
                break
        if wavelength_col is None:
            raise ValueError(f"solar weight CSV needs wavelength column: {csv_path}")

        weight_col: str | None = None
        for name, key in normalized.items():
            if name == wavelength_col:
                continue
            if "weight" in key or "irradiance" in key or "spectral" in key:
                weight_col = name
                break
        if weight_col is None:
            candidates = [name for name in fields if name != wavelength_col]
            if not candidates:
                raise ValueError(f"solar weight CSV needs weight/irradiance column: {csv_path}")
            weight_col = candidates[0]

        lambdas: list[float] = []
        weights: list[float] = []
        for row in reader:
            lam = _parse_comsol_number(row.get(wavelength_col))
            weight = _parse_comsol_number(row.get(weight_col))
            if math.isfinite(lam) and math.isfinite(weight) and weight >= 0:
                lambdas.append(float(lam) * wavelength_scale)
                weights.append(float(weight))

    if len(lambdas) < 2:
        raise ValueError(f"solar weight CSV needs at least two valid rows: {csv_path}")
    order = np.argsort(np.asarray(lambdas, dtype=float))
    return np.asarray(lambdas, dtype=float)[order], np.asarray(weights, dtype=float)[order]


def _solar_weights_for_lambdas(
    lambda_um: np.ndarray,
    *,
    mode: str = "blackbody_5778K",
    weight_csv: str | Path | None = None,
) -> np.ndarray:
    if weight_csv is not None:
        source_lambda, source_weight = _load_solar_weight_csv(weight_csv)
        return np.interp(lambda_um, source_lambda, source_weight, left=0.0, right=0.0)
    key = str(mode).strip().lower()
    if key in {"none", "off", "uniform", "arithmetic"}:
        return np.ones_like(lambda_um, dtype=float)
    if key in {"blackbody", "blackbody_5778k", "bb5778", "solar_blackbody"}:
        return _solar_blackbody_weights(lambda_um, temperature_k=5778.0)
    raise ValueError(f"Unsupported solar weight mode: {mode}")


def _safe_weighted_average(values: np.ndarray, weights: np.ndarray) -> float:
    mask = np.isfinite(values) & np.isfinite(weights) & (weights >= 0)
    if int(np.count_nonzero(mask)) == 0:
        return float("nan")
    total = float(np.sum(weights[mask]))
    if total <= 0.0:
        return float("nan")
    return float(np.sum(values[mask] * weights[mask]) / total)


def _summarize_band(
    rows: Sequence[dict[str, Any]],
    *,
    lower_um: float,
    upper_um: float,
    metric_prefix: str,
    total_dielectric_base_nm: float | None = None,
    solar_weight_mode: str = "blackbody_5778K",
    solar_weight_csv: str | Path | None = None,
    parameter_labels: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    labels = list(parameter_labels or ["parameter_nm"])
    by_parameter: dict[tuple[float, ...], list[dict[str, Any]]] = {}
    for row in _band_rows(rows, lower_um, upper_um):
        key = tuple(round(float(item), 9) for item in _parameter_key(row))
        by_parameter.setdefault(key, []).append(row)

    summaries: list[dict[str, Any]] = []
    for parameter_values, group in sorted(by_parameter.items()):
        group = sorted(group, key=lambda item: float(item["lambda_um"]))
        a_vals = np.asarray([float(row["A"]) for row in group], dtype=float)
        r_vals = np.asarray([float(row["R"]) for row in group], dtype=float)
        t_vals = np.asarray([float(row["T"]) for row in group], dtype=float)
        lambdas = np.asarray([float(row["lambda_um"]) for row in group], dtype=float)
        peak = group[int(np.argmax(a_vals))]
        trough = group[int(np.argmin(a_vals))]
        summary: dict[str, Any] = {
            "parameter_key": _parameter_key_id(parameter_values),
            "parameter_nm": float(parameter_values[0]),
            f"{metric_prefix}_A_avg": float(np.mean(a_vals)),
            f"{metric_prefix}_R_avg": float(np.mean(r_vals)),
            f"{metric_prefix}_T_avg": float(np.mean(t_vals)),
            f"{metric_prefix}_A_min": float(trough["A"]),
            f"{metric_prefix}_A_min_lambda_um": float(trough["lambda_um"]),
            f"{metric_prefix}_A_max": float(peak["A"]),
            f"{metric_prefix}_A_max_lambda_um": float(peak["lambda_um"]),
            "lambda_min_um": float(np.min(lambdas)),
            "lambda_max_um": float(np.max(lambdas)),
            "num_lambda_points": int(len(group)),
        }
        for idx, value in enumerate(parameter_values):
            label = labels[idx] if idx < len(labels) else f"parameter_{idx + 1}_nm"
            summary[label] = float(value)
        if lower_um <= 8.9 <= upper_um:
            summary["A_at_8p9um"] = _nearest_value(group, 8.9)
        if lower_um <= 10.0 <= upper_um:
            summary["A_at_10um"] = _nearest_value(group, 10.0)
        if lower_um <= 12.0 <= upper_um:
            summary["A_at_12um"] = _nearest_value(group, 12.0)
        if total_dielectric_base_nm is not None:
            summary["total_dielectric_thickness_um"] = (
                float(total_dielectric_base_nm) + 2.0 * float(parameter_values[0])
            ) / 1000.0
        if metric_prefix == "solar":
            weights = _solar_weights_for_lambdas(
                lambdas,
                mode=solar_weight_mode,
                weight_csv=solar_weight_csv,
            )
            summary["solar_weight_mode"] = str(solar_weight_csv) if solar_weight_csv is not None else str(solar_weight_mode)
            summary["solar_A_weighted"] = _safe_weighted_average(a_vals, weights)
            summary["solar_R_weighted"] = _safe_weighted_average(r_vals, weights)
            summary["solar_T_weighted"] = _safe_weighted_average(t_vals, weights)
        summaries.append(summary)
    return summaries


def analyze_pdrc_comsol_candidates(
    *,
    ir_csv_files: Sequence[str | Path],
    solar_csv_file: str | Path | None = None,
    parameter_selector: str | Sequence[str] = "d_TiO2",
    parameter_label: str | Sequence[str] = "d_TiO2_equal_nm",
    total_dielectric_base_nm: float = 1800.0,
    solar_band: tuple[float, float] = (0.3, 2.5),
    ir_band: tuple[float, float] = (8.0, 13.0),
    solar_weight_mode: str = "blackbody_5778K",
    solar_weight_csv: str | Path | None = None,
) -> dict[str, Any]:
    """Analyze PDRC COMSOL scan files and combine solar/IR metrics."""
    parameter_selectors = _normalize_list(parameter_selector)
    parameter_labels = _normalize_list(parameter_label)
    if not parameter_labels:
        parameter_labels = [f"{item}_nm" for item in parameter_selectors]
    if len(parameter_labels) != len(parameter_selectors):
        if len(parameter_labels) == 1 and len(parameter_selectors) == 1:
            pass
        else:
            raise ValueError("parameter_label and parameter_selector must have the same number of entries.")

    ir_source_ranges: list[dict[str, Any]] = []
    ir_rows_raw: list[dict[str, Any]] = []
    for csv_file in ir_csv_files:
        one = load_pdrc_comsol_rows(csv_file, parameter_selector=parameter_selectors)
        if one:
            ir_source_ranges.append(
                {
                    "file": str(csv_file),
                    "rows": len(one),
                    "lambda_range_um": [min(row["lambda_um"] for row in one), max(row["lambda_um"] for row in one)],
                    "parameter_ranges_nm": {
                        parameter_labels[idx]: [
                            min(_parameter_key(row)[idx] for row in one),
                            max(_parameter_key(row)[idx] for row in one),
                        ]
                        for idx in range(len(parameter_labels))
                    },
                }
            )
        ir_rows_raw.extend(one)
    ir_rows = merge_pdrc_comsol_rows(ir_rows_raw)
    ir_summary = _summarize_band(
        ir_rows,
        lower_um=ir_band[0],
        upper_um=ir_band[1],
        metric_prefix="ir",
        total_dielectric_base_nm=total_dielectric_base_nm,
        parameter_labels=parameter_labels,
    )
    complete_ir_summary = [
        row
        for row in ir_summary
        if float(row["lambda_min_um"]) <= ir_band[0] + 1e-9
        and float(row["lambda_max_um"]) >= ir_band[1] - 1e-9
    ]

    solar_summary: list[dict[str, Any]] = []
    solar_rows: list[dict[str, Any]] = []
    if solar_csv_file is not None:
        solar_rows = merge_pdrc_comsol_rows(
            load_pdrc_comsol_rows(solar_csv_file, parameter_selector=parameter_selectors)
        )
        solar_summary = _summarize_band(
            solar_rows,
            lower_um=solar_band[0],
            upper_um=solar_band[1],
            metric_prefix="solar",
            solar_weight_mode=solar_weight_mode,
            solar_weight_csv=solar_weight_csv,
            parameter_labels=parameter_labels,
        )

    solar_by_parameter = {str(row["parameter_key"]): row for row in solar_summary}
    final_metrics: list[dict[str, Any]] = []
    for ir_row in complete_ir_summary:
        solar_row = solar_by_parameter.get(str(ir_row["parameter_key"]))
        if solar_csv_file is not None and solar_row is None:
            continue
        a_solar = float(solar_row["solar_A_avg"]) if solar_row else float("nan")
        r_solar = float(solar_row["solar_R_avg"]) if solar_row else float("nan")
        t_solar = float(solar_row["solar_T_avg"]) if solar_row else float("nan")
        a_solar_weighted = float(solar_row.get("solar_A_weighted", float("nan"))) if solar_row else float("nan")
        r_solar_weighted = float(solar_row.get("solar_R_weighted", float("nan"))) if solar_row else float("nan")
        t_solar_weighted = float(solar_row.get("solar_T_weighted", float("nan"))) if solar_row else float("nan")
        epsilon = float(ir_row["ir_A_avg"])
        parameter_columns = {label: float(ir_row[label]) for label in parameter_labels if label in ir_row}
        final_metrics.append(
            {
                **parameter_columns,
                "parameter_key": str(ir_row["parameter_key"]),
                "total_dielectric_thickness_um": float(ir_row.get("total_dielectric_thickness_um", float("nan"))),
                "A_solar_avg": a_solar,
                "R_solar_avg": r_solar,
                "T_solar_avg": t_solar,
                "A_solar_weighted": a_solar_weighted,
                "R_solar_weighted": r_solar_weighted,
                "T_solar_weighted": t_solar_weighted,
                "solar_weight_mode": str(solar_row.get("solar_weight_mode", "")) if solar_row else "",
                "A_solar_max": float(solar_row["solar_A_max"]) if solar_row else float("nan"),
                "A_solar_max_lambda_um": float(solar_row["solar_A_max_lambda_um"]) if solar_row else float("nan"),
                "epsilon_8_13_avg": epsilon,
                "A_min_8_13": float(ir_row["ir_A_min"]),
                "A_min_lambda_um": float(ir_row["ir_A_min_lambda_um"]),
                "A_max_8_13": float(ir_row["ir_A_max"]),
                "A_max_lambda_um": float(ir_row["ir_A_max_lambda_um"]),
                "A_at_8p9um": float(ir_row.get("A_at_8p9um", float("nan"))),
                "A_at_10um": float(ir_row.get("A_at_10um", float("nan"))),
                "A_at_12um": float(ir_row.get("A_at_12um", float("nan"))),
                "cooling_score": float(epsilon - a_solar) if math.isfinite(a_solar) else float("nan"),
                "cooling_score_weighted": float(epsilon - a_solar_weighted) if math.isfinite(a_solar_weighted) else float("nan"),
                "passes_solar": bool(math.isfinite(a_solar) and a_solar < 0.15),
                "passes_solar_weighted": bool(math.isfinite(a_solar_weighted) and a_solar_weighted < 0.15),
                "passes_ir": bool(epsilon > 0.70),
            }
        )

    return {
        "parameter_label": parameter_labels[0],
        "parameter_labels": parameter_labels,
        "solar_weight_mode": str(solar_weight_csv) if solar_weight_csv is not None else str(solar_weight_mode),
        "ir_source_ranges": ir_source_ranges,
        "ir_rows": ir_rows,
        "solar_rows": solar_rows,
        "ir_summary": ir_summary,
        "complete_ir_summary": complete_ir_summary,
        "solar_summary": solar_summary,
        "final_metrics": sorted(final_metrics, key=lambda row: tuple(float(row[label]) for label in parameter_labels)),
    }


def _write_dict_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_spectrum_rows(path: Path, rows: Sequence[dict[str, Any]], parameter_labels: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[*parameter_labels, "lambda_um", "R", "T", "A", "source_file"])
        writer.writeheader()
        for row in rows:
            values = _parameter_key(row)
            writer.writerow(
                {
                    **{
                        label: values[idx] if idx < len(values) else ""
                        for idx, label in enumerate(parameter_labels)
                    },
                    "lambda_um": row["lambda_um"],
                    "R": row["R"],
                    "T": row["T"],
                    "A": row["A"],
                    "source_file": row["source_file"],
                }
            )


def _metric_label_cn(metric: str) -> str:
    labels = {
        "A_solar_avg": "太阳平均吸收率",
        "A_solar_weighted": "太阳加权吸收率",
        "R_solar_weighted": "太阳加权反射率",
        "epsilon_8_13_avg": "8-13 μm 平均发射率",
        "A_min_8_13": "8-13 μm 最小吸收率",
        "cooling_score": "冷却得分",
        "cooling_score_weighted": "加权冷却得分",
    }
    return labels.get(metric, metric)


def _make_ir_summary_plot(path: Path, rows: Sequence[dict[str, Any]], parameter_label: str) -> None:
    if not rows:
        return
    apply_plot_style()
    xs = [float(row[parameter_label]) for row in rows]
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    style_axis(ax)
    ax.plot(xs, [float(row["epsilon_8_13_avg"]) for row in rows], "-o", color=GREEN, lw=2.2, ms=4, label="8-13 μm 平均吸收/发射率")
    ax.plot(xs, [float(row["A_min_8_13"]) for row in rows], "--", color=MUTED, lw=1.25, alpha=0.65, label="窗口内最小 A")
    if "A_at_8p9um" in rows[0]:
        ax.plot(xs, [float(row["A_at_8p9um"]) for row in rows], ":", color=BLUE, lw=1.0, alpha=0.42, label="A(8.9 μm)")
    if "A_at_10um" in rows[0]:
        ax.plot(xs, [float(row["A_at_10um"]) for row in rows], ":", color=AMBER, lw=1.0, alpha=0.42, label="A(10 μm)")
    if "A_at_12um" in rows[0]:
        ax.plot(xs, [float(row["A_at_12um"]) for row in rows], ":", color=CYAN, lw=1.0, alpha=0.42, label="A(12 μm)")
    best = max(rows, key=lambda row: float(row["epsilon_8_13_avg"]))
    ax.axhline(0.70, color=MUTED, lw=1.1, alpha=0.7, linestyle=":", label="目标 0.70")
    ax.axvline(float(best[parameter_label]), color=RED, lw=1.2, alpha=0.85, linestyle="--", label=f"最佳 {float(best[parameter_label]):.0f} nm")
    ax.set_xlabel(parameter_label)
    ax.set_ylabel("吸收率 / 发射率")
    ax.set_title("PDRC 红外窗口扫描")
    ax.legend(loc="best")
    fig.tight_layout()
    save_publication_figure(fig, path)
    plt.close(fig)


def _make_final_metrics_plot(path: Path, rows: Sequence[dict[str, Any]], parameter_label: str) -> None:
    if not rows:
        return
    apply_plot_style()
    xs = [float(row[parameter_label]) for row in rows]
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    style_axis(ax)
    ax.plot(xs, [float(row["A_solar_avg"]) for row in rows], "-", color=AMBER, lw=1.2, alpha=0.48, label="太阳算术平均 A（辅助）")
    if "A_solar_weighted" in rows[0]:
        ax.plot(xs, [float(row["A_solar_weighted"]) for row in rows], "-o", color=RED, lw=2.3, ms=4, label="太阳加权吸收率")
    ax.plot(xs, [float(row["epsilon_8_13_avg"]) for row in rows], "-s", color=GREEN, lw=2.1, label="8-13 μm 平均发射率")
    ax.plot(xs, [float(row["cooling_score"]) for row in rows], "-", color=BLUE, lw=1.1, alpha=0.45, label="未加权冷却得分（辅助）")
    if "cooling_score_weighted" in rows[0]:
        ax.plot(xs, [float(row["cooling_score_weighted"]) for row in rows], "-^", color=CYAN, lw=2.2, ms=4, label="加权冷却得分")
    ax.axhline(0.15, color=RED, lw=1, alpha=0.45, linestyle=":", label="太阳吸收阈值 0.15")
    ax.axhline(0.70, color=GREEN, lw=1, alpha=0.45, linestyle=":", label="红外发射阈值 0.70")
    ax.set_xlabel(parameter_label)
    ax.set_ylabel("指标值")
    ax.set_title("PDRC 候选结构指标")
    ax.legend(loc="best")
    fig.tight_layout()
    save_publication_figure(fig, path)
    plt.close(fig)


def _make_two_parameter_scatter_plot(
    path: Path,
    rows: Sequence[dict[str, Any]],
    parameter_labels: Sequence[str],
    *,
    metric: str,
    title: str,
) -> None:
    if len(parameter_labels) < 2 or not rows:
        return
    apply_plot_style()
    x_label, y_label = parameter_labels[0], parameter_labels[1]
    xs = [float(row[x_label]) for row in rows]
    ys = [float(row[y_label]) for row in rows]
    colors = [float(row[metric]) for row in rows]
    fig, ax = plt.subplots(figsize=(7.8, 6.0))
    style_axis(ax)
    scatter = ax.scatter(xs, ys, c=colors, s=110, cmap="viridis", edgecolors="white", linewidths=0.9)
    best = max(rows, key=lambda row: float(row[metric]))
    ax.scatter([float(best[x_label])], [float(best[y_label])], marker="*", s=240, c=RED, edgecolors="white", linewidths=1.0)
    annotate_point(
        ax,
        float(best[x_label]),
        float(best[y_label]),
        f"最佳\n{_metric_label_cn(metric)}={float(best[metric]):.3f}",
    )
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    cbar = fig.colorbar(scatter, ax=ax, label=_metric_label_cn(metric))
    style_colorbar(cbar)
    fig.tight_layout()
    save_publication_figure(fig, path)
    plt.close(fig)


def _grid_from_rows(
    rows: Sequence[dict[str, Any]],
    parameter_labels: Sequence[str],
    metric: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x_label, y_label = parameter_labels[0], parameter_labels[1]
    xs = np.asarray(sorted({float(row[x_label]) for row in rows}), dtype=float)
    ys = np.asarray(sorted({float(row[y_label]) for row in rows}), dtype=float)
    grid = np.full((len(ys), len(xs)), np.nan, dtype=float)
    for row in rows:
        x_idx = int(np.where(xs == float(row[x_label]))[0][0])
        y_idx = int(np.where(ys == float(row[y_label]))[0][0])
        grid[y_idx, x_idx] = float(row[metric])
    return xs, ys, grid


def _make_two_parameter_heatmap_plot(
    path: Path,
    rows: Sequence[dict[str, Any]],
    parameter_labels: Sequence[str],
    *,
    metric: str,
    title: str,
    cmap: str = "viridis",
) -> None:
    if len(parameter_labels) < 2 or not rows:
        return
    apply_plot_style()
    x_label, y_label = parameter_labels[0], parameter_labels[1]
    xs, ys, grid = _grid_from_rows(rows, parameter_labels, metric)
    fig, ax = plt.subplots(figsize=(8.2, 6.0))
    style_axis(ax, grid=False)
    image = ax.imshow(
        grid,
        origin="lower",
        aspect="auto",
        cmap=cmap,
        extent=[xs.min(), xs.max(), ys.min(), ys.max()],
        interpolation="nearest",
    )
    ax.scatter(
        [float(row[x_label]) for row in rows],
        [float(row[y_label]) for row in rows],
        s=55,
        facecolors="none",
        edgecolors="white",
        linewidths=0.9,
    )
    if len(rows) <= 36:
        for row in rows:
            ax.text(float(row[x_label]), float(row[y_label]), f"{float(row[metric]):.3f}", ha="center", va="center", fontsize=7.5, color="white")
    best = max(rows, key=lambda row: float(row[metric]))
    ax.scatter([float(best[x_label])], [float(best[y_label])], marker="*", s=260, c=RED, edgecolors="white", linewidths=1.0)
    annotate_point(ax, float(best[x_label]), float(best[y_label]), f"最佳\n{float(best[metric]):.3f}")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    cbar = fig.colorbar(image, ax=ax, label=_metric_label_cn(metric))
    style_colorbar(cbar)
    fig.tight_layout()
    save_publication_figure(fig, path)
    plt.close(fig)


def _make_final_dashboard_plot(path: Path, rows: Sequence[dict[str, Any]], parameter_labels: Sequence[str]) -> None:
    if len(parameter_labels) < 2 or not rows:
        return
    apply_plot_style()
    x_label, y_label = parameter_labels[0], parameter_labels[1]
    fig = plt.figure(figsize=(7.2, 5.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.25, 1.25, 1.0])
    axes = [fig.add_subplot(gs[:, :2]), fig.add_subplot(gs[0, 2]), fig.add_subplot(gs[1, 2])]
    metric_specs = [
        ("cooling_score_weighted", "加权综合冷却得分", "viridis"),
        ("epsilon_8_13_avg", "8-13 μm 平均发射率", "YlGn"),
        ("A_solar_weighted", "太阳加权吸收率", "YlOrRd_r"),
    ]
    for ax, (metric, title, cmap) in zip(axes, metric_specs):
        style_axis(ax, grid=False)
        xs, ys, grid = _grid_from_rows(rows, parameter_labels, metric)
        image = ax.imshow(
            grid,
            origin="lower",
            aspect="auto",
            cmap=cmap,
            extent=[xs.min(), xs.max(), ys.min(), ys.max()],
            interpolation="nearest",
        )
        for row in rows:
            ax.scatter(float(row[x_label]), float(row[y_label]), s=50, facecolors="none", edgecolors="white", linewidths=0.8)
            if len(rows) <= 36:
                ax.text(float(row[x_label]), float(row[y_label]), f"{float(row[metric]):.3f}", ha="center", va="center", fontsize=7.3, color="white")
        best = min(rows, key=lambda row: float(row[metric])) if metric == "A_solar_weighted" else max(rows, key=lambda row: float(row[metric]))
        ax.scatter([float(best[x_label])], [float(best[y_label])], marker="*", s=230, c=RED, edgecolors="white", linewidths=1.0)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(title)
        cbar = fig.colorbar(image, ax=ax, label=_metric_label_cn(metric))
        style_colorbar(cbar)

    fig.suptitle("PDRC 候选结构：综合得分与约束分解", fontsize=10, fontweight="semibold", color=INK)
    save_publication_figure(fig, path)
    plt.close(fig)


def export_pdrc_comsol_candidate_bundle(
    *,
    ir_csv_files: Sequence[str | Path],
    solar_csv_file: str | Path | None = None,
    prefix: str = "pdrc_comsol_candidates",
    parameter_selector: str = "d_TiO2",
    parameter_label: str = "d_TiO2_equal_nm",
    total_dielectric_base_nm: float = 1800.0,
    solar_weight_mode: str = "blackbody_5778K",
    solar_weight_csv: str | Path | None = None,
) -> dict[str, str]:
    """Export a complete PDRC COMSOL candidate-analysis bundle."""
    result = analyze_pdrc_comsol_candidates(
        ir_csv_files=ir_csv_files,
        solar_csv_file=solar_csv_file,
        parameter_selector=parameter_selector,
        parameter_label=parameter_label,
        total_dielectric_base_nm=total_dielectric_base_nm,
        solar_weight_mode=solar_weight_mode,
        solar_weight_csv=solar_weight_csv,
    )
    saved: dict[str, str] = {}
    parameter_labels = list(result.get("parameter_labels", [result["parameter_label"]]))
    primary_parameter_label = parameter_labels[0]
    ir_rows = result["complete_ir_summary"]
    final_rows = result["final_metrics"]

    ir_summary_csv = output_file(f"{prefix}_ir_summary.csv")
    _write_dict_csv(ir_summary_csv, ir_rows)
    saved["ir_summary_csv"] = str(ir_summary_csv)

    ir_merged_csv = output_file(f"{prefix}_ir_merged.csv")
    _write_spectrum_rows(ir_merged_csv, result["ir_rows"], parameter_labels)
    saved["ir_merged_csv"] = str(ir_merged_csv)

    if result["solar_summary"]:
        solar_summary_csv = output_file(f"{prefix}_solar_summary.csv")
        _write_dict_csv(solar_summary_csv, result["solar_summary"])
        saved["solar_summary_csv"] = str(solar_summary_csv)

    if final_rows:
        final_csv = output_file(f"{prefix}_final_metrics.csv")
        _write_dict_csv(final_csv, final_rows)
        saved["final_metrics_csv"] = str(final_csv)

    json_path = output_file(f"{prefix}_summary.json")
    payload = {
        "parameter_label": parameter_label,
        "parameter_labels": parameter_labels,
        "solar_weight_mode": result["solar_weight_mode"],
        "ir_source_ranges": result["ir_source_ranges"],
        "best_ir": max(ir_rows, key=lambda row: float(row["ir_A_avg"])) if ir_rows else None,
        "best_final": max(final_rows, key=lambda row: float(row["cooling_score_weighted"])) if final_rows else None,
        "final_metrics": final_rows,
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    saved["summary_json"] = str(json_path)

    txt_path = output_file(f"{prefix}_summary.txt")
    lines = [
        "PDRC COMSOL 候选结构分析",
        "=" * 80,
        f"parameter_label = {parameter_label}",
        f"parameter_labels = {parameter_labels}",
        f"solar_weight_mode = {result['solar_weight_mode']}",
        "",
        "IR source files:",
    ]
    for item in result["ir_source_ranges"]:
        lines.append(f"  {item['file']} | lambda={item['lambda_range_um']} um | parameters={item.get('parameter_ranges_nm')} nm")
    if final_rows:
        lines.extend(["", "Final candidates:"])
        for row in final_rows:
            parameter_text = ", ".join(f"{label}={float(row[label]):.1f} nm" for label in parameter_labels if label in row)
            lines.append(
                f"  {parameter_text} | "
                f"A_solar_avg={float(row['A_solar_avg']):.4f} | "
                f"A_solar_weighted={float(row['A_solar_weighted']):.4f} | "
                f"epsilon_8_13_avg={float(row['epsilon_8_13_avg']):.4f} | "
                f"score_weighted={float(row['cooling_score_weighted']):.4f} | "
                f"passes=solar:{row['passes_solar']}, weighted:{row['passes_solar_weighted']}, ir:{row['passes_ir']}"
            )
        best = max(final_rows, key=lambda row: float(row["cooling_score_weighted"]))
        best_parameter_text = ", ".join(f"{label}={float(best[label]):.1f} nm" for label in parameter_labels if label in best)
        lines.extend(
            [
                "",
                f"Best by weighted cooling_score: {best_parameter_text}",
                "Note: default solar weighting uses a 5778 K blackbody proxy; pass --solar-weight-csv for ASTM/AM1.5 data.",
            ]
        )
    with txt_path.open("w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["summary_txt"] = str(txt_path)

    ir_plot = output_file(f"{prefix}_ir_summary.png")
    # Convert ir row names to final-style names for plotting.
    ir_plot_rows = []
    for row in ir_rows:
        plot_row = {
            "epsilon_8_13_avg": row["ir_A_avg"],
            "A_min_8_13": row["ir_A_min"],
            "A_at_8p9um": row.get("A_at_8p9um", float("nan")),
            "A_at_10um": row.get("A_at_10um", float("nan")),
            "A_at_12um": row.get("A_at_12um", float("nan")),
        }
        for label in parameter_labels:
            if label in row:
                plot_row[label] = row[label]
        ir_plot_rows.append(plot_row)
    if len(parameter_labels) == 1:
        _make_ir_summary_plot(ir_plot, ir_plot_rows, primary_parameter_label)
    else:
        _make_two_parameter_heatmap_plot(
            ir_plot,
            ir_plot_rows,
            parameter_labels,
            metric="epsilon_8_13_avg",
            title="PDRC 红外窗口扫描",
            cmap="YlGn",
        )
        ir_scatter_plot = output_file(f"{prefix}_ir_summary_scatter.png")
        _make_two_parameter_scatter_plot(
            ir_scatter_plot,
            ir_plot_rows,
            parameter_labels,
            metric="epsilon_8_13_avg",
            title="PDRC 红外窗口实测点",
        )
        saved["ir_summary_scatter_png"] = str(ir_scatter_plot)
    saved["ir_summary_png"] = str(ir_plot)

    if final_rows:
        metrics_plot = output_file(f"{prefix}_final_metrics.png")
        if len(parameter_labels) == 1:
            _make_final_metrics_plot(metrics_plot, final_rows, primary_parameter_label)
        else:
            _make_two_parameter_heatmap_plot(
                metrics_plot,
                final_rows,
                parameter_labels,
                metric="cooling_score_weighted",
                title="PDRC 加权冷却得分",
                cmap="viridis",
            )
            metrics_scatter_plot = output_file(f"{prefix}_final_metrics_scatter.png")
            _make_two_parameter_scatter_plot(
                metrics_scatter_plot,
                final_rows,
                parameter_labels,
                metric="cooling_score_weighted",
                title="PDRC 加权冷却得分实测点",
            )
            saved["final_metrics_scatter_png"] = str(metrics_scatter_plot)
            dashboard_plot = output_file(f"{prefix}_final_dashboard.png")
            _make_final_dashboard_plot(dashboard_plot, final_rows, parameter_labels)
            saved["final_dashboard_png"] = str(dashboard_plot)
        saved["final_metrics_png"] = str(metrics_plot)

    source_files = [str(Path(path)) for path in ir_csv_files]
    if solar_csv_file is not None:
        source_files.append(str(Path(solar_csv_file)))
    if solar_weight_csv is not None:
        source_files.append(str(Path(solar_weight_csv)))
    audit = build_figure_audit(
        figure_id=f"{prefix}_candidate_maps",
        title="PDRC COMSOL 候选结构指标地图",
        evidence_level="external_validation",
        checks=[audit_source_files(source_files)],
        source_files=source_files,
    )
    audit_path = output_file(f"{prefix}_figure_audit.json")
    saved["audit_json"] = write_figure_audit(audit_path, audit)

    manifest_path = output_file(f"{prefix}_manifest.json")
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)
    saved["manifest"] = str(manifest_path)
    return saved
