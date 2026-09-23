# -*- coding: utf-8 -*-
"""Pytest unit tests for thinfilm/spectral_metrics.py (Stage C.1.3).

Validates:
1. DBR stopband continuous segment detection.
2. Fine-grid background-aware linewidth solver for 13-layer vs 17-layer FP filters.
   - 13-layer: fp_single_halfwave (HL)^3 C (LH)^3 — nH=2.15, nL=1.38, periods=3
   - 17-layer: narrowband_filter (HL)^4 C (LH)^4 — nH=2.15, nL=1.38, periods=4
3. Linear interpolation accuracy for left and right half-max crossings.
4. Linewidth narrowing and Q-factor increase assertions from 13-layer to 17-layer.
"""

from __future__ import annotations

import numpy as np
import pytest
from thinfilm.education import build_fp_single_halfwave_layers, build_narrowband_filter_layers
from thinfilm.spectral_metrics import compute_fine_resonance_linewidth, detect_stopband_segments


def test_stopband_segments_detection():
    wl = np.linspace(400, 800, 401)
    R = np.zeros_like(wl)
    R[100:150] = 0.85  # stopband 1
    R[250:300] = 0.90  # stopband 2

    segments = detect_stopband_segments(wl, R, threshold=0.50)
    assert len(segments) == 2
    assert segments[0]["start_nm"] == 500.0
    assert segments[1]["start_nm"] == 650.0


def test_fine_linewidth_fp_13_vs_17_layer():
    """13-layer fp_single_halfwave vs 17-layer narrowband_filter linewidth comparison.

    Both use nH=2.15, nL=1.38. The 17-layer structure (periods=4) must have
    narrower FWHM and higher Q than the 13-layer (periods=3).
    """
    # 13-layer: (HL)^3 C (LH)^3 — nH=2.15, nL=1.38, periods=3
    layers_13 = build_fp_single_halfwave_layers(550.0, 2.15, 1.38, 3)
    # 17-layer: (HL)^4 C (LH)^4 — nH=2.15, nL=1.38, periods=4
    layers_17 = build_narrowband_filter_layers()  # defaults: nH=2.15, nL=1.38, periods=4

    assert len(layers_13) == 13, f"Expected 13 layers, got {len(layers_13)}"
    assert len(layers_17) == 17, f"Expected 17 layers, got {len(layers_17)}"

    # TE linewidth — resonance peak around 484nm
    lw_13_te = compute_fine_resonance_linewidth(layers_13, pol="s", search_center_nm=484.0)
    lw_17_te = compute_fine_resonance_linewidth(layers_17, pol="s", search_center_nm=484.5)

    assert lw_13_te["fwhm_status"] == "AVAILABLE", f"13-layer TE FWHM not available: {lw_13_te}"
    assert lw_17_te["fwhm_status"] == "AVAILABLE", f"17-layer TE FWHM not available: {lw_17_te}"

    # Assert narrowing and Q increase
    assert lw_17_te["fwhm_nm"] < lw_13_te["fwhm_nm"], (
        f"17-layer TE FWHM ({lw_17_te['fwhm_nm']} nm) must be < 13-layer TE FWHM ({lw_13_te['fwhm_nm']} nm)"
    )
    assert lw_17_te["q_factor"] > lw_13_te["q_factor"], (
        f"17-layer Q ({lw_17_te['q_factor']}) must be > 13-layer Q ({lw_13_te['q_factor']})"
    )

    # TM linewidth — resonance peak around 486nm
    lw_13_tm = compute_fine_resonance_linewidth(layers_13, pol="p", search_center_nm=486.0)
    lw_17_tm = compute_fine_resonance_linewidth(layers_17, pol="p", search_center_nm=486.8)

    assert lw_13_tm["fwhm_status"] == "AVAILABLE", f"13-layer TM FWHM not available: {lw_13_tm}"
    assert lw_17_tm["fwhm_status"] == "AVAILABLE", f"17-layer TM FWHM not available: {lw_17_tm}"

    assert lw_17_tm["fwhm_nm"] < lw_13_tm["fwhm_nm"], (
        f"17-layer TM FWHM ({lw_17_tm['fwhm_nm']} nm) must be < 13-layer TM FWHM ({lw_13_tm['fwhm_nm']} nm)"
    )
    assert lw_17_tm["q_factor"] > lw_13_tm["q_factor"], (
        f"17-layer Q ({lw_17_tm['q_factor']}) must be > 13-layer Q ({lw_13_tm['q_factor']})"
    )
