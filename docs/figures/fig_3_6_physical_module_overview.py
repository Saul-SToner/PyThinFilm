"""Draw Fig. 3-6: PyThinFilm physical modules and verification chain."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT_DIR = Path(__file__).resolve().parent
STEM = OUT_DIR / "fig_3_6_physical_module_overview"

# 165 x 147 mm: A4 Word body-width overview.
WIDTH_IN = 6.50
HEIGHT_IN = 5.80

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


def box(
    ax,
    x,
    y,
    w,
    h,
    title,
    detail,
    *,
    style="main",
    title_size=7.8,
    detail_size=6.35,
):
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
        linespacing=1.25,
        transform=ax.transAxes,
    )


def arrow(ax, start, end, *, rad=0.0, dashed=False):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            connectionstyle=f"arc3,rad={rad}",
            mutation_scale=7.4,
            linewidth=0.70,
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

    # Stable entry layer.
    entry_x, entry_y, entry_w, entry_h = 0.245, 0.855, 0.510, 0.080
    box(
        ax,
        entry_x,
        entry_y,
        entry_w,
        entry_h,
        "稳定运行入口",
        "run_teaching_demo.py · run_case.py · 独立演示脚本",
        style="intermediate",
    )

    # Main-tree and repository research branches.
    lane_y, lane_h, lane_w = 0.705, 0.092, 0.390
    left_lane_x, right_lane_x = 0.075, 0.535
    box(
        ax,
        left_lane_x,
        lane_y,
        lane_w,
        lane_h,
        "教学主树（平台展示）",
        "平面膜正向仿真 / 材料切换 / 结果导出",
        style="intermediate",
    )
    box(
        ax,
        right_lane_x,
        lane_y,
        lane_w,
        lane_h,
        "仓库研究支线（独立入口）",
        "光栅波导 / Tamm / PDRC / 高级专题",
        style="analysis",
    )
    ax.text(
        left_lane_x + lane_w / 2,
        0.674,
        "教学平台不暴露厚度反演入口",
        fontsize=6.35,
        color=MUTED,
        ha="center",
        va="center",
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5},
        transform=ax.transAxes,
    )

    # Physics implementation layer.
    core_y, core_h = 0.505, 0.105
    core_boxes = [
        (0.025, 0.205, "真实材料 n / k", "materials.py\n有效波段内插值", "intermediate"),
        (0.260, 0.245, "TMM 计算核心", "education.py\n特征矩阵向量化", "core"),
        (0.535, 0.205, "亚波长 EMT", "rcwa.py\n零阶 EMT + TMM；非严格 RCWA", "main"),
        (0.770, 0.205, "COMSOL CSV", "外部导入\n非内部全波求解", "analysis"),
    ]
    for x, w, title, detail, style in core_boxes:
        box(
            ax,
            x,
            core_y,
            w,
            core_h,
            title,
            detail,
            style=style,
            title_size=7.35,
            detail_size=5.95,
        )

    # Physical outputs.
    out_y, out_h, out_w = 0.335, 0.090, 0.390
    left_out_x, right_out_x = 0.075, 0.535
    box(
        ax,
        left_out_x,
        out_y,
        out_w,
        out_h,
        "TMM 物理结果",
        r"$R/T/A$ · $E(z)$ · 反射相位 · 教学案例指标",
        style="core",
    )
    box(
        ax,
        right_out_x,
        out_y,
        out_w,
        out_h,
        "研究支线结果",
        "EMT 近似谱 · COMSOL 峰值 / FWHM / Q / 加权量",
        style="analysis",
    )

    # Verification layer.
    verify_y, verify_h, verify_w = 0.180, 0.088, 0.390
    left_verify_x, right_verify_x = 0.075, 0.535
    box(
        ax,
        left_verify_x,
        verify_y,
        verify_w,
        verify_h,
        "理论与参考数据复验",
        "validation.py · 单层减反 / F-P / 高反膜",
        style="verify",
    )
    box(
        ax,
        right_verify_x,
        verify_y,
        verify_w,
        verify_h,
        "自动测试与管道自检",
        "pytest 270 用例 · smoke_test.py",
        style="verify",
    )

    # Evidence archive.
    archive_x, archive_y, archive_w, archive_h = 0.245, 0.060, 0.510, 0.068
    box(
        ax,
        archive_x,
        archive_y,
        archive_w,
        archive_h,
        "复验结果与证据归档",
        "CSV / JSON / SVG / PNG / 日志与证据清单",
        style="main",
        title_size=7.65,
        detail_size=6.15,
    )

    # Entry fan-out.
    arrow(ax, (0.43, entry_y), (left_lane_x + lane_w / 2, lane_y + lane_h), rad=0.12)
    arrow(ax, (0.57, entry_y), (right_lane_x + lane_w / 2, lane_y + lane_h), rad=-0.12)

    # Teaching tree to material support and TMM.
    arrow(ax, (0.225, lane_y), (0.025 + 0.205 / 2, core_y + core_h), rad=0.10)
    arrow(ax, (0.330, lane_y), (0.260 + 0.245 / 2, core_y + core_h), rad=-0.06)
    arrow(ax, (0.025 + 0.205, core_y + core_h / 2), (0.260, core_y + core_h / 2))

    # Research tree to TMM-based, EMT and external-data paths.
    arrow(ax, (0.640, lane_y), (0.260 + 0.245 * 0.78, core_y + core_h), rad=0.16)
    arrow(ax, (0.735, lane_y), (0.535 + 0.205 / 2, core_y + core_h), rad=-0.04)
    arrow(ax, (0.825, lane_y), (0.770 + 0.205 / 2, core_y + core_h), rad=-0.12)

    # Implementation to outputs.
    arrow(ax, (0.260 + 0.245 / 2, core_y), (left_out_x + out_w / 2, out_y + out_h))
    arrow(ax, (0.535 + 0.205 / 2, core_y), (right_out_x + out_w * 0.34, out_y + out_h), rad=0.05)
    arrow(ax, (0.770 + 0.205 / 2, core_y), (right_out_x + out_w * 0.73, out_y + out_h), rad=-0.05)

    # Results to verification.
    arrow(ax, (left_out_x + out_w / 2, out_y), (left_verify_x + verify_w / 2, verify_y + verify_h))
    arrow(ax, (left_out_x + out_w * 0.70, out_y), (right_verify_x + verify_w * 0.18, verify_y + verify_h), rad=-0.12)
    arrow(ax, (right_out_x + out_w / 2, out_y), (right_verify_x + verify_w / 2, verify_y + verify_h))

    # Verification merge into evidence archive.
    arrow(ax, (left_verify_x + verify_w / 2, verify_y), (archive_x + archive_w * 0.36, archive_y + archive_h), rad=-0.08)
    arrow(ax, (right_verify_x + verify_w / 2, verify_y), (archive_x + archive_w * 0.64, archive_y + archive_h), rad=0.08)

    ax.text(
        0.50,
        0.010,
        "图 3-6  PyThinFilm 物理功能模块与复验链路总览图",
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
