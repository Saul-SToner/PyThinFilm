"""Draw Fig. 2-3: mapping from physical basis to PyThinFilm modules."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT_DIR = Path(__file__).resolve().parent
STEM = OUT_DIR / "fig_2_3_physics_mapping"

# 165 x 137 mm: A4 Word body-width landscape schematic.
WIDTH_IN = 6.50
HEIGHT_IN = 5.40

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


def box(ax, x, y, w, h, title, detail, *, style="main", title_size=7.9, detail_size=6.45):
    face, edge = STYLES[style]
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.004,rounding_size=0.004",
        facecolor=face,
        edgecolor=edge,
        linewidth=0.78 if style in ("core", "verify", "analysis") else 0.70,
        transform=ax.transAxes,
        clip_on=False,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h * 0.63,
        title,
        fontsize=title_size,
        fontweight="semibold",
        ha="center",
        va="center",
        transform=ax.transAxes,
    )
    ax.text(
        x + w / 2,
        y + h * 0.33,
        detail,
        fontsize=detail_size,
        color=MUTED,
        ha="center",
        va="center",
        linespacing=1.28,
        transform=ax.transAxes,
    )


def arrow(ax, start, end, *, rad=0.0, dashed=False):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            connectionstyle=f"arc3,rad={rad}",
            mutation_scale=7.5,
            linewidth=0.72,
            linestyle="--" if dashed else "-",
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

    col_x = [0.045, 0.365, 0.705]
    col_w = [0.245, 0.270, 0.250]
    row_y = [0.715, 0.535, 0.355, 0.175]
    h = 0.115

    headers = ["物理依据 / 数据输入", "模块实现", "计算结果 / 适用边界"]
    for x, w, label in zip(col_x, col_w, headers):
        ax.text(
            x + w / 2,
            0.895,
            label,
            fontsize=7.6,
            fontweight="semibold",
            color=MUTED,
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.plot(
            [x, x + w],
            [0.870, 0.870],
            color="#D8DDE0",
            linewidth=0.65,
            transform=ax.transAxes,
        )

    # TMM core lane.
    box(
        ax,
        col_x[0],
        row_y[0],
        col_w[0],
        h,
        "边界连续与光学导纳",
        r"切向 $E/H$ 连续，$\eta_j$ 与 $\delta_j$",
        style="intermediate",
    )
    box(
        ax,
        col_x[1],
        row_y[0],
        col_w[1],
        h,
        "TMM 特征矩阵主线",
        r"thinfilm/education.py · $M=\prod_j M_j$",
        style="core",
    )
    box(
        ax,
        col_x[2],
        row_y[0],
        col_w[2],
        h,
        "光谱、场与反射相位",
        r"$R/T/A$ · $E(z)$ · $\arg(r)$",
        style="core",
    )

    # Real-material lane.
    box(
        ax,
        col_x[0],
        row_y[1],
        col_w[0],
        h,
        "真实材料色散",
        r"离散 $n(\lambda), k(\lambda)$ 与有效波段",
        style="intermediate",
    )
    box(
        ax,
        col_x[1],
        row_y[1],
        col_w[1],
        h,
        "材料读取、缓存与插值",
        "thinfilm/materials.py · numpy.interp",
        style="main",
    )
    box(
        ax,
        col_x[2],
        row_y[1],
        col_w[2],
        h,
        "复折射率输入",
        "仅在源数据有效波段内送入 TMM",
        style="verify",
    )

    # EMT lane, explicitly bounded.
    box(
        ax,
        col_x[0],
        row_y[2],
        col_w[0],
        h,
        "亚波长零阶 EMT",
        r"$P/\lambda\ll1$，TE/TM 等效折射率",
        style="intermediate",
    )
    box(
        ax,
        col_x[1],
        row_y[2],
        col_w[1],
        h,
        "有效介质 + TMM",
        "guided_grating/rcwa.py",
        style="main",
    )
    box(
        ax,
        col_x[2],
        row_y[2],
        col_w[2],
        h,
        "亚波长近似谱",
        "当前实现不是严格 RCWA",
        style="analysis",
    )

    # External-data lane, kept separate from internal solvers.
    box(
        ax,
        col_x[0],
        row_y[3],
        col_w[0],
        h,
        "COMSOL 扫描 CSV",
        "外部全波结果文件",
        style="analysis",
    )
    box(
        ax,
        col_x[1],
        row_y[3],
        col_w[1],
        h,
        "导入与指标计算",
        "comsol_io.py · validation.py · pdrc.py",
        style="analysis",
    )
    box(
        ax,
        col_x[2],
        row_y[3],
        col_w[2],
        h,
        "特征与复验指标",
        "峰值 / FWHM / Q / 误差与加权量",
        style="verify",
    )

    # Horizontal mappings.
    for y in row_y:
        arrow(ax, (col_x[0] + col_w[0], y + h / 2), (col_x[1], y + h / 2))
        arrow(ax, (col_x[1] + col_w[1], y + h / 2), (col_x[2], y + h / 2))

    # Dependency arrows: material data and EMT feed/reuse the TMM core.
    arrow(
        ax,
        (col_x[1] + col_w[1] * 0.38, row_y[1] + h),
        (col_x[1] + col_w[1] * 0.38, row_y[0]),
        dashed=True,
    )
    ax.text(
        0.50,
        0.080,
        "COMSOL 通道仅负责外部数据导入与特征提取；PyThinFilm 不替代 COMSOL 全波求解",
        fontsize=6.7,
        color=MUTED,
        ha="center",
        va="center",
        transform=ax.transAxes,
    )
    ax.text(
        0.50,
        0.018,
        "图 2-3  平台底层物理方程与模块实现映射图",
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
