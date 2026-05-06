from __future__ import annotations

import argparse
from pathlib import Path

from thinfilm import export_final_delivery_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="一键生成教学薄膜三案例的验证、敏感性、系统误差和最终交付总包。"
    )
    parser.add_argument("--single-ar-csv", required=True, help="单层减反膜 COMSOL CSV 路径")
    parser.add_argument("--fp-csv", required=True, help="F-P 滤光片 COMSOL CSV 路径")
    parser.add_argument("--high-reflector-csv", required=True, help="高反膜 COMSOL CSV 路径")
    parser.add_argument("--prefix", default="teaching_pipeline", help="输出文件前缀")
    parser.add_argument("--reference-label", default="COMSOL", help="参考曲线标签")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = export_final_delivery_bundle(
        single_ar_csv=Path(args.single_ar_csv),
        fp_single_csv=Path(args.fp_csv),
        high_reflector_csv=Path(args.high_reflector_csv),
        prefix=str(args.prefix),
        reference_label=str(args.reference_label),
    )
    print("教学薄膜三案例最终交付总包已生成")
    print(f"总包清单: {result['manifest']}")
    print(f"总包索引: {result['index']}")
    print(f"综合性能总表: {result['overall_files']['json']}")
    print(f"竞赛口径总结: {result['competition_files']['txt']}")


if __name__ == "__main__":
    main()
