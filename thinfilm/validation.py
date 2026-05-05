from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import matplotlib.pyplot as plt
import numpy as np

from .education import simulate_report_case
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
    ref_spec = load_spectrum_csv(Path(reference_csv), y_selector=y_selector)

    active_quantity = _pick_quantity(case_id, ref_spec.y_kind, quantity)
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
            "quantity": result["quantity"],
            "reference_label": result["reference_label"],
            "reference_csv": result["reference_csv"],
            "summary": summary,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        saved["json"] = str(json_path)

    if save_txt:
        txt_path = output_file(f"{stem}_summary.txt")
        lines = [
            "Teaching Validation Summary",
            "=" * 80,
            f"case_id              = {result['case_id']}",
            f"title_cn             = {result['title_cn']}",
            f"quantity             = {result['quantity']}",
            f"reference_label      = {result['reference_label']}",
            f"reference_csv        = {result['reference_csv']}",
            f"lambda0_nm           = {float(result['lambda0_nm']):.6f}",
            f"mae                  = {float(summary['mae']):.12e}",
            f"rmse                 = {float(summary['rmse']):.12e}",
            f"max_abs_error        = {float(summary['max_abs_error']):.12e}",
            f"mean_bias            = {float(summary['mean_bias']):.12e}",
            f"lambda0_error        = {float(summary['lambda0_error']):.12e}",
        ]
        with open(txt_path, "w", encoding="utf-8") as f:
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
        f.write("case_id,quantity,reference_label,mae,rmse,max_abs_error,mean_bias,lambda0_error\n")
        for item in rows:
            s = item["summary"]
            f.write(
                ",".join(
                    [
                        str(item["case_id"]),
                        str(item["quantity"]),
                        str(item["reference_label"]),
                        f"{float(s['mae']):.12g}",
                        f"{float(s['rmse']):.12g}",
                        f"{float(s['max_abs_error']):.12g}",
                        f"{float(s['mean_bias']):.12g}",
                        f"{float(s['lambda0_error']):.12g}",
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
            "quantity": item["quantity"],
            "reference_label": item["reference_label"],
            "summary": item["summary"],
        }
        for item in rows
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

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
