from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
from pathlib import Path
from pprint import pprint

from guided_grating import (
    run_comsol_csv_demo,
    run_comsol_two_param_sweep_demo,
    run_minimal_demo,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行光栅波导支线示例，或读取 COMSOL 导出的光栅 CSV。"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="可选：指定 COMSOL 导出的单条光谱 CSV 路径。",
    )
    parser.add_argument(
        "--sweep-csv",
        type=str,
        default=None,
        help="可选：指定 COMSOL 导出的 wavelength + 参数联合扫描 CSV 路径。",
    )
    parser.add_argument(
        "--target-wavelength",
        type=float,
        default=1550.0,
        help="联合扫描筛选时的目标中心波长，默认 1550 nm。",
    )
    parser.add_argument(
        "--sweep-name",
        type=str,
        default=None,
        help="可选：指定联合扫描第二列的参数名，例如 period、t_wg、fill_factor。",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.sweep_csv:
        result = run_comsol_two_param_sweep_demo(
            Path(args.sweep_csv),
            target_wavelength_nm=args.target_wavelength,
            sweep_name=args.sweep_name or "period",
        )
        best = result["summary"]["best_candidate"]
        print("已导入并分析 COMSOL 联合扫描表。")
        print(f"  source_csv: {result['source_csv']}")
        sweep_unit = result["summary"].get("sweep_display_unit", "nm")
        print(
            f"  best_{result['summary']['sweep_name']}_{sweep_unit}: "
            f"{best['period_nm']:.6f} | peak_wavelength_nm: {best['peak_wavelength_nm']:.6f}"
        )
    elif args.csv:
        result = run_comsol_csv_demo(Path(args.csv))
        print("已导入并导出 COMSOL 单条光谱。")
        print(f"  source_csv: {result['source_csv']}")
    else:
        result = run_minimal_demo()
        print("已导出光栅波导支线最小示例。")

    if "warning" in result:
        print(f"  warning: {result['warning']}")
    print("  summary:")
    pprint(result["summary"], sort_dicts=False)
    print("  files:")
    for key, value in result["files"].items():
        print(f"    {key}: {value}")


if __name__ == "__main__":
    main()
