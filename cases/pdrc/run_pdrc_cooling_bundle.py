from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
from pathlib import Path

import numpy as np

from thinfilm import export_pdrc_cooling_outputs
from thinfilm.io import load_spectrum_csv
from thinfilm.paths import output_file


def _band_average(lambda_um: np.ndarray, values: np.ndarray, lower: float, upper: float) -> float:
    mask = (lambda_um >= lower) & (lambda_um <= upper)
    if int(np.count_nonzero(mask)) < 2:
        return float("nan")
    return float(np.trapezoid(values[mask], lambda_um[mask]) / (upper - lower))


def export_comsol_ir_window_summary(reference_csv: Path, *, prefix: str) -> dict[str, str]:
    lam_spec = load_spectrum_csv(reference_csv, y_selector="1-abs(ewfd.S11)^2-abs(ewfd.S21)^2")
    r_spec = load_spectrum_csv(reference_csv, y_selector="abs(ewfd.S11)^2")
    t_spec = load_spectrum_csv(reference_csv, y_selector="abs(ewfd.S21)^2")

    lambda_um = lam_spec.x_nm / 1000.0
    a_vals = lam_spec.y.astype(float)
    r_vals = np.interp(lam_spec.x_nm, r_spec.x_nm, r_spec.y.astype(float))
    t_vals = np.interp(lam_spec.x_nm, t_spec.x_nm, t_spec.y.astype(float))

    epsilon_8_13_avg = _band_average(lambda_um, a_vals, 8.0, 13.0)
    r_8_13_avg = _band_average(lambda_um, r_vals, 8.0, 13.0)
    t_8_13_avg = _band_average(lambda_um, t_vals, 8.0, 13.0)
    peak_idx = int(np.argmax(a_vals))

    txt_path = output_file(f"{prefix}_comsol_ir_window_summary.txt")
    lines = [
        "PDRC COMSOL 8-13 um 窗口摘要",
        "=" * 80,
        f"reference_csv       = {reference_csv}",
        f"points              = {len(lambda_um)}",
        f"lambda_min_um       = {float(np.min(lambda_um)):.6f}",
        f"lambda_max_um       = {float(np.max(lambda_um)):.6f}",
        f"R_8_13_avg          = {r_8_13_avg:.12e}",
        f"T_8_13_avg          = {t_8_13_avg:.12e}",
        f"epsilon_8_13_avg    = {epsilon_8_13_avg:.12e}",
        f"A_peak              = {float(a_vals[peak_idx]):.12e}",
        f"A_peak_lambda_um    = {float(lambda_um[peak_idx]):.6f}",
        "",
        "判读：如果目标是 PDRC 高红外发射，epsilon_8_13_avg 通常希望 > 0.70；",
        "当前摘要只评价你导出的 8-13 um COMSOL 文件，不包含太阳波段平均吸收。",
    ]
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")

    csv_path = output_file(f"{prefix}_comsol_ir_window_clean.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("lambda_um,R,T,A,emissivity,band\n")
        for lam, rv, tv, av in zip(lambda_um, r_vals, t_vals, a_vals):
            f.write(f"{lam:.12g},{rv:.12g},{tv:.12g},{av:.12g},{av:.12g},atmospheric_window\n")

    return {
        "comsol_summary_txt": str(txt_path),
        "comsol_clean_csv": str(csv_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="导出 PDRC 被动日间辐射冷却平面多层膜第一版总包")
    parser.add_argument("--prefix", default="pdrc_multilayer_cooling_Ag500_v1")
    parser.add_argument("--variant", default="full", choices=["full", "simple"])
    parser.add_argument("--theta-deg", type=float, default=0.0)
    parser.add_argument("--pol", default="p", choices=["p", "s"])
    parser.add_argument("--ag-thickness-nm", type=float, default=500.0)
    parser.add_argument(
        "--comsol-csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\pdrc_ir_window_Ag500.csv",
        help="可选：COMSOL 8-13 um 全局计算表，用于导出窗口摘要。",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    files = export_pdrc_cooling_outputs(
        prefix=str(args.prefix),
        variant=str(args.variant),
        theta_deg=float(args.theta_deg),
        pol=str(args.pol),
        ag_thickness_nm=float(args.ag_thickness_nm),
    )
    print("PDRC Python TMM 总包已导出")
    for key, value in files.items():
        print(f"{key}: {value}")

    comsol_csv = Path(args.comsol_csv)
    if comsol_csv.exists():
        comsol_files = export_comsol_ir_window_summary(comsol_csv, prefix=str(args.prefix))
        print("COMSOL 8-13 um 窗口摘要已导出")
        for key, value in comsol_files.items():
            print(f"{key}: {value}")
    else:
        print(f"未找到 COMSOL CSV，跳过窗口摘要: {comsol_csv}")


if __name__ == "__main__":
    main()
