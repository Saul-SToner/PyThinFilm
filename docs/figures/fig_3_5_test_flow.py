"""Draw Fig. 3-5: local tests and evidence-material generation workflow."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT_DIR = Path(__file__).resolve().parent
STEM = OUT_DIR / "fig_3_5_test_flow"

# 150 x 163 mm: matched to the manuscript flowchart template.
WIDTH_IN = 5.90
HEIGHT_IN = 6.40

INK = "#263238"
MUTED = "#65727A"
ARROW = "#6D777E"

STYLES = {
    "main": ("#F5F6FA", "#8A92A3"),
    "intermediate": ("#F7F6F9", "#9C9AA8"),
    "core": ("#F1F5F7", "#6F8796"),
    "branch": ("#F7F6F9", "#9C9AA8"),
    "verify": ("#F2F7F6", "#7D9A96"),
    "analysis": ("#F8F5EF", "#A5957E"),
}


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "Arial", "SimHei", "DejaVu Sans"],
        "font.size": 8.0,
        "text.color": INK,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def box(ax, x, y, w, h, title, detail, *, style="main"):
    face, edge = STYLES[style]
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.004,rounding_size=0.004",
        facecolor=face,
        edgecolor=edge,
        linewidth=0.76 if style in ("core", "verify", "analysis") else 0.70,
        transform=ax.transAxes,
        clip_on=False,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h * 0.63,
        title,
        fontsize=8.25,
        fontweight="semibold",
        ha="center",
        va="center",
        transform=ax.transAxes,
    )
    ax.text(
        x + w / 2,
        y + h * 0.33,
        detail,
        fontsize=6.85,
        color=MUTED,
        ha="center",
        va="center",
        linespacing=1.28,
        transform=ax.transAxes,
    )


def arrow(ax, start, end, *, rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            connectionstyle=f"arc3,rad={rad}",
            mutation_scale=7.5,
            linewidth=0.72,
            color=ARROW,
            shrinkA=1,
            shrinkB=1,
            transform=ax.transAxes,
            clip_on=False,
        )
    )


def draw():
    fig, ax = plt.subplots(figsize=(WIDTH_IN, HEIGHT_IN))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    cx = 0.50
    main_w = 0.54
    main_h = 0.082
    main_x = cx - main_w / 2

    trigger_y = 0.855
    run_y = 0.675
    evidence_y = 0.505
    archive_y = 0.340
    list_y = 0.205
    doc_y = 0.075

    box(
        ax,
        main_x,
        trigger_y,
        main_w,
        main_h,
        "触发本地验证",
        "运行 pytest 测试集与 smoke_test.py",
        style="intermediate",
    )

    branch_w = 0.375
    branch_h = 0.092
    left_x = 0.065
    right_x = 1 - 0.065 - branch_w

    box(
        ax,
        left_x,
        run_y,
        branch_w,
        branch_h,
        "pytest 单元与物理测试",
        "270 个用例：数值一致性 / 守恒 / 模块边界",
        style="core",
    )
    box(
        ax,
        right_x,
        run_y,
        branch_w,
        branch_h,
        "功能管道冒烟自检",
        "导入检查 / 演示入口 / 输出链路",
        style="core",
    )

    box(
        ax,
        left_x,
        evidence_y,
        branch_w,
        branch_h,
        "pytest 运行证据",
        "pytest_log.txt · 图 3-3 终端截图",
        style="branch",
    )
    box(
        ax,
        right_x,
        evidence_y,
        branch_w,
        branch_h,
        "smoke test 运行证据",
        "smoke_test_log.txt · 图 3-4 终端截图",
        style="branch",
    )

    box(
        ax,
        main_x,
        archive_y,
        main_w,
        main_h,
        "证据文件集中归档",
        "docs/evidence/ 日志 · docs/figures/ 图示",
        style="verify",
    )
    box(
        ax,
        main_x,
        list_y,
        main_w,
        main_h,
        "证据清单映射",
        "evidence_list.md 记录图号、来源与插入位置",
        style="analysis",
    )
    box(
        ax,
        main_x,
        doc_y,
        main_w,
        main_h,
        "作品说明书排版",
        "引用现有日志、流程图与测试截图",
        style="main",
    )

    arrow(
        ax,
        (cx - 0.085, trigger_y),
        (left_x + branch_w / 2, run_y + branch_h),
        rad=0.16,
    )
    arrow(
        ax,
        (cx + 0.085, trigger_y),
        (right_x + branch_w / 2, run_y + branch_h),
        rad=-0.16,
    )
    arrow(
        ax,
        (left_x + branch_w / 2, run_y),
        (left_x + branch_w / 2, evidence_y + branch_h),
    )
    arrow(
        ax,
        (right_x + branch_w / 2, run_y),
        (right_x + branch_w / 2, evidence_y + branch_h),
    )
    arrow(
        ax,
        (left_x + branch_w / 2, evidence_y),
        (cx - 0.085, archive_y + main_h),
        rad=-0.14,
    )
    arrow(
        ax,
        (right_x + branch_w / 2, evidence_y),
        (cx + 0.085, archive_y + main_h),
        rad=0.14,
    )
    arrow(ax, (cx, archive_y), (cx, list_y + main_h))
    arrow(ax, (cx, list_y), (cx, doc_y + main_h))

    ax.text(
        0.50,
        0.035,
        "仅整理与引用既有证据，不修改真实仿真结果图或测试截图",
        fontsize=6.7,
        color=MUTED,
        ha="center",
        va="center",
        transform=ax.transAxes,
    )
    ax.text(
        0.50,
        0.006,
        "图 3-5  测试与证据材料生成流程图",
        fontsize=9.2,
        fontweight="semibold",
        color=INK,
        ha="center",
        va="bottom",
        transform=ax.transAxes,
    )

    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(STEM.with_suffix(".svg"), format="svg", bbox_inches=None)
    fig.savefig(STEM.with_suffix(".png"), format="png", dpi=300, bbox_inches=None)
    plt.close(fig)


if __name__ == "__main__":
    draw()
