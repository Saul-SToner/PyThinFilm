from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse

from thinfilm import export_tamm_interface_window_scan_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="对 Tamm 界面二维母数据执行多窗口/多判据扫描，比较不同二维窗口设置下的局域判断。"
    )
    parser.add_argument(
        "--prefix",
        default="tamm_interface_window_scan_v1",
        help="输出文件前缀",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = export_tamm_interface_window_scan_bundle(
        csv_mapping={
            "E3_121to125": r"C:\Users\L2791\OneDrive\Desktop\deg.p\E3.csv",
            "E4_current_110to120": r"C:\Users\L2791\OneDrive\Desktop\deg.p\E4.csv",
            "E5_yplus5_110to120": r"C:\Users\L2791\OneDrive\Desktop\deg.p\tamm_interface_110to120_yplus5nm.csv",
            "E5_yplus2_110to120": r"C:\Users\L2791\OneDrive\Desktop\deg.p\tamm_interface_110to120_yplus2nm.csv",
            "E5_yplus10_110to120": r"C:\Users\L2791\OneDrive\Desktop\deg.p\tamm_interface_110to120_yplus10nm.csv",
            "test111_full2d": r"C:\Users\L2791\OneDrive\Desktop\deg.p\tamm_interface_test_111nm_455um.csv",
        },
        prefix=str(args.prefix),
    )
    print("Tamm 界面二维窗口扫描总包已导出")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
