# -*- coding: utf-8 -*-
"""Formal spectral metrics and resonance peak linewidth solver for PyThinFilm.

Provides rigorous DBR stopband detection, intra-stopband defect peak search,
fine-grid (<= 0.01nm) spectral re-computation, background-aware half-max level calculation,
linear interpolation half-max crossing determination, and Q-factor calculation.

Used by:
- thinfilm.education
- tools.export_visualization_cases
- tests.test_spectral_metrics
- tests.test_web3d_narrowband_linewidth
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from thinfilm.education import LayerSpec, multilayer_rt_spectrum, build_fp_single_halfwave_layers, build_narrowband_filter_layers


def detect_stopband_segments(wl: np.ndarray, R: np.ndarray, threshold: float = 0.50) -> List[Dict[str, Any]]:
    """Detect continuous stopband segments where reflectance R >= threshold."""
    above_indices = np.where(R >= threshold)[0]
    if len(above_indices) == 0:
        return []

    diffs = np.diff(above_indices)
    split_points = np.where(diffs > 1)[0] + 1
    groups = np.split(above_indices, split_points)

    segments = []
    for g in groups:
        if len(g) == 0:
            continue
        start_idx, end_idx = g[0], g[-1]
        sub_r = R[start_idx : end_idx + 1]
        max_r_idx = start_idx + int(np.argmax(sub_r))

        segments.append({
            "start_index": int(start_idx),
            "end_index": int(end_idx),
            "start_nm": round(float(wl[start_idx]), 2),
            "end_nm": round(float(wl[end_idx]), 2),
            "width_nm": round(float(wl[end_idx] - wl[start_idx]), 2),
            "max_R": round(float(R[max_r_idx]), 6),
            "wavelength_at_max_R_nm": round(float(wl[max_r_idx]), 2)
        })
    return segments


def compute_fine_resonance_linewidth(
    layers: List[LayerSpec],
    n_incident: float = 1.0,
    n_substrate: float = 1.52,
    theta0_deg: float = 45.0,
    pol: str = "s",
    search_center_nm: float = 485.0,
    fine_step_nm: float = 0.01,
    fine_half_span_nm: float = 15.0,
) -> Dict[str, Any]:
    """Compute rigorous background-aware FWHM linewidth and Q-factor on a fine wavelength grid."""
    wl_min = search_center_nm - fine_half_span_nm
    wl_max = search_center_nm + fine_half_span_nm
    num_points = int(round((wl_max - wl_min) / fine_step_nm)) + 1
    wl_fine = np.linspace(wl_min, wl_max, num_points)

    res = multilayer_rt_spectrum(
        wl_fine, layers, n_incident=n_incident, n_substrate=n_substrate, theta0_deg=theta0_deg, pol=pol
    )

    T = res["T"]
    R = res["R"]
    A = res["A"]

    idx_peak = int(np.argmax(T))
    wl_peak = float(wl_fine[idx_peak])
    T_peak = float(T[idx_peak])
    R_peak = float(R[idx_peak])
    A_peak = float(A[idx_peak])

    # Left and right local backgrounds (outer 10% points of span)
    bg_left = float(np.min(T[: max(1, len(T) // 10)]))
    bg_right = float(np.min(T[-max(1, len(T) // 10) :]))
    background_level = float(min(bg_left, bg_right))
    prominence = float(T_peak - background_level)

    # Formal half-max level definition: T_half = T_bg + 0.5 * (T_peak - T_bg)
    half_level = float(background_level + 0.5 * prominence)

    # Find left half crossing
    left_crossings = np.where(T[:idx_peak] <= half_level)[0]
    right_crossings = np.where(T[idx_peak:] <= half_level)[0]

    fwhm_status = "NOT_AVAILABLE"
    q_status = "NOT_AVAILABLE"
    wl_left = None
    wl_right = None
    fwhm_nm = None
    q_factor = None

    if len(left_crossings) > 0 and len(right_crossings) > 0:
        idx_l = left_crossings[-1]
        w1, w2 = wl_fine[idx_l], wl_fine[idx_l + 1]
        t1, t2 = T[idx_l], T[idx_l + 1]
        wl_left = float(w1 + (half_level - t1) * (w2 - w1) / (t2 - t1))

        idx_r = right_crossings[0] + idx_peak
        w1, w2 = wl_fine[idx_r - 1], wl_fine[idx_r]
        t1, t2 = T[idx_r - 1], T[idx_r]
        wl_right = float(w1 + (half_level - t1) * (w2 - w1) / (t2 - t1))

        fwhm_nm = float(wl_right - wl_left)
        q_factor = float(wl_peak / fwhm_nm)
        fwhm_status = "AVAILABLE"
        q_status = "AVAILABLE"

    return {
        "polarization": pol,
        "peak_wavelength_nm": round(wl_peak, 2),
        "peak_transmission": round(T_peak, 6),
        "reflection_at_peak": round(R_peak, 6),
        "absorption_at_peak": round(A_peak, 6),
        "prominence": round(prominence, 6),
        "left_background": round(bg_left, 6),
        "right_background": round(bg_right, 6),
        "background_level": round(background_level, 6),
        "half_level": round(half_level, 6),
        "left_half_crossing_nm": round(wl_left, 3) if wl_left is not None else None,
        "right_half_crossing_nm": round(wl_right, 3) if wl_right is not None else None,
        "fwhm_status": fwhm_status,
        "fwhm_nm": round(fwhm_nm, 4) if fwhm_nm is not None else None,
        "q_status": q_status,
        "q_factor": round(q_factor, 2) if q_factor is not None else None,
        "zero_background_approximation_valid": background_level < 0.01,
        "fine_grid_step_nm": fine_step_nm,
        "fine_grid_span_nm": [wl_min, wl_max]
    }
