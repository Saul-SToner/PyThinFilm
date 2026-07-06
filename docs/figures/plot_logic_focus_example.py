"""Generate a synthetic example of full R/T/A versus focused-R plotting."""

from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thinfilm.plot_logic import focused_power_limits, rta_trace_styles


OUT = Path(__file__).resolve().parent / "plot_logic_focus_example"

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "Arial", "SimHei", "DejaVu Sans"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.unicode_minus": False,
        "font.size": 8,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def draw() -> None:
    x = np.linspace(0.0, 1.0, 121)
    r = 0.970 + 0.025 * np.exp(-((x - 0.55) / 0.20) ** 2) + 0.003 * np.sin(4 * np.pi * x)
    a = 0.0010 + 0.00025 * np.cos(2 * np.pi * x)
    t = 1.0 - r - a
    curves = {"R": r, "T": t, "A": a}
    colors = {"R": "#547C95", "T": "#8FA7B2", "A": "#B29A78"}
    styles = rta_trace_styles("R", curves)
    mpl_styles = {"solid": "-", "dash": "--", "dot": ":"}

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.15), constrained_layout=True)
    for ax in axes:
        ax.set_facecolor("#FBFCFC")
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#AEB8BD")
        ax.tick_params(colors="#65727A", labelsize=7)
        ax.grid(axis="y", color="#E2E7E9", linewidth=0.65)
        ax.set_xlabel("归一化扫描参数", color="#263238")

    # Full conservation overview.
    for kind in ("R", "T", "A"):
        axes[0].plot(x, curves[kind], color=colors[kind], lw=1.7, label=kind)
    axes[0].set_ylim(-0.02, 1.02)
    axes[0].set_ylabel("R / T / A", color="#263238")
    axes[0].set_title("a  R/T/A 总览：守恒关系", loc="left", fontsize=9, fontweight="semibold")
    axes[0].legend(frameon=False, ncol=3, loc="center right")

    # Focused information view.
    for kind in ("R", "T", "A"):
        style = styles[kind]
        axes[1].plot(
            x,
            curves[kind],
            color=colors[kind],
            lw=float(style["linewidth"]),
            alpha=float(style["alpha"]),
            ls=mpl_styles[str(style["dash"])],
            label=kind,
        )
    y0, y1 = focused_power_limits(r)
    axes[1].set_ylim(y0, y1)
    axes[1].set_ylabel("反射率 R（聚焦范围）", color="#263238")
    axes[1].set_title("b  主变量聚焦：突出 R 的细微变化", loc="left", fontsize=9, fontweight="semibold")
    axes[1].text(
        0.98,
        0.06,
        "A≈0，仅作弱化参考",
        transform=axes[1].transAxes,
        ha="right",
        color="#65727A",
        fontsize=7,
    )

    fig.suptitle("自适应 R/T/A 作图逻辑示例（合成数据，非仿真结果）", fontsize=10.5, fontweight="semibold", color="#263238")
    fig.savefig(OUT.with_suffix(".png"), dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    draw()
