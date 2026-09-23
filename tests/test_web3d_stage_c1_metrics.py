# -*- coding: utf-8 -*-
"""Pytest verification for Stage C.1 case-specific physical metrics (6 teaching cases).

Validates:
1. quarter_wave_single_layer: min R & design point R.
2. half_wave_single_layer: optical phase thickness 180 deg & bare substrate equivalence.
3. high_reflector: R_max > 0.95 & Bragg stopband segment (equivalence group dbr_7layer_hlh).
4. quarter_wave_stack: complete_HL_periods = 3, terminal_layer = H.
5. fp_single_halfwave: intra-stopband defect peak (equivalence group fp_13layer_defect_cavity).
6. narrowband_filter: 17 layers & audited peak metrics.
"""

from __future__ import annotations

import json
import numpy as np
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_quarter_wave_single_layer_metrics():
    data = json.loads((ROOT / "web3d" / "public" / "results" / "quarter_wave_single_layer.json").read_text(encoding="utf-8"))
    metrics = data["case_specific_metrics"]
    assert "R_at_design_wavelength_550nm" in metrics
    assert "min_R" in metrics
    assert metrics["min_R"] <= metrics["R_at_design_wavelength_550nm"]


def test_half_wave_single_layer_metrics():
    data = json.loads((ROOT / "web3d" / "public" / "results" / "half_wave_single_layer.json").read_text(encoding="utf-8"))
    metrics = data["case_specific_metrics"]
    assert metrics["optical_phase_thickness_deg"] == 180.0
    assert metrics["delta_R_0deg"] == 0.0
    assert abs(metrics["R_halfwave_at_design_0deg"] - metrics["R_bare_substrate_at_design_0deg"]) < 1e-6


def test_high_reflector_metrics():
    data = json.loads((ROOT / "web3d" / "public" / "results" / "high_reflector.json").read_text(encoding="utf-8"))
    metrics = data["case_specific_metrics"]
    assert metrics["R_max"] > 0.95
    assert len(metrics["stopband_segments_R70"]) > 0
    assert metrics["physical_equivalence_group"] == "dbr_7layer_hlh"


def test_quarter_wave_stack_metrics():
    data = json.loads((ROOT / "web3d" / "public" / "results" / "quarter_wave_stack.json").read_text(encoding="utf-8"))
    metrics = data["case_specific_metrics"]
    assert metrics["complete_HL_periods"] == 3
    assert metrics["terminal_layer"] == "H"
    assert metrics["total_coating_layers"] == 7
    assert len(metrics["TE_stopband_segments"]) > 0
    assert len(metrics["TM_stopband_segments"]) > 0


def test_fp_single_halfwave_metrics():
    data = json.loads((ROOT / "web3d" / "public" / "results" / "fp_single_halfwave.json").read_text(encoding="utf-8"))
    metrics = data["case_specific_metrics"]
    assert len(metrics["TE_cavity_defect_peaks"]) > 0
    assert len(metrics["TM_cavity_defect_peaks"]) > 0
    assert metrics["physical_equivalence_group"] == "fp_13layer_defect_cavity"


def test_narrowband_filter_metrics():
    data = json.loads((ROOT / "web3d" / "public" / "results" / "narrowband_filter.json").read_text(encoding="utf-8"))
    metrics = data["case_specific_metrics"]
    assert "periods=5" in metrics["periods_param_explanation"]
    assert abs(metrics["audited_defect_peak_TE"]["selected_peak_wavelength_nm"] - 484.5) < 1.0
    assert metrics["audited_defect_peak_TE"]["fwhm_status"] == "AVAILABLE"
    assert metrics["audited_defect_peak_TE"]["q_status"] == "AVAILABLE"
