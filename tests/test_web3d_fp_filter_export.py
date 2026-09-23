# -*- coding: utf-8 -*-
"""Pytest verification for fp_filter exported JSON data (Stage B.1C.1).

Validates:
1. Re-invokes Python TMM core simulate_report_design('fp_filter').
2. Checks web3d/public/results/fp_filter.json against direct Python calculation.
3. Strict monotonicity of wavelength array.
4. Absence of NaN / Inf values.
5. Full spectrum energy conservation: max(abs(R + T + A - 1.0)) < 1e-6 for TE and TM.
6. 13 layers structure (Air / (HL)^3 C (LH)^3 / Glass).
7. Separation of global max T and true intra-stopband defect mode (TE peak T > 0.90 at 484.0nm).
"""

from __future__ import annotations

import json
import numpy as np
import pytest
from pathlib import Path
from thinfilm import simulate_report_design

ROOT = Path(__file__).resolve().parent.parent


def test_fp_filter_python_export_verification():
    json_path = ROOT / "web3d" / "public" / "results" / "fp_filter.json"
    assert json_path.exists(), f"fp_filter.json file missing at {json_path}"

    # Load JSON
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Direct calculation from Python engine
    res_te = simulate_report_design("fp_filter", theta_deg=45.0, pol="s")
    res_tm = simulate_report_design("fp_filter", theta_deg=45.0, pol="p")

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

    # 5. Layer count check (13 layers)
    assert len(data["layers"]) == 13
    assert data["layers"][6]["type"] == "C" # Layer 7 is Cavity Spacer (C)
    assert data["layers"][6]["role"] == "cavity_spacer"

    # 6. Global vs Intra-stopband defect mode metrics check
    assert data["global_transmission_metrics"]["TE"]["wavelength_nm"] == 664.0
    assert data["resonance_metrics"]["TE"]["selected_peak"]["wavelength_nm"] == 484.0
    assert data["resonance_metrics"]["TE"]["selected_peak"]["T_peak"] > 0.90
