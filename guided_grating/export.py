from __future__ import annotations

import json
from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np

from thinfilm.paths import output_file
from thinfilm.plot_logic import focused_power_limits, rta_trace_styles
from thinfilm.plotting import save_publication_figure
from thinfilm.figure_audit import audit_rta_data, build_figure_audit, write_figure_audit
from thinfilm._shared import (
    MAIN_RED,
    TARGET_GREEN,
    TRANS_BLUE,
    ABS_GOLD,
    GRID_COLOR,
    TEXT_DARK,
    PANEL_BG,
    apply_font_defaults,
    style_axis,
)

apply_font_defaults()

from .spectra import summarize_guided_grating_spectrum


def _analysis_lines(summary: Dict[str, Any], target_wavelength_nm: float | None) -> list[str]:
    lines = [
        f"峰位 = {summary['peak_wavelength_nm']:.3f} nm",
        f"峰值反射率 = {summary['peak_reflectance']:.6f}",
        f"半高全宽 = {summary['fwhm_nm']:.3f} nm",
    ]
    if target_wavelength_nm is not None:
        delta = float(summary["peak_wavelength_nm"]) - float(target_wavelength_nm)
        lines.append(f"目标波长 = {float(target_wavelength_nm):.3f} nm")
        lines.append(f"偏差 = {delta:+.3f} nm")
    return lines


