from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
from pathlib import Path

from thinfilm import export_tamm_interface_priority


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="导出 Tamm 第2阶段界面拼接优先级建议，默认使用 90/100/110/120 nm 候选组。"
    )
    parser.add_argument(
        "--csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\tamm_spectrum_dW_scan(4).csv",
        help="包含 d_W 联合扫描与 S11 相位列的 COMSOL CSV 路径",
    )
    parser.add_argument(
        "--prefix",
        default="tamm_interface_priority_v1",
        help="输出文件前缀",
    )
    parser.add_argument(
        "--candidates",
        nargs="*",
        type=float,
        default=[90.0, 100.0, 110.0, 120.0],
        help="候选 d_W（nm）列表",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = export_tamm_interface_priority(
        reference_csv=Path(args.csv),
        prefix=str(args.prefix),
        candidate_dws_nm=args.candidates,
    )
    print("Tamm 第2阶段界面优先级建议已导出")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
