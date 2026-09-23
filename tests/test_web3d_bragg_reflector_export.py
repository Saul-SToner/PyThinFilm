# -*- coding: utf-8 -*-
"""Pytest verification for bragg_reflector exported JSON data (Stage B.1B).

Validates:
1. Re-invokes Python TMM core simulate_report_design('bragg_reflector').
2. Checks web3d/public/results/bragg_reflector.json against direct Python calculation.
3. Strict monotonicity of wavelength array.
4. Absence of NaN / Inf values.
5. Full spectrum energy conservation: max(abs(R + T + A - 1.0)) < 1e-6 for TE and TM.
6. 550nm design point match and high reflection band peak reflectance.
"""

from __future__ import annotations

import json
import numpy as np
import pytest
from pathlib import Path
from thinfilm import simulate_report_design

ROOT = Path(__file__).resolve().parent.parent


def test_bragg_reflector_python_export_verification():
    json_path = ROOT / "web3d" / "public" / "results" / "bragg_reflector.json"
    assert json_path.exists(), f"bragg_reflector.json file missing at {json_path}"

    # Load JSON
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Direct calculation from Python engine
    res_te = simulate_report_design("bragg_reflector", theta_deg=45.0, pol="s")
    res_tm = simulate_report_design("bragg_reflector", theta_deg=45.0, pol="p")

    # 1. Wavelength array strictly increasing
    wl_json = np.array(data["wavelength_nm"])
    wl_py = res_te["wavelength_nm"]

    assert len(wl_json) == len(wl_py)
    assert np.all(np.diff(wl_json) > 0), "Wavelength array is not strictly increasing"

    # 2. No NaN / Inf
    for pol_key in ["TE", "TM"]:
        r_arr = np.array(data[pol_key]["R"])
        t_arr = np.array(data[pol_key]["T"])
        a_arr = np.array(data[pol_key]["A"])

        assert not np.any(np.isnan(r_arr)), f"{pol_key} R contains NaN"
        assert not np.any(np.isnan(t_arr)), f"{pol_key} T contains NaN"
        assert not np.any(np.isnan(a_arr)), f"{pol_key} A contains NaN"

        assert not np.any(np.isinf(r_arr)), f"{pol_key} R contains Inf"
        assert not np.any(np.isinf(t_arr)), f"{pol_key} T contains Inf"
        assert not np.any(np.isinf(a_arr)), f"{pol_key} A contains Inf"

        # Bounds check
        assert np.all((r_arr >= 0.0) & (r_arr <= 1.0))
        assert np.all((t_arr >= 0.0) & (t_arr <= 1.0))
        assert np.all((a_arr >= 0.0) & (a_arr <= 1.0))

        # 3. Energy Conservation check: max(abs(R + T + A - 1.0)) < 1e-6
        sum_arr = r_arr + t_arr + a_arr
        max_residual = np.max(np.abs(sum_arr - 1.0))
        assert max_residual < 1e-6, f"{pol_key} max energy residual {max_residual} exceeds 1e-6"

    # 4. Point-by-point matching with direct Python core calculation
    r_te_py = res_te["R"]
    t_te_py = res_te["T"]
    r_te_json = np.array(data["TE"]["R"])
    t_te_json = np.array(data["TE"]["T"])

    assert np.max(np.abs(r_te_json - r_te_py)) < 1e-5
    assert np.max(np.abs(t_te_json - t_te_py)) < 1e-5

    r_tm_py = res_tm["R"]
    t_tm_py = res_tm["T"]
    r_tm_json = np.array(data["TM"]["R"])
    t_tm_json = np.array(data["TM"]["T"])

    assert np.max(np.abs(r_tm_json - r_tm_py)) < 1e-5
    assert np.max(np.abs(t_tm_json - t_tm_py)) < 1e-5

    # 5. Layer count check (7 layers: H L H L H L H)
    assert len(data["layers"]) == 7
    assert data["layers"][0]["type"] == "H"
    assert data["layers"][1]["type"] == "L"

    # 6. Peak reflectance check in DBR high reflection band
    idx_550 = int(np.argmin(np.abs(wl_py - 550.0)))
    assert wl_json[idx_550] == 550.0
    assert data["design_point_550nm"]["TE"]["R"] > 0.70 # DBR high reflectance band
