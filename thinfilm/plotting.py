"""Shared plotting helpers for report-style figures.

The project exports figures for teaching cases and research modules.  This
module keeps the visual defaults consistent without changing the underlying
data or adding interpolated points.
"""

from __future__ import annotations

from pathlib import Path
from string import ascii_lowercase
from typing import Sequence

import numpy as np

import matplotlib.pyplot as plt


INK = "#272727"
MUTED = "#767676"
GRID = "#E6E6E6"
FRAME = "#A8A8A8"
PAPER = "#FFFFFF"
PANEL = "#FFFFFF"
BLUE = "#0F4D92"
CYAN = "#42949E"
GREEN = "#2E9E44"
AMBER = "#B07A1C"
RED = "#B64342"
PURPLE = "#7C6CCF"

COLOR_REFLECTANCE = BLUE
COLOR_TRANSMITTANCE = CYAN
COLOR_ABSORPTANCE = PURPLE
COLOR_CALLOUT = RED

PALETTE = [BLUE, GREEN, AMBER, RED, CYAN, PURPLE]


def apply_plot_style() -> None:
    """Apply the repository-wide Nature-style static figure contract."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "Arial", "Noto Sans CJK SC", "DejaVu Sans", "sans-serif"],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 8,
            "figure.facecolor": PAPER,
            "axes.facecolor": PANEL,
            "axes.edgecolor": FRAME,
            "axes.labelcolor": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "axes.titleweight": "semibold",
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "legend.frameon": False,
            "legend.fontsize": 7,
            "lines.linewidth": 1.5,
            "savefig.facecolor": PAPER,
            "savefig.dpi": 300,
        }
    )


def style_axis(ax: plt.Axes, *, grid: bool = False) -> None:
    """Style one axis using the shared report theme."""
    ax.set_facecolor(PANEL)
    for side, spine in ax.spines.items():
        spine.set_visible(side in {"left", "bottom"})
        spine.set_color(INK)
        spine.set_linewidth(0.8)
    ax.tick_params(axis="both", colors=INK, labelsize=7, width=0.7, length=3)
    if grid:
        ax.grid(True, color=GRID, linewidth=0.75, alpha=0.65)
        ax.set_axisbelow(True)


def add_panel_labels(fig: plt.Figure) -> None:
    """Add small bold lowercase labels to unique visible data panels."""
    candidates: list[plt.Axes] = []
    seen: set[tuple[float, float, float, float]] = set()
    for ax in fig.axes:
        if not ax.axison:
            continue
        bounds = tuple(round(value, 3) for value in ax.get_position().bounds)
        if bounds[2] < 0.10 or bounds in seen:
            continue
        seen.add(bounds)
        candidates.append(ax)
    if len(candidates) <= 1:
        return
    candidates.sort(key=lambda ax: (-ax.get_position().y1, ax.get_position().x0))
    for label, ax in zip(ascii_lowercase, candidates):
        if any(text.get_gid() == "nature-panel-label" for text in ax.texts):
            continue
        artist = ax.text(-0.08, 1.03, label, transform=ax.transAxes, fontsize=8, fontweight="bold", ha="left", va="bottom", color=INK)
        artist.set_gid("nature-panel-label")


def save_publication_figure(
    fig: plt.Figure,
    png_path: str | Path,
    *,
    dpi: int = 300,
    max_width_in: float | None = 7.2,
    add_labels: bool = True,
    close: bool = False,
) -> dict[str, str]:
    """Save one publication-ready PNG from a Python-rendered figure."""
    path = Path(png_path)
    base = path.with_suffix("")
    base.parent.mkdir(parents=True, exist_ok=True)
    if max_width_in is not None:
        width, height = fig.get_size_inches()
        if width > max_width_in:
            scale = max_width_in / width
            fig.set_size_inches(max_width_in, min(height * scale, 7.8), forward=True)
    if add_labels:
        add_panel_labels(fig)
    outputs = {"png": str(base.with_suffix(".png"))}
    fig.savefig(outputs["png"], dpi=dpi, bbox_inches="tight")
    if close:
        plt.close(fig)
    return outputs


def style_colorbar(cbar: object) -> None:
    """Style a Matplotlib colorbar if present."""
    if hasattr(cbar, "outline"):
        cbar.outline.set_edgecolor(FRAME)
        cbar.outline.set_linewidth(0.8)
    if hasattr(cbar, "ax"):
        cbar.ax.tick_params(colors=MUTED, labelsize=8)
        cbar.ax.yaxis.label.set_color(INK)


def annotate_point(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    *,
    xytext: tuple[float, float] = (8.0, 8.0),
) -> None:
    """Annotate a highlighted data point."""
    ax.annotate(
        text,
        xy=(x, y),
        xytext=xytext,
        textcoords="offset points",
        fontsize=8.5,
        color=INK,
        bbox={"boxstyle": "round,pad=0.28", "facecolor": "#ffffff", "edgecolor": "#d7dce5", "alpha": 0.92},
        arrowprops={"arrowstyle": "->", "color": MUTED, "linewidth": 0.9},
    )


def add_value_labels(
    ax: plt.Axes,
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    fmt: str = "{:.3f}",
    dy: float = 0.012,
) -> None:
    """Add compact numeric labels above markers or bars."""
    for x, y in zip(xs, ys):
        ax.text(float(x), float(y) + dy, fmt.format(float(y)), ha="center", va="bottom", fontsize=8, color=INK)


def add_zero_reference(ax: plt.Axes, *, label: str | None = None) -> None:
    """Draw the physical no-change baseline used by residual/delta plots."""
    ax.axhline(0.0, color=MUTED, linewidth=1.0, alpha=0.85, linestyle="--", label=label)


def plot_bars_with_missing(
    ax: plt.Axes,
    positions: Sequence[float],
    values: Sequence[float | None],
    *,
    color: str,
    width: float = 0.56,
    missing_label: str = "未通过/无结果",
) -> None:
    """Plot bars while keeping missing results distinct from physical zero."""
    x = np.asarray(positions, dtype=float)
    finite_values = np.asarray([np.nan if value is None else float(value) for value in values], dtype=float)
    mask = np.isfinite(finite_values)
    if np.any(mask):
        ax.bar(x[mask], finite_values[mask], color=color, width=width)
    missing = ~mask
    if np.any(missing):
        y0, y1 = ax.get_ylim()
        marker_y = y0 + 0.04 * max(y1 - y0, 1.0)
        ax.scatter(x[missing], np.full(np.sum(missing), marker_y), marker="x", s=48, color=RED, zorder=5, label=missing_label)
        ax.legend(loc="best")


apply_plot_style()
