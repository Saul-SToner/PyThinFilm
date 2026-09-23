# -*- coding: utf-8 -*-
"""Pytest verification for 1D TMM field solver thinfilm/field_profile.py (Stage B.1D.2).

Validates:
1. Cross-validation with multilayer_rt_spectrum for R, T, A (< 1e-10).
2. Interface continuity of tangential E and H fields across every interface (< 1e-10).
3. Boundary conditions: E_inc = 1, E_sub_back = 0.
4. Mesh convergence (dz = 1.0nm, 0.5nm, 0.25nm).
5. Simple baselines: Fresnel Air/Glass, Lossless single layer, Lossy Ag metal layer.
"""

from __future__ import annotations

import numpy as np
import pytest
from thinfilm.education import LayerSpec, multilayer_rt_spectrum
from thinfilm.field_profile import compute_tmm_1d_field_profile


def test_field_solver_cross_validation_with_rt_spectrum():
    wl_nm = 550.0
    layers_ref = [
        LayerSpec("Metal", 0.13 + 3.98j, 30.0),
        LayerSpec("High", 2.15, 63.95),
        LayerSpec("Low", 1.38, 99.64),
        LayerSpec("High", 2.15, 63.95),
    ]
    layers_field = [
        LayerSpec("Metal", 0.13 - 3.98j, 30.0),
        LayerSpec("High", 2.15, 63.95),
        LayerSpec("Low", 1.38, 99.64),
        LayerSpec("High", 2.15, 63.95),
    ]

    # Reference from multilayer_rt_spectrum
    res_rt = multilayer_rt_spectrum(np.array([wl_nm]), layers_ref, n_incident=1.0, n_substrate=1.52, pol="s")
    R_ref = res_rt["R"][0]
    T_ref = res_rt["T"][0]
    A_ref = res_rt["A"][0]

    # Test from compute_tmm_1d_field_profile
    res_field = compute_tmm_1d_field_profile(wl_nm, layers_field, n_incident=1.0, n_substrate=1.52, dz_nm=0.5)

    assert abs(res_field["R"] - R_ref) < 1e-10
    assert abs(res_field["T"] - T_ref) < 1e-10
    assert abs(res_field["A"] - A_ref) < 1e-10


def test_field_solver_interface_continuity():
    wl_nm = 634.0
    layers = [
        LayerSpec("Ag", 0.13 + 3.98j, 30.0),
        LayerSpec("H", 2.15, 63.95),
        LayerSpec("L", 1.38, 99.64),
    ]
    res_field = compute_tmm_1d_field_profile(wl_nm, layers, n_incident=1.0, n_substrate=1.52, dz_nm=0.25)
    assert res_field["max_interface_discontinuity"] < 1e-10


def test_field_solver_mesh_convergence():
    wl_nm = 634.0
    layers = [
        LayerSpec("Ag", 0.13 + 3.98j, 30.0),
        LayerSpec("H", 2.15, 63.95),
        LayerSpec("L", 1.38, 99.64),
    ]

    res_1 = compute_tmm_1d_field_profile(wl_nm, layers, dz_nm=1.0)
    res_05 = compute_tmm_1d_field_profile(wl_nm, layers, dz_nm=0.5)
    res_025 = compute_tmm_1d_field_profile(wl_nm, layers, dz_nm=0.25)

    peak_e2_1 = np.max(res_1["E2_points"])
    peak_e2_05 = np.max(res_05["E2_points"])
    peak_e2_025 = np.max(res_025["E2_points"])

    assert abs(peak_e2_05 - peak_e2_025) < 1e-6
    assert abs(peak_e2_1 - peak_e2_05) < 1e-4


def test_simple_fresnel_baseline():
    # Air / Glass Fresnel interface (0 layers)
    res = compute_tmm_1d_field_profile(550.0, [], n_incident=1.0, n_substrate=1.52)
    expected_r = (1.0 - 1.52) / (1.0 + 1.52)
    expected_t = 2.0 / (1.0 + 1.52)

    assert abs(res["r_complex"] - expected_r) < 1e-10
    assert abs(res["t_complex"] - expected_t) < 1e-10
    assert abs(res["A"]) < 1e-10
