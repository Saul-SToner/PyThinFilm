"""Shared utility functions and constants for the thinfilm package.

These functions were previously duplicated across validation.py,
sensitivity.py, and guided_grating/export.py. Centralizing them
eliminates copy-paste drift and provides a single source of truth.
"""

from __future__ import annotations

from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np

from .plotting import style_axis as _plotting_style_axis


# ---------------------------------------------------------------------------
# Color constants (report-style palette)
# ---------------------------------------------------------------------------

COLOR_REFLECTANCE = "#0F4D92"    # reflectance / primary response (Blue)
COLOR_TRANSMITTANCE = "#42949E"  # transmittance (Teal)
COLOR_ABSORPTANCE = "#7C6CCF"    # absorptance / emissivity (Purple)
COLOR_CALLOUT = "#B64342"        # target and callout accent (Red)

MAIN_RED = COLOR_REFLECTANCE
TARGET_GREEN = COLOR_CALLOUT
TRANS_BLUE = COLOR_TRANSMITTANCE
ABS_GOLD = COLOR_ABSORPTANCE
GRID_COLOR = "#E6E6E6"
TEXT_DARK = "#272727"
PANEL_BG = "#FFFFFF"

# Aliases for modules that used different names for the same values
REF_BLUE = TRANS_BLUE
ERR_GOLD = ABS_GOLD

# ---------------------------------------------------------------------------
# DPI constant
# ---------------------------------------------------------------------------

DEFAULT_FIGURE_DPI = 300


# ---------------------------------------------------------------------------
# Plot style
# ---------------------------------------------------------------------------

_FONT_LIST = [
    "Microsoft YaHei",
    "Arial",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]

DEFAULT_MIN_GRID = 80


def apply_font_defaults() -> None:
    """Set matplotlib font defaults for Chinese + Latin labels."""
    plt.rcParams["font.sans-serif"] = _FONT_LIST
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42


def style_axis(ax: plt.Axes, *, grid: bool = True) -> None:
    """Apply report-style axis formatting.

    This is the canonical implementation, delegating to plotting.py.
    """
    _plotting_style_axis(ax, grid=grid)


# ---------------------------------------------------------------------------
# Quantity selection helpers
# ---------------------------------------------------------------------------

def default_case_quantity(case_id: str) -> str:
    """Determine default quantity (R or T) from case id."""
    key = str(case_id).strip().lower()
    if "fp_" in key:
        return "T"
    return "R"


def reference_kind_to_quantity(y_kind: str) -> str | None:
    """Map reference y_kind label to quantity letter."""
    key = str(y_kind).strip().lower()
    if "trans" in key:
        return "T"
    if "abs" in key:
        return "A"
    if "reflect" in key:
        return "R"
    return None


def pick_quantity(case_id: str, reference_kind: str, quantity: str | None) -> str:
    """Resolve the effective quantity from explicit or inferred sources."""
    if quantity is not None:
        return str(quantity).strip().upper()
    ref_quantity = reference_kind_to_quantity(reference_kind)
    if ref_quantity is not None:
        return ref_quantity
    return default_case_quantity(case_id)


def series_for_quantity(result: Dict[str, Any], quantity: str) -> np.ndarray:
    """Extract the R/T/A array from a simulation result dict."""
    key = str(quantity).strip().upper()
    if key not in {"R", "T", "A"}:
        raise ValueError("quantity must be 'R', 'T', or 'A'.")
    return np.asarray(result[key], dtype=float)


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------

def resample_pair(
    x1_nm: np.ndarray,
    y1: np.ndarray,
    x2_nm: np.ndarray,
    y2: np.ndarray,
    n_grid: int = 600,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Resample two curves onto a common wavelength grid."""
    x_min = max(float(np.min(x1_nm)), float(np.min(x2_nm)))
    x_max = min(float(np.max(x1_nm)), float(np.max(x2_nm)))
    if x_max <= x_min:
        raise ValueError("Theory and reference curves do not overlap in wavelength.")
    grid = np.linspace(x_min, x_max, max(int(n_grid), DEFAULT_MIN_GRID))
    return grid, np.interp(grid, x1_nm, y1), np.interp(grid, x2_nm, y2)


# ---------------------------------------------------------------------------
# Error metrics
# ---------------------------------------------------------------------------

def error_metrics(theory: np.ndarray, reference: np.ndarray) -> Dict[str, float]:
    """Compute MAE, RMSE, max absolute error, and mean bias."""
    diff = np.asarray(theory, dtype=float) - np.asarray(reference, dtype=float)
    return {
        "mae": float(np.mean(np.abs(diff))),
        "rmse": float(np.sqrt(np.mean(diff ** 2))),
        "max_abs_error": float(np.max(np.abs(diff))),
        "mean_bias": float(np.mean(diff)),
    }
