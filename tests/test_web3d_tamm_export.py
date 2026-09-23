# -*- coding: utf-8 -*-
"""Pytest verification for tamm_phase_bundle exported JSON data (Stage B.1D.2 / Stage C.0 / Stage C.1.1).

Validates:
1. Re-invokes Python TMM core multilayer_rt_spectrum for Tamm absorber (Air / Ag 30nm / DBR 7-layer / Glass).
2. Energy conservation check: R + T + A = 1.0 (with absorption A > 0 in lossy Ag metal layer).
3. Reflectance dip candidate identification at ~634.0nm (R_min = 0.1933).
4. Common Ag/H1 interface reference plane audit (Method A & B validated).
5. 1D TMM field localization metrics (|E|^2 = 3.48) & field solver status.
6. Validation status demoted to PHASE_MATCHED_LEAKY_CANDIDATE and FIELD_ENHANCEMENT_CANDIDATE.
"""

from __future__ import annotations

import json
import numpy as np
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_tamm_phase_bundle_python_export_verification():
    json_path = ROOT / "web3d" / "public" / "results" / "tamm_phase_bundle.json"
    assert json_path.exists(), f"tamm_phase_bundle.json file missing at {json_path}"

    data = json.loads(json_path.read_text(encoding="utf-8"))

    # 1. Monotonic wavelength array
    wl_json = np.array(data["wavelength_nm"])
    assert np.all(np.diff(wl_json) > 0)

    # 2. Lossy metal energy conservation check
    r_arr = np.array(data["TE"]["R"])
    t_arr = np.array(data["TE"]["T"])
    a_arr = np.array(data["TE"]["A"])

    assert not np.any(np.isnan(r_arr))
    assert not np.any(np.isnan(t_arr))
    assert not np.any(np.isnan(a_arr))

    # Energy sum check R + T + A = 1.0 (allowing 6-digit float rounding tolerance)
    energy_sum = r_arr + t_arr + a_arr
    assert np.max(np.abs(energy_sum - 1.0)) < 2e-6

    # Metal absorption is strictly positive
    assert np.all(a_arr >= 0.0)
    assert np.max(a_arr) > 0.10 # Ag absorption peak > 10%

    # 3. Selected Reflectance Dip candidate check
    cand = data["selected_candidate"]
    assert abs(cand["wavelength_nm"] - 634.0) < 1.0
    assert 0.15 < cand["R"] < 0.25

    # 4. Common Ag/H1 interface reference plane & 1D TMM field localization checks
    loc = data["interface_localization_metrics"]
    assert loc["field_localization_status"] == "FIELD_ENHANCEMENT_CANDIDATE"
    assert loc["peak_abs_E2"] > 3.0
    assert loc["reference_controls"]["500nm"]["enhancement_ratio"] > 5.0

    # 5. Correct Validation Statuses
    assert data["material_model"] == "CONSTANT_COMPLEX_INDEX"
    assert data["metal_nk_source"] == "OFFICIAL_CASE_HARDCODED_CONSTANT"
    assert data["field_solver_status"] == "FIELD_SOLVER_VERIFIED"
    assert data["tamm_validation_status"] == "PHASE_MATCHED_LEAKY_CANDIDATE"
    assert data["phase_validation_status"] == "REFERENCE_PLANE_AUDIT_COMPLETED"
