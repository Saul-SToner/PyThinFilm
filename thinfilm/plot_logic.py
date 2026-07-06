"""Data-driven visual hierarchy for optical R/T/A plots.

The full R/T/A overview remains available for conservation checks, while a
focused view gives the scientifically informative quantity most of the visual
range.  This module contains no rendering code so Matplotlib and Plotly can
share exactly the same decisions.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np


RTA_KINDS = ("R", "T", "A")


def _finite(values: Sequence[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float).reshape(-1)
    return arr[np.isfinite(arr)]


def infer_rta_focus(
    R: Sequence[float],
    T: Sequence[float],
    A: Sequence[float],
    *,
    context: str = "",
    preferred: str | None = None,
) -> str:
    """Choose the primary optical quantity from case semantics and data.

    Explicit preference wins.  Recognized case semantics come next; otherwise
    the curve with the largest robust variation is selected.  Ties keep the
    stable R, T, A priority order.
    """
    if preferred is not None:
        kind = str(preferred).upper()
        if kind not in RTA_KINDS:
            raise ValueError(f"preferred must be one of {RTA_KINDS}, got {preferred!r}")
        return kind

    key = str(context).strip().lower()
    transmission_terms = ("wdm", "fp_", "fabry", "bandpass", "transmission", "透射", "滤波")
    absorption_terms = ("absor", "tamm", "pdrc", "cooling", "emiss", "吸收", "发射", "制冷")
    reflection_terms = ("reflector", "mirror", "bragg", "grating", "solar_cell_ar", "phone_lens_ar", "减反", "反射")
    if any(term in key for term in transmission_terms):
        return "T"
    if any(term in key for term in absorption_terms):
        return "A"
    if any(term in key for term in reflection_terms):
        return "R"

    arrays = {"R": _finite(R), "T": _finite(T), "A": _finite(A)}
    scores: dict[str, float] = {}
    for kind in RTA_KINDS:
        vals = arrays[kind]
        if vals.size == 0:
            scores[kind] = float("-inf")
            continue
        q05, q95 = np.percentile(vals, [5.0, 95.0])
        robust_span = float(q95 - q05)
        full_span = float(np.max(vals) - np.min(vals))
        scores[kind] = robust_span + 0.20 * full_span + 0.05 * float(np.std(vals))
    return max(RTA_KINDS, key=lambda kind: scores[kind])


def focused_power_limits(
    values: Sequence[float],
    *,
    min_span: float = 0.08,
    pad_fraction: float = 0.12,
    lower_bound: float = 0.0,
    upper_bound: float = 1.02,
) -> tuple[float, float]:
    """Return non-clipping focused limits for a bounded power quantity."""
    vals = _finite(values)
    if vals.size == 0:
        return (lower_bound, min(upper_bound, lower_bound + min_span))
    ymin = float(np.min(vals))
    ymax = float(np.max(vals))
    span = ymax - ymin
    pad = max(0.008, span * pad_fraction)
    y0 = max(lower_bound, ymin - pad)
    y1 = min(upper_bound, ymax + pad)
    if y1 - y0 < min_span:
        mid = 0.5 * (y0 + y1)
        y0 = max(lower_bound, mid - min_span / 2.0)
        y1 = min(upper_bound, mid + min_span / 2.0)
        if y1 - y0 < min_span:
            if y0 <= lower_bound:
                y1 = min(upper_bound, lower_bound + min_span)
            else:
                y0 = max(lower_bound, upper_bound - min_span)
    return (float(y0), float(y1))


def padded_numeric_limits(
    values: Sequence[float], *, min_span: float = 10.0, pad_fraction: float = 0.15
) -> tuple[float, float]:
    """Return readable limits for dimensional values without forcing zero."""
    vals = _finite(values)
    if vals.size == 0:
        return (0.0, float(min_span))
    vmin, vmax = float(np.min(vals)), float(np.max(vals))
    shown_span = max(vmax - vmin, float(min_span))
    mid = 0.5 * (vmin + vmax)
    half = 0.5 * shown_span * (1.0 + 2.0 * pad_fraction)
    return (mid - half, mid + half)


def rta_trace_styles(
    focus: str,
    curves: Mapping[str, Sequence[float]],
) -> dict[str, dict[str, float | str]]:
    """Return line hierarchy, strongly muting negligible secondary curves."""
    focus = str(focus).upper()
    if focus not in RTA_KINDS:
        raise ValueError(f"focus must be one of {RTA_KINDS}, got {focus!r}")
    styles: dict[str, dict[str, float | str]] = {}
    secondary_dashes = {"R": "solid", "T": "dash", "A": "dot"}
    for kind in RTA_KINDS:
        vals = _finite(curves[kind])
        negligible = bool(
            vals.size
            and float(np.max(np.abs(vals))) < 0.02
            and float(np.max(vals) - np.min(vals)) < 0.01
        )
        if kind == focus:
            styles[kind] = {"linewidth": 2.8, "alpha": 1.0, "dash": "solid"}
        elif negligible:
            styles[kind] = {"linewidth": 1.0, "alpha": 0.24, "dash": secondary_dashes[kind]}
        else:
            styles[kind] = {"linewidth": 1.45, "alpha": 0.48, "dash": secondary_dashes[kind]}
    return styles
