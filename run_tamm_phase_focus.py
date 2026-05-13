from __future__ import annotations

import argparse
from pathlib import Path

from thinfilm import export_tamm_phase_focus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="导出 Tamm 第2阶段代表点相位对比图，默认聚焦 d_W = 100, 110, 120 nm。"
    )
    parser.add_argument(
        "--csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\tamm_spectrum_dW_scan(4).csv",
        help="包含 d_W 联合扫描与 S11 相位列的 COMSOL CSV 路径",
    )
    parser.add_argument(
        "--prefix",
        default="tamm_phase_focus_v1",
        help="输出文件前缀",
    )
    parser.add_argument(
        "--focus",
        nargs="*",
        type=float,
        default=[100.0, 110.0, 120.0],
        help="需要聚焦对比的 d_W（nm）列表",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = export_tamm_phase_focus(
        reference_csv=Path(args.csv),
        prefix=str(args.prefix),
        focus_dws_nm=args.focus,
    )
    print("Tamm 第2阶段代表点相位对比已导出")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
