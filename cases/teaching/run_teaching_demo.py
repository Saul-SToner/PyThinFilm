from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse

from thinfilm import (
    export_teaching_case_outputs,
    export_teaching_main_branch_catalog,
    export_teaching_comparison_figures,
    export_teaching_report_bundle,
    export_teaching_suite_outputs,
    list_teaching_cases,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行设计报告第2章教学仿真案例，并导出图表与数据。"
    )
    parser.add_argument(
        "--case",
        type=str,
        default=None,
        help="只运行单个案例，例如 single_ar 或 neutral_beamsplitter。",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="仅列出可用案例，不执行导出。",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="导出报告风格的多曲线对比图。",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="一键导出主树完整报告包：单案例、对比图、清单摘要。",
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="导出主树目录配置，供前端或 APP 直接读取。",
    )
    return parser


def print_case_catalog() -> None:
    print("可用案例：")
    for item in list_teaching_cases():
        print(f"  {item['case_id']:<24} {item['title_cn']}")


def print_output_dict(outputs: dict[str, str], indent: str = "  ") -> None:
    for key, value in outputs.items():
        print(f"{indent}{key}: {value}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        print_case_catalog()
        return

    if args.case:
        files = export_teaching_case_outputs(args.case)
        print(f"已导出单个案例: {args.case}")
        print_output_dict(files)
        return

    if args.compare:
        files = export_teaching_comparison_figures()
        print("已导出报告风格对比图。")
        for figure_id, outputs in files.items():
            print(f"\n[{figure_id}]")
            print_output_dict(outputs)
        return

    if args.catalog:
        catalog = export_teaching_main_branch_catalog()
        print("已导出主树目录配置。")
        print(f"  catalog_json: {catalog['catalog_json']}")
        print(f"  sections    : {len(catalog['sections'])}")
        print(f"  comparisons : {len(catalog['comparisons'])}")
        return

    if args.report:
        bundle = export_teaching_report_bundle()
        print("已导出主树报告包。")
        print(f"  case_index_csv: {bundle['case_index_csv']}")
        print(f"  manifest_json : {bundle['manifest_json']}")
        print(f"  manifest_txt  : {bundle['manifest_txt']}")
        print(f"  cases         : {len(bundle['cases'])}")
        print(f"  comparisons   : {len(bundle['comparison_figures'])}")
        return

    files = export_teaching_suite_outputs()
    print("已导出第2章全部案例。")
    for case_id, outputs in files.items():
        print(f"\n[{case_id}]")
        print_output_dict(outputs)


if __name__ == "__main__":
    main()
