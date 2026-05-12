from __future__ import annotations

import argparse
from pathlib import Path

from thinfilm import export_advanced_ar_topic_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="导出高级减反专题总包：单层减反膜、多孔二氧化硅膜层、蛾眼等效渐变层、2D 蛾眼 COMSOL。"
    )
    parser.add_argument(
        "--single-ar-csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\AR_MgF2_BK7G18_550nm_theta0.csv",
        help="单层减反膜参考 CSV 路径",
    )
    parser.add_argument(
        "--porous-csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\porous.csv",
        help="多孔二氧化硅膜层参考 CSV 路径",
    )
    parser.add_argument(
        "--porous-double-csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\New.csv",
        help="多孔二氧化硅双层减反结构参考 CSV 路径",
    )
    parser.add_argument(
        "--moth-eye-effective-csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\Rugate2.csv",
        help="蛾眼等效渐变层参考 CSV 路径",
    )
    parser.add_argument(
        "--moth-eye-2d-csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\moth_eye_2D_trapezoid_P200_H300_Wtop40_Wbottom180_Glass_550nm_theta0_comsol.csv",
        help="2D 蛾眼梯形结构 COMSOL CSV 路径",
    )
    parser.add_argument(
        "--prefix",
        default="advanced_ar_topic",
        help="输出文件前缀",
    )
    parser.add_argument(
        "--reference-label",
        default="COMSOL",
        help="参考曲线标签",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = export_advanced_ar_topic_bundle(
        single_ar_csv=Path(args.single_ar_csv),
        porous_csv=Path(args.porous_csv),
        porous_double_csv=Path(args.porous_double_csv),
        moth_eye_effective_csv=Path(args.moth_eye_effective_csv),
        moth_eye_2d_csv=Path(args.moth_eye_2d_csv),
        prefix=str(args.prefix),
        reference_label=str(args.reference_label),
    )
    print("高级减反专题总包已导出")
    print(f"manifest     = {result['manifest']}")
    print(f"overview_png = {result['overview_png']}")
    if "txt" in result:
        print(f"summary_txt  = {result['txt']}")


if __name__ == "__main__":
    main()
