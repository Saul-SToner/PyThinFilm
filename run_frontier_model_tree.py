from __future__ import annotations

import argparse

from thinfilm import (
    export_frontier_model_bundle,
    export_frontier_model_tree,
    get_frontier_model_tree,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="导出前沿研究模型树，当前重点为拓扑 Tamm 边界态与热辐射空间调控模块。"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="仅打印当前前沿研究模型树摘要，不导出文件。",
    )
    parser.add_argument(
        "--bundle",
        action="store_true",
        help="导出带 manifest 和索引的前沿研究模型树总包。",
    )
    parser.add_argument(
        "--prefix",
        default="frontier_research_module_bundle",
        help="输出文件前缀。",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.show:
        tree = get_frontier_model_tree()
        print(tree["summary_cn"])
        print("推荐推进顺序：")
        for item in tree["recommended_sequence_cn"]:
            print(f"  - {item}")
        print("模块：")
        for module in tree["modules"]:
            print(f"  [{module['module_id']}] {module['title_cn']}")
            for stage in module["stages"]:
                print(f"    - {stage['title_cn']} | {stage['status']}")
        return

    if args.bundle:
        files = export_frontier_model_bundle(prefix=str(args.prefix))
        print("前沿研究模型树总包已导出")
        for key, value in files.items():
            print(f"{key}: {value}")
        return

    files = export_frontier_model_tree(prefix=f"{args.prefix}_roadmap")
    print("前沿研究模型树已导出")
    for key, value in files.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