def export_guided_grating_result(
    result: Dict[str, Any],
    prefix: str = "guided_grating_demo",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
    target_wavelength_nm: float | None = None,
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    sample_id = str(result.get("sample_id") or "guided_grating_case")
    stem = f"{prefix}_{sample_id}"

    wl = np.asarray(result["wavelength_nm"], dtype=float)
    r_vals = np.asarray(result["R"], dtype=float)
    t_vals = np.asarray(result["T"], dtype=float)
    a_vals = np.asarray(result["A"], dtype=float)
    summary = summarize_guided_grating_spectrum(result)

    evidence_level = "placeholder" if bool(result.get("is_placeholder", False)) else "approximation"
    figure_audit = build_figure_audit(
        figure_id=f"{stem}_main",
        title=f"光栅波导反射率 | {sample_id}",
        evidence_level=evidence_level,
        checks=[audit_rta_data(
            wl, r_vals, t_vals, a_vals,
            focus="R", feature_kind="peak",
            feature_wavelength=float(summary["peak_wavelength_nm"]),
            conservation_tolerance=1e-5,
        )],
    )
    audit_path = output_file(f"{stem}_figure_audit.json")
    saved["audit_json"] = write_figure_audit(audit_path, figure_audit)

    if save_csv:
        csv_path = output_file(f"{stem}_spectrum.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write("wavelength_nm,R,T,A\n")
            for row in zip(wl, r_vals, t_vals, a_vals):
                f.write(",".join(f"{float(x):.12g}" for x in row) + "\n")
        saved["csv"] = str(csv_path)

    if save_json:
        json_path = output_file(f"{stem}_summary.json")
        payload = {
            "sample_id": sample_id,
            "model_type": result.get("model_type"),
            "warning": result.get("warning"),
            "spec": result.get("spec", {}),
            "summary": summary,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        saved["json"] = str(json_path)

    if save_txt:
        txt_path = output_file(f"{stem}_summary.txt")
        lines = [
            "Guided Grating Branch Summary",
            "=" * 80,
            f"sample_id              = {sample_id}",
            f"backend                = {result.get('backend')}",
            f"is_placeholder         = {bool(result.get('is_placeholder', False))}",
            f"peak_reflectance       = {summary['peak_reflectance']:.6f}",
            f"peak_wavelength_nm     = {summary['peak_wavelength_nm']:.6f}",
            f"fwhm_nm                = {summary['fwhm_nm']:.6f}",
            f"min_reflectance        = {summary['min_reflectance']:.6f}",
            f"max_transmittance      = {summary['max_transmittance']:.6f}",
            f"max_absorptance        = {summary['max_absorptance']:.6f}",
            f"warning                = {result.get('warning', '')}",
        ]
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        saved["txt"] = str(txt_path)

    if save_plot:
        png_path = output_file(f"{stem}_RTA.png")
        fig, ax = plt.subplots(figsize=(8, 5))
        style_axis(ax)
        curves = {"R": r_vals, "T": t_vals, "A": a_vals}
        colors = {"R": MAIN_RED, "T": TRANS_BLUE, "A": ABS_GOLD}
        line_styles = {"solid": "-", "dash": "--", "dot": ":"}
        trace_styles = rta_trace_styles("R", curves)
        for kind in ("R", "T", "A"):
            style = trace_styles[kind]
            ax.plot(
                wl,
                curves[kind],
                label=kind,
                linewidth=float(style["linewidth"]),
                alpha=float(style["alpha"]),
                linestyle=line_styles[str(style["dash"])],
                color=colors[kind],
                zorder=3 if kind == "R" else 2,
            )
        ax.axvline(summary["peak_wavelength_nm"], linestyle="--", linewidth=1.3, color="#555555", alpha=0.85, label="峰位")
        if target_wavelength_nm is not None:
            ax.axvline(float(target_wavelength_nm), linestyle=":", linewidth=1.5, color=TARGET_GREEN, alpha=0.95, label="目标波长")
        ax.set_title(f"光栅波导谱线 | {sample_id}", fontweight="semibold")
        ax.set_xlabel("波长 (nm)")
        ax.set_ylabel("反射率 / 透射率 / 吸收率")
        ax.set_xlim(float(wl[0]), float(wl[-1]))
        ax.set_ylim(0.0, 1.02)
        ax.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="#c9d2dc")
        ax.text(
            0.985,
            0.97,
            "\n".join(_analysis_lines(summary, target_wavelength_nm)),
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.85, "edgecolor": "#cccccc"},
        )
        fig.tight_layout()
        save_publication_figure(fig, png_path)
        plt.close(fig)
        saved["png"] = str(png_path)

        main_png = output_file(f"{stem}_main.png")
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        style_axis(ax2)
        ax2.plot(wl, r_vals, linewidth=2.8, color=MAIN_RED)
        ax2.fill_between(wl, r_vals, color=MAIN_RED, alpha=0.10)
        ax2.axvline(summary["peak_wavelength_nm"], linestyle="--", linewidth=1.3, color="#555555", alpha=0.85)
        if target_wavelength_nm is not None:
            ax2.axvline(float(target_wavelength_nm), linestyle=":", linewidth=1.5, color=TARGET_GREEN, alpha=0.95)
        if summary["fwhm_nm"] > 0.0:
            half_width = 0.5 * float(summary["fwhm_nm"])
            peak_wl = float(summary["peak_wavelength_nm"])
            ax2.axvspan(
                peak_wl - half_width,
                peak_wl + half_width,
                color="#94a3b8",
                alpha=0.12,
                linewidth=0,
            )
        ymin, ymax = focused_power_limits(r_vals)
        ax2.scatter(
            [summary["peak_wavelength_nm"]],
            [summary["peak_reflectance"]],
            color=MAIN_RED,
            edgecolor="white",
            linewidth=1.0,
            s=42,
            zorder=5,
        )
        ax2.set_title("光栅波导反射率", fontweight="semibold")
        ax2.set_xlabel("波长 (nm)")
        ax2.set_ylabel("R")
        ax2.set_xlim(float(wl[0]), float(wl[-1]))
        ax2.set_ylim(ymin, ymax)
        ax2.text(
            0.985,
            0.97,
            "\n".join(_analysis_lines(summary, target_wavelength_nm)),
            transform=ax2.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.85, "edgecolor": "#cccccc"},
        )
        fig2.tight_layout()
        save_publication_figure(fig2, main_png)
        plt.close(fig2)
        saved["main_png"] = str(main_png)

    return saved

