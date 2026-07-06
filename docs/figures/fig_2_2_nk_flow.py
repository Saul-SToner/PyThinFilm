"""Draw Fig. 2-2: real-material n/k loading and interpolation workflow."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT_DIR = Path(__file__).resolve().parent
STEM = OUT_DIR / "fig_2_2_nk_flow"

# 150 x 163 mm: matched to the Fig. 2-1 manuscript template.
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
        "pdf.fonttype": 42,
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
        fontsize=8.35,
        fontweight="semibold",
        ha="center",
        va="center",
        transform=ax.transAxes,
    )
    ax.text(
        x + w / 2,
        y + h * 0.33,
        detail,
        fontsize=7.05,
        color=MUTED,
        ha="center",
        va="center",
        linespacing=1.30,
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

    input_y = 0.855
    lookup_y = 0.735
    cache_y = 0.615
    branch_y = 0.455
    range_y = 0.310
    interp_y = 0.185
    output_y = 0.060

    box(
        ax,
        main_x,
        input_y,
        main_w,
        main_h,
        "材料与波长输入",
        "材料名称 / 数据源筛选，仿真波长网格",
        style="intermediate",
    )
    box(
        ax,
        main_x,
        lookup_y,
        main_w,
        main_h,
        "材料名称规范化与检索",
        "别名映射，查询 data/real_nk/manifest.json",
        style="intermediate",
    )
    box(
        ax,
        main_x,
        cache_y,
        main_w,
        main_h,
        "内存缓存查询",
        "相同材料与数据源是否已有 MaterialDataset？",
        style="main",
    )

    branch_w = 0.37
    branch_h = 0.086
    left_x = 0.070
    right_x = 1 - 0.070 - branch_w
    box(
        ax,
        left_x,
        branch_y,
        branch_w,
        branch_h,
        "缓存命中",
        "直接复用只读 MaterialDataset",
        style="branch",
    )
    box(
        ax,
        right_x,
        branch_y,
        branch_w,
        branch_h,
        "CSV 读取与数据集构建",
        "按波长排序 / 只读数组 / 写入缓存",
        style="branch",
    )

    box(
        ax,
        main_x,
        range_y,
        main_w,
        main_h,
        "有效波长范围检查",
        "默认禁止超出源数据范围外推",
        style="verify",
    )
    box(
        ax,
        main_x,
        interp_y,
        main_w,
        main_h,
        "n / k 线性插值",
        r"numpy.interp 映射到目标波长 $\lambda$",
        style="core",
    )
    box(
        ax,
        main_x,
        output_y,
        main_w,
        main_h,
        "复折射率输出至 TMM",
        r"$\tilde{n}(\lambda)=n(\lambda)+i\,k(\lambda)$",
        style="core",
    )

    arrow(ax, (cx, input_y), (cx, lookup_y + main_h))
    arrow(ax, (cx, lookup_y), (cx, cache_y + main_h))

    arrow(
        ax,
        (cx - 0.09, cache_y),
        (left_x + branch_w / 2, branch_y + branch_h),
        rad=0.15,
    )
    arrow(
        ax,
        (cx + 0.09, cache_y),
        (right_x + branch_w / 2, branch_y + branch_h),
        rad=-0.15,
    )
    ax.text(0.355, 0.566, "是", fontsize=6.8, color=MUTED, ha="center", transform=ax.transAxes)
    ax.text(0.645, 0.566, "否", fontsize=6.8, color=MUTED, ha="center", transform=ax.transAxes)

    arrow(
        ax,
        (left_x + branch_w / 2, branch_y),
        (cx - 0.09, range_y + main_h),
        rad=-0.14,
    )
    arrow(
        ax,
        (right_x + branch_w / 2, branch_y),
        (cx + 0.09, range_y + main_h),
        rad=0.14,
    )
    arrow(ax, (cx, range_y), (cx, interp_y + main_h))
    arrow(ax, (cx, interp_y), (cx, output_y + main_h))

    ax.text(
        0.50,
        0.012,
        "图 2-2  真实材料 nk 数据读取与插值流程图",
        fontsize=9.2,
        fontweight="semibold",
        color=INK,
        ha="center",
        va="bottom",
        transform=ax.transAxes,
    )

    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(STEM.with_suffix(".png"), format="png", dpi=300, bbox_inches=None)
    plt.close(fig)


if __name__ == "__main__":
    draw()
