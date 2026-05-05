from __future__ import annotations

from thinfilm import export_teaching_suite_outputs


if __name__ == "__main__":
    print("Running file:", __file__)
    print("thinfilm_core.py 已简化为教学主树兼容入口。")
    print("当前将直接导出第 2 章教学案例。")
    files = export_teaching_suite_outputs()
    print(f"已导出案例数量: {len(files)}")
