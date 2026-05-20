from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thinfilm import export_tamm_reflection_phase_screen


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="筛选 Tamm 1D 端结构对：同一波长下高反射且反射相位差接近 pi。"
    )
    parser.add_argument(
        "--csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\tamm_spectrum_dW_scan(4).csv",
        help="包含 d_W、R/T/A 和 S11 相位列的 COMSOL 1D 扫描 CSV 路径。",
    )
    parser.add_argument(
        "--prefix",
        default="tamm_reflection_phase_screen_v1",
        help="输出文件前缀。",
    )
    parser.add_argument(
        "--candidates",
        nargs="*",
        type=float,
        default=None,
        help="可选候选 d_W（nm）列表；不填则使用 CSV 中全部 d_W 组。",
    )
    parser.add_argument("--lambda-min-um", type=float, default=None, help="可选：波长窗口下限（um）。")
    parser.add_argument("--lambda-max-um", type=float, default=None, help="可选：波长窗口上限（um）。")
    parser.add_argument("--min-reflectance", type=float, default=0.70, help="端结构通过筛选所需的最低 min(R_left,R_right)。")
    parser.add_argument("--max-phase-error-rad", type=float, default=0.35, help="允许的 |pi-delta_phase| 最大误差。")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    window = None
    if args.lambda_min_um is not None and args.lambda_max_um is not None:
        window = (float(args.lambda_min_um), float(args.lambda_max_um))

    files = export_tamm_reflection_phase_screen(
        reference_csv=str(Path(args.csv)),
        prefix=str(args.prefix),
        candidate_dws_nm=args.candidates,
        lambda_window_um=window,
        min_reflectance=float(args.min_reflectance),
        max_phase_error_rad=float(args.max_phase_error_rad),
    )
    print("Tamm 1D 反射相位端结构筛选已导出")
    for key, value in files.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
