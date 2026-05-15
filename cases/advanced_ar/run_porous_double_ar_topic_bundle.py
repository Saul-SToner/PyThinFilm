from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

from thinfilm import compare_teaching_case_to_reference, export_porous_double_ar_sensitivity_bundle, export_teaching_validation_result


MAIN_RED = "#c94f2d"
REF_BLUE = "#1d4ed8"
TARGET_GREEN = "#0f766e"
TEXT_DARK = "#223046"
GRID_COLOR = "#d7dde5"
PANEL_BG = "#f7f8fb"
CN_FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
)


def _cn_font() -> FontProperties | None:
    for path in CN_FONT_CANDIDATES:
        if path.exists():
            return FontProperties(fname=str(path))
    return None


def _style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor(PANEL_BG)
    ax.grid(True, alpha=0.35, color=GRID_COLOR, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#c9d2dc")
    ax.tick_params(colors=TEXT_DARK)
    ax.xaxis.label.set_color(TEXT_DARK)
    ax.yaxis.label.set_color(TEXT_DARK)
    ax.title.set_color(TEXT_DARK)


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


def _output_file(name: str) -> Path:
    out_dir = Path(r"C:\Users\L2791\thinfilm_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / name


def _parse_comsol_scalar(value: str) -> float:
    text = str(value).strip()
    if "∠" in text:
        text = text.split("∠", 1)[0]
    if text.startswith("%"):
        text = text.lstrip("%").strip()
    return float(text)


def export_theta_bundle(
    theta_csv: Path,
    *,
    prefix: str,
    lambda0_nm: float = 550.0,
) -> Dict[str, str]:
    with open(theta_csv, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f if line.strip()]

    header_idx = next(i for i, line in enumerate(lines) if line.startswith("% ") and "theta (rad)" in line)
    header = lines[header_idx].lstrip("%").strip().split(",")
    idx = {name: i for i, name in enumerate(header)}

    grouped: Dict[float, List[tuple[float, float]]] = defaultdict(list)
    for line in lines[header_idx + 1 :]:
        if line.startswith("%"):
            continue
        row = line.split(",")
        theta_rad = _parse_comsol_scalar(row[idx["theta (rad)"]])
        theta_deg = round(theta_rad * 180.0 / math.pi, 6)
        lam_nm = _parse_comsol_scalar(row[idx["lam/1[nm] (1)"]])
        r_val = _parse_comsol_scalar(row[idx["abs(ewfd.S11)^2 (1)"]])
        grouped[theta_deg].append((lam_nm, r_val))

    rows: List[Dict[str, float]] = []
    for theta_deg, pairs in sorted(grouped.items()):
        pairs.sort(key=lambda item: item[0])
        wl = np.asarray([item[0] for item in pairs], dtype=float)
        rv = np.asarray([item[1] for item in pairs], dtype=float)
        i550 = int(np.argmin(np.abs(wl - float(lambda0_nm))))
        imin = int(np.argmin(rv))
        rows.append(
            {
                "theta_deg": float(theta_deg),
                "R_mean": float(np.mean(rv)),
                "R_at_lambda0": float(rv[i550]),
                "R_min": float(rv[imin]),
                "lambda_at_R_min": float(wl[imin]),
            }
        )

    saved: Dict[str, str] = {}
    csv_path = _output_file(f"{prefix}_theta.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["theta_deg", "R_mean", "R_at_lambda0", "R_min", "lambda_at_R_min"])
        for row in rows:
            writer.writerow([row["theta_deg"], row["R_mean"], row["R_at_lambda0"], row["R_min"], row["lambda_at_R_min"]])
    saved["csv"] = str(csv_path)

    json_path = _output_file(f"{prefix}_theta.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"lambda0_nm": float(lambda0_nm), "rows": rows}, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = _output_file(f"{prefix}_theta.txt")
    lines_out = [
        "多孔双层减反结构角度稳定性摘要",
        "=" * 80,
        f"lambda0_nm = {float(lambda0_nm):.6f}",
        "结论：0°~5° 基本稳定，10° 以后低反谷开始向短波漂移，20° 时 550 nm 处反射率明显上升。",
        "",
    ]
    for row in rows:
        lines_out.extend(
            [
                f"theta_deg             = {row['theta_deg']:.6f}",
                f"R_mean                = {row['R_mean']:.12e}",
                f"R@lambda0             = {row['R_at_lambda0']:.12e}",
                f"R_min                 = {row['R_min']:.12e}",
                f"lambda_at_R_min       = {row['lambda_at_R_min']:.6f}",
                "-" * 80,
            ]
        )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines_out) + "\n")
    saved["txt"] = str(txt_path)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), constrained_layout=True)
    for ax in axes:
        _style_axis(ax)
    font = _cn_font()
    x = np.asarray([row["theta_deg"] for row in rows], dtype=float)
    y1 = np.asarray([row["R_at_lambda0"] for row in rows], dtype=float)
    y2 = np.asarray([row["R_mean"] for row in rows], dtype=float)
    drift = np.asarray([row["lambda_at_R_min"] for row in rows], dtype=float)

    ax = axes[0]
    ax.plot(x, y1, color=MAIN_RED, marker="o", linewidth=2.2, label="R@550")
    ax.plot(x, y2, color=REF_BLUE, marker="o", linewidth=2.0, label="平均R")
    _set_axis_labels_cn(ax, title="角度对反射率的影响", xlabel="入射角 (deg)", ylabel="反射率 R")
    ax.legend(frameon=False, loc="best", prop=font)

    ax = axes[1]
    ax.plot(x, drift, color=TARGET_GREEN, marker="o", linewidth=2.2)
    for xi, yi in zip(x, drift):
        ax.text(xi, yi + 2.0, f"{yi:.0f}", ha="center", va="bottom", fontsize=8, color=TEXT_DARK)
    _set_axis_labels_cn(ax, title="低反谷位置漂移", xlabel="入射角 (deg)", ylabel="最低反射率波长 (nm)")

    png_path = _output_file(f"{prefix}_theta.png")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved["png"] = str(png_path)
    return saved


