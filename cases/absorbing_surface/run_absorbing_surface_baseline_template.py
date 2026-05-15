from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse

from thinfilm import export_absorbing_surface_baseline_reference_template


def main() -> None:
    parser = argparse.ArgumentParser(description="导出粗糙吸收表面平面基准模板。")
    parser.add_argument(
        "--prefix",
        default="rough_absorbing_surface_planar_baseline_template",
        help="输出文件前缀。",
    )
    parser.add_argument(
        "--lambda0",
        type=float,
        default=550.0,
        help="中心波长（nm）。默认 550。",
    )
    args = parser.parse_args()

    result = export_absorbing_surface_baseline_reference_template(
        prefix=args.prefix,
        lambda0_nm=args.lambda0,
    )
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
