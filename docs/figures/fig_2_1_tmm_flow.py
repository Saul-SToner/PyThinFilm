"""Draw Fig. 2-1 as an editable, manuscript-style vertical flowchart."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT_DIR = Path(__file__).resolve().parent
STEM = OUT_DIR / "fig_2_1_tmm_flow"

# 150 x 169 mm: compact enough for an A4 Word text area.
WIDTH_IN = 5.90
HEIGHT_IN = 6.66

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
    """Add a restrained two-line process box in axes coordinates."""
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
        fontsize=8.4,
        fontweight="semibold",
        ha="center",
        va="center",
        linespacing=1.28,
        transform=ax.transAxes,
    )
    detail_y = y + h * (0.30 if "\n" in detail else 0.34)
    ax.text(
        x + w / 2,
        detail_y,
        detail,
        fontsize=7.15,
        color=MUTED,
        ha="center",
        va="center",
        linespacing=1.34,
        transform=ax.transAxes,
    )


def straight_arrow(ax, start, end):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=7.5,
            linewidth=0.72,
            color=ARROW,
            shrinkA=1,
            shrinkB=1,
            transform=ax.transAxes,
            clip_on=False,
        )
    )


def branch_arrow(ax, start, end, rad):
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
    main_h = 0.085
    main_x = cx - main_w / 2
    ys = [0.835, 0.705, 0.575, 0.445, 0.315]

    steps = [
        ("结构与光学输入", r"$d_j,\ \tilde{n}_j(\lambda),\ \theta_0$，TE / TM"),
        ("层内相位与导纳", r"Snell 定律，光学导纳 $\eta_j$ 与相位 $\delta_j$"),
        ("单层特征矩阵", r"由 $\eta_j$、$\delta_j$ 构造 $2\times2$ 矩阵 $M_j$"),
        ("多层矩阵级联", r"$M=M_1M_2\cdots M_N$，求复振幅 $r,t$"),
        ("物理量输出", "$R$ / $T$ / $A$ 光谱\n腔内电场分布 $E(z)$"),
    ]

    for i, ((title, detail), y) in enumerate(zip(steps, ys)):
        style = "core" if i == 2 else "main" if i == 4 else "intermediate"
        box(ax, main_x, y, main_w, main_h, title, detail, style=style)

    for upper_y, lower_y in zip(ys[:-1], ys[1:]):
        straight_arrow(
            ax,
            (cx, upper_y),
            (cx, lower_y + main_h),
        )

    branch_w = 0.355
    branch_h = 0.078
    left_x = 0.080
    right_x = 1 - 0.080 - branch_w
    branch_y = 0.175
    box(ax, left_x, branch_y, branch_w, branch_h, "光谱结果", r"$R(\lambda),\ T(\lambda),\ A(\lambda)$", style="branch")
    box(ax, right_x, branch_y, branch_w, branch_h, "腔内电场分布", r"$E(z)$ 一维逆向递推", style="branch")

    split_y = ys[-1]
    branch_arrow(
        ax,
        (cx - 0.080, split_y),
        (left_x + branch_w / 2, branch_y + branch_h),
        0.16,
    )
    branch_arrow(
        ax,
        (cx + 0.080, split_y),
        (right_x + branch_w / 2, branch_y + branch_h),
        -0.16,
    )

    check_w = branch_w
    check_h = 0.060
    check_y = 0.075
    box(ax, left_x, check_y, check_w, check_h, "能量守恒复验", r"$R+T+A=1$", style="verify")
    box(ax, right_x, check_y, check_w, check_h, "场分布可视化", "驻波 / 局域增强分析", style="analysis")
    straight_arrow(
        ax,
        (left_x + branch_w / 2, branch_y),
        (left_x + branch_w / 2, check_y + check_h),
    )
    straight_arrow(
        ax,
        (right_x + branch_w / 2, branch_y),
        (right_x + branch_w / 2, check_y + check_h),
    )

    ax.text(
        0.50,
        0.018,
        "图 2-1  传输矩阵法（TMM）计算流程示意图",
        fontsize=9.2,
        fontweight="semibold",
        color=INK,
        ha="center",
        va="bottom",
        transform=ax.transAxes,
    )

    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(STEM.with_suffix(".svg"), format="svg", bbox_inches=None)
    fig.savefig(STEM.with_suffix(".pdf"), format="pdf", bbox_inches=None)
    fig.savefig(STEM.with_suffix(".png"), format="png", dpi=300, bbox_inches=None)
    plt.close(fig)


if __name__ == "__main__":
    draw()
