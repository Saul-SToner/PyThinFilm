# -*- coding: utf-8 -*-
"""Pytest verification for Stage C.1 exported JSON files (6 teaching cases).

Validates:
1. JSON results exist for all 6 Stage C.1 teaching cases.
2. Monotonic wavelength arrays.
3. Energy conservation check R + T + A = 1.0 across spectrum.
4. Correct schema fields.
"""

from __future__ import annotations

import json
import numpy as np
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STAGE_C1_CASES = [
    "quarter_wave_single_layer",
    "half_wave_single_layer",
    "high_reflector",
    "quarter_wave_stack",
    "fp_single_halfwave",
    "narrowband_filter"
]


@pytest.mark.parametrize("case_id", STAGE_C1_CASES)
def test_stage_c1_json_exports_validity(case_id: str):
    json_path = ROOT / "web3d" / "public" / "results" / f"{case_id}.json"
    assert json_path.exists(), f"Missing JSON export for {case_id} at {json_path}"

    data = json.loads(json_path.read_text(encoding="utf-8"))

    assert data["case_id"] == case_id
    assert data["calculation_source"] == "python_export"

    wl = np.array(data["wavelength_nm"])
    assert np.all(np.diff(wl) > 0)

    # Energy conservation check R + T + A = 1.0
    r_arr = np.array(data["TE"]["R"])
    t_arr = np.array(data["TE"]["T"])
    a_arr = np.array(data["TE"]["A"])

    energy_sum = r_arr + t_arr + a_arr
    assert np.max(np.abs(energy_sum - 1.0)) < 1e-6
