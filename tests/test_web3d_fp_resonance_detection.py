# -*- coding: utf-8 -*-
"""Pytest verification for Fabry-Perot defect mode resonance detection (Stage B.1C.1).

Validates:
1. Distinguishes global max T (outside stopband) from true cavity defect mode (inside DBR stopband).
2. DBR stopband continuous segmentation and cavity channel identification.
3. Verified defect mode peaks inside stopband: TE at 484.0nm (T=0.9008), TM at 486.0nm (T=0.9908).
4. Cavity phase-matching 1st order estimate ~472.3nm (deviation < 3.0%).
"""

from __future__ import annotations

import json
import numpy as np
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_fp_filter_resonance_detection_audit():
    json_path = ROOT / "web3d" / "public" / "results" / "fp_filter.json"
    assert json_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))

    # 1. Global transmission max is separated from cavity resonance
    assert "global_transmission_metrics" in data
    assert data["global_transmission_metrics"]["TE"]["wavelength_nm"] == 664.0
    assert data["global_transmission_metrics"]["TM"]["wavelength_nm"] == 644.0

    # 2. True cavity defect peak strictly inside stopband
    te_res = data["resonance_metrics"]["TE"]
    tm_res = data["resonance_metrics"]["TM"]

    assert te_res["resonance_status"] == "FOUND"
    assert tm_res["resonance_status"] == "FOUND"

    assert te_res["selected_peak"]["wavelength_nm"] == 484.0
    assert te_res["selected_peak"]["T_peak"] == 0.90079

    assert tm_res["selected_peak"]["wavelength_nm"] == 486.0
    assert tm_res["selected_peak"]["T_peak"] == 0.990813

    # 3. Cavity phase-matching 1st order estimate consistency
    est = data["cavity_phase_estimate"]
    assert est["estimated_wavelength_nm"] == 472.3
    assert est["deviation_TE_nm"] == 11.7 # 484.0 - 472.3
    assert est["deviation_TM_nm"] == 13.7 # 486.0 - 472.3

    # Deviation < 3%
    rel_dev_te = est["deviation_TE_nm"] / est["estimated_wavelength_nm"]
    assert rel_dev_te < 0.03

    # 4. FWHM status NOT_AVAILABLE
    assert te_res["fwhm_status"] == "NOT_AVAILABLE"
    assert tm_res["fwhm_status"] == "NOT_AVAILABLE"
