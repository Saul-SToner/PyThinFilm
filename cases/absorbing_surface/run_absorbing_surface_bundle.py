from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
from pathlib import Path

from thinfilm import export_absorbing_surface_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="导出准随机粗糙吸收表面分析总包。")
    parser.add_argument(
        "--csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\2D periodic quasi-random rough absorbing surface.csv",
        help="COMSOL 导出的粗糙吸收表面 CSV 路径",
    )
    parser.add_argument(
        "--prefix",
        default="rough_absorbing_surface_v1",
        help="输出文件前缀",
    )
    parser.add_argument(
        "--lambda0",
        type=float,
        default=550.0,
        help="中心波长（nm）",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = export_absorbing_surface_bundle(
        reference_csv=Path(args.csv),
        prefix=str(args.prefix),
        lambda0_nm=float(args.lambda0),
    )
    print("准随机粗糙吸收表面总包已导出")
    for key, value in result.items():
        print(f"{key:14s}= {value}")


if __name__ == "__main__":
    main()
