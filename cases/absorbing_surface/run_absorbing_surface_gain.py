from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse

from thinfilm import export_absorbing_surface_gain_analysis


def main() -> None:
    parser = argparse.ArgumentParser(description="粗糙吸收表面相对平面基准的吸收增益分析。")
    parser.add_argument("--rough-csv", required=True, help="粗糙表面 CSV 路径。")
    parser.add_argument("--baseline-csv", required=True, help="平面基准 CSV 路径。")
    parser.add_argument("--prefix", default="rough_absorbing_surface_gain", help="输出文件前缀。")
    parser.add_argument("--lambda0", type=float, default=550.0, help="中心波长（nm）。默认 550。")
    parser.add_argument("--rough-label", default="粗糙表面", help="粗糙表面标签。")
    parser.add_argument("--baseline-label", default="平面基准", help="平面基准标签。")
    args = parser.parse_args()

    result = export_absorbing_surface_gain_analysis(
        rough_csv=args.rough_csv,
        baseline_csv=args.baseline_csv,
        prefix=args.prefix,
        lambda0_nm=args.lambda0,
        rough_label=args.rough_label,
        baseline_label=args.baseline_label,
    )
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