def export_guided_grating_sweep_summary(
    bundle_summary: Dict[str, Any],
    prefix: str = "guided_grating_sweep",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, str]:
    saved: Dict[str, str] = {}
    stem = f"{prefix}_{bundle_summary.get('sample_id', 'bundle')}"
    period_rows = list(bundle_summary.get("period_summaries", []))
    best = bundle_summary.get("best_candidate", {})
    sweep_name = str(bundle_summary.get("sweep_name", "period"))
    sweep_display_unit = str(bundle_summary.get("sweep_display_unit", "nm"))
    sweep_col = f"{sweep_name}_{sweep_display_unit}"

    if save_csv:
        csv_path = output_file(f"{stem}_period_summary.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write(
                f"{sweep_col},peak_wavelength_nm,peak_reflectance,fwhm_nm,"
                "target_wavelength_nm,target_error_nm,min_reflectance,max_transmittance\n"
            )
            for row in period_rows:
                f.write(
                    ",".join(
                        [
                            f"{float(row['period_nm']):.12g}",
                            f"{float(row['peak_wavelength_nm']):.12g}",
                            f"{float(row['peak_reflectance']):.12g}",
                            f"{float(row['fwhm_nm']):.12g}",
                            f"{float(bundle_summary['target_wavelength_nm']):.12g}",
                            f"{float(row['target_error_nm']):.12g}",
                            f"{float(row['min_reflectance']):.12g}",
                            f"{float(row['max_transmittance']):.12g}",
                        ]
                    )
                    + "\n"
                )
        saved["csv"] = str(csv_path)

    if save_json:
        json_path = output_file(f"{stem}_summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(bundle_summary, f, ensure_ascii=False, indent=2)
        saved["json"] = str(json_path)

    if save_txt:
        txt_path = output_file(f"{stem}_summary.txt")
        lines = [
            "Guided Grating Lambda-Period Sweep Summary",
            "=" * 80,
            f"sample_id              = {bundle_summary.get('sample_id', '')}",
            f"source_csv             = {bundle_summary.get('source_csv', '')}",
            f"sweep_name             = {sweep_name}",
            f"target_wavelength_nm   = {bundle_summary.get('target_wavelength_nm', 0.0):.6f}",
            f"num_periods            = {bundle_summary.get('num_periods', 0)}",
            f"has_duplicate_block    = {bundle_summary.get('has_duplicate_block', False)}",
            "",
            "Best candidate",
            "-" * 80,
            f"{sweep_col:<22} = {float(best.get('period_nm', 0.0)):.6f}",
            f"peak_wavelength_nm     = {float(best.get('peak_wavelength_nm', 0.0)):.6f}",
            f"peak_reflectance       = {float(best.get('peak_reflectance', 0.0)):.6f}",
            f"fwhm_nm                = {float(best.get('fwhm_nm', 0.0)):.6f}",
            f"target_error_nm        = {float(best.get('target_error_nm', 0.0)):.6f}",
        ]
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        saved["txt"] = str(txt_path)

    if save_plot and period_rows:
        analysis_png = output_file(f"{stem}_error_analysis.png")
        x_vals = np.asarray([float(row["period_nm"]) for row in period_rows], dtype=float)
        peak_vals = np.asarray([float(row["peak_wavelength_nm"]) for row in period_rows], dtype=float)
        error_vals = np.asarray([float(row["target_error_nm"]) for row in period_rows], dtype=float)
        fwhm_vals = np.asarray([float(row["fwhm_nm"]) for row in period_rows], dtype=float)
        rpeak_vals = np.asarray([float(row["peak_reflectance"]) for row in period_rows], dtype=float)
        best_x = float(best.get("period_nm", x_vals[0]))

        fig = plt.figure(figsize=(7.2, 4.6), constrained_layout=True)
        gs = fig.add_gridspec(2, 3, width_ratios=[1.25, 1.25, 1.0])
        ax1 = fig.add_subplot(gs[:, :2])
        ax2 = fig.add_subplot(gs[0, 2])
        ax3 = fig.add_subplot(gs[1, 2])

        for ax in (ax1, ax2, ax3):
            style_axis(ax)
            ax.axvline(best_x, linestyle=":", color="#64748b", linewidth=1.2, alpha=0.75)

        ax1.plot(x_vals, peak_vals, marker="o", linewidth=2.2, color=MAIN_RED)
        ax1.scatter([best_x], [float(best.get("peak_wavelength_nm", peak_vals[0]))], color=MAIN_RED, edgecolor="white", s=50, zorder=5)
        ax1.axhline(float(bundle_summary["target_wavelength_nm"]), linestyle=":", color=TARGET_GREEN, linewidth=1.4)
        ax1.set_title("峰位波长")
        ax1.set_xlabel(sweep_col)
        ax1.set_ylabel("nm")

        ax2.plot(x_vals, error_vals, marker="o", linewidth=2.2, color=TRANS_BLUE)
        ax2.scatter([best_x], [float(best.get("target_error_nm", error_vals[0]))], color=TRANS_BLUE, edgecolor="white", s=50, zorder=5)
        ax2.set_title("目标误差")
        ax2.set_xlabel(sweep_col)
        ax2.set_ylabel("nm")

        ax3.plot(x_vals, fwhm_vals, marker="o", linewidth=2.2, color=ABS_GOLD)
        ax3.scatter([best_x], [float(best.get("fwhm_nm", fwhm_vals[0]))], color=ABS_GOLD, edgecolor="white", s=50, zorder=5)
        ax3.set_title("半高全宽")
        ax3.set_xlabel(sweep_col)
        ax3.set_ylabel("nm")

        fig.suptitle("光栅近似扫描：目标峰位与稳健性", fontsize=10, fontweight="semibold", color=TEXT_DARK)
        save_publication_figure(fig, analysis_png)
        plt.close(fig)
        saved["analysis_png"] = str(analysis_png)

    return saved