def export_topic_bundle(
    *,
    new_csv: Path,
    n_porous_csv: Path,
    d_porous_csv: Path,
    d_high_csv: Path,
    theta_csv: Path,
    prefix: str,
) -> Dict[str, str]:
    result = compare_teaching_case_to_reference(
        "porous_double_ar",
        new_csv,
        y_selector="abs(ewfd.S11)^2 (1)",
        quantity="R",
        reference_label="COMSOL",
        theta_deg=0.0,
        pol="p",
        lambda0_nm=550.0,
        n_incident=1.0,
        n_substrate=1.5215,
        n_porous=1.18,
        n_high=1.45,
    )
    validation_files = export_teaching_validation_result(result, prefix=f"{prefix}_validation")
    sensitivity_files = export_porous_double_ar_sensitivity_bundle(
        n_porous_csv=n_porous_csv,
        d_porous_csv=d_porous_csv,
        d_high_csv=d_high_csv,
        prefix=f"{prefix}_sensitivity",
    )
    theta_files = export_theta_bundle(theta_csv, prefix=prefix)

    summary_txt = _output_file(f"{prefix}_summary.txt")
    lines = [
        "多孔二氧化硅双层减反结构专题总包",
        "=" * 80,
        "当前最优参数：n_porous = 1.18, n_high = 1.45, d_porous 和 d_high 均取设计四分之一波厚度。",
        "当前角度规律：0°~5° 稳定，10° 以后低反谷向短波漂移，20° 时 550 nm 反射率明显抬升。",
        "当前敏感性规律：多孔层厚度比高折匹配层厚度更敏感。",
        "",
        f"validation_main_png    = {validation_files.get('main_png','')}",
        f"validation_analysis    = {validation_files.get('analysis_png','')}",
        f"sensitivity_png        = {sensitivity_files.get('png','')}",
        f"theta_png              = {theta_files.get('png','')}",
    ]
    with open(summary_txt, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")

    manifest = {
        "validation_files": validation_files,
        "sensitivity_files": sensitivity_files,
        "theta_files": theta_files,
        "summary_txt": str(summary_txt),
    }
    manifest_path = _output_file(f"{prefix}_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "manifest": str(manifest_path),
        "summary_txt": str(summary_txt),
        "validation_main_png": validation_files.get("main_png", ""),
        "sensitivity_png": sensitivity_files.get("png", ""),
        "theta_png": theta_files.get("png", ""),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="导出多孔双层减反结构专题总包")
    parser.add_argument("--new-csv", default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\New.csv")
    parser.add_argument("--n-porous-csv", default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\n_porous.csv")
    parser.add_argument("--d-porous-csv", default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\err_d_porous.csv")
    parser.add_argument("--d-high-csv", default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\err_d_high.csv")
    parser.add_argument("--theta-csv", default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\theta.csv")
    parser.add_argument("--prefix", default="porous_double_ar_topic_v1")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = export_topic_bundle(
        new_csv=Path(args.new_csv),
        n_porous_csv=Path(args.n_porous_csv),
        d_porous_csv=Path(args.d_porous_csv),
        d_high_csv=Path(args.d_high_csv),
        theta_csv=Path(args.theta_csv),
        prefix=str(args.prefix),
    )
    print("多孔双层减反结构专题总包已导出")
    print(f"manifest    = {result['manifest']}")
    print(f"summary_txt = {result['summary_txt']}")


if __name__ == "__main__":
    main()
