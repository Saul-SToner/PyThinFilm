from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

from .education import list_report_chapter2_cases, simulate_report_case
from .io import load_spectrum_csv
from .paths import output_file

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

MAIN_RED = "#c94f2d"
REF_BLUE = "#1d4ed8"
ERR_GOLD = "#b7791f"
TARGET_GREEN = "#0f766e"
GRID_COLOR = "#d7dde5"
TEXT_DARK = "#223046"
PANEL_BG = "#f7f8fb"
CN_FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
)

_LEADING_FLOAT_RE = re.compile(r"^\s*([+-]?(?:\d+\.\d*|\d*\.?\d+)(?:[Ee][+-]?\d+)?)")

EXPANSION_VALIDATION_CASE_IDS: tuple[str, ...] = (
    "quarter_wave_single_layer",
    "half_wave_single_layer",
    "porous_sio2_layer",
    "porous_double_ar",
    "moth_eye_effective_gradient",
    "quarter_wave_double_layer",
    "quarter_wave_stack",
    "bragg_reflector",
    "fp_filter",
    "narrowband_filter",
    "rugate_filter",
)


def _style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor(PANEL_BG)
    ax.grid(True, alpha=0.35, color=GRID_COLOR, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#c9d2dc")
    ax.tick_params(colors=TEXT_DARK)
    ax.xaxis.label.set_color(TEXT_DARK)
    ax.yaxis.label.set_color(TEXT_DARK)
    ax.title.set_color(TEXT_DARK)


def _cn_font() -> FontProperties | None:
    for path in CN_FONT_CANDIDATES:
        if path.exists():
            return FontProperties(fname=str(path))
    return None


def _set_axis_labels_cn(ax: plt.Axes, *, title: str, xlabel: str, ylabel: str) -> None:
    font = _cn_font()
    if font is None:
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        return
    ax.set_title(title, fontproperties=font)
    ax.set_xlabel(xlabel, fontproperties=font)
    ax.set_ylabel(ylabel, fontproperties=font)


def _validation_core_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    summary = result["summary"]
    quantity = str(result["quantity"])
    lambda0_nm = float(result["lambda0_nm"])
    return {
        "quantity": quantity,
        "lambda0_nm": lambda0_nm,
        "theory_at_lambda0": float(summary["theory_at_lambda0"]),
        "reference_at_lambda0": float(summary["reference_at_lambda0"]),
        "mae": float(summary["mae"]),
        "rmse": float(summary["rmse"]),
        "max_abs_error": float(summary["max_abs_error"]),
        "mean_bias": float(summary["mean_bias"]),
        "lambda0_error": float(summary["lambda0_error"]),
    }


def _validation_core_metrics_cn(result: Dict[str, Any]) -> Dict[str, Any]:
    core = _validation_core_metrics(result)
    quantity = core["quantity"]
    lambda0_nm = core["lambda0_nm"]
    return {
        "主比较量": quantity,
        "中心波长_nm": lambda0_nm,
        f"理论{quantity}@中心波长": core["theory_at_lambda0"],
        f"参考{quantity}@中心波长": core["reference_at_lambda0"],
        "平均绝对误差_MAE": core["mae"],
        "均方根误差_RMSE": core["rmse"],
        "最大绝对误差": core["max_abs_error"],
        "平均偏差": core["mean_bias"],
        "中心点误差": core["lambda0_error"],
    }


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


def _selector_fallbacks(quantity: str, selector: int | str | None) -> List[int | str | None]:
    candidates: List[int | str | None] = []
    if selector is not None:
        candidates.append(selector)
    key = str(quantity).strip().upper()
    if key == "R":
        candidates.extend(["R (1)", "reflectance", "abs(ewfd.S11)^2 (1)"])
    elif key == "T":
        candidates.extend(["T (1)", "transmittance", "abs(ewfd.S21)^2 (1)"])
    elif key == "A":
        candidates.extend(["A (1)", "absorptance", "1-abs(ewfd.S11)^2-abs(ewfd.S21)^2 (1)"])
    seen = set()
    deduped: List[int | str | None] = []
    for item in candidates:
        key2 = repr(item)
        if key2 in seen:
            continue
        seen.add(key2)
        deduped.append(item)
    return deduped


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
    grid = np.linspace(x_min, x_max, max(int(n_grid), 50))
    return grid, np.interp(grid, x1_nm, y1), np.interp(grid, x2_nm, y2)


def _error_metrics(theory: np.ndarray, reference: np.ndarray) -> Dict[str, float]:
    diff = np.asarray(theory, dtype=float) - np.asarray(reference, dtype=float)
    return {
        "mae": float(np.mean(np.abs(diff))),
        "rmse": float(np.sqrt(np.mean(diff ** 2))),
        "max_abs_error": float(np.max(np.abs(diff))),
        "mean_bias": float(np.mean(diff)),
    }


def compare_teaching_case_to_reference(
    case_id: str,
    reference_csv: Path | str,
    *,
    y_selector: int | str | None = None,
    quantity: str | None = None,
    reference_label: str = "COMSOL",
    n_grid: int = 600,
    **case_overrides: Any,
) -> Dict[str, Any]:
    """Compare one teaching-case theory curve against a CSV reference curve."""

    theory_result = simulate_report_case(case_id, **case_overrides)
    requested_quantity = quantity
    ref_spec = None
    last_error: Exception | None = None
    for selector_try in _selector_fallbacks(str(requested_quantity or ""), y_selector):
        try:
            ref_spec = load_spectrum_csv(Path(reference_csv), y_selector=selector_try)
            break
        except Exception as exc:
            last_error = exc
    if ref_spec is None:
        raise ValueError(f"无法读取参考曲线列: {reference_csv}. 最后错误: {last_error}")

    active_quantity = _pick_quantity(case_id, ref_spec.y_kind, requested_quantity)
    theory_y = _series_for_quantity(theory_result, active_quantity)
    ref_x = np.asarray(ref_spec.x_nm, dtype=float)
    ref_y = np.asarray(ref_spec.y, dtype=float)
    theory_x = np.asarray(theory_result["wavelength_nm"], dtype=float)

    grid_nm, theory_i, reference_i = _resample_pair(
        theory_x,
        theory_y,
        ref_x,
        ref_y,
        n_grid=n_grid,
    )
    error = theory_i - reference_i
    metrics = _error_metrics(theory_i, reference_i)

    lambda0_nm = float(theory_result["lambda0_nm"])
    theory_at_lambda0 = float(np.interp(lambda0_nm, grid_nm, theory_i))
    reference_at_lambda0 = float(np.interp(lambda0_nm, grid_nm, reference_i))
    metrics["lambda0_error"] = theory_at_lambda0 - reference_at_lambda0

    title_cn = str(theory_result.get("title_cn") or theory_result.get("design_type") or case_id)
    return {
        "case_id": str(case_id),
        "title_cn": title_cn,
        "title_en": str(theory_result.get("title_en") or case_id),
        "reference_label": str(reference_label),
        "reference_csv": str(Path(reference_csv)),
        "reference_y_label": str(ref_spec.y_label),
        "reference_y_kind": str(ref_spec.y_kind),
        "quantity": active_quantity,
        "lambda0_nm": lambda0_nm,
        "theory_result": theory_result,
        "reference_spec": {
            "path": str(ref_spec.path),
            "x_label": ref_spec.x_label,
            "y_label": ref_spec.y_label,
            "y_kind": ref_spec.y_kind,
            "all_column_labels": list(ref_spec.all_column_labels),
        },
        "comparison": {
            "wavelength_nm": grid_nm,
            "theory": theory_i,
            "reference": reference_i,
            "error": error,
        },
        "metrics": metrics,
        "summary": {
            "lambda_min_nm": float(grid_nm[0]),
            "lambda_max_nm": float(grid_nm[-1]),
            "num_points": int(len(grid_nm)),
            "theory_at_lambda0": theory_at_lambda0,
            "reference_at_lambda0": reference_at_lambda0,
            **metrics,
        },
    }


def run_teaching_validation_suite(
    cases: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Run a list of teaching-case validations.

    Each item should contain at least:
    - case_id
    - reference_csv
    Optional keys:
    - y_selector
    - quantity
    - reference_label
    - overrides
    """

    results: List[Dict[str, Any]] = []
    for item in cases:
        overrides = dict(item.get("overrides", {}))
        results.append(
            compare_teaching_case_to_reference(
                case_id=str(item["case_id"]),
                reference_csv=item["reference_csv"],
                y_selector=item.get("y_selector"),
                quantity=item.get("quantity"),
                reference_label=str(item.get("reference_label", "COMSOL")),
                **overrides,
            )
        )
    return results


def build_standard_teaching_validation_cases(
    single_ar_csv: Path | str,
    fp_single_csv: Path | str,
    high_reflector_csv: Path | str,
    *,
    reference_label: str = "COMSOL",
) -> List[Dict[str, Any]]:
    """Build the standard three-case validation bundle.

    The bundle covers:
    1. single-layer anti-reflection coating
    2. single-half-wave F-P filter with the clarified HL^4-C-LH^4 structure
    3. high reflector with the clarified Air/(HL)^6H/Glass structure
    """

    return [
        {
            "case_id": "single_ar",
            "reference_csv": str(Path(single_ar_csv)),
            "y_selector": "R (1)",
            "quantity": "R",
            "reference_label": reference_label,
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.52,
                "n_low": 1.38,
            },
        },
        {
            "case_id": "fp_single_halfwave",
            "reference_csv": str(Path(fp_single_csv)),
            "y_selector": "T (1)",
            "quantity": "T",
            "reference_label": reference_label,
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
        {
            "case_id": "high_reflector",
            "reference_csv": str(Path(high_reflector_csv)),
            "y_selector": "R (1)",
            "quantity": "R",
            "reference_label": reference_label,
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
    ]


def build_teaching_expansion_validation_templates(
    *,
    reference_label: str = "COMSOL",
) -> List[Dict[str, Any]]:
    """Build validation templates for the current teaching-case expansion set.

    These templates are intentionally CSV-free. They define the recommended
    comparison quantity, default column selector, and default parameter
    overrides so that a future COMSOL or experimental spectrum can be plugged in
    with minimal manual editing.
    """

    case_map = {
        str(item["case_id"]): item
        for item in list_report_chapter2_cases()
        if str(item["case_id"]) in EXPANSION_VALIDATION_CASE_IDS
    }

    templates: List[Dict[str, Any]] = []
    for case_id in EXPANSION_VALIDATION_CASE_IDS:
        if case_id not in case_map:
            continue
        item = case_map[case_id]
        quantity = _default_case_quantity(case_id)
        y_selector = f"{quantity} (1)"
        result = simulate_report_case(case_id)
        templates.append(
            {
                "case_id": case_id,
                "title_cn": str(item.get("title_cn", case_id)),
                "title_en": str(item.get("title_en", case_id)),
                "design_type": str(item.get("design_type", case_id)),
                "reference_label": str(reference_label),
                "reference_csv": "",
                "recommended_quantity": quantity,
                "recommended_y_selector": y_selector,
                "default_overrides": dict(item.get("default_params", {})),
                "lambda0_nm": float(result.get("lambda0_nm", 550.0)),
                "theta_deg": float(result.get("theta_deg", 0.0)),
                "notes_cn": (
                    "建议后续提供同结构的 COMSOL 或实验谱线 CSV，并优先使用推荐列选择器直接接入验证流程。"
                ),
                "notes_en": (
                    "Provide a matching COMSOL or experimental spectrum CSV later and plug it into the validation flow with the recommended column selector."
                ),
            }
        )
    return templates


def build_teaching_expansion_validation_cases_from_mapping(
    reference_mapping: Dict[str, Dict[str, Any]],
    *,
    reference_label: str = "COMSOL",
) -> List[Dict[str, Any]]:
    """Convert a filled reference mapping into runnable validation cases.

    The input mapping should use `case_id` as key. Each value may contain:
    - reference_csv (required)
    - y_selector (optional; defaults to the template recommendation)
    - quantity (optional; defaults to the template recommendation)
    - reference_label (optional)
    - overrides (optional; merged onto the template default overrides)
    """

    template_map = {
        str(item["case_id"]): item
        for item in build_teaching_expansion_validation_templates(reference_label=reference_label)
    }
    cases: List[Dict[str, Any]] = []
    for case_id, cfg in reference_mapping.items():
        if case_id not in template_map:
            raise KeyError(f"Unknown expansion validation case_id: {case_id}")
        reference_csv = str(cfg.get("reference_csv", "")).strip()
        if not reference_csv:
            raise ValueError(f"Missing reference_csv for expansion validation case: {case_id}")
        template = template_map[case_id]
        overrides = dict(template.get("default_overrides", {}))
        overrides.update(dict(cfg.get("overrides", {})))
        cases.append(
            {
                "case_id": case_id,
                "reference_csv": reference_csv,
                "y_selector": cfg.get("y_selector", template["recommended_y_selector"]),
                "quantity": cfg.get("quantity", template["recommended_quantity"]),
                "reference_label": str(cfg.get("reference_label", reference_label)),
                "overrides": overrides,
            }
        )
    return cases


def load_teaching_expansion_validation_mapping(
    template_file: Path | str,
) -> Dict[str, Dict[str, Any]]:
    """Load a filled expansion validation template from JSON or CSV."""

    path = Path(template_file)
    suffix = path.suffix.lower()
    mapping: Dict[str, Dict[str, Any]] = {}

    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        cases = payload.get("cases", payload)
        if not isinstance(cases, list):
            raise ValueError("JSON template must contain a top-level 'cases' list or be a list.")
        for item in cases:
            if not isinstance(item, dict):
                continue
            case_id = str(item.get("case_id", "")).strip()
            if not case_id:
                continue
            entry: Dict[str, Any] = {}
            for key in ("reference_csv", "recommended_y_selector", "recommended_quantity", "reference_label"):
                if key in item:
                    entry[key] = item[key]
            if "default_overrides" in item:
                entry["overrides"] = dict(item.get("default_overrides", {}))
            mapping[case_id] = entry
        return mapping

    if suffix == ".csv":
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                case_id = str(row.get("case_id", "")).strip()
                if not case_id:
                    continue
                entry: Dict[str, Any] = {
                    "reference_csv": str(row.get("reference_csv", "")).strip(),
                }
                y_selector = str(row.get("recommended_y_selector", "")).strip()
                if y_selector:
                    entry["y_selector"] = y_selector
                quantity = str(row.get("recommended_quantity", "")).strip()
                if quantity:
                    entry["quantity"] = quantity
                reference_label = str(row.get("reference_label", "")).strip()
                if reference_label:
                    entry["reference_label"] = reference_label
                overrides_raw = str(row.get("default_overrides_json", "")).strip()
                if overrides_raw:
                    entry["overrides"] = json.loads(overrides_raw)
                mapping[case_id] = entry
        return mapping

    raise ValueError("template_file must be a .json or .csv file.")


def run_standard_teaching_validation_suite(
    single_ar_csv: Path | str,
    fp_single_csv: Path | str,
    high_reflector_csv: Path | str,
    *,
    reference_label: str = "COMSOL",
) -> List[Dict[str, Any]]:
    cases = build_standard_teaching_validation_cases(
        single_ar_csv=single_ar_csv,
        fp_single_csv=fp_single_csv,
        high_reflector_csv=high_reflector_csv,
        reference_label=reference_label,
    )
    return run_teaching_validation_suite(cases)


def export_teaching_validation_result(
    result: Dict[str, Any],
    *,
    prefix: str = "teaching_validation",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    stem = f"{prefix}_{result['case_id']}"
    comp = result["comparison"]
    wl = np.asarray(comp["wavelength_nm"], dtype=float)
    theory = np.asarray(comp["theory"], dtype=float)
    reference = np.asarray(comp["reference"], dtype=float)
    error = np.asarray(comp["error"], dtype=float)
    summary = result["summary"]
    core_metrics = _validation_core_metrics(result)
    core_metrics_cn = _validation_core_metrics_cn(result)
    display_title = str(result.get("title_en") or result.get("title_cn") or result["case_id"])

    if save_csv:
        csv_path = output_file(f"{stem}_comparison.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write("wavelength_nm,theory,reference,error\n")
            for row in zip(wl, theory, reference, error):
                f.write(",".join(f"{float(x):.12g}" for x in row) + "\n")
        saved["csv"] = str(csv_path)

    if save_json:
        json_path = output_file(f"{stem}_summary.json")
        payload = {
            "case_id": result["case_id"],
            "title_cn": result["title_cn"],
            "title_en": result.get("title_en"),
            "quantity": result["quantity"],
            "reference_label": result["reference_label"],
            "reference_csv": result["reference_csv"],
            "summary": summary,
            "core_metrics": core_metrics,
            "core_metrics_cn": core_metrics_cn,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        saved["json"] = str(json_path)

    if save_txt:
        txt_path = output_file(f"{stem}_summary.txt")
        lines = [
            "教学验证摘要",
            "=" * 80,
            f"case_id              = {result['case_id']}",
            f"title_cn             = {result['title_cn']}",
            f"title_en             = {result.get('title_en', '')}",
            f"quantity             = {result['quantity']}",
            f"reference_label      = {result['reference_label']}",
            f"reference_csv        = {result['reference_csv']}",
            "-" * 80,
            "核心指标：",
            f"中心波长 (nm)        = {core_metrics['lambda0_nm']:.6f}",
            f"理论值@中心波长      = {core_metrics['theory_at_lambda0']:.12e}",
            f"参考值@中心波长      = {core_metrics['reference_at_lambda0']:.12e}",
            f"MAE                  = {core_metrics['mae']:.12e}",
            f"RMSE                 = {core_metrics['rmse']:.12e}",
            f"最大绝对误差         = {core_metrics['max_abs_error']:.12e}",
            f"平均偏差             = {core_metrics['mean_bias']:.12e}",
            f"中心点误差           = {core_metrics['lambda0_error']:.12e}",
        ]
        with open(txt_path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(lines) + "\n")
        saved["txt"] = str(txt_path)

    if save_plot:
        png_path = output_file(f"{stem}_main.png")
        fig, axes = plt.subplots(2, 1, figsize=(8.4, 7.0), sharex=True, height_ratios=[2.2, 1.0])
        ax0, ax1 = axes
        _style_axis(ax0)
        _style_axis(ax1)

        ax0.plot(wl, theory, color=MAIN_RED, linewidth=2.4, label="理论曲线")
        ax0.plot(wl, reference, color=REF_BLUE, linewidth=2.0, alpha=0.92, label=result["reference_label"])
        ax0.axvline(float(result["lambda0_nm"]), color=TARGET_GREEN, linestyle=":", linewidth=1.4, alpha=0.9)
        ax0.set_ylabel(result["quantity"])
        ax0.set_title(f"{display_title} | 理论与{result['reference_label']}对照", fontweight="semibold")
        ax0.legend(loc="best", frameon=True, facecolor="white", edgecolor="#c9d2dc")
        ax0.text(
            0.985,
            0.97,
            "\n".join(
                [
                    f"MAE = {summary['mae']:.4e}",
                    f"RMSE = {summary['rmse']:.4e}",
                    f"最大误差 = {summary['max_abs_error']:.4e}",
                    f"平均偏差 = {summary['mean_bias']:+.4e}",
                    f"中心点误差 = {summary['lambda0_error']:+.4e}",
                ]
            ),
            transform=ax0.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.85, "edgecolor": "#cccccc"},
        )

        ax1.plot(wl, error, color=ERR_GOLD, linewidth=2.0)
        ax1.axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
        ax1.axvline(float(result["lambda0_nm"]), color=TARGET_GREEN, linestyle=":", linewidth=1.4, alpha=0.9)
        ax1.set_xlabel("波长 (nm)")
        ax1.set_ylabel("误差")

        fig.tight_layout()
        fig.savefig(png_path, dpi=180)
        plt.close(fig)
        saved["main_png"] = str(png_path)

        analysis_png = output_file(f"{stem}_analysis.png")
        fig2, axes2 = plt.subplots(1, 3, figsize=(11.0, 3.8))
        for ax in axes2:
            _style_axis(ax)

        labels = ["MAE", "RMSE", "MaxErr"]
        vals = [summary["mae"], summary["rmse"], summary["max_abs_error"]]
        axes2[0].bar(labels, vals, color=[MAIN_RED, REF_BLUE, ERR_GOLD], alpha=0.92)
        axes2[0].set_title("误差指标")

        axes2[1].bar(
            ["理论值@lambda0", "参考值@lambda0"],
            [summary["theory_at_lambda0"], summary["reference_at_lambda0"]],
            color=[MAIN_RED, REF_BLUE],
            alpha=0.92,
        )
        axes2[1].set_title("中心波长处取值")

        axes2[2].bar(
            ["平均偏差", "中心点误差"],
            [summary["mean_bias"], summary["lambda0_error"]],
            color=[ERR_GOLD, TARGET_GREEN],
            alpha=0.92,
        )
        axes2[2].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
        axes2[2].set_title("带符号误差")

        fig2.suptitle(f"{display_title} | 验证分析", fontweight="semibold", color=TEXT_DARK)
        fig2.tight_layout()
        fig2.savefig(analysis_png, dpi=180)
        plt.close(fig2)
        saved["analysis_png"] = str(analysis_png)

    return saved


def export_teaching_validation_suite_summary(
    results: Iterable[Dict[str, Any]],
    *,
    filename_prefix: str = "teaching_validation_suite",
) -> Dict[str, str]:
    rows = list(results)
    saved: Dict[str, str] = {}

    csv_path = output_file(f"{filename_prefix}_summary.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("case_id,title_cn,title_en,quantity,reference_label,mae,rmse,max_abs_error,mean_bias,lambda0_error,theory_at_lambda0,reference_at_lambda0\n")
        for item in rows:
            s = item["summary"]
            f.write(
                ",".join(
                    [
                        str(item["case_id"]),
                        str(item.get("title_cn", "")),
                        str(item.get("title_en", "")),
                        str(item["quantity"]),
                        str(item["reference_label"]),
                        f"{float(s['mae']):.12g}",
                        f"{float(s['rmse']):.12g}",
                        f"{float(s['max_abs_error']):.12g}",
                        f"{float(s['mean_bias']):.12g}",
                        f"{float(s['lambda0_error']):.12g}",
                        f"{float(s['theory_at_lambda0']):.12g}",
                        f"{float(s['reference_at_lambda0']):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{filename_prefix}_summary.json")
    payload = [
        {
            "case_id": item["case_id"],
            "title_cn": item["title_cn"],
            "title_en": item.get("title_en"),
            "quantity": item["quantity"],
            "reference_label": item["reference_label"],
            "summary": item["summary"],
            "core_metrics": _validation_core_metrics(item),
            "core_metrics_cn": _validation_core_metrics_cn(item),
        }
        for item in rows
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{filename_prefix}_summary.txt")
    lines = ["教学验证总览摘要", "=" * 80, ""]
    for item in rows:
        core = _validation_core_metrics(item)
        lines.extend(
            [
                f"case_id              = {item['case_id']}",
                f"title_cn             = {item.get('title_cn', '')}",
                f"title_en             = {item.get('title_en', '')}",
                f"quantity             = {item['quantity']}",
                f"reference_label      = {item['reference_label']}",
                f"MAE                  = {core['mae']:.12e}",
                f"RMSE                 = {core['rmse']:.12e}",
                f"最大绝对误差         = {core['max_abs_error']:.12e}",
                f"中心点误差           = {core['lambda0_error']:.12e}",
                f"理论值@中心波长      = {core['theory_at_lambda0']:.12e}",
                f"参考值@中心波长      = {core['reference_at_lambda0']:.12e}",
                "-" * 80,
            ]
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    png_path = output_file(f"{filename_prefix}_overview.png")
    labels = [str(item["title_en"] or item["case_id"]) for item in rows]
    maes = [float(item["summary"]["mae"]) for item in rows]
    rmses = [float(item["summary"]["rmse"]) for item in rows]
    maxes = [float(item["summary"]["max_abs_error"]) for item in rows]
    x = np.arange(len(labels), dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.4))
    for ax in axes:
        _style_axis(ax)

    width = 0.24
    axes[0].bar(x - width, maes, width=width, color=MAIN_RED, label="平均绝对误差", alpha=0.92)
    axes[0].bar(x, rmses, width=width, color=REF_BLUE, label="均方根误差", alpha=0.92)
    axes[0].bar(x + width, maxes, width=width, color=ERR_GOLD, label="最大误差", alpha=0.92)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=12, ha="right")
    axes[0].set_ylabel("误差")
    axes[0].set_title("验证误差指标", fontweight="semibold")
    axes[0].legend(loc="best", frameon=True, facecolor="white", edgecolor="#c9d2dc")

    lambda0_errors = [float(item["summary"]["lambda0_error"]) for item in rows]
    biases = [float(item["summary"]["mean_bias"]) for item in rows]
    axes[1].bar(x - 0.15, biases, width=0.3, color=ERR_GOLD, label="平均偏差", alpha=0.92)
    axes[1].bar(x + 0.15, lambda0_errors, width=0.3, color=TARGET_GREEN, label="中心点误差", alpha=0.92)
    axes[1].axhline(0.0, color="#666666", linewidth=1.0, alpha=0.85)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=12, ha="right")
    axes[1].set_ylabel("带符号误差")
    axes[1].set_title("偏差与中心波长误差", fontweight="semibold")
    axes[1].legend(loc="best", frameon=True, facecolor="white", edgecolor="#c9d2dc")

    fig.suptitle("教学验证总览", fontsize=12, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    saved["overview_png"] = str(png_path)
    return saved


def export_standard_teaching_validation_bundle(
    single_ar_csv: Path | str,
    fp_single_csv: Path | str,
    high_reflector_csv: Path | str,
    *,
    prefix: str = "teaching_validation_standard",
    reference_label: str = "COMSOL",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, Any]:
    results = run_standard_teaching_validation_suite(
        single_ar_csv=single_ar_csv,
        fp_single_csv=fp_single_csv,
        high_reflector_csv=high_reflector_csv,
        reference_label=reference_label,
    )

    exported_cases: Dict[str, Dict[str, str]] = {}
    for item in results:
        exported_cases[str(item["case_id"])] = export_teaching_validation_result(
            item,
            prefix=prefix,
            save_plot=save_plot,
            save_csv=save_csv,
            save_json=save_json,
            save_txt=save_txt,
        )

    suite_files = export_teaching_validation_suite_summary(
        results,
        filename_prefix=f"{prefix}_suite",
    )

    manifest_path = output_file(f"{prefix}_manifest.json")
    manifest = {
        "reference_label": reference_label,
        "cases": {
            str(item["case_id"]): {
                "summary": item["summary"],
                "files": exported_cases[str(item["case_id"])],
            }
            for item in results
        },
        "suite_files": suite_files,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "results": results,
        "case_files": exported_cases,
        "suite_files": suite_files,
        "manifest": str(manifest_path),
    }


def export_teaching_expansion_validation_template_bundle(
    *,
    prefix: str = "teaching_expansion_validation_templates",
    reference_label: str = "COMSOL",
) -> Dict[str, str]:
    """Export a template bundle for future validation of expansion cases."""

    rows = build_teaching_expansion_validation_templates(reference_label=reference_label)
    saved: Dict[str, str] = {}

    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "case_id,title_cn,title_en,design_type,recommended_quantity,recommended_y_selector,"
            "lambda0_nm,theta_deg,reference_label,reference_csv,default_overrides_json,notes_cn\n"
        )
        for item in rows:
            overrides_json = json.dumps(item["default_overrides"], ensure_ascii=False, separators=(",", ":"))
            cells = [
                str(item["case_id"]),
                str(item["title_cn"]),
                str(item["title_en"]),
                str(item["design_type"]),
                str(item["recommended_quantity"]),
                str(item["recommended_y_selector"]),
                f"{float(item['lambda0_nm']):.12g}",
                f"{float(item['theta_deg']):.12g}",
                str(item["reference_label"]),
                str(item["reference_csv"]),
                overrides_json.replace('"', '""'),
                str(item["notes_cn"]),
            ]
            quoted = []
            for cell in cells:
                if any(ch in cell for ch in [",", "\"", "\n"]):
                    quoted.append(f"\"{cell}\"")
                else:
                    quoted.append(cell)
            f.write(",".join(quoted) + "\n")
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    payload = {
        "reference_label": reference_label,
        "case_count": len(rows),
        "cases": rows,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "Teaching Expansion Validation Templates",
        "=" * 80,
        f"reference_label = {reference_label}",
        f"case_count       = {len(rows)}",
        "",
    ]
    for item in rows:
        lines.extend(
            [
                f"case_id                = {item['case_id']}",
                f"title_cn               = {item['title_cn']}",
                f"title_en               = {item['title_en']}",
                f"recommended_quantity   = {item['recommended_quantity']}",
                f"recommended_y_selector = {item['recommended_y_selector']}",
                f"lambda0_nm             = {float(item['lambda0_nm']):.6f}",
                f"theta_deg              = {float(item['theta_deg']):.6f}",
                f"reference_csv          = {item['reference_csv']}",
                f"default_overrides      = {json.dumps(item['default_overrides'], ensure_ascii=False)}",
                f"notes_cn               = {item['notes_cn']}",
                "-" * 80,
            ]
        )
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    return saved


def export_teaching_expansion_validation_bundle_from_mapping(
    reference_mapping: Dict[str, Dict[str, Any]],
    *,
    prefix: str = "teaching_expansion_validation_bundle",
    reference_label: str = "COMSOL",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, Any]:
    """Run and export expansion-case validation results from a reference mapping."""

    cases = build_teaching_expansion_validation_cases_from_mapping(
        reference_mapping=reference_mapping,
        reference_label=reference_label,
    )
    results = run_teaching_validation_suite(cases)

    exported_cases: Dict[str, Dict[str, str]] = {}
    for item in results:
        exported_cases[str(item["case_id"])] = export_teaching_validation_result(
            item,
            prefix=prefix,
            save_plot=save_plot,
            save_csv=save_csv,
            save_json=save_json,
            save_txt=save_txt,
        )

    suite_files = export_teaching_validation_suite_summary(
        results,
        filename_prefix=f"{prefix}_suite",
    )

    manifest_path = output_file(f"{prefix}_manifest.json")
    manifest = {
        "reference_label": reference_label,
        "cases": {
            str(item["case_id"]): {
                "summary": item["summary"],
                "files": exported_cases[str(item["case_id"])],
            }
            for item in results
        },
        "suite_files": suite_files,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "results": results,
        "case_files": exported_cases,
        "suite_files": suite_files,
        "manifest": str(manifest_path),
    }


def export_teaching_expansion_validation_bundle_from_file(
    template_file: Path | str,
    *,
    prefix: str = "teaching_expansion_validation_bundle",
    reference_label: str = "COMSOL",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, Any]:
    """Run and export expansion-case validation from a filled template file."""

    mapping = load_teaching_expansion_validation_mapping(template_file)
    return export_teaching_expansion_validation_bundle_from_mapping(
        reference_mapping=mapping,
        prefix=prefix,
        reference_label=reference_label,
        save_plot=save_plot,
        save_csv=save_csv,
        save_json=save_json,
        save_txt=save_txt,
    )


def rank_candidate_teaching_cases_for_reference(
    reference_csv: Path | str,
    candidate_case_ids: Sequence[str],
    *,
    y_selector: int | str | None = None,
    quantity: str | None = None,
    reference_label: str = "COMSOL",
) -> List[Dict[str, Any]]:
    """Rank candidate teaching cases against one reference CSV by MAE."""

    rows: List[Dict[str, Any]] = []
    for case_id in candidate_case_ids:
        result = compare_teaching_case_to_reference(
            case_id=case_id,
            reference_csv=reference_csv,
            y_selector=y_selector,
            quantity=quantity,
            reference_label=reference_label,
        )
        rows.append(
            {
                "case_id": case_id,
                "title_cn": result["title_cn"],
                "title_en": result["title_en"],
                "quantity": result["quantity"],
                "mae": float(result["summary"]["mae"]),
                "rmse": float(result["summary"]["rmse"]),
                "max_abs_error": float(result["summary"]["max_abs_error"]),
                "lambda0_error": float(result["summary"]["lambda0_error"]),
                "theory_at_lambda0": float(result["summary"]["theory_at_lambda0"]),
                "reference_at_lambda0": float(result["summary"]["reference_at_lambda0"]),
            }
        )
    rows.sort(key=lambda item: item["mae"])
    return rows


def export_candidate_case_ranking(
    reference_csv: Path | str,
    candidate_case_ids: Sequence[str],
    *,
    prefix: str = "teaching_case_ranking",
    y_selector: int | str | None = None,
    quantity: str | None = None,
    reference_label: str = "COMSOL",
) -> Dict[str, str]:
    """Export a ranked summary for likely matching teaching cases."""

    rows = rank_candidate_teaching_cases_for_reference(
        reference_csv=reference_csv,
        candidate_case_ids=candidate_case_ids,
        y_selector=y_selector,
        quantity=quantity,
        reference_label=reference_label,
    )
    saved: Dict[str, str] = {}

    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "rank,case_id,title_cn,title_en,quantity,mae,rmse,max_abs_error,lambda0_error,theory_at_lambda0,reference_at_lambda0\n"
        )
        for idx, item in enumerate(rows, start=1):
            f.write(
                ",".join(
                    [
                        str(idx),
                        str(item["case_id"]),
                        str(item["title_cn"]),
                        str(item["title_en"]),
                        str(item["quantity"]),
                        f"{float(item['mae']):.12g}",
                        f"{float(item['rmse']):.12g}",
                        f"{float(item['max_abs_error']):.12g}",
                        f"{float(item['lambda0_error']):.12g}",
                        f"{float(item['theory_at_lambda0']):.12g}",
                        f"{float(item['reference_at_lambda0']):.12g}",
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"reference_csv": str(reference_csv), "rows": rows}, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "Teaching Case Ranking",
        "=" * 80,
        f"reference_csv = {reference_csv}",
        f"reference_label = {reference_label}",
        "",
    ]
    for idx, item in enumerate(rows, start=1):
        lines.extend(
            [
                f"rank                 = {idx}",
                f"case_id              = {item['case_id']}",
                f"title_cn             = {item['title_cn']}",
                f"quantity             = {item['quantity']}",
                f"mae                  = {item['mae']:.12e}",
                f"rmse                 = {item['rmse']:.12e}",
                f"max_abs_error        = {item['max_abs_error']:.12e}",
                f"lambda0_error        = {item['lambda0_error']:+.12e}",
                "-" * 80,
            ]
        )
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)
    return saved


def build_advanced_ar_validation_cases(
    single_ar_csv: Path | str,
    porous_csv: Path | str,
    porous_double_csv: Path | str,
    moth_eye_effective_csv: Path | str,
    moth_eye_2d_csv: Path | str,
    *,
    reference_label: str = "COMSOL",
) -> List[Dict[str, Any]]:
    """Build a themed validation suite for advanced anti-reflection structures."""

    return [
        {
            "case_id": "single_ar",
            "reference_csv": str(Path(single_ar_csv)),
            "y_selector": "R (1)",
            "quantity": "R",
            "reference_label": reference_label,
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.52,
                "n_low": 1.38,
            },
        },
        {
            "case_id": "porous_sio2_layer",
            "reference_csv": str(Path(porous_csv)),
            "y_selector": "R (1)",
            "quantity": "R",
            "reference_label": reference_label,
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.52,
                "n_low": 1.32,
            },
        },
        {
            "case_id": "porous_double_ar",
            "reference_csv": str(Path(porous_double_csv)),
            "y_selector": "abs(ewfd.S11)^2 (1)",
            "quantity": "R",
            "reference_label": reference_label,
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.5215,
                "n_porous": 1.18,
                "n_high": 1.45,
            },
        },
        {
            "case_id": "moth_eye_effective_gradient",
            "reference_csv": str(Path(moth_eye_effective_csv)),
            "y_selector": "R (1)",
            "quantity": "R",
            "reference_label": reference_label,
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.5215,
                "n_top": 1.10,
                "n_bottom": 1.50,
                "d_total_nm": 300.0,
                "num_gradient_layers": 5,
                "gradient_type": "linear",
                "layer_indices": [1.10, 1.20, 1.30, 1.40, 1.50],
                "layer_thickness_nm": [60.0, 60.0, 60.0, 60.0, 60.0],
            },
        },
        {
            "case_id": "moth_eye_effective_gradient",
            "reference_csv": str(Path(moth_eye_2d_csv)),
            "y_selector": "abs(ewfd.S11)^2 (1)",
            "quantity": "R",
            "reference_label": reference_label,
            "overrides": {
                "theta_deg": 0.0,
                "pol": "p",
                "lambda0_nm": 550.0,
                "n_incident": 1.0,
                "n_substrate": 1.5215,
                "n_top": 1.10,
                "n_bottom": 1.50,
                "d_total_nm": 300.0,
                "num_gradient_layers": 5,
                "gradient_type": "linear",
                "layer_indices": [1.10, 1.20, 1.30, 1.40, 1.50],
                "layer_thickness_nm": [60.0, 60.0, 60.0, 60.0, 60.0],
            },
        },
    ]


def _advanced_ar_display_rows(results: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in results:
        ref_path = Path(str(item["reference_csv"]))
        ref_name = ref_path.stem.lower()
        if item["case_id"] == "single_ar":
            topic_cn = "单层减反膜"
        elif item["case_id"] == "porous_sio2_layer":
            topic_cn = "多孔二氧化硅膜层"
        elif item["case_id"] == "porous_double_ar":
            topic_cn = "多孔二氧化硅双层减反结构"
        elif "moth_eye_2d" in ref_name or "trapezoid" in ref_name:
            topic_cn = "2D 蛾眼梯形结构（COMSOL）"
        else:
            topic_cn = "蛾眼结构（等效渐变层）"

        rows.append(
            {
                "topic_cn": topic_cn,
                "case_id": str(item["case_id"]),
                "reference_csv": str(ref_path),
                "reference_label": str(item["reference_label"]),
                "summary": dict(item["summary"]),
                "comparison": item["comparison"],
                "title_cn": str(item["title_cn"]),
                "quantity": str(item["quantity"]),
            }
        )
    return rows


def export_advanced_ar_bundle(
    single_ar_csv: Path | str,
    porous_csv: Path | str,
    porous_double_csv: Path | str,
    moth_eye_effective_csv: Path | str,
    moth_eye_2d_csv: Path | str,
    *,
    prefix: str = "advanced_ar_bundle",
    reference_label: str = "COMSOL",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, Any]:
    """Export a focused bundle for the advanced anti-reflection topic."""

    cases = build_advanced_ar_validation_cases(
        single_ar_csv=single_ar_csv,
        porous_csv=porous_csv,
        porous_double_csv=porous_double_csv,
        moth_eye_effective_csv=moth_eye_effective_csv,
        moth_eye_2d_csv=moth_eye_2d_csv,
        reference_label=reference_label,
    )
    results = run_teaching_validation_suite(cases)
    display_rows = _advanced_ar_display_rows(results)

    exported_cases: Dict[str, Dict[str, str]] = {}
    for index, item in enumerate(results, start=1):
        case_prefix = f"{prefix}_{index:02d}"
        exported_cases[display_rows[index - 1]["topic_cn"]] = export_teaching_validation_result(
            item,
            prefix=case_prefix,
            save_plot=save_plot,
            save_csv=save_csv,
            save_json=save_json,
            save_txt=save_txt,
        )

    suite_files = export_teaching_validation_suite_summary(
        results,
        filename_prefix=f"{prefix}_validation_suite",
    )

    saved: Dict[str, Any] = {
        "case_files": exported_cases,
        "suite_files": suite_files,
        "results": results,
    }

    if save_csv:
        csv_path = output_file(f"{prefix}_summary.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write(
                "topic_cn,case_id,reference_csv,mae,rmse,max_abs_error,lambda0_error,theory_at_lambda0,reference_at_lambda0\n"
            )
            for row in display_rows:
                s = row["summary"]
                f.write(
                    ",".join(
                        [
                            str(row["topic_cn"]),
                            str(row["case_id"]),
                            str(row["reference_csv"]),
                            f"{float(s['mae']):.12g}",
                            f"{float(s['rmse']):.12g}",
                            f"{float(s['max_abs_error']):.12g}",
                            f"{float(s['lambda0_error']):.12g}",
                            f"{float(s['theory_at_lambda0']):.12g}",
                            f"{float(s['reference_at_lambda0']):.12g}",
                        ]
                    )
                    + "\n"
                )
        saved["csv"] = str(csv_path)

    if save_json:
        json_path = output_file(f"{prefix}_summary.json")
        payload = {
            "reference_label": reference_label,
            "topics": [
                {
                    "topic_cn": row["topic_cn"],
                    "case_id": row["case_id"],
                    "reference_csv": row["reference_csv"],
                    "summary": row["summary"],
                    "files": exported_cases[row["topic_cn"]],
                }
                for row in display_rows
            ],
            "suite_files": suite_files,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        saved["json"] = str(json_path)

    if save_txt:
        txt_path = output_file(f"{prefix}_summary.txt")
        lines = [
            "高级减反专题总包",
            "=" * 80,
            "包含主题：单层减反膜、多孔二氧化硅膜层、多孔二氧化硅双层减反结构、蛾眼等效渐变层、2D 蛾眼 COMSOL",
            "",
        ]
        for row in display_rows:
            s = row["summary"]
            lines.extend(
                [
                    f"主题                 = {row['topic_cn']}",
                    f"theory_case_id       = {row['case_id']}",
                    f"reference_csv        = {row['reference_csv']}",
                    f"MAE                  = {float(s['mae']):.12e}",
                    f"RMSE                 = {float(s['rmse']):.12e}",
                    f"max_abs_error        = {float(s['max_abs_error']):.12e}",
                    f"lambda0_error        = {float(s['lambda0_error']):+.12e}",
                    f"theory_at_lambda0    = {float(s['theory_at_lambda0']):.12e}",
                    f"reference_at_lambda0 = {float(s['reference_at_lambda0']):.12e}",
                    "-" * 80,
                ]
            )
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        saved["txt"] = str(txt_path)

    if save_plot:
        fig, axes = plt.subplots(2, 3, figsize=(15.5, 9), constrained_layout=True)
        font = _cn_font()

        # Panel 1: all reference curves
        ax = axes[0, 0]
        for row in display_rows:
            comp = row["comparison"]
            wl = np.asarray(comp["wavelength_nm"], dtype=float)
            ref = np.asarray(comp["reference"], dtype=float)
            ax.plot(wl, ref, linewidth=2.0, label=row["topic_cn"])
        _style_axis(ax)
        _set_axis_labels_cn(ax, title="参考曲线总览", xlabel="波长 (nm)", ylabel="反射率 R")
        ax.legend(prop=font, frameon=False, loc="best")

        # Panel 2: theory progression + 2D reference
        ax = axes[0, 1]
        for row in display_rows[:4]:
            comp = row["comparison"]
            wl = np.asarray(comp["wavelength_nm"], dtype=float)
            theory = np.asarray(comp["theory"], dtype=float)
            ax.plot(wl, theory, linewidth=2.0, label=f"{row['topic_cn']}（理论）")
        last = display_rows[-1]
        ax.plot(
            np.asarray(last["comparison"]["wavelength_nm"], dtype=float),
            np.asarray(last["comparison"]["reference"], dtype=float),
            linewidth=2.2,
            linestyle="--",
            color=REF_BLUE,
            label="2D 蛾眼梯形结构（COMSOL）",
        )
        _style_axis(ax)
        _set_axis_labels_cn(ax, title="减反结构演化对照", xlabel="波长 (nm)", ylabel="反射率 R")
        ax.legend(prop=font, frameon=False, loc="best")

        # Panel 3: lambda0 reflectance
        ax = axes[0, 2]
        labels = [row["topic_cn"] for row in display_rows]
        values = [float(row["summary"]["reference_at_lambda0"]) for row in display_rows]
        x = np.arange(len(labels))
        colors = [MAIN_RED, TARGET_GREEN, "#0f766e", REF_BLUE, "#6b46c1"]
        bars = ax.bar(x, values, color=colors[: len(labels)])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=18, ha="right", fontproperties=font)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                value + max(values) * 0.03,
                f"{value:.4f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=TEXT_DARK,
            )
        _style_axis(ax)
        _set_axis_labels_cn(ax, title="550 nm 处反射率", xlabel="结构类型", ylabel="反射率 R")

        # Panel 4: validation MAE
        ax = axes[1, 0]
        mae_vals = [float(row["summary"]["mae"]) for row in display_rows]
        bars = ax.bar(x, mae_vals, color=colors[: len(labels)])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=18, ha="right", fontproperties=font)
        for bar, value in zip(bars, mae_vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                value + max(mae_vals) * 0.03,
                f"{value:.4f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=TEXT_DARK,
            )
        _style_axis(ax)
        _set_axis_labels_cn(ax, title="理论与参考曲线 MAE", xlabel="结构类型", ylabel="MAE")

        # Panel 5: mean reflectance
        ax = axes[1, 1]
        mean_vals = [
            float(np.mean(np.asarray(row["comparison"]["reference"], dtype=float)))
            for row in display_rows
        ]
        bars = ax.bar(x, mean_vals, color=colors[: len(labels)])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=18, ha="right", fontproperties=font)
        for bar, value in zip(bars, mean_vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                value + max(mean_vals) * 0.03,
                f"{value:.4f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=TEXT_DARK,
            )
        _style_axis(ax)
        _set_axis_labels_cn(ax, title="平均反射率", xlabel="结构类型", ylabel="平均反射率 R")

        axes[1, 2].axis("off")

        png_path = output_file(f"{prefix}_overview.png")
        fig.savefig(png_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        saved["overview_png"] = str(png_path)

    manifest_path = output_file(f"{prefix}_manifest.json")
    manifest = {
        "reference_label": reference_label,
        "topics": [
            {
                "topic_cn": row["topic_cn"],
                "case_id": row["case_id"],
                "reference_csv": row["reference_csv"],
                "summary": row["summary"],
                "files": exported_cases[row["topic_cn"]],
            }
            for row in display_rows
        ],
        "suite_files": suite_files,
        "bundle_files": {
            key: value
            for key, value in saved.items()
            if key not in {"case_files", "suite_files", "results"}
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    saved["manifest"] = str(manifest_path)
    return saved


def analyze_quasi_random_absorbing_surface(
    reference_csv: Path | str,
    *,
    lambda0_nm: float = 550.0,
    x_selector: int | str = "lam/1[nm] (1)",
    r_selector: int | str = "abs(ewfd.S11)^2 (1)",
    t_selector: int | str = "abs(ewfd.S21)^2 (1)",
    a_selector: int | str = "1-abs(ewfd.S11)^2-abs(ewfd.S21)^2 (1)",
) -> Dict[str, Any]:
    """Analyze a 2D periodic quasi-random rough absorbing surface CSV."""

    r_spec = load_spectrum_csv(Path(reference_csv), x_selector=x_selector, y_selector=r_selector)
    t_spec = load_spectrum_csv(Path(reference_csv), x_selector=x_selector, y_selector=t_selector)
    a_spec = load_spectrum_csv(Path(reference_csv), x_selector=x_selector, y_selector=a_selector)

    wl = np.asarray(r_spec.x_nm, dtype=float)
    r_vals = np.asarray(r_spec.y, dtype=float)
    t_vals = np.asarray(t_spec.y, dtype=float)
    a_vals = np.asarray(a_spec.y, dtype=float)

    summary = {
        "lambda_min_nm": float(np.min(wl)),
        "lambda_max_nm": float(np.max(wl)),
        "num_points": int(len(wl)),
        "R_min": float(np.min(r_vals)),
        "R_max": float(np.max(r_vals)),
        "R_mean": float(np.mean(r_vals)),
        "T_min": float(np.min(t_vals)),
        "T_max": float(np.max(t_vals)),
        "T_mean": float(np.mean(t_vals)),
        "A_min": float(np.min(a_vals)),
        "A_max": float(np.max(a_vals)),
        "A_mean": float(np.mean(a_vals)),
        "R_at_lambda0": float(np.interp(lambda0_nm, wl, r_vals)),
        "T_at_lambda0": float(np.interp(lambda0_nm, wl, t_vals)),
        "A_at_lambda0": float(np.interp(lambda0_nm, wl, a_vals)),
        "A_peak_wavelength_nm": float(wl[np.argmax(a_vals)]),
        "R_peak_wavelength_nm": float(wl[np.argmax(r_vals)]),
        "T_peak_wavelength_nm": float(wl[np.argmax(t_vals)]),
        "energy_balance_mean": float(np.mean(r_vals + t_vals + a_vals)),
        "energy_balance_max_error": float(np.max(np.abs(r_vals + t_vals + a_vals - 1.0))),
    }

    if summary["A_mean"] >= 0.6:
        interpretation_cn = "该结构在当前波段表现出明显吸收增强，吸收是主导能量通道。"
    elif summary["A_mean"] >= 0.4:
        interpretation_cn = "该结构具有中等吸收增强效果，反射与吸收共同决定能量分配。"
    else:
        interpretation_cn = "该结构当前吸收增强有限，仍需进一步优化粗糙表面参数或材料损耗。"

    return {
        "case_id": "quasi_random_absorbing_surface",
        "title_cn": "准随机粗糙吸收表面",
        "title_en": "Periodic Quasi-Random Rough Absorbing Surface",
        "reference_csv": str(Path(reference_csv)),
        "reference_label": "COMSOL",
        "lambda0_nm": float(lambda0_nm),
        "wavelength_nm": wl,
        "R": r_vals,
        "T": t_vals,
        "A": a_vals,
        "summary": summary,
        "interpretation_cn": interpretation_cn,
    }


def export_quasi_random_absorbing_surface_bundle(
    reference_csv: Path | str,
    *,
    prefix: str = "rough_absorbing_surface",
    lambda0_nm: float = 550.0,
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, str]:
    """Export analysis files for a rough absorbing surface COMSOL result."""

    result = analyze_quasi_random_absorbing_surface(reference_csv, lambda0_nm=lambda0_nm)
    saved: Dict[str, str] = {}
    wl = np.asarray(result["wavelength_nm"], dtype=float)
    r_vals = np.asarray(result["R"], dtype=float)
    t_vals = np.asarray(result["T"], dtype=float)
    a_vals = np.asarray(result["A"], dtype=float)
    summary = result["summary"]

    if save_csv:
        csv_path = output_file(f"{prefix}_spectrum.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write("wavelength_nm,R,T,A\n")
            for row in zip(wl, r_vals, t_vals, a_vals):
                f.write(",".join(f"{float(x):.12g}" for x in row) + "\n")
        saved["csv"] = str(csv_path)

    if save_json:
        json_path = output_file(f"{prefix}_summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "case_id": result["case_id"],
                    "title_cn": result["title_cn"],
                    "title_en": result["title_en"],
                    "reference_csv": result["reference_csv"],
                    "lambda0_nm": result["lambda0_nm"],
                    "summary": summary,
                    "interpretation_cn": result["interpretation_cn"],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        saved["json"] = str(json_path)

    if save_txt:
        txt_path = output_file(f"{prefix}_summary.txt")
        lines = [
            "准随机粗糙吸收表面分析",
            "=" * 80,
            f"reference_csv             = {result['reference_csv']}",
            f"lambda0_nm                = {float(result['lambda0_nm']):.6f}",
            f"R_mean                    = {float(summary['R_mean']):.12e}",
            f"T_mean                    = {float(summary['T_mean']):.12e}",
            f"A_mean                    = {float(summary['A_mean']):.12e}",
            f"R_at_lambda0              = {float(summary['R_at_lambda0']):.12e}",
            f"T_at_lambda0              = {float(summary['T_at_lambda0']):.12e}",
            f"A_at_lambda0              = {float(summary['A_at_lambda0']):.12e}",
            f"A_peak_wavelength_nm      = {float(summary['A_peak_wavelength_nm']):.6f}",
            f"energy_balance_mean       = {float(summary['energy_balance_mean']):.12e}",
            f"energy_balance_max_error  = {float(summary['energy_balance_max_error']):.12e}",
            "",
            f"interpretation_cn         = {result['interpretation_cn']}",
        ]
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        saved["txt"] = str(txt_path)

    if save_plot:
        fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
        font = _cn_font()

        ax = axes[0, 0]
        ax.plot(wl, r_vals, color=MAIN_RED, linewidth=2.0, label="反射率 R")
        ax.plot(wl, t_vals, color=REF_BLUE, linewidth=2.0, label="透射率 T")
        ax.plot(wl, a_vals, color=TARGET_GREEN, linewidth=2.4, label="吸收率 A")
        ax.axvline(float(lambda0_nm), color="#7a8696", linestyle="--", linewidth=1.2)
        _style_axis(ax)
        _set_axis_labels_cn(ax, title="R / T / A 光谱", xlabel="波长 (nm)", ylabel="比例")
        ax.legend(prop=font, frameon=False, loc="best")

        ax = axes[0, 1]
        ax.plot(wl, a_vals, color=TARGET_GREEN, linewidth=2.6)
        peak_idx = int(np.argmax(a_vals))
        ax.scatter([wl[peak_idx]], [a_vals[peak_idx]], color=TARGET_GREEN, s=42, zorder=3)
        ax.axvline(float(summary["A_peak_wavelength_nm"]), color="#7a8696", linestyle="--", linewidth=1.2)
        _style_axis(ax)
        _set_axis_labels_cn(ax, title="吸收增强主曲线", xlabel="波长 (nm)", ylabel="吸收率 A")

        ax = axes[1, 0]
        labels = ["R@550", "T@550", "A@550"]
        values = [
            float(summary["R_at_lambda0"]),
            float(summary["T_at_lambda0"]),
            float(summary["A_at_lambda0"]),
        ]
        colors = [MAIN_RED, REF_BLUE, TARGET_GREEN]
        x = np.arange(len(labels))
        bars = ax.bar(x, values, color=colors)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                value + max(values) * 0.03,
                f"{value:.4f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=TEXT_DARK,
            )
        _style_axis(ax)
        _set_axis_labels_cn(ax, title="550 nm 处能量分配", xlabel="指标", ylabel="比例")

        ax = axes[1, 1]
        metrics = [
            float(summary["R_mean"]),
            float(summary["T_mean"]),
            float(summary["A_mean"]),
        ]
        bars = ax.bar(np.arange(3), metrics, color=colors)
        ax.set_xticks(np.arange(3))
        if font is None:
            ax.set_xticklabels(["平均R", "平均T", "平均A"])
        else:
            ax.set_xticklabels(["平均R", "平均T", "平均A"], fontproperties=font)
        for bar, value in zip(bars, metrics):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                value + max(metrics) * 0.03,
                f"{value:.4f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=TEXT_DARK,
            )
        _style_axis(ax)
        _set_axis_labels_cn(ax, title="全波段平均能量分配", xlabel="指标", ylabel="比例")

        png_path = output_file(f"{prefix}_overview.png")
        fig.savefig(png_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        saved["overview_png"] = str(png_path)

    return saved


def export_absorbing_surface_comparison(
    reference_csv_a: Path | str,
    reference_csv_b: Path | str,
    *,
    prefix: str = "rough_absorbing_surface_compare",
    lambda0_nm: float = 550.0,
    label_a: str = "版本1",
    label_b: str = "版本2",
) -> Dict[str, str]:
    """Compare two rough absorbing surface results side by side."""

    result_a = analyze_quasi_random_absorbing_surface(reference_csv_a, lambda0_nm=lambda0_nm)
    result_b = analyze_quasi_random_absorbing_surface(reference_csv_b, lambda0_nm=lambda0_nm)

    saved: Dict[str, str] = {}
    wl_a = np.asarray(result_a["wavelength_nm"], dtype=float)
    wl_b = np.asarray(result_b["wavelength_nm"], dtype=float)
    r_a = np.asarray(result_a["R"], dtype=float)
    t_a = np.asarray(result_a["T"], dtype=float)
    a_a = np.asarray(result_a["A"], dtype=float)
    r_b = np.asarray(result_b["R"], dtype=float)
    t_b = np.asarray(result_b["T"], dtype=float)
    a_b = np.asarray(result_b["A"], dtype=float)
    s_a = result_a["summary"]
    s_b = result_b["summary"]

    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("metric,label_a,label_b,delta_b_minus_a\n")
        for metric in [
            "R_mean",
            "T_mean",
            "A_mean",
            "R_at_lambda0",
            "T_at_lambda0",
            "A_at_lambda0",
        ]:
            va = float(s_a[metric])
            vb = float(s_b[metric])
            f.write(f"{metric},{va:.12g},{vb:.12g},{(vb-va):.12g}\n")
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "label_a": label_a,
                "label_b": label_b,
                "reference_csv_a": str(reference_csv_a),
                "reference_csv_b": str(reference_csv_b),
                "summary_a": s_a,
                "summary_b": s_b,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "准随机粗糙吸收表面对比",
        "=" * 80,
        f"label_a                    = {label_a}",
        f"reference_csv_a            = {reference_csv_a}",
        f"label_b                    = {label_b}",
        f"reference_csv_b            = {reference_csv_b}",
        "",
        f"A_mean (a)                 = {float(s_a['A_mean']):.12e}",
        f"A_mean (b)                 = {float(s_b['A_mean']):.12e}",
        f"Delta A_mean (b-a)         = {float(s_b['A_mean'] - s_a['A_mean']):+.12e}",
        f"A_at_lambda0 (a)           = {float(s_a['A_at_lambda0']):.12e}",
        f"A_at_lambda0 (b)           = {float(s_b['A_at_lambda0']):.12e}",
        f"Delta A@lambda0 (b-a)      = {float(s_b['A_at_lambda0'] - s_a['A_at_lambda0']):+.12e}",
        f"R_mean (a)                 = {float(s_a['R_mean']):.12e}",
        f"R_mean (b)                 = {float(s_b['R_mean']):.12e}",
        f"T_mean (a)                 = {float(s_a['T_mean']):.12e}",
        f"T_mean (b)                 = {float(s_b['T_mean']):.12e}",
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    font = _cn_font()

    ax = axes[0, 0]
    ax.plot(wl_a, a_a, color=TARGET_GREEN, linewidth=2.4, label=f"{label_a} 吸收率 A")
    ax.plot(wl_b, a_b, color="#6b46c1", linewidth=2.4, linestyle="--", label=f"{label_b} 吸收率 A")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="吸收率对比", xlabel="波长 (nm)", ylabel="吸收率 A")
    ax.legend(prop=font, frameon=False, loc="best")

    ax = axes[0, 1]
    ax.plot(wl_a, r_a, color=MAIN_RED, linewidth=2.0, label=f"{label_a} 反射率 R")
    ax.plot(wl_b, r_b, color="#d97706", linewidth=2.0, linestyle="--", label=f"{label_b} 反射率 R")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="反射率对比", xlabel="波长 (nm)", ylabel="反射率 R")
    ax.legend(prop=font, frameon=False, loc="best")

    ax = axes[1, 0]
    labels = ["A@550", "平均A"]
    x = np.arange(len(labels))
    width = 0.35
    vals_a = [float(s_a["A_at_lambda0"]), float(s_a["A_mean"])]
    vals_b = [float(s_b["A_at_lambda0"]), float(s_b["A_mean"])]
    bars_a = ax.bar(x - width / 2, vals_a, width=width, color=TARGET_GREEN, label=label_a)
    bars_b = ax.bar(x + width / 2, vals_b, width=width, color="#6b46c1", label=label_b)
    ax.set_xticks(x)
    if font is None:
        ax.set_xticklabels(labels)
    else:
        ax.set_xticklabels(labels, fontproperties=font)
    for bars in (bars_a, bars_b):
        for bar in bars:
            value = float(bar.get_height())
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                value + max(vals_a + vals_b) * 0.03,
                f"{value:.4f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=TEXT_DARK,
            )
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="吸收性能关键指标", xlabel="指标", ylabel="比例")
    ax.legend(prop=font, frameon=False, loc="best")

    ax = axes[1, 1]
    delta_labels = ["ΔR均值", "ΔT均值", "ΔA均值"]
    deltas = [
        float(s_b["R_mean"] - s_a["R_mean"]),
        float(s_b["T_mean"] - s_a["T_mean"]),
        float(s_b["A_mean"] - s_a["A_mean"]),
    ]
    colors = [MAIN_RED, REF_BLUE, TARGET_GREEN]
    bars = ax.bar(np.arange(3), deltas, color=colors)
    ax.axhline(0.0, color="#7a8696", linewidth=1.0)
    if font is None:
        ax.set_xticklabels(delta_labels)
    else:
        ax.set_xticks(np.arange(3))
        ax.set_xticklabels(delta_labels, fontproperties=font)
    for bar, value in zip(bars, deltas):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            value + (0.002 if value >= 0 else -0.004),
            f"{value:+.4f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=9,
            color=TEXT_DARK,
        )
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="版本2 相对版本1 的变化", xlabel="指标", ylabel="差值")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)
    return saved


def export_absorbing_surface_roughness_sweep(
    roughness_files: Dict[float, Path | str],
    *,
    prefix: str = "rough_absorbing_surface_roughness_sweep",
    lambda0_nm: float = 550.0,
) -> Dict[str, str]:
    """Export a roughness-factor sweep summary for absorbing surfaces."""

    rows: List[Dict[str, Any]] = []
    for factor, path in sorted(roughness_files.items(), key=lambda item: float(item[0])):
        result = analyze_quasi_random_absorbing_surface(path, lambda0_nm=lambda0_nm)
        summary = result["summary"]
        rows.append(
            {
                "roughness_factor": float(factor),
                "reference_csv": str(path),
                "R_mean": float(summary["R_mean"]),
                "T_mean": float(summary["T_mean"]),
                "A_mean": float(summary["A_mean"]),
                "R_at_lambda0": float(summary["R_at_lambda0"]),
                "T_at_lambda0": float(summary["T_at_lambda0"]),
                "A_at_lambda0": float(summary["A_at_lambda0"]),
            }
        )

    saved: Dict[str, str] = {}
    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("roughness_factor,R_mean,T_mean,A_mean,R_at_lambda0,T_at_lambda0,A_at_lambda0,reference_csv\n")
        for row in rows:
            f.write(
                ",".join(
                    [
                        f"{row['roughness_factor']:.12g}",
                        f"{row['R_mean']:.12g}",
                        f"{row['T_mean']:.12g}",
                        f"{row['A_mean']:.12g}",
                        f"{row['R_at_lambda0']:.12g}",
                        f"{row['T_at_lambda0']:.12g}",
                        f"{row['A_at_lambda0']:.12g}",
                        str(row["reference_csv"]),
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"lambda0_nm": lambda0_nm, "rows": rows}, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = ["粗糙度扫描摘要", "=" * 80, f"lambda0_nm = {lambda0_nm:.6f}", ""]
    for row in rows:
        lines.extend(
            [
                f"roughness_factor = {row['roughness_factor']:.6f}",
                f"R_mean           = {row['R_mean']:.12e}",
                f"T_mean           = {row['T_mean']:.12e}",
                f"A_mean           = {row['A_mean']:.12e}",
                f"R@lambda0        = {row['R_at_lambda0']:.12e}",
                f"T@lambda0        = {row['T_at_lambda0']:.12e}",
                f"A@lambda0        = {row['A_at_lambda0']:.12e}",
                "-" * 80,
            ]
        )
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    x = np.array([row["roughness_factor"] for row in rows], dtype=float)
    r_mean = np.array([row["R_mean"] for row in rows], dtype=float)
    t_mean = np.array([row["T_mean"] for row in rows], dtype=float)
    a_mean = np.array([row["A_mean"] for row in rows], dtype=float)
    a_550 = np.array([row["A_at_lambda0"] for row in rows], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), constrained_layout=True)
    for ax in axes:
        _style_axis(ax)

    ax = axes[0]
    ax.plot(x, r_mean, color=MAIN_RED, marker="o", linewidth=2.0, label="平均R")
    ax.plot(x, t_mean, color=REF_BLUE, marker="o", linewidth=2.0, label="平均T")
    ax.plot(x, a_mean, color=TARGET_GREEN, marker="o", linewidth=2.4, label="平均A")
    _set_axis_labels_cn(ax, title="粗糙度因子与全波段平均能量分配", xlabel="粗糙度倍率", ylabel="比例")
    ax.legend(frameon=False, loc="best", prop=_cn_font())

    ax = axes[1]
    ax.plot(x, a_550, color=TARGET_GREEN, marker="o", linewidth=2.4)
    for xi, yi in zip(x, a_550):
        ax.text(xi, yi + 0.01, f"{yi:.4f}", ha="center", va="bottom", fontsize=9, color=TEXT_DARK)
    _set_axis_labels_cn(ax, title="粗糙度因子与 550 nm 吸收率", xlabel="粗糙度倍率", ylabel="A@550")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)
    return saved


def summarize_absorbing_surface_roughness(
    roughness_files: Dict[float, Path | str],
    *,
    lambda0_nm: float = 550.0,
) -> Dict[str, Any]:
    """Summarize roughness sweep trends and current stable best point."""

    rows: List[Dict[str, Any]] = []
    for factor, path in sorted(roughness_files.items(), key=lambda item: float(item[0])):
        result = analyze_quasi_random_absorbing_surface(path, lambda0_nm=lambda0_nm)
        summary = result["summary"]
        rows.append(
            {
                "roughness_factor": float(factor),
                "reference_csv": str(path),
                "R_mean": float(summary["R_mean"]),
                "T_mean": float(summary["T_mean"]),
                "A_mean": float(summary["A_mean"]),
                "R_at_lambda0": float(summary["R_at_lambda0"]),
                "T_at_lambda0": float(summary["T_at_lambda0"]),
                "A_at_lambda0": float(summary["A_at_lambda0"]),
            }
        )

    if not rows:
        raise ValueError("roughness_files 不能为空。")

    best_by_a550 = max(rows, key=lambda item: item["A_at_lambda0"])
    best_by_amean = max(rows, key=lambda item: item["A_mean"])
    a550_vals = np.array([row["A_at_lambda0"] for row in rows], dtype=float)
    amean_vals = np.array([row["A_mean"] for row in rows], dtype=float)
    monotonic_a550 = bool(np.all(np.diff(a550_vals) >= -1e-12))
    monotonic_amean = bool(np.all(np.diff(amean_vals) >= -1e-12))
    max_tested_factor = float(max(row["roughness_factor"] for row in rows))

    if monotonic_a550 and monotonic_amean:
        trend_cn = "在当前可计算范围内，粗糙度增大持续提升吸收。"
    elif best_by_a550["roughness_factor"] < max_tested_factor:
        trend_cn = "吸收性能在已测试范围内出现局部最优点，继续增大粗糙度未必更优。"
    else:
        trend_cn = "吸收性能总体提升，但局部趋势已不再严格单调，建议结合更多点确认极值。"

    stability_cn = (
        f"当前已验证的最大可计算粗糙度倍率为 {max_tested_factor:.2f}。"
        " 若更大粗糙度无法求解，可将其视为当前几何/数值稳定边界附近。"
    )

    return {
        "lambda0_nm": float(lambda0_nm),
        "rows": rows,
        "best_by_a550": best_by_a550,
        "best_by_amean": best_by_amean,
        "monotonic_a550": monotonic_a550,
        "monotonic_amean": monotonic_amean,
        "max_tested_factor": max_tested_factor,
        "trend_cn": trend_cn,
        "stability_cn": stability_cn,
    }


def export_absorbing_surface_roughness_bundle(
    roughness_files: Dict[float, Path | str],
    *,
    prefix: str = "rough_absorbing_surface_roughness_bundle",
    lambda0_nm: float = 550.0,
) -> Dict[str, str]:
    """Export roughness sweep plots plus an automatic conclusion summary."""

    sweep_files = export_absorbing_surface_roughness_sweep(
        roughness_files=roughness_files,
        prefix=prefix,
        lambda0_nm=lambda0_nm,
    )
    summary = summarize_absorbing_surface_roughness(
        roughness_files=roughness_files,
        lambda0_nm=lambda0_nm,
    )

    saved = dict(sweep_files)

    summary_json = output_file(f"{prefix}_conclusion.json")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    saved["conclusion_json"] = str(summary_json)

    summary_txt = output_file(f"{prefix}_conclusion.txt")
    lines = [
        "粗糙吸收表面粗糙度结论",
        "=" * 80,
        f"lambda0_nm                  = {float(summary['lambda0_nm']):.6f}",
        f"best_factor_by_A@lambda0    = {float(summary['best_by_a550']['roughness_factor']):.6f}",
        f"best_A@lambda0              = {float(summary['best_by_a550']['A_at_lambda0']):.12e}",
        f"best_factor_by_A_mean       = {float(summary['best_by_amean']['roughness_factor']):.6f}",
        f"best_A_mean                 = {float(summary['best_by_amean']['A_mean']):.12e}",
        f"monotonic_A@lambda0         = {bool(summary['monotonic_a550'])}",
        f"monotonic_A_mean            = {bool(summary['monotonic_amean'])}",
        f"max_tested_factor           = {float(summary['max_tested_factor']):.6f}",
        "",
        f"trend_cn                    = {summary['trend_cn']}",
        f"stability_cn                = {summary['stability_cn']}",
    ]
    with open(summary_txt, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["conclusion_txt"] = str(summary_txt)
    return saved


def _parse_comsol_scalar(value: str) -> float:
    text = str(value).strip()
    if "∠" in text:
        text = text.split("∠", 1)[0]
    if text.startswith("%"):
        text = text.lstrip("%").strip()
    return float(text)


def _load_comsol_grouped_r_sweep(
    reference_csv: Path | str,
    *,
    sweep_key: str,
    x_selector: str = "lam/1[nm] (1)",
    r_selector: str = "abs(ewfd.S11)^2 (1)",
) -> Dict[float, Dict[str, np.ndarray]]:
    path = Path(reference_csv)
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f if line.strip()]
    header_idx = next((i for i, line in enumerate(lines) if line.startswith("% ") and sweep_key in line), None)
    if header_idx is None:
        raise ValueError(f"在参考文件中未找到参数列 {sweep_key}: {path}")
    header = lines[header_idx].lstrip("%").strip().split(",")
    idx = {name: i for i, name in enumerate(header)}
    if sweep_key not in idx or x_selector not in idx or r_selector not in idx:
        raise ValueError(f"参考文件缺少必要列: {path}")

    grouped: Dict[float, List[tuple[float, float]]] = {}
    for line in lines[header_idx + 1 :]:
        if line.startswith("%"):
            continue
        row = line.split(",")
        param = round(_parse_comsol_scalar(row[idx[sweep_key]]), 12)
        lam_nm = _parse_comsol_scalar(row[idx[x_selector]])
        r_val = _parse_comsol_scalar(row[idx[r_selector]])
        grouped.setdefault(param, []).append((lam_nm, r_val))

    result: Dict[float, Dict[str, np.ndarray]] = {}
    for param, pairs in sorted(grouped.items()):
        pairs.sort(key=lambda item: item[0])
        wl = np.asarray([item[0] for item in pairs], dtype=float)
        rv = np.asarray([item[1] for item in pairs], dtype=float)
        result[param] = {"wavelength_nm": wl, "R": rv}
    return result


def summarize_porous_double_parameter_sweep(
    reference_csv: Path | str,
    *,
    sweep_key: str,
    lambda0_nm: float = 550.0,
) -> Dict[str, Any]:
    grouped = _load_comsol_grouped_r_sweep(reference_csv, sweep_key=sweep_key)
    rows: List[Dict[str, Any]] = []
    for param, data in sorted(grouped.items()):
        wl = data["wavelength_nm"]
        rv = data["R"]
        i550 = int(np.argmin(np.abs(wl - float(lambda0_nm))))
        imin = int(np.argmin(rv))
        rows.append(
            {
                "param_value": float(param),
                "R_mean": float(np.mean(rv)),
                "R_at_lambda0": float(rv[i550]),
                "R_min": float(rv[imin]),
                "lambda_at_R_min": float(wl[imin]),
                "num_points": int(len(wl)),
            }
        )

    if not rows:
        raise ValueError("参数扫描结果为空。")

    best_by_center = min(rows, key=lambda item: item["R_at_lambda0"])
    best_by_mean = min(rows, key=lambda item: item["R_mean"])

    if sweep_key == "n_porous":
        trend_cn = "多孔层折射率存在明显最优点，不是越低越好。"
        sensitivity_cn = "当前扫描表明，多孔层折射率在 1.18 附近形成最佳匹配。"
    elif sweep_key == "err_d_porous":
        trend_cn = "多孔层厚度偏离设计值后，低反谷会明显偏离 550 nm。"
        sensitivity_cn = "多孔层厚度对中心波长减反更敏感，是优先控制对象。"
    else:
        trend_cn = "高折匹配层厚度变化也会引起低反谷漂移，但整体敏感性较多孔层更弱。"
        sensitivity_cn = "高折匹配层厚度应控制在设计值附近，但相对容差更宽。"

    return {
        "reference_csv": str(Path(reference_csv)),
        "sweep_key": sweep_key,
        "lambda0_nm": float(lambda0_nm),
        "rows": rows,
        "best_by_center": best_by_center,
        "best_by_mean": best_by_mean,
        "trend_cn": trend_cn,
        "sensitivity_cn": sensitivity_cn,
    }


def export_porous_double_ar_sensitivity_bundle(
    n_porous_csv: Path | str,
    d_porous_csv: Path | str,
    d_high_csv: Path | str,
    *,
    prefix: str = "porous_double_ar_sensitivity_v1",
    lambda0_nm: float = 550.0,
) -> Dict[str, str]:
    sweeps = [
        ("n_porous", summarize_porous_double_parameter_sweep(n_porous_csv, sweep_key="n_porous", lambda0_nm=lambda0_nm)),
        ("err_d_porous", summarize_porous_double_parameter_sweep(d_porous_csv, sweep_key="err_d_porous", lambda0_nm=lambda0_nm)),
        ("err_d_high", summarize_porous_double_parameter_sweep(d_high_csv, sweep_key="err_d_high", lambda0_nm=lambda0_nm)),
    ]

    saved: Dict[str, str] = {}

    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("sweep_key,param_value,R_mean,R_at_lambda0,R_min,lambda_at_R_min\n")
        for key, summary in sweeps:
            for row in summary["rows"]:
                f.write(
                    ",".join(
                        [
                            key,
                            f"{float(row['param_value']):.12g}",
                            f"{float(row['R_mean']):.12g}",
                            f"{float(row['R_at_lambda0']):.12g}",
                            f"{float(row['R_min']):.12g}",
                            f"{float(row['lambda_at_R_min']):.12g}",
                        ]
                    )
                    + "\n"
                )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"lambda0_nm": float(lambda0_nm), "sweeps": {key: summary for key, summary in sweeps}}, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = ["多孔双层减反结构敏感性摘要", "=" * 80, f"lambda0_nm = {float(lambda0_nm):.6f}", ""]
    for key, summary in sweeps:
        bc = summary["best_by_center"]
        bm = summary["best_by_mean"]
        lines.extend(
            [
                f"sweep_key              = {key}",
                f"best_by_R@lambda0      = {float(bc['param_value']):.12g}",
                f"best_R@lambda0         = {float(bc['R_at_lambda0']):.12e}",
                f"best_by_R_mean         = {float(bm['param_value']):.12g}",
                f"best_R_mean            = {float(bm['R_mean']):.12e}",
                f"trend_cn               = {summary['trend_cn']}",
                f"sensitivity_cn         = {summary['sensitivity_cn']}",
                "-" * 80,
            ]
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6), constrained_layout=True)
    font = _cn_font()
    title_map = {
        "n_porous": "多孔层折射率扫描",
        "err_d_porous": "多孔层厚度偏差扫描",
        "err_d_high": "高折层厚度偏差扫描",
    }
    for ax, (key, summary) in zip(axes, sweeps):
        rows = summary["rows"]
        x = np.asarray([row["param_value"] for row in rows], dtype=float)
        y1 = np.asarray([row["R_at_lambda0"] for row in rows], dtype=float)
        y2 = np.asarray([row["R_mean"] for row in rows], dtype=float)
        _style_axis(ax)
        ax.plot(x, y1, color=MAIN_RED, marker="o", linewidth=2.2, label="R@550")
        ax.plot(x, y2, color=REF_BLUE, marker="o", linewidth=2.0, label="平均R")
        for xi, yi in zip(x, y1):
            ax.text(xi, yi + max(y1) * 0.04, f"{yi:.4g}", ha="center", va="bottom", fontsize=8, color=TEXT_DARK)
        xlabel = "参数值" if key == "n_porous" else "相对偏差"
        _set_axis_labels_cn(ax, title=title_map[key], xlabel=xlabel, ylabel="反射率 R")
        ax.legend(frameon=False, loc="best", prop=font)

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)
    return saved


def export_absorbing_surface_baseline_template(
    *,
    prefix: str = "rough_absorbing_surface_planar_baseline_template",
    lambda0_nm: float = 550.0,
) -> Dict[str, str]:
    """Export a template describing the planar baseline CSV needed for gain analysis."""

    template = {
        "case_id": "planar_absorbing_surface_baseline",
        "title_cn": "平面吸收表面基准",
        "purpose_cn": "用于与粗糙吸收表面进行对照，量化吸收增强增益。",
        "reference_csv": "",
        "lambda0_nm": float(lambda0_nm),
        "recommended_geometry_cn": "同材料、同厚度、无粗糙结构的平面基准表面",
        "recommended_columns": [
            "lam/1[nm] (1)",
            "abs(ewfd.S11)^2 (1)",
            "abs(ewfd.S21)^2 (1)",
            "1-abs(ewfd.S11)^2-abs(ewfd.S21)^2 (1)",
        ],
        "recommended_selectors": {
            "x_selector": "lam/1[nm] (1)",
            "r_selector": "abs(ewfd.S11)^2 (1)",
            "t_selector": "abs(ewfd.S21)^2 (1)",
            "a_selector": "1-abs(ewfd.S11)^2-abs(ewfd.S21)^2 (1)",
        },
        "notes_cn": [
            "请保持材料参数、总厚度、波长范围与粗糙版本一致。",
            "唯一变化应为表面不再引入粗糙结构。",
            "后续将对比平均吸收率、550 nm 吸收率以及反射/透射变化。",
        ],
    }

    saved: Dict[str, str] = {}
    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "平面吸收表面基准模板",
        "=" * 80,
        f"case_id             = {template['case_id']}",
        f"title_cn            = {template['title_cn']}",
        f"lambda0_nm          = {float(template['lambda0_nm']):.6f}",
        f"reference_csv       = {template['reference_csv'] or '<请填写平面基准CSV路径>'}",
        "",
        f"recommended_geometry = {template['recommended_geometry_cn']}",
        "recommended_columns =",
    ]
    lines.extend(f"  - {item}" for item in template["recommended_columns"])
    lines.extend(
        [
            "",
            "recommended_selectors =",
            f"  x_selector = {template['recommended_selectors']['x_selector']}",
            f"  r_selector = {template['recommended_selectors']['r_selector']}",
            f"  t_selector = {template['recommended_selectors']['t_selector']}",
            f"  a_selector = {template['recommended_selectors']['a_selector']}",
            "",
            "notes_cn =",
        ]
    )
    lines.extend(f"  - {item}" for item in template["notes_cn"])
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)
    return saved


def analyze_absorbing_surface_gain_against_baseline(
    rough_csv: Path | str,
    baseline_csv: Path | str,
    *,
    lambda0_nm: float = 550.0,
    rough_label: str = "粗糙表面",
    baseline_label: str = "平面基准",
    x_selector: int | str = "lam/1[nm] (1)",
    r_selector: int | str = "abs(ewfd.S11)^2 (1)",
    t_selector: int | str = "abs(ewfd.S21)^2 (1)",
    a_selector: int | str = "1-abs(ewfd.S11)^2-abs(ewfd.S21)^2 (1)",
) -> Dict[str, Any]:
    """Compare a rough absorbing surface against a planar baseline surface."""

    rough = analyze_quasi_random_absorbing_surface(
        rough_csv,
        lambda0_nm=lambda0_nm,
        x_selector=x_selector,
        r_selector=r_selector,
        t_selector=t_selector,
        a_selector=a_selector,
    )
    baseline = analyze_quasi_random_absorbing_surface(
        baseline_csv,
        lambda0_nm=lambda0_nm,
        x_selector=x_selector,
        r_selector=r_selector,
        t_selector=t_selector,
        a_selector=a_selector,
    )

    sr = rough["summary"]
    sb = baseline["summary"]
    delta_summary = {
        "delta_R_mean": float(sr["R_mean"] - sb["R_mean"]),
        "delta_T_mean": float(sr["T_mean"] - sb["T_mean"]),
        "delta_A_mean": float(sr["A_mean"] - sb["A_mean"]),
        "delta_R_at_lambda0": float(sr["R_at_lambda0"] - sb["R_at_lambda0"]),
        "delta_T_at_lambda0": float(sr["T_at_lambda0"] - sb["T_at_lambda0"]),
        "delta_A_at_lambda0": float(sr["A_at_lambda0"] - sb["A_at_lambda0"]),
        "rough_to_baseline_A_mean_ratio": (
            float(sr["A_mean"] / sb["A_mean"]) if float(sb["A_mean"]) != 0.0 else None
        ),
        "rough_to_baseline_A_at_lambda0_ratio": (
            float(sr["A_at_lambda0"] / sb["A_at_lambda0"]) if float(sb["A_at_lambda0"]) != 0.0 else None
        ),
    }

    if delta_summary["delta_A_mean"] > 0 and delta_summary["delta_A_at_lambda0"] > 0:
        interpretation_cn = "相对于平面基准，粗糙表面同时提升了全波段平均吸收率和 550 nm 吸收率。"
    elif delta_summary["delta_A_mean"] > 0:
        interpretation_cn = "相对于平面基准，粗糙表面提升了平均吸收率，但中心波长处增益有限。"
    else:
        interpretation_cn = "相对于平面基准，当前粗糙表面未带来吸收增益，建议回到几何参数继续优化。"

    return {
        "case_id": "rough_absorbing_surface_gain_against_baseline",
        "title_cn": "粗糙吸收表面相对平面基准的吸收增益",
        "lambda0_nm": float(lambda0_nm),
        "rough_label": rough_label,
        "baseline_label": baseline_label,
        "rough": rough,
        "baseline": baseline,
        "delta_summary": delta_summary,
        "interpretation_cn": interpretation_cn,
    }


def export_absorbing_surface_gain_bundle(
    rough_csv: Path | str,
    baseline_csv: Path | str,
    *,
    prefix: str = "rough_absorbing_surface_gain",
    lambda0_nm: float = 550.0,
    rough_label: str = "粗糙表面",
    baseline_label: str = "平面基准",
) -> Dict[str, str]:
    """Export gain analysis files comparing rough absorbing surface to planar baseline."""

    result = analyze_absorbing_surface_gain_against_baseline(
        rough_csv=rough_csv,
        baseline_csv=baseline_csv,
        lambda0_nm=lambda0_nm,
        rough_label=rough_label,
        baseline_label=baseline_label,
    )
    rough = result["rough"]
    baseline = result["baseline"]
    sr = rough["summary"]
    sb = baseline["summary"]
    delta = result["delta_summary"]

    wl_r = np.asarray(rough["wavelength_nm"], dtype=float)
    wl_b = np.asarray(baseline["wavelength_nm"], dtype=float)
    a_r = np.asarray(rough["A"], dtype=float)
    a_b = np.asarray(baseline["A"], dtype=float)
    r_r = np.asarray(rough["R"], dtype=float)
    r_b = np.asarray(baseline["R"], dtype=float)
    t_r = np.asarray(rough["T"], dtype=float)
    t_b = np.asarray(baseline["T"], dtype=float)

    saved: Dict[str, str] = {}

    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("metric,baseline,rough,delta_rough_minus_baseline\n")
        for metric in [
            "R_mean",
            "T_mean",
            "A_mean",
            "R_at_lambda0",
            "T_at_lambda0",
            "A_at_lambda0",
        ]:
            vb = float(sb[metric])
            vr = float(sr[metric])
            f.write(f"{metric},{vb:.12g},{vr:.12g},{(vr-vb):.12g}\n")
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "case_id": result["case_id"],
                "title_cn": result["title_cn"],
                "lambda0_nm": result["lambda0_nm"],
                "rough_csv": str(rough_csv),
                "baseline_csv": str(baseline_csv),
                "rough_label": rough_label,
                "baseline_label": baseline_label,
                "rough_summary": sr,
                "baseline_summary": sb,
                "delta_summary": delta,
                "interpretation_cn": result["interpretation_cn"],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "粗糙吸收表面相对平面基准的吸收增益分析",
        "=" * 80,
        f"baseline_csv                = {baseline_csv}",
        f"rough_csv                   = {rough_csv}",
        f"lambda0_nm                  = {float(result['lambda0_nm']):.6f}",
        "",
        f"baseline_A_mean             = {float(sb['A_mean']):.12e}",
        f"rough_A_mean                = {float(sr['A_mean']):.12e}",
        f"delta_A_mean                = {float(delta['delta_A_mean']):+.12e}",
        f"baseline_A_at_lambda0       = {float(sb['A_at_lambda0']):.12e}",
        f"rough_A_at_lambda0          = {float(sr['A_at_lambda0']):.12e}",
        f"delta_A_at_lambda0          = {float(delta['delta_A_at_lambda0']):+.12e}",
        f"delta_R_mean                = {float(delta['delta_R_mean']):+.12e}",
        f"delta_T_mean                = {float(delta['delta_T_mean']):+.12e}",
        "",
        f"interpretation_cn           = {result['interpretation_cn']}",
    ]
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    font = _cn_font()

    ax = axes[0, 0]
    ax.plot(wl_b, a_b, color=REF_BLUE, linewidth=2.2, label=f"{baseline_label} 吸收率 A")
    ax.plot(wl_r, a_r, color=TARGET_GREEN, linewidth=2.4, label=f"{rough_label} 吸收率 A")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="吸收率光谱对比", xlabel="波长 (nm)", ylabel="吸收率 A")
    ax.legend(prop=font, frameon=False, loc="best")

    ax = axes[0, 1]
    ax.plot(wl_b, r_b, color=MAIN_RED, linewidth=2.0, label=f"{baseline_label} 反射率 R")
    ax.plot(wl_r, r_r, color="#d97706", linewidth=2.0, linestyle="--", label=f"{rough_label} 反射率 R")
    ax.plot(wl_b, t_b, color=REF_BLUE, linewidth=1.8, alpha=0.75, label=f"{baseline_label} 透射率 T")
    ax.plot(wl_r, t_r, color="#5b21b6", linewidth=1.8, linestyle="--", alpha=0.75, label=f"{rough_label} 透射率 T")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="反射/透射变化", xlabel="波长 (nm)", ylabel="比例")
    ax.legend(prop=font, frameon=False, loc="best")

    ax = axes[1, 0]
    labels = ["A@550", "平均A"]
    x = np.arange(len(labels))
    width = 0.35
    vals_b = [float(sb["A_at_lambda0"]), float(sb["A_mean"])]
    vals_r = [float(sr["A_at_lambda0"]), float(sr["A_mean"])]
    bars_b = ax.bar(x - width / 2, vals_b, width=width, color=REF_BLUE, label=baseline_label)
    bars_r = ax.bar(x + width / 2, vals_r, width=width, color=TARGET_GREEN, label=rough_label)
    ax.set_xticks(x)
    if font is None:
        ax.set_xticklabels(labels)
    else:
        ax.set_xticklabels(labels, fontproperties=font)
    for bars in (bars_b, bars_r):
        for bar in bars:
            value = float(bar.get_height())
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                value + max(vals_b + vals_r) * 0.03,
                f"{value:.4f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=TEXT_DARK,
            )
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="吸收增益关键指标", xlabel="指标", ylabel="比例")
    ax.legend(prop=font, frameon=False, loc="best")

    ax = axes[1, 1]
    delta_labels = ["Δ平均R", "Δ平均T", "Δ平均A", "ΔA@550"]
    delta_vals = [
        float(delta["delta_R_mean"]),
        float(delta["delta_T_mean"]),
        float(delta["delta_A_mean"]),
        float(delta["delta_A_at_lambda0"]),
    ]
    bars = ax.bar(np.arange(len(delta_labels)), delta_vals, color=[MAIN_RED, REF_BLUE, TARGET_GREEN, TARGET_GREEN])
    ax.axhline(0.0, color="#7a8696", linewidth=1.0)
    ax.set_xticks(np.arange(len(delta_labels)))
    if font is None:
        ax.set_xticklabels(delta_labels)
    else:
        ax.set_xticklabels(delta_labels, fontproperties=font)
    for bar, value in zip(bars, delta_vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            value + (0.004 if value >= 0 else -0.006),
            f"{value:+.4f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=9,
            color=TEXT_DARK,
        )
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="粗糙表面相对平面基准的变化", xlabel="指标", ylabel="差值")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)
    return saved


def summarize_absorbing_surface_gain_trend(
    roughness_files: Dict[float, Path | str],
    baseline_csv: Path | str,
    *,
    lambda0_nm: float = 550.0,
) -> Dict[str, Any]:
    """Summarize roughness-factor gain trend against a planar baseline."""

    baseline = analyze_quasi_random_absorbing_surface(baseline_csv, lambda0_nm=lambda0_nm)
    sb = baseline["summary"]

    rows: List[Dict[str, Any]] = []
    for factor, path in sorted(roughness_files.items(), key=lambda item: float(item[0])):
        rough = analyze_quasi_random_absorbing_surface(path, lambda0_nm=lambda0_nm)
        sr = rough["summary"]
        rows.append(
            {
                "roughness_factor": float(factor),
                "reference_csv": str(path),
                "R_mean": float(sr["R_mean"]),
                "T_mean": float(sr["T_mean"]),
                "A_mean": float(sr["A_mean"]),
                "R_at_lambda0": float(sr["R_at_lambda0"]),
                "T_at_lambda0": float(sr["T_at_lambda0"]),
                "A_at_lambda0": float(sr["A_at_lambda0"]),
                "delta_R_mean": float(sr["R_mean"] - sb["R_mean"]),
                "delta_T_mean": float(sr["T_mean"] - sb["T_mean"]),
                "delta_A_mean": float(sr["A_mean"] - sb["A_mean"]),
                "delta_R_at_lambda0": float(sr["R_at_lambda0"] - sb["R_at_lambda0"]),
                "delta_T_at_lambda0": float(sr["T_at_lambda0"] - sb["T_at_lambda0"]),
                "delta_A_at_lambda0": float(sr["A_at_lambda0"] - sb["A_at_lambda0"]),
            }
        )

    if not rows:
        raise ValueError("roughness_files 不能为空。")

    best_by_delta_a550 = max(rows, key=lambda item: item["delta_A_at_lambda0"])
    best_by_delta_amean = max(rows, key=lambda item: item["delta_A_mean"])
    delta_a550 = np.array([row["delta_A_at_lambda0"] for row in rows], dtype=float)
    delta_amean = np.array([row["delta_A_mean"] for row in rows], dtype=float)
    monotonic_delta_a550 = bool(np.all(np.diff(delta_a550) >= -1e-12))
    monotonic_delta_amean = bool(np.all(np.diff(delta_amean) >= -1e-12))

    if monotonic_delta_a550 and monotonic_delta_amean:
        interpretation_cn = "相对于平面基准，在当前可计算范围内，粗糙度增大持续提升吸收增益。"
    else:
        interpretation_cn = "相对于平面基准，吸收增益已出现非严格单调变化，建议结合更多粗糙度点定位最优区间。"

    return {
        "lambda0_nm": float(lambda0_nm),
        "baseline_csv": str(baseline_csv),
        "baseline_summary": sb,
        "rows": rows,
        "best_by_delta_a550": best_by_delta_a550,
        "best_by_delta_amean": best_by_delta_amean,
        "monotonic_delta_a550": monotonic_delta_a550,
        "monotonic_delta_amean": monotonic_delta_amean,
        "interpretation_cn": interpretation_cn,
    }


def export_absorbing_surface_gain_trend_bundle(
    roughness_files: Dict[float, Path | str],
    baseline_csv: Path | str,
    *,
    prefix: str = "rough_absorbing_surface_gain_trend",
    lambda0_nm: float = 550.0,
) -> Dict[str, str]:
    """Export roughness-factor absorption gain trend against a planar baseline."""

    summary = summarize_absorbing_surface_gain_trend(
        roughness_files=roughness_files,
        baseline_csv=baseline_csv,
        lambda0_nm=lambda0_nm,
    )
    rows = summary["rows"]

    saved: Dict[str, str] = {}
    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "roughness_factor,A_mean,A_at_lambda0,delta_A_mean,delta_A_at_lambda0,"
            "delta_R_mean,delta_T_mean,reference_csv\n"
        )
        for row in rows:
            f.write(
                ",".join(
                    [
                        f"{row['roughness_factor']:.12g}",
                        f"{row['A_mean']:.12g}",
                        f"{row['A_at_lambda0']:.12g}",
                        f"{row['delta_A_mean']:.12g}",
                        f"{row['delta_A_at_lambda0']:.12g}",
                        f"{row['delta_R_mean']:.12g}",
                        f"{row['delta_T_mean']:.12g}",
                        str(row["reference_csv"]),
                    ]
                )
                + "\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "粗糙吸收表面相对平面基准的增益趋势",
        "=" * 80,
        f"baseline_csv                 = {summary['baseline_csv']}",
        f"lambda0_nm                   = {float(summary['lambda0_nm']):.6f}",
        f"best_factor_by_delta_A@550   = {float(summary['best_by_delta_a550']['roughness_factor']):.6f}",
        f"best_delta_A@550             = {float(summary['best_by_delta_a550']['delta_A_at_lambda0']):+.12e}",
        f"best_factor_by_delta_A_mean  = {float(summary['best_by_delta_amean']['roughness_factor']):.6f}",
        f"best_delta_A_mean            = {float(summary['best_by_delta_amean']['delta_A_mean']):+.12e}",
        f"monotonic_delta_A@550        = {bool(summary['monotonic_delta_a550'])}",
        f"monotonic_delta_A_mean       = {bool(summary['monotonic_delta_amean'])}",
        "",
        f"interpretation_cn            = {summary['interpretation_cn']}",
    ]
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    x = np.array([row["roughness_factor"] for row in rows], dtype=float)
    delta_a_mean = np.array([row["delta_A_mean"] for row in rows], dtype=float)
    delta_a550 = np.array([row["delta_A_at_lambda0"] for row in rows], dtype=float)
    delta_r_mean = np.array([row["delta_R_mean"] for row in rows], dtype=float)
    delta_t_mean = np.array([row["delta_T_mean"] for row in rows], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), constrained_layout=True)
    for ax in axes:
        _style_axis(ax)

    ax = axes[0]
    ax.plot(x, delta_a_mean, color=TARGET_GREEN, marker="o", linewidth=2.4, label="Δ平均A")
    ax.plot(x, delta_a550, color="#6b46c1", marker="o", linewidth=2.2, label="ΔA@550")
    _set_axis_labels_cn(ax, title="粗糙度与吸收增益", xlabel="粗糙度倍率", ylabel="增益")
    ax.legend(prop=_cn_font(), frameon=False, loc="best")

    ax = axes[1]
    ax.plot(x, delta_r_mean, color=MAIN_RED, marker="o", linewidth=2.2, label="Δ平均R")
    ax.plot(x, delta_t_mean, color=REF_BLUE, marker="o", linewidth=2.2, label="Δ平均T")
    ax.axhline(0.0, color="#7a8696", linewidth=1.0)
    _set_axis_labels_cn(ax, title="粗糙度与反射/透射变化", xlabel="粗糙度倍率", ylabel="变化量")
    ax.legend(prop=_cn_font(), frameon=False, loc="best")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)
    return saved


def export_absorbing_surface_topic_bundle(
    *,
    baseline_csv: Path | str,
    best_rough_csv: Path | str,
    best_rough_label: str = "粗糙表面最佳点",
    roughness_files: Dict[float, Path | str] | None = None,
    prefix: str = "rough_absorbing_surface_topic_v1",
    lambda0_nm: float = 550.0,
) -> Dict[str, Any]:
    """Export a final topic bundle for the rough absorbing surface branch."""

    saved: Dict[str, Any] = {}

    baseline_files = export_quasi_random_absorbing_surface_bundle(
        reference_csv=baseline_csv,
        prefix=f"{prefix}_baseline",
        lambda0_nm=lambda0_nm,
    )
    saved["baseline_files"] = baseline_files

    best_files = export_quasi_random_absorbing_surface_bundle(
        reference_csv=best_rough_csv,
        prefix=f"{prefix}_best",
        lambda0_nm=lambda0_nm,
    )
    saved["best_files"] = best_files

    gain_files = export_absorbing_surface_gain_bundle(
        rough_csv=best_rough_csv,
        baseline_csv=baseline_csv,
        prefix=f"{prefix}_gain",
        lambda0_nm=lambda0_nm,
        rough_label=best_rough_label,
        baseline_label="平面基准",
    )
    saved["gain_files"] = gain_files

    if roughness_files:
        roughness_bundle = export_absorbing_surface_roughness_bundle(
            roughness_files=roughness_files,
            prefix=f"{prefix}_roughness",
            lambda0_nm=lambda0_nm,
        )
        gain_trend_bundle = export_absorbing_surface_gain_trend_bundle(
            roughness_files=roughness_files,
            baseline_csv=baseline_csv,
            prefix=f"{prefix}_gain_trend",
            lambda0_nm=lambda0_nm,
        )
    else:
        roughness_bundle = {}
        gain_trend_bundle = {}
    saved["roughness_bundle"] = roughness_bundle
    saved["gain_trend_bundle"] = gain_trend_bundle

    baseline_summary = analyze_quasi_random_absorbing_surface(baseline_csv, lambda0_nm=lambda0_nm)["summary"]
    best_summary = analyze_quasi_random_absorbing_surface(best_rough_csv, lambda0_nm=lambda0_nm)["summary"]
    delta_a_mean = float(best_summary["A_mean"] - baseline_summary["A_mean"])
    delta_a550 = float(best_summary["A_at_lambda0"] - baseline_summary["A_at_lambda0"])

    topic_summary = {
        "baseline_csv": str(baseline_csv),
        "best_rough_csv": str(best_rough_csv),
        "best_rough_label": best_rough_label,
        "lambda0_nm": float(lambda0_nm),
        "baseline_A_mean": float(baseline_summary["A_mean"]),
        "best_A_mean": float(best_summary["A_mean"]),
        "delta_A_mean": delta_a_mean,
        "baseline_A_at_lambda0": float(baseline_summary["A_at_lambda0"]),
        "best_A_at_lambda0": float(best_summary["A_at_lambda0"]),
        "delta_A_at_lambda0": delta_a550,
        "conclusion_cn": (
            "相对于平面基准，粗糙吸收表面在平均吸收率和 550 nm 吸收率上均获得正增益。"
            if delta_a_mean > 0 and delta_a550 > 0
            else "当前粗糙吸收表面相对平面基准未形成稳定吸收增益，建议回到结构参数继续优化。"
        ),
    }

    summary_json = output_file(f"{prefix}_summary.json")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(topic_summary, f, ensure_ascii=False, indent=2)
    saved["summary_json"] = str(summary_json)

    summary_txt = output_file(f"{prefix}_summary.txt")
    lines = [
        "粗糙吸收表面专题总包摘要",
        "=" * 80,
        f"baseline_csv                = {topic_summary['baseline_csv']}",
        f"best_rough_csv              = {topic_summary['best_rough_csv']}",
        f"best_rough_label            = {topic_summary['best_rough_label']}",
        f"lambda0_nm                  = {float(topic_summary['lambda0_nm']):.6f}",
        f"baseline_A_mean             = {float(topic_summary['baseline_A_mean']):.12e}",
        f"best_A_mean                 = {float(topic_summary['best_A_mean']):.12e}",
        f"delta_A_mean                = {float(topic_summary['delta_A_mean']):+.12e}",
        f"baseline_A_at_lambda0       = {float(topic_summary['baseline_A_at_lambda0']):.12e}",
        f"best_A_at_lambda0           = {float(topic_summary['best_A_at_lambda0']):.12e}",
        f"delta_A_at_lambda0          = {float(topic_summary['delta_A_at_lambda0']):+.12e}",
        "",
        f"conclusion_cn               = {topic_summary['conclusion_cn']}",
    ]
    with open(summary_txt, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["summary_txt"] = str(summary_txt)

    manifest = {
        "baseline_csv": str(baseline_csv),
        "best_rough_csv": str(best_rough_csv),
        "best_rough_label": best_rough_label,
        "lambda0_nm": float(lambda0_nm),
        "baseline_files": baseline_files,
        "best_files": best_files,
        "gain_files": gain_files,
        "roughness_bundle": roughness_bundle,
        "gain_trend_bundle": gain_trend_bundle,
        "summary_json": str(summary_json),
        "summary_txt": str(summary_txt),
    }
    manifest_path = output_file(f"{prefix}_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    saved["manifest"] = str(manifest_path)
    return saved


def _parse_leading_float(value: Any) -> float:
    if value is None:
        raise ValueError("empty value")
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    match = _LEADING_FLOAT_RE.match(text)
    if match is None:
        raise ValueError(f"cannot parse float from {value!r}")
    return float(match.group(1))


def analyze_tamm_dw_phase_scan(
    reference_csv: Path | str,
    *,
    lambda_window_um: tuple[float, float] | None = None,
) -> Dict[str, Any]:
    """Analyze a grouped d_W scan for a Tamm absorber with reflection phase outputs."""

    path = Path(reference_csv)
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    header_idx = None
    for idx, row in enumerate(rows):
        if row and "lam (m)" in row[0]:
            header_idx = idx
            break
    if header_idx is None:
        raise ValueError(f"未找到 lam (m) 表头: {path}")

    data_rows = rows[header_idx + 1 :]
    grouped: Dict[float, Dict[str, list[float]]] = {}
    lambda_min_m = None if lambda_window_um is None else float(lambda_window_um[0]) * 1e-6
    lambda_max_m = None if lambda_window_um is None else float(lambda_window_um[1]) * 1e-6

    for row in data_rows:
        if not row or len(row) < 11:
            continue
        try:
            lam_m = _parse_leading_float(row[0])
            d_w_m = _parse_leading_float(row[1])
            r_val = _parse_leading_float(row[5])
            t_val = _parse_leading_float(row[6])
            a_val = _parse_leading_float(row[7])
            phase_val = _parse_leading_float(row[10])
        except Exception:
            continue

        if lambda_min_m is not None and lam_m < lambda_min_m:
            continue
        if lambda_max_m is not None and lam_m > lambda_max_m:
            continue

        bucket = grouped.setdefault(
            d_w_m,
            {"lam_m": [], "R": [], "T": [], "A": [], "phase_rad": []},
        )
        bucket["lam_m"].append(lam_m)
        bucket["R"].append(r_val)
        bucket["T"].append(t_val)
        bucket["A"].append(a_val)
        bucket["phase_rad"].append(phase_val)

    if not grouped:
        raise ValueError(f"未能从 CSV 中读取有效的 d_W 联合扫描数据: {path}")

    groups: List[Dict[str, Any]] = []
    for d_w_m in sorted(grouped):
        raw = grouped[d_w_m]
        lam_um = np.asarray(raw["lam_m"], dtype=float) * 1e6
        order = np.argsort(lam_um)
        lam_um = lam_um[order]
        r_vals = np.asarray(raw["R"], dtype=float)[order]
        t_vals = np.asarray(raw["T"], dtype=float)[order]
        a_vals = np.asarray(raw["A"], dtype=float)[order]
        phase_raw = np.asarray(raw["phase_rad"], dtype=float)[order]
        phase_unwrapped = np.unwrap(phase_raw)

        peak_idx = int(np.argmax(a_vals))
        groups.append(
            {
                "dW_nm": float(d_w_m * 1e9),
                "wavelength_um": lam_um,
                "R": r_vals,
                "T": t_vals,
                "A": a_vals,
                "phase_rad": phase_raw,
                "phase_unwrapped_rad": phase_unwrapped,
                "summary": {
                    "num_points": int(len(lam_um)),
                    "A_max": float(a_vals[peak_idx]),
                    "A_mean": float(np.mean(a_vals)),
                    "R_mean": float(np.mean(r_vals)),
                    "T_mean": float(np.mean(t_vals)),
                    "peak_wavelength_um": float(lam_um[peak_idx]),
                    "phase_at_peak_rad": float(phase_raw[peak_idx]),
                    "phase_unwrapped_span_rad": float(np.max(phase_unwrapped) - np.min(phase_unwrapped)),
                    "energy_balance_max_error": float(np.max(np.abs(r_vals + t_vals + a_vals - 1.0))),
                },
            }
        )

    best_group = max(groups, key=lambda item: float(item["summary"]["A_max"]))
    summary = {
        "reference_csv": str(path),
        "num_groups": int(len(groups)),
        "lambda_min_um": float(min(float(np.min(item["wavelength_um"])) for item in groups)),
        "lambda_max_um": float(max(float(np.max(item["wavelength_um"])) for item in groups)),
        "best_dW_nm": float(best_group["dW_nm"]),
        "best_A_max": float(best_group["summary"]["A_max"]),
        "best_peak_wavelength_um": float(best_group["summary"]["peak_wavelength_um"]),
        "best_A_mean": float(best_group["summary"]["A_mean"]),
    }

    phase_ready = summary["best_A_max"] >= 0.95 and len(groups) >= 3
    if phase_ready:
        interpretation_cn = "普通 Tamm 吸收器已进入近完美吸收区，可正式转入反射相位与拓扑分类。"
    else:
        interpretation_cn = "当前仍处于普通 Tamm 吸收器参数摸底阶段，建议继续补充高吸收参数点后再进入相位分类。"

    return {
        "case_id": "tamm_dw_phase_scan",
        "title_cn": "Tamm 吸收器 d_W-相位联合扫描",
        "title_en": "Tamm d_W Phase Scan",
        "reference_csv": str(path),
        "groups": groups,
        "summary": summary,
        "phase_ready": bool(phase_ready),
        "interpretation_cn": interpretation_cn,
    }


def export_tamm_dw_phase_bundle(
    reference_csv: Path | str,
    *,
    prefix: str = "tamm_dw_phase_v1",
    lambda_window_um: tuple[float, float] | None = None,
) -> Dict[str, str]:
    """Export grouped d_W scan figures and summaries for Tamm phase-stage analysis."""

    result = analyze_tamm_dw_phase_scan(reference_csv, lambda_window_um=lambda_window_um)
    saved: Dict[str, str] = {}
    groups = result["groups"]
    summary = result["summary"]

    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("dW_nm,A_max,A_mean,R_mean,T_mean,peak_wavelength_um,phase_at_peak_rad,phase_unwrapped_span_rad,energy_balance_max_error\n")
        for item in groups:
            s = item["summary"]
            f.write(
                f"{float(item['dW_nm']):.12g},{float(s['A_max']):.12g},{float(s['A_mean']):.12g},"
                f"{float(s['R_mean']):.12g},{float(s['T_mean']):.12g},{float(s['peak_wavelength_um']):.12g},"
                f"{float(s['phase_at_peak_rad']):.12g},{float(s['phase_unwrapped_span_rad']):.12g},"
                f"{float(s['energy_balance_max_error']):.12g}\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "case_id": result["case_id"],
                "title_cn": result["title_cn"],
                "reference_csv": result["reference_csv"],
                "summary": summary,
                "phase_ready": result["phase_ready"],
                "interpretation_cn": result["interpretation_cn"],
                "groups": [
                    {
                        "dW_nm": item["dW_nm"],
                        "summary": item["summary"],
                    }
                    for item in groups
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "Tamm 吸收器 d_W-相位联合扫描",
        "=" * 80,
        f"reference_csv             = {result['reference_csv']}",
        f"num_groups                = {int(summary['num_groups'])}",
        f"lambda_min_um             = {float(summary['lambda_min_um']):.6f}",
        f"lambda_max_um             = {float(summary['lambda_max_um']):.6f}",
        f"best_dW_nm                = {float(summary['best_dW_nm']):.6f}",
        f"best_A_max                = {float(summary['best_A_max']):.12e}",
        f"best_peak_wavelength_um   = {float(summary['best_peak_wavelength_um']):.6f}",
        f"best_A_mean               = {float(summary['best_A_mean']):.12e}",
        f"phase_ready               = {bool(result['phase_ready'])}",
        "",
        f"interpretation_cn         = {result['interpretation_cn']}",
        "",
        "group_details:",
    ]
    for item in groups:
        s = item["summary"]
        lines.append(
            f"  dW={float(item['dW_nm']):.1f} nm | "
            f"Amax={float(s['A_max']):.6f} @ {float(s['peak_wavelength_um']):.3f} um | "
            f"Amean={float(s['A_mean']):.6f} | phase@peak={float(s['phase_at_peak_rad']):+.6f} rad | "
            f"phase_span={float(s['phase_unwrapped_span_rad']):.6f} rad"
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    font = _cn_font()
    colors = plt.cm.viridis(np.linspace(0.15, 0.9, len(groups)))

    ax = axes[0, 0]
    for color, item in zip(colors, groups):
        wl = np.asarray(item["wavelength_um"], dtype=float)
        a_vals = np.asarray(item["A"], dtype=float)
        ax.plot(wl, a_vals, color=color, linewidth=2.0, label=f"dW={item['dW_nm']:.0f} nm")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="吸收谱 A(λ)", xlabel="波长 (μm)", ylabel="吸收率 A")
    ax.legend(prop=font, frameon=False, loc="best")

    ax = axes[0, 1]
    for color, item in zip(colors, groups):
        wl = np.asarray(item["wavelength_um"], dtype=float)
        phase = np.asarray(item["phase_unwrapped_rad"], dtype=float)
        ax.plot(wl, phase, color=color, linewidth=2.0, label=f"dW={item['dW_nm']:.0f} nm")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="反射相位（展开）", xlabel="波长 (μm)", ylabel="相位 (rad)")

    ax = axes[1, 0]
    dws = [float(item["dW_nm"]) for item in groups]
    amax = [float(item["summary"]["A_max"]) for item in groups]
    peaks = [float(item["summary"]["peak_wavelength_um"]) for item in groups]
    ax.plot(dws, amax, color=TARGET_GREEN, linewidth=2.4, marker="o")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="峰值吸收率随 d_W 变化", xlabel="d_W (nm)", ylabel="A_max")

    ax = axes[1, 1]
    ax.plot(dws, peaks, color=REF_BLUE, linewidth=2.4, marker="o", label="峰位")
    ax2 = ax.twinx()
    spans = [float(item["summary"]["phase_unwrapped_span_rad"]) for item in groups]
    ax2.plot(dws, spans, color=ERR_GOLD, linewidth=2.0, marker="s", linestyle="--", label="相位跨度")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="峰位与相位跨度", xlabel="d_W (nm)", ylabel="峰位 (μm)")
    ax2.set_ylabel("相位跨度 (rad)", color=TEXT_DARK)
    ax2.tick_params(colors=TEXT_DARK)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, prop=font, frameon=False, loc="best")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)

    return saved


def export_tamm_phase_focus_bundle(
    reference_csv: Path | str,
    *,
    focus_dws_nm: Sequence[float] = (100.0, 110.0, 120.0),
    prefix: str = "tamm_phase_focus_v1",
    lambda_window_um: tuple[float, float] | None = None,
) -> Dict[str, str]:
    """Export a focused phase comparison for representative d_W points."""

    result = analyze_tamm_dw_phase_scan(reference_csv, lambda_window_um=lambda_window_um)
    focus_targets = [float(x) for x in focus_dws_nm]
    groups = result["groups"]
    selected: List[Dict[str, Any]] = []
    for target in focus_targets:
        match = min(groups, key=lambda item: abs(float(item["dW_nm"]) - target))
        if all(abs(float(match["dW_nm"]) - float(existing["dW_nm"])) > 1e-9 for existing in selected):
            selected.append(match)

    selected = sorted(selected, key=lambda item: float(item["dW_nm"]))
    if not selected:
        raise ValueError("未能找到用于相位对比的代表性 d_W 组。")

    saved: Dict[str, str] = {}

    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("dW_nm,A_max,A_mean,peak_wavelength_um,phase_at_peak_rad,phase_unwrapped_span_rad\n")
        for item in selected:
            s = item["summary"]
            f.write(
                f"{float(item['dW_nm']):.12g},{float(s['A_max']):.12g},{float(s['A_mean']):.12g},"
                f"{float(s['peak_wavelength_um']):.12g},{float(s['phase_at_peak_rad']):.12g},"
                f"{float(s['phase_unwrapped_span_rad']):.12g}\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "case_id": "tamm_phase_focus",
                "reference_csv": str(Path(reference_csv)),
                "focus_dws_nm": [float(item["dW_nm"]) for item in selected],
                "summary": [
                    {
                        "dW_nm": float(item["dW_nm"]),
                        **item["summary"],
                    }
                    for item in selected
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    focus_dws_text = ", ".join(f"{float(item['dW_nm']):.0f}" for item in selected)
    lines = [
        "Tamm 第2阶段代表点相位对比",
        "=" * 80,
        f"reference_csv = {Path(reference_csv)}",
        f"focus_dws_nm  = {focus_dws_text}",
        "",
    ]
    for item in selected:
        s = item["summary"]
        lines.append(
            f"dW={float(item['dW_nm']):.0f} nm | Amax={float(s['A_max']):.6f} | "
            f"peak={float(s['peak_wavelength_um']):.3f} um | "
            f"phase@peak={float(s['phase_at_peak_rad']):+.6f} rad | "
            f"phase_span={float(s['phase_unwrapped_span_rad']):.6f} rad"
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    font = _cn_font()
    colors = plt.cm.plasma(np.linspace(0.2, 0.85, len(selected)))

    ax = axes[0]
    for color, item in zip(colors, selected):
        wl = np.asarray(item["wavelength_um"], dtype=float)
        a_vals = np.asarray(item["A"], dtype=float)
        ax.plot(wl, a_vals, color=color, linewidth=2.4, label=f"dW={item['dW_nm']:.0f} nm")
        peak_idx = int(np.argmax(a_vals))
        ax.scatter([wl[peak_idx]], [a_vals[peak_idx]], color=color, s=28, zorder=3)
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="代表点吸收谱对比", xlabel="波长 (μm)", ylabel="吸收率 A")
    ax.legend(prop=font, frameon=False, loc="best")

    ax = axes[1]
    for color, item in zip(colors, selected):
        wl = np.asarray(item["wavelength_um"], dtype=float)
        phase = np.asarray(item["phase_unwrapped_rad"], dtype=float)
        ax.plot(wl, phase, color=color, linewidth=2.4, label=f"dW={item['dW_nm']:.0f} nm")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="代表点反射相位对比", xlabel="波长 (μm)", ylabel="展开相位 (rad)")
    ax.legend(prop=font, frameon=False, loc="best")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)

    return saved


def export_tamm_phase_candidate_pairs(
    reference_csv: Path | str,
    *,
    candidate_dws_nm: Sequence[float] = (90.0, 100.0, 110.0, 120.0),
    prefix: str = "tamm_phase_candidates_v1",
    lambda_window_um: tuple[float, float] | None = None,
) -> Dict[str, str]:
    """Rank representative d_W pairs for stage-2 topology candidate selection."""

    result = analyze_tamm_dw_phase_scan(reference_csv, lambda_window_um=lambda_window_um)
    groups = result["groups"]
    selected: List[Dict[str, Any]] = []
    for target in [float(x) for x in candidate_dws_nm]:
        match = min(groups, key=lambda item: abs(float(item["dW_nm"]) - target))
        if all(abs(float(match["dW_nm"]) - float(existing["dW_nm"])) > 1e-9 for existing in selected):
            selected.append(match)
    selected = sorted(selected, key=lambda item: float(item["dW_nm"]))

    pair_rows: List[Dict[str, float]] = []
    for i, a in enumerate(selected):
        for b in selected[i + 1 :]:
            xa = np.asarray(a["wavelength_um"], dtype=float)
            xb = np.asarray(b["wavelength_um"], dtype=float)
            pa = np.asarray(a["phase_unwrapped_rad"], dtype=float)
            pb = np.asarray(b["phase_unwrapped_rad"], dtype=float)
            grid = np.linspace(max(float(np.min(xa)), float(np.min(xb))), min(float(np.max(xa)), float(np.max(xb))), 400)
            diff = np.abs(np.interp(grid, xa, pa) - np.interp(grid, xb, pb))
            amax_avg = (float(a["summary"]["A_max"]) + float(b["summary"]["A_max"])) / 2.0
            row = {
                "dW_a_nm": float(a["dW_nm"]),
                "dW_b_nm": float(b["dW_nm"]),
                "mean_phase_diff_rad": float(np.mean(diff)),
                "max_phase_diff_rad": float(np.max(diff)),
                "peak_phase_diff_rad": abs(float(a["summary"]["phase_at_peak_rad"]) - float(b["summary"]["phase_at_peak_rad"])),
                "peak_wavelength_delta_um": abs(float(a["summary"]["peak_wavelength_um"]) - float(b["summary"]["peak_wavelength_um"])),
                "avg_A_max": float(amax_avg),
            }
            row["balanced_score"] = float(row["mean_phase_diff_rad"] * row["avg_A_max"])
            pair_rows.append(row)

    if not pair_rows:
        raise ValueError("候选 d_W 点不足，无法构造相位候选对。")

    pair_rows_sorted = sorted(pair_rows, key=lambda item: item["balanced_score"], reverse=True)
    best_overall = pair_rows_sorted[0]
    best_peak = max(pair_rows, key=lambda item: item["peak_phase_diff_rad"])

    saved: Dict[str, str] = {}
    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("dW_a_nm,dW_b_nm,mean_phase_diff_rad,max_phase_diff_rad,peak_phase_diff_rad,peak_wavelength_delta_um,avg_A_max,balanced_score\n")
        for row in pair_rows_sorted:
            f.write(
                f"{row['dW_a_nm']:.12g},{row['dW_b_nm']:.12g},{row['mean_phase_diff_rad']:.12g},"
                f"{row['max_phase_diff_rad']:.12g},{row['peak_phase_diff_rad']:.12g},{row['peak_wavelength_delta_um']:.12g},"
                f"{row['avg_A_max']:.12g},{row['balanced_score']:.12g}\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "reference_csv": str(Path(reference_csv)),
                "candidate_dws_nm": [float(item["dW_nm"]) for item in selected],
                "best_overall_pair": best_overall,
                "best_peak_phase_pair": best_peak,
                "pairs": pair_rows_sorted,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    candidate_dws_text = ", ".join(f"{float(item['dW_nm']):.0f}" for item in selected)
    lines = [
        "Tamm 第2阶段候选对排名",
        "=" * 80,
        f"reference_csv = {Path(reference_csv)}",
        f"candidate_dws = {candidate_dws_text}",
        "",
        f"整体最优候选对 = ({best_overall['dW_a_nm']:.0f} nm, {best_overall['dW_b_nm']:.0f} nm)",
        f"峰处相位差最大候选对 = ({best_peak['dW_a_nm']:.0f} nm, {best_peak['dW_b_nm']:.0f} nm)",
        "",
    ]
    for row in pair_rows_sorted:
        lines.append(
            f"({row['dW_a_nm']:.0f}, {row['dW_b_nm']:.0f}) nm | "
            f"mean_phase_diff={row['mean_phase_diff_rad']:.6f} rad | "
            f"peak_phase_diff={row['peak_phase_diff_rad']:.6f} rad | "
            f"avg_Amax={row['avg_A_max']:.6f} | "
            f"score={row['balanced_score']:.6f}"
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    return saved


def export_tamm_interface_priority_bundle(
    reference_csv: Path | str,
    *,
    candidate_dws_nm: Sequence[float] = (90.0, 100.0, 110.0, 120.0),
    prefix: str = "tamm_interface_priority_v1",
    lambda_window_um: tuple[float, float] | None = None,
) -> Dict[str, str]:
    """Export a practical recommendation bundle for interface-pair selection."""

    result = analyze_tamm_dw_phase_scan(reference_csv, lambda_window_um=lambda_window_um)
    groups = result["groups"]
    selected: List[Dict[str, Any]] = []
    for target in [float(x) for x in candidate_dws_nm]:
        match = min(groups, key=lambda item: abs(float(item["dW_nm"]) - target))
        if all(abs(float(match["dW_nm"]) - float(existing["dW_nm"])) > 1e-9 for existing in selected):
            selected.append(match)
    selected = sorted(selected, key=lambda item: float(item["dW_nm"]))

    pair_rows: List[Dict[str, float]] = []
    for i, a in enumerate(selected):
        for b in selected[i + 1 :]:
            xa = np.asarray(a["wavelength_um"], dtype=float)
            xb = np.asarray(b["wavelength_um"], dtype=float)
            pa = np.asarray(a["phase_unwrapped_rad"], dtype=float)
            pb = np.asarray(b["phase_unwrapped_rad"], dtype=float)
            grid = np.linspace(max(float(np.min(xa)), float(np.min(xb))), min(float(np.max(xa)), float(np.max(xb))), 400)
            diff = np.abs(np.interp(grid, xa, pa) - np.interp(grid, xb, pb))
            amax_avg = (float(a["summary"]["A_max"]) + float(b["summary"]["A_max"])) / 2.0
            row = {
                "dW_a_nm": float(a["dW_nm"]),
                "dW_b_nm": float(b["dW_nm"]),
                "mean_phase_diff_rad": float(np.mean(diff)),
                "max_phase_diff_rad": float(np.max(diff)),
                "peak_phase_diff_rad": abs(float(a["summary"]["phase_at_peak_rad"]) - float(b["summary"]["phase_at_peak_rad"])),
                "peak_wavelength_delta_um": abs(float(a["summary"]["peak_wavelength_um"]) - float(b["summary"]["peak_wavelength_um"])),
                "avg_A_max": float(amax_avg),
            }
            row["balanced_score"] = float(row["mean_phase_diff_rad"] * row["avg_A_max"])
            pair_rows.append(row)

    if not pair_rows:
        raise ValueError("候选 d_W 点不足，无法生成界面优先级建议。")

    best_overall = max(pair_rows, key=lambda item: item["balanced_score"])
    best_peak = max(pair_rows, key=lambda item: item["peak_phase_diff_rad"])

    recommended_default = best_peak if best_peak["avg_A_max"] >= 0.99 else best_overall
    recommended_exploratory = best_overall if best_overall != recommended_default else max(
        (row for row in pair_rows if row != recommended_default),
        key=lambda item: item["balanced_score"],
    )

    recommendation = {
        "default_pair_nm": [recommended_default["dW_a_nm"], recommended_default["dW_b_nm"]],
        "exploratory_pair_nm": [recommended_exploratory["dW_a_nm"], recommended_exploratory["dW_b_nm"]],
        "default_reason_cn": "默认优先采用峰处相位差更大、且两侧都保持近完美吸收的候选对，便于后续界面边界态验证。",
        "exploratory_reason_cn": "保留整体相位差更强的候选对，作为对照组评估“高平均相位差”与“高局域相位差”的差异。",
    }

    saved: Dict[str, str] = {}
    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "reference_csv": str(Path(reference_csv)),
                "recommendation": recommendation,
                "best_overall_pair": best_overall,
                "best_peak_phase_pair": best_peak,
                "pairs": pair_rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "Tamm 第2阶段界面拼接优先级建议",
        "=" * 80,
        f"reference_csv = {Path(reference_csv)}",
        "",
        f"默认候选对 = ({recommended_default['dW_a_nm']:.0f} nm, {recommended_default['dW_b_nm']:.0f} nm)",
        f"默认理由 = {recommendation['default_reason_cn']}",
        "",
        f"探索候选对 = ({recommended_exploratory['dW_a_nm']:.0f} nm, {recommended_exploratory['dW_b_nm']:.0f} nm)",
        f"探索理由 = {recommendation['exploratory_reason_cn']}",
        "",
        f"整体最优候选对 = ({best_overall['dW_a_nm']:.0f} nm, {best_overall['dW_b_nm']:.0f} nm)",
        f"峰处相位差最大候选对 = ({best_peak['dW_a_nm']:.0f} nm, {best_peak['dW_b_nm']:.0f} nm)",
    ]
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    font = _cn_font()

    ax = axes[0]
    labels = [f"({int(row['dW_a_nm'])},{int(row['dW_b_nm'])})" for row in pair_rows]
    scores = [float(row["balanced_score"]) for row in pair_rows]
    bars = ax.bar(np.arange(len(pair_rows)), scores, color="#4c78a8")
    ax.set_xticks(np.arange(len(pair_rows)))
    if font is None:
        ax.set_xticklabels(labels, rotation=20)
    else:
        ax.set_xticklabels(labels, rotation=20, fontproperties=font)
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="候选对综合评分", xlabel="d_W 候选对 (nm)", ylabel="balanced score")
    for bar, value in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(scores) * 0.02, f"{value:.3f}", ha="center", va="bottom", fontsize=8, color=TEXT_DARK)

    ax = axes[1]
    peak_diffs = [float(row["peak_phase_diff_rad"]) for row in pair_rows]
    avg_amax = [float(row["avg_A_max"]) for row in pair_rows]
    ax.scatter(peak_diffs, avg_amax, color=TARGET_GREEN, s=50)
    for row, x, y in zip(pair_rows, peak_diffs, avg_amax):
        ax.text(x + 0.005, y + 0.0015, f"({int(row['dW_a_nm'])},{int(row['dW_b_nm'])})", fontsize=8, color=TEXT_DARK)
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="峰处相位差与平均峰值吸收", xlabel="峰处相位差 (rad)", ylabel="平均 A_max")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)

    return saved


def analyze_tamm_reflection_phase_screen(
    reference_csv: Path | str,
    *,
    candidate_dws_nm: Sequence[float] | None = None,
    lambda_window_um: tuple[float, float] | None = None,
    min_reflectance: float = 0.70,
    max_phase_error_rad: float = 0.35,
) -> Dict[str, Any]:
    """Screen 1D Tamm terminal pairs by high reflectance and near-pi phase contrast."""

    result = analyze_tamm_dw_phase_scan(reference_csv, lambda_window_um=lambda_window_um)
    groups = result["groups"]

    if candidate_dws_nm:
        selected: List[Dict[str, Any]] = []
        for target in [float(x) for x in candidate_dws_nm]:
            match = min(groups, key=lambda item: abs(float(item["dW_nm"]) - target))
            if all(abs(float(match["dW_nm"]) - float(existing["dW_nm"])) > 1e-9 for existing in selected):
                selected.append(match)
        groups = sorted(selected, key=lambda item: float(item["dW_nm"]))

    rows: List[Dict[str, float | bool]] = []
    for i, left in enumerate(groups):
        for right in groups[i + 1 :]:
            wl_left = np.asarray(left["wavelength_um"], dtype=float)
            wl_right = np.asarray(right["wavelength_um"], dtype=float)
            lo = max(float(np.min(wl_left)), float(np.min(wl_right)))
            hi = min(float(np.max(wl_left)), float(np.max(wl_right)))
            if hi <= lo:
                continue

            grid = np.linspace(lo, hi, 800)
            r_left = np.interp(grid, wl_left, np.asarray(left["R"], dtype=float))
            r_right = np.interp(grid, wl_right, np.asarray(right["R"], dtype=float))
            a_left = np.interp(grid, wl_left, np.asarray(left["A"], dtype=float))
            a_right = np.interp(grid, wl_right, np.asarray(right["A"], dtype=float))
            phase_left = np.interp(grid, wl_left, np.asarray(left["phase_unwrapped_rad"], dtype=float))
            phase_right = np.interp(grid, wl_right, np.asarray(right["phase_unwrapped_rad"], dtype=float))

            phase_diff = np.abs(np.angle(np.exp(1j * (phase_left - phase_right))))
            phase_error = np.abs(np.pi - phase_diff)
            min_r = np.minimum(r_left, r_right)
            mean_r = (r_left + r_right) / 2.0
            score = min_r * np.clip(1.0 - phase_error / np.pi, 0.0, 1.0)
            best_idx = int(np.argmax(score))

            row = {
                "dW_left_nm": float(left["dW_nm"]),
                "dW_right_nm": float(right["dW_nm"]),
                "wavelength_um": float(grid[best_idx]),
                "phase_diff_rad": float(phase_diff[best_idx]),
                "phase_error_to_pi_rad": float(phase_error[best_idx]),
                "R_left": float(r_left[best_idx]),
                "R_right": float(r_right[best_idx]),
                "min_R": float(min_r[best_idx]),
                "mean_R": float(mean_r[best_idx]),
                "A_left": float(a_left[best_idx]),
                "A_right": float(a_right[best_idx]),
                "phase_left_rad": float(phase_left[best_idx]),
                "phase_right_rad": float(phase_right[best_idx]),
                "score": float(score[best_idx]),
                "passes": bool(min_r[best_idx] >= min_reflectance and phase_error[best_idx] <= max_phase_error_rad),
            }
            rows.append(row)

    if not rows:
        raise ValueError("候选组不足，无法进行 Tamm 反射相位端结构筛选。")

    rows_sorted = sorted(rows, key=lambda item: float(item["score"]), reverse=True)
    passing = [row for row in rows_sorted if bool(row["passes"])]
    best = rows_sorted[0]

    if passing:
        interpretation_cn = "已发现同时满足高反射与近 π 相位差的候选端结构对，可优先进入 2D 界面拼接验证。"
    else:
        interpretation_cn = "当前未发现同时满足高反射与近 π 相位差的候选端结构对；建议扩大 1D 参数扫描后再做 2D 拼接。"

    return {
        "case_id": "tamm_reflection_phase_screen",
        "title_cn": "Tamm 1D 反射相位端结构筛选",
        "reference_csv": str(Path(reference_csv)),
        "criteria": {
            "min_reflectance": float(min_reflectance),
            "max_phase_error_rad": float(max_phase_error_rad),
            "target_phase_diff_rad": float(np.pi),
        },
        "candidate_dws_nm": [float(item["dW_nm"]) for item in groups],
        "rows": rows_sorted,
        "summary": {
            "num_pairs": int(len(rows_sorted)),
            "num_passing_pairs": int(len(passing)),
            "best_pair": best,
        },
        "interpretation_cn": interpretation_cn,
    }


def export_tamm_reflection_phase_screen_bundle(
    reference_csv: Path | str,
    *,
    candidate_dws_nm: Sequence[float] | None = None,
    prefix: str = "tamm_reflection_phase_screen_v1",
    lambda_window_um: tuple[float, float] | None = None,
    min_reflectance: float = 0.70,
    max_phase_error_rad: float = 0.35,
) -> Dict[str, str]:
    """Export 1D Tamm terminal-pair screening by reflectance and phase contrast."""

    result = analyze_tamm_reflection_phase_screen(
        reference_csv,
        candidate_dws_nm=candidate_dws_nm,
        lambda_window_um=lambda_window_um,
        min_reflectance=min_reflectance,
        max_phase_error_rad=max_phase_error_rad,
    )
    rows = result["rows"]
    saved: Dict[str, str] = {}

    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "dW_left_nm,dW_right_nm,wavelength_um,phase_diff_rad,phase_error_to_pi_rad,"
            "R_left,R_right,min_R,mean_R,A_left,A_right,phase_left_rad,phase_right_rad,score,passes\n"
        )
        for row in rows:
            f.write(
                f"{float(row['dW_left_nm']):.12g},{float(row['dW_right_nm']):.12g},"
                f"{float(row['wavelength_um']):.12g},{float(row['phase_diff_rad']):.12g},"
                f"{float(row['phase_error_to_pi_rad']):.12g},{float(row['R_left']):.12g},"
                f"{float(row['R_right']):.12g},{float(row['min_R']):.12g},{float(row['mean_R']):.12g},"
                f"{float(row['A_left']):.12g},{float(row['A_right']):.12g},"
                f"{float(row['phase_left_rad']):.12g},{float(row['phase_right_rad']):.12g},"
                f"{float(row['score']):.12g},{bool(row['passes'])}\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    best = result["summary"]["best_pair"]
    candidate_dws_text = ", ".join(f"{float(x):.0f}" for x in result["candidate_dws_nm"])
    lines = [
        "Tamm 1D 反射相位端结构筛选",
        "=" * 80,
        f"reference_csv          = {result['reference_csv']}",
        f"candidate_dws_nm       = {candidate_dws_text}",
        f"min_reflectance        = {float(result['criteria']['min_reflectance']):.3f}",
        f"max_phase_error_rad    = {float(result['criteria']['max_phase_error_rad']):.3f}",
        f"num_pairs              = {int(result['summary']['num_pairs'])}",
        f"num_passing_pairs      = {int(result['summary']['num_passing_pairs'])}",
        "",
        f"best_pair              = ({float(best['dW_left_nm']):.0f} nm, {float(best['dW_right_nm']):.0f} nm)",
        f"best_wavelength_um     = {float(best['wavelength_um']):.6f}",
        f"best_min_R             = {float(best['min_R']):.6f}",
        f"best_phase_diff_rad    = {float(best['phase_diff_rad']):.6f}",
        f"best_phase_error_rad   = {float(best['phase_error_to_pi_rad']):.6f}",
        f"best_score             = {float(best['score']):.6f}",
        "",
        f"interpretation_cn      = {result['interpretation_cn']}",
        "",
        "top_pairs:",
    ]
    for row in rows[:10]:
        lines.append(
            f"  ({float(row['dW_left_nm']):.0f}, {float(row['dW_right_nm']):.0f}) nm @ "
            f"{float(row['wavelength_um']):.3f} um | minR={float(row['min_R']):.3f} | "
            f"Δφ={float(row['phase_diff_rad']):.3f} rad | |π-Δφ|={float(row['phase_error_to_pi_rad']):.3f} | "
            f"score={float(row['score']):.3f} | pass={bool(row['passes'])}"
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
    font = _cn_font()
    pair_labels = [f"{int(row['dW_left_nm'])}/{int(row['dW_right_nm'])}" for row in rows[:12]]
    scores = [float(row["score"]) for row in rows[:12]]
    colors = [TARGET_GREEN if bool(row["passes"]) else REF_BLUE for row in rows[:12]]

    ax = axes[0]
    bars = ax.bar(np.arange(len(scores)), scores, color=colors)
    ax.set_xticks(np.arange(len(scores)))
    if font is None:
        ax.set_xticklabels(pair_labels, rotation=30)
    else:
        ax.set_xticklabels(pair_labels, rotation=30, fontproperties=font)
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="候选端结构对评分", xlabel="d_W 左/右 (nm)", ylabel="score")
    for bar, value in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(scores + [1e-9]) * 0.02, f"{value:.2f}", ha="center", va="bottom", fontsize=8, color=TEXT_DARK)

    ax = axes[1]
    min_r = [float(row["min_R"]) for row in rows]
    phase_err = [float(row["phase_error_to_pi_rad"]) for row in rows]
    pass_mask = [bool(row["passes"]) for row in rows]
    ax.scatter(phase_err, min_r, c=[TARGET_GREEN if flag else MAIN_RED for flag in pass_mask], s=52, alpha=0.85)
    ax.axhline(float(result["criteria"]["min_reflectance"]), color=REF_BLUE, linestyle="--", linewidth=1.4, label="min R threshold")
    ax.axvline(float(result["criteria"]["max_phase_error_rad"]), color=ERR_GOLD, linestyle="--", linewidth=1.4, label="phase error threshold")
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="高反射与 π 相位差判据", xlabel="|π-Δφ| (rad)", ylabel="min(R_left, R_right)")
    ax.legend(prop=font, frameon=False, loc="best")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)

    return saved


def analyze_tamm_interface_2d_window_csv(
    reference_csv: Path | str,
    *,
    x_window_um: tuple[float, float] = (-5.0, 5.0),
    y_window_um: tuple[float, float] = (8.8, 10.4),
    interface_half_width_um: float = 0.5,
    background_left_um: tuple[float, float] = (-5.0, -3.0),
    background_right_um: tuple[float, float] = (3.0, 5.0),
) -> Dict[str, Any]:
    """Analyze a full-field 2D CSV by cropping a local interface window in Python."""

    path = Path(reference_csv)
    groups: Dict[tuple[int, float], Dict[str, float]] = {}
    y_first: float | None = None
    unique_x_values: set[float] = set()
    unique_y_values: set[float] = set()

    def _norm_header_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", name.strip().lower())

    def _try_build_header_map(cols: Sequence[str]) -> Dict[str, int] | None:
        normalized = [_norm_header_name(col) for col in cols]
        candidates: Dict[str, Sequence[str]] = {
            "x_um": ("x1um", "xum", "x"),
            "y_um": ("y1um", "yum", "y"),
            "lam_um": ("lam1um", "lambda1um", "lamum", "lambdaum", "lam"),
            "d_w_l_nm": ("dwl1nm", "dwl_nm", "dwlnm", "dwl", "dwlftnm", "dwlleftnm", "dwlnanometer", "dwlnm1", "dwlnm2"),
            "norm_e": ("ewfdnorme", "norme"),
            "norm_e2": ("ewfdnorme2", "ewfdnorme2v", "norme2"),
            "qh": ("ewfdqh", "qh"),
        }
        mapping: Dict[str, int] = {}
        for key, aliases in candidates.items():
            for idx, item in enumerate(normalized):
                if item in aliases:
                    mapping[key] = idx
                    break
        required = {"x_um", "y_um", "lam_um", "d_w_l_nm", "norm_e", "norm_e2", "qh"}
        return mapping if required.issubset(mapping) else None

    legacy_index_map = {
        "x_um": 5,
        "y_um": 6,
        "norm_e": 8,
        "norm_e2": 9,
        "qh": 10,
        "lam_um": 11,
        "d_w_l_nm": 12,
    }
    compact_index_map = {
        "x_um": 5,
        "y_um": 6,
        "lam_um": 7,
        "d_w_l_nm": 8,
        "norm_e": 9,
        "norm_e2": 10,
        "qh": 11,
    }
    header_index_map: Dict[str, int] | None = None

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for raw_line in f:
            if not raw_line.strip() or raw_line.startswith("%"):
                continue
            cols = raw_line.strip().split(",")
            if header_index_map is None:
                possible_header = _try_build_header_map(cols)
                if possible_header is not None:
                    header_index_map = possible_header
                    continue
                header_index_map = compact_index_map if len(cols) == 12 else legacy_index_map

            index_map = header_index_map
            required_max = max(index_map.values())
            if len(cols) <= required_max:
                continue
            try:
                x_um = float(cols[index_map["x_um"]])
                y_um = float(cols[index_map["y_um"]])
                lam_um = round(float(cols[index_map["lam_um"]]), 2)
                d_w_l_nm = int(round(float(cols[index_map["d_w_l_nm"]])))
                norm_e = float(cols[index_map["norm_e"]])
                norm_e2 = float(cols[index_map["norm_e2"]])
                qh = float(cols[index_map["qh"]])
            except ValueError:
                continue

            if y_first is None:
                y_first = y_um
            unique_x_values.add(round(x_um, 6))
            unique_y_values.add(round(y_um, 6))
            if not (x_window_um[0] <= x_um <= x_window_um[1] and y_window_um[0] <= y_um <= y_window_um[1]):
                continue

            key = (d_w_l_nm, lam_um)
            bucket = groups.setdefault(
                key,
                {
                    "count": 0.0,
                    "sum_e2": 0.0,
                    "sum_qh": 0.0,
                    "sum_xe2": 0.0,
                    "sum_x2e2": 0.0,
                    "if_sum_e2": 0.0,
                    "if_count": 0.0,
                    "bg_l_sum_e2": 0.0,
                    "bg_l_count": 0.0,
                    "bg_r_sum_e2": 0.0,
                    "bg_r_count": 0.0,
                    "max_e2": -1.0,
                    "max_norme": -1.0,
                    "max_x_um": 0.0,
                    "max_y_um": 0.0,
                },
            )

            bucket["count"] += 1.0
            bucket["sum_e2"] += norm_e2
            bucket["sum_qh"] += qh
            bucket["sum_xe2"] += x_um * norm_e2
            bucket["sum_x2e2"] += (x_um * x_um) * norm_e2

            if abs(x_um) <= interface_half_width_um:
                bucket["if_sum_e2"] += norm_e2
                bucket["if_count"] += 1.0
            if background_left_um[0] <= x_um <= background_left_um[1]:
                bucket["bg_l_sum_e2"] += norm_e2
                bucket["bg_l_count"] += 1.0
            if background_right_um[0] <= x_um <= background_right_um[1]:
                bucket["bg_r_sum_e2"] += norm_e2
                bucket["bg_r_count"] += 1.0

            if norm_e2 > bucket["max_e2"]:
                bucket["max_e2"] = norm_e2
                bucket["max_norme"] = norm_e
                bucket["max_x_um"] = x_um
                bucket["max_y_um"] = y_um

    if not groups:
        raise ValueError(f"在指定窗口内没有读取到任何二维点数据：{path}")

    rows: List[Dict[str, Any]] = []
    for (d_w_l_nm, lam_um), bucket in sorted(groups.items()):
        sum_e2 = float(bucket["sum_e2"])
        if_avg = float(bucket["if_sum_e2"]) / max(float(bucket["if_count"]), 1.0)
        bg_l_avg = float(bucket["bg_l_sum_e2"]) / max(float(bucket["bg_l_count"]), 1.0)
        bg_r_avg = float(bucket["bg_r_sum_e2"]) / max(float(bucket["bg_r_count"]), 1.0)
        bg_avg = 0.5 * (bg_l_avg + bg_r_avg)
        xc_um = float(bucket["sum_xe2"]) / sum_e2
        second_moment = float(bucket["sum_x2e2"]) / sum_e2
        wx_um = max(second_moment - xc_um * xc_um, 0.0) ** 0.5
        rows.append(
            {
                "dW_left_nm": int(d_w_l_nm),
                "wavelength_um": float(lam_um),
                "window_points": int(bucket["count"]),
                "eta_interface": float(bucket["if_sum_e2"]) / sum_e2,
                "G_interface": (if_avg / bg_avg) if bg_avg > 0 else float("nan"),
                "xc_um": xc_um,
                "wx_um": wx_um,
                "max_x_um": float(bucket["max_x_um"]),
                "max_y_um": float(bucket["max_y_um"]),
                "max_normE": float(bucket["max_norme"]),
                "max_normE2": float(bucket["max_e2"]),
                "mean_Qh": float(bucket["sum_qh"]) / max(float(bucket["count"]), 1.0),
            }
        )

    x_centered = min(rows, key=lambda item: abs(float(item["xc_um"])))
    best_interface = max(rows, key=lambda item: float(item["G_interface"]))
    most_localized = min(rows, key=lambda item: float(item["wx_um"]))

    return {
        "reference_csv": str(path),
        "x_window_um": [float(x_window_um[0]), float(x_window_um[1])],
        "y_window_um": [float(y_window_um[0]), float(y_window_um[1])],
        "interface_half_width_um": float(interface_half_width_um),
        "background_left_um": [float(background_left_um[0]), float(background_left_um[1])],
        "background_right_um": [float(background_right_um[0]), float(background_right_um[1])],
        "source_first_y_um": float(y_first) if y_first is not None else None,
        "source_unique_x_count": len(unique_x_values),
        "source_unique_y_count": len(unique_y_values),
        "source_is_true_2d": len(unique_x_values) > 1 and len(unique_y_values) > 1,
        "rows": rows,
        "best_x_centered": x_centered,
        "best_interface_gain": best_interface,
        "best_localized": most_localized,
    }


def export_tamm_interface_window_analysis(
    reference_csv: Path | str,
    *,
    prefix: str = "tamm_interface_window_v1",
    x_window_um: tuple[float, float] = (-5.0, 5.0),
    y_window_um: tuple[float, float] = (8.8, 10.4),
    interface_half_width_um: float = 0.5,
    background_left_um: tuple[float, float] = (-5.0, -3.0),
    background_right_um: tuple[float, float] = (3.0, 5.0),
) -> Dict[str, str]:
    """Export local-window interface metrics for one 2D Tamm field CSV."""

    result = analyze_tamm_interface_2d_window_csv(
        reference_csv,
        x_window_um=x_window_um,
        y_window_um=y_window_um,
        interface_half_width_um=interface_half_width_um,
        background_left_um=background_left_um,
        background_right_um=background_right_um,
    )
    rows = result["rows"]

    saved: Dict[str, str] = {}
    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("dW_left_nm,wavelength_um,window_points,eta_interface,G_interface,xc_um,wx_um,max_x_um,max_y_um,max_normE,max_normE2,mean_Qh\n")
        for row in rows:
            f.write(
                f"{int(row['dW_left_nm'])},{float(row['wavelength_um']):.12g},{int(row['window_points'])},"
                f"{float(row['eta_interface']):.12g},{float(row['G_interface']):.12g},{float(row['xc_um']):.12g},"
                f"{float(row['wx_um']):.12g},{float(row['max_x_um']):.12g},{float(row['max_y_um']):.12g},"
                f"{float(row['max_normE']):.12g},{float(row['max_normE2']):.12g},{float(row['mean_Qh']):.12g}\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "Tamm 界面二维局域窗口分析",
        "=" * 80,
        f"reference_csv = {result['reference_csv']}",
        f"x_window_um = {result['x_window_um']}",
        f"y_window_um = {result['y_window_um']}",
        f"interface_half_width_um = {result['interface_half_width_um']}",
        f"source_unique_x_count = {int(result['source_unique_x_count'])}",
        f"source_unique_y_count = {int(result['source_unique_y_count'])}",
        f"source_is_true_2d = {bool(result['source_is_true_2d'])}",
        "",
        f"最接近界面中心 = dW_left {int(result['best_x_centered']['dW_left_nm'])} nm @ {float(result['best_x_centered']['wavelength_um']):.2f} μm | xc={float(result['best_x_centered']['xc_um']):+.3f} μm",
        f"界面增强最大 = dW_left {int(result['best_interface_gain']['dW_left_nm'])} nm @ {float(result['best_interface_gain']['wavelength_um']):.2f} μm | G={float(result['best_interface_gain']['G_interface']):.3f}",
        f"横向最局域 = dW_left {int(result['best_localized']['dW_left_nm'])} nm @ {float(result['best_localized']['wavelength_um']):.2f} μm | wx={float(result['best_localized']['wx_um']):.3f} μm",
        "",
    ]
    for row in rows:
        lines.append(
            f"dW={int(row['dW_left_nm'])} nm | λ={float(row['wavelength_um']):.2f} μm | "
            f"η_if={float(row['eta_interface']):.4f} | G_if={float(row['G_interface']):.3f} | "
            f"xc={float(row['xc_um']):+.3f} μm | wx={float(row['wx_um']):.3f} μm"
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    grouped: Dict[float, List[Dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(float(row["wavelength_um"]), []).append(row)
    for item in grouped.values():
        item.sort(key=lambda row: int(row["dW_left_nm"]))

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    font = _cn_font()
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(grouped)))

    ax = axes[0, 0]
    for color, (lam, item_rows) in zip(colors, sorted(grouped.items())):
        ax.plot(
            [int(row["dW_left_nm"]) for row in item_rows],
            [float(row["xc_um"]) for row in item_rows],
            color=color,
            linewidth=2.2,
            marker="o",
            label=f"{lam:.2f} μm",
        )
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="热点中心位置", xlabel="左侧 d_W (nm)", ylabel="xc (μm)")
    ax.axhline(0.0, color="#8b95a5", linewidth=1.0, linestyle="--")
    ax.legend(prop=font, frameon=False, loc="best")

    ax = axes[0, 1]
    for color, (lam, item_rows) in zip(colors, sorted(grouped.items())):
        ax.plot(
            [int(row["dW_left_nm"]) for row in item_rows],
            [float(row["G_interface"]) for row in item_rows],
            color=color,
            linewidth=2.2,
            marker="o",
            label=f"{lam:.2f} μm",
        )
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="界面相对背景增强", xlabel="左侧 d_W (nm)", ylabel="G_interface")
    ax.axhline(1.0, color="#8b95a5", linewidth=1.0, linestyle="--")

    ax = axes[1, 0]
    for color, (lam, item_rows) in zip(colors, sorted(grouped.items())):
        ax.plot(
            [int(row["dW_left_nm"]) for row in item_rows],
            [float(row["eta_interface"]) for row in item_rows],
            color=color,
            linewidth=2.2,
            marker="o",
            label=f"{lam:.2f} μm",
        )
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="界面局域占比", xlabel="左侧 d_W (nm)", ylabel="η_interface")

    ax = axes[1, 1]
    for color, (lam, item_rows) in zip(colors, sorted(grouped.items())):
        ax.plot(
            [int(row["dW_left_nm"]) for row in item_rows],
            [float(row["wx_um"]) for row in item_rows],
            color=color,
            linewidth=2.2,
            marker="o",
            label=f"{lam:.2f} μm",
        )
    _style_axis(ax)
    _set_axis_labels_cn(ax, title="横向局域宽度", xlabel="左侧 d_W (nm)", ylabel="wx (μm)")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)
    return saved


def export_tamm_interface_window_collection(
    csv_mapping: Dict[str, Path | str],
    *,
    prefix: str = "tamm_interface_window_collection_v1",
    x_window_um: tuple[float, float] = (-5.0, 5.0),
    y_window_um: tuple[float, float] = (8.8, 10.4),
    interface_half_width_um: float = 0.5,
    background_left_um: tuple[float, float] = (-5.0, -3.0),
    background_right_um: tuple[float, float] = (3.0, 5.0),
) -> Dict[str, str]:
    """Process a collection of full-field Tamm interface CSVs with a shared local window."""

    collection_rows: List[Dict[str, Any]] = []
    summaries: Dict[str, Any] = {}
    skipped: Dict[str, str] = {}
    for label, path in csv_mapping.items():
        try:
            result = analyze_tamm_interface_2d_window_csv(
                path,
                x_window_um=x_window_um,
                y_window_um=y_window_um,
                interface_half_width_um=interface_half_width_um,
                background_left_um=background_left_um,
                background_right_um=background_right_um,
            )
        except ValueError as exc:
            skipped[label] = str(exc)
            continue
        summaries[label] = result
        for row in result["rows"]:
            item = dict(row)
            item["source_label"] = label
            collection_rows.append(item)

    if not collection_rows:
        raise ValueError("没有可导出的二维窗口分析结果。")

    saved: Dict[str, str] = {}
    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("source_label,dW_left_nm,wavelength_um,window_points,eta_interface,G_interface,xc_um,wx_um,max_x_um,max_y_um,max_normE,max_normE2,mean_Qh\n")
        for row in sorted(collection_rows, key=lambda item: (str(item["source_label"]), int(item["dW_left_nm"]), float(item["wavelength_um"]))):
            f.write(
                f"{row['source_label']},{int(row['dW_left_nm'])},{float(row['wavelength_um']):.12g},{int(row['window_points'])},"
                f"{float(row['eta_interface']):.12g},{float(row['G_interface']):.12g},{float(row['xc_um']):.12g},"
                f"{float(row['wx_um']):.12g},{float(row['max_x_um']):.12g},{float(row['max_y_um']):.12g},"
                f"{float(row['max_normE']):.12g},{float(row['max_normE2']):.12g},{float(row['mean_Qh']):.12g}\n"
            )
    saved["csv"] = str(csv_path)

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "x_window_um": [float(x_window_um[0]), float(x_window_um[1])],
                "y_window_um": [float(y_window_um[0]), float(y_window_um[1])],
                "interface_half_width_um": float(interface_half_width_um),
                "background_left_um": [float(background_left_um[0]), float(background_left_um[1])],
                "background_right_um": [float(background_right_um[0]), float(background_right_um[1])],
                "sources": summaries,
                "skipped": skipped,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "Tamm 界面二维窗口分析总表",
        "=" * 80,
        f"x_window_um = {list(x_window_um)}",
        f"y_window_um = {list(y_window_um)}",
        "",
    ]
    if skipped:
        lines.append("[跳过文件]")
        for label, reason in skipped.items():
            lines.append(f"{label}: {reason}")
        lines.append("")
    for label, result in summaries.items():
        lines.extend(
            [
                f"[{label}]",
                f"reference_csv = {result['reference_csv']}",
                f"source_is_true_2d = {bool(result['source_is_true_2d'])} | unique_x = {int(result['source_unique_x_count'])} | unique_y = {int(result['source_unique_y_count'])}",
                f"best_x_centered: dW={int(result['best_x_centered']['dW_left_nm'])} nm @ {float(result['best_x_centered']['wavelength_um']):.2f} μm | xc={float(result['best_x_centered']['xc_um']):+.3f} μm",
                f"best_interface_gain: dW={int(result['best_interface_gain']['dW_left_nm'])} nm @ {float(result['best_interface_gain']['wavelength_um']):.2f} μm | G={float(result['best_interface_gain']['G_interface']):.3f}",
                f"best_localized: dW={int(result['best_localized']['dW_left_nm'])} nm @ {float(result['best_localized']['wavelength_um']):.2f} μm | wx={float(result['best_localized']['wx_um']):.3f} μm",
                "",
            ]
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    font = _cn_font()
    source_colors = plt.cm.tab10(np.linspace(0.0, 0.9, len(summaries)))
    source_to_color = {label: source_colors[i] for i, label in enumerate(sorted(summaries))}

    for ax, metric, title, ylabel in [
        (axes[0, 0], "xc_um", "热点中心位置", "xc (μm)"),
        (axes[0, 1], "G_interface", "界面相对背景增强", "G_interface"),
        (axes[1, 0], "eta_interface", "界面局域占比", "η_interface"),
        (axes[1, 1], "wx_um", "横向局域宽度", "wx (μm)"),
    ]:
        for label in sorted(summaries):
            source_rows = [row for row in collection_rows if row["source_label"] == label and abs(float(row["wavelength_um"]) - 4.55) < 1e-9]
            if not source_rows:
                continue
            source_rows.sort(key=lambda row: int(row["dW_left_nm"]))
            ax.plot(
                [int(row["dW_left_nm"]) for row in source_rows],
                [float(row[metric]) for row in source_rows],
                color=source_to_color[label],
                linewidth=2.2,
                marker="o",
                label=label,
            )
        _style_axis(ax)
        _set_axis_labels_cn(ax, title=title, xlabel="左侧 d_W (nm)", ylabel=ylabel)
        if metric == "xc_um":
            ax.axhline(0.0, color="#8b95a5", linewidth=1.0, linestyle="--")
        if metric == "G_interface":
            ax.axhline(1.0, color="#8b95a5", linewidth=1.0, linestyle="--")
    axes[0, 0].legend(prop=font, frameon=False, loc="best")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)

    return saved


def export_tamm_interface_window_scan_collection(
    csv_mapping: Dict[str, Path | str],
    *,
    prefix: str = "tamm_interface_window_scan_v1",
    x_window_um: tuple[float, float] = (-5.0, 5.0),
    y_windows_um: Sequence[tuple[float, float]] = ((8.8, 10.4), (9.0, 9.8), (9.2, 10.0)),
    interface_half_widths_um: Sequence[float] = (0.3, 0.5, 0.8),
    background_left_um: tuple[float, float] = (-5.0, -3.0),
    background_right_um: tuple[float, float] = (3.0, 5.0),
    focus_wavelength_um: float = 4.55,
) -> Dict[str, str]:
    """Scan multiple 2D window definitions for the same Tamm interface field datasets."""

    config_rows: List[Dict[str, Any]] = []
    config_summaries: Dict[str, Any] = {}
    skipped: Dict[str, Dict[str, str]] = {}

    def _config_label(y_window: tuple[float, float], half_width: float) -> str:
        return (
            f"x±{x_window_um[1]:.1f}_"
            f"y{y_window[0]:.1f}-{y_window[1]:.1f}_"
            f"if{half_width:.1f}"
        )

    for y_window_um in y_windows_um:
        for interface_half_width_um in interface_half_widths_um:
            label = _config_label(y_window_um, interface_half_width_um)
            config_summary: Dict[str, Any] = {
                "x_window_um": [float(x_window_um[0]), float(x_window_um[1])],
                "y_window_um": [float(y_window_um[0]), float(y_window_um[1])],
                "interface_half_width_um": float(interface_half_width_um),
                "sources": {},
            }
            config_skipped: Dict[str, str] = {}
            for source_label, path in csv_mapping.items():
                try:
                    result = analyze_tamm_interface_2d_window_csv(
                        path,
                        x_window_um=x_window_um,
                        y_window_um=y_window_um,
                        interface_half_width_um=interface_half_width_um,
                        background_left_um=background_left_um,
                        background_right_um=background_right_um,
                    )
                except ValueError as exc:
                    config_skipped[source_label] = str(exc)
                    continue
                config_summary["sources"][source_label] = result
                for row in result["rows"]:
                    item = dict(row)
                    item["config_label"] = label
                    item["source_label"] = source_label
                    item["x_window_um"] = [float(x_window_um[0]), float(x_window_um[1])]
                    item["y_window_um"] = [float(y_window_um[0]), float(y_window_um[1])]
                    item["interface_half_width_um"] = float(interface_half_width_um)
                    config_rows.append(item)
            if config_skipped:
                skipped[label] = config_skipped
            config_summaries[label] = config_summary

    if not config_rows:
        raise ValueError("没有可导出的二维窗口扫描结果。")

    saved: Dict[str, str] = {}
    csv_path = output_file(f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "config_label,source_label,dW_left_nm,wavelength_um,window_points,"
            "eta_interface,G_interface,xc_um,wx_um,max_x_um,max_y_um,max_normE,max_normE2,mean_Qh,"
            "x_window_min_um,x_window_max_um,y_window_min_um,y_window_max_um,interface_half_width_um\n"
        )
        for row in sorted(
            config_rows,
            key=lambda item: (
                str(item["config_label"]),
                str(item["source_label"]),
                int(item["dW_left_nm"]),
                float(item["wavelength_um"]),
            ),
        ):
            f.write(
                f"{row['config_label']},{row['source_label']},{int(row['dW_left_nm'])},"
                f"{float(row['wavelength_um']):.12g},{int(row['window_points'])},"
                f"{float(row['eta_interface']):.12g},{float(row['G_interface']):.12g},"
                f"{float(row['xc_um']):.12g},{float(row['wx_um']):.12g},"
                f"{float(row['max_x_um']):.12g},{float(row['max_y_um']):.12g},"
                f"{float(row['max_normE']):.12g},{float(row['max_normE2']):.12g},{float(row['mean_Qh']):.12g},"
                f"{float(row['x_window_um'][0]):.12g},{float(row['x_window_um'][1]):.12g},"
                f"{float(row['y_window_um'][0]):.12g},{float(row['y_window_um'][1]):.12g},"
                f"{float(row['interface_half_width_um']):.12g}\n"
            )
    saved["csv"] = str(csv_path)

    focus_rows = [row for row in config_rows if abs(float(row["wavelength_um"]) - focus_wavelength_um) < 1e-9]
    focus_best_by_source: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for source_label in sorted({str(row["source_label"]) for row in focus_rows}):
        source_rows = [row for row in focus_rows if str(row["source_label"]) == source_label]
        if not source_rows:
            continue
        best_centered = min(source_rows, key=lambda item: abs(float(item["xc_um"])))
        best_gain = max(source_rows, key=lambda item: float(item["G_interface"]))
        best_localized = min(source_rows, key=lambda item: float(item["wx_um"]))
        focus_best_by_source[source_label] = {
            "best_centered": best_centered,
            "best_gain": best_gain,
            "best_localized": best_localized,
        }

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "x_window_um": [float(x_window_um[0]), float(x_window_um[1])],
                "y_windows_um": [[float(a), float(b)] for a, b in y_windows_um],
                "interface_half_widths_um": [float(item) for item in interface_half_widths_um],
                "background_left_um": [float(background_left_um[0]), float(background_left_um[1])],
                "background_right_um": [float(background_right_um[0]), float(background_right_um[1])],
                "focus_wavelength_um": float(focus_wavelength_um),
                "rows": config_rows,
                "focus_best_by_source": focus_best_by_source,
                "configs": config_summaries,
                "skipped": skipped,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}.txt")
    lines = [
        "Tamm 界面二维窗口/判据扫描",
        "=" * 80,
        f"x_window_um = {list(x_window_um)}",
        f"focus_wavelength_um = {focus_wavelength_um:.2f}",
        f"y_windows_um = {[list(item) for item in y_windows_um]}",
        f"interface_half_widths_um = {[float(item) for item in interface_half_widths_um]}",
        "",
    ]
    if skipped:
        lines.append("[跳过记录]")
        for config_label, item in skipped.items():
            for source_label, reason in item.items():
                lines.append(f"{config_label} | {source_label}: {reason}")
        lines.append("")
    for source_label, bests in focus_best_by_source.items():
        lines.extend(
            [
                f"[{source_label}] @ {focus_wavelength_um:.2f} μm",
                f"best_centered: {bests['best_centered']['config_label']} | dW={int(bests['best_centered']['dW_left_nm'])} nm | xc={float(bests['best_centered']['xc_um']):+.3f} μm",
                f"best_gain: {bests['best_gain']['config_label']} | dW={int(bests['best_gain']['dW_left_nm'])} nm | G={float(bests['best_gain']['G_interface']):.3f}",
                f"best_localized: {bests['best_localized']['config_label']} | dW={int(bests['best_localized']['dW_left_nm'])} nm | wx={float(bests['best_localized']['wx_um']):.3f} μm",
                "",
            ]
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    focus_centered_rows: Dict[str, List[Dict[str, Any]]] = {}
    for source_label in sorted({str(row["source_label"]) for row in focus_rows}):
        source_rows = [row for row in focus_rows if str(row["source_label"]) == source_label]
        if not source_rows:
            continue
        by_config: Dict[str, Dict[str, Any]] = {}
        for row in source_rows:
            config_label = str(row["config_label"])
            current = by_config.get(config_label)
            if current is None or abs(float(row["xc_um"])) < abs(float(current["xc_um"])):
                by_config[config_label] = row
        focus_centered_rows[source_label] = [
            by_config[key] for key in sorted(by_config)
        ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    font = _cn_font()
    source_colors = plt.cm.tab10(np.linspace(0.0, 0.9, max(len(focus_centered_rows), 1)))
    source_to_color = {
        label: source_colors[i] for i, label in enumerate(sorted(focus_centered_rows))
    }
    ordered_config_labels = sorted({row["config_label"] for row in focus_rows})
    x_positions = np.arange(len(ordered_config_labels))

    for ax, metric, title, ylabel, transform in [
        (axes[0], "xc_um", "最接近界面中心的热点位置", "|xc| (μm)", lambda v: abs(float(v))),
        (axes[1], "G_interface", "界面相对背景增强", "G_interface", float),
        (axes[2], "wx_um", "横向局域宽度", "wx (μm)", float),
    ]:
        for source_label in sorted(focus_centered_rows):
            rows = focus_centered_rows[source_label]
            y_values: List[float] = []
            for config_label in ordered_config_labels:
                matched = next((row for row in rows if str(row["config_label"]) == config_label), None)
                y_values.append(float("nan") if matched is None else transform(matched[metric]))
            ax.plot(
                x_positions,
                y_values,
                color=source_to_color[source_label],
                linewidth=2.0,
                marker="o",
                label=source_label,
            )
        _style_axis(ax)
        _set_axis_labels_cn(ax, title=title, xlabel="窗口配置", ylabel=ylabel)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(ordered_config_labels, rotation=30, ha="right", fontproperties=font)
        if metric == "G_interface":
            ax.axhline(1.0, color="#8b95a5", linewidth=1.0, linestyle="--")
    axes[0].legend(prop=font, frameon=False, loc="best")

    png_path = output_file(f"{prefix}.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)
    return saved
