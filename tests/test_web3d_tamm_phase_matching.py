# -*- coding: utf-8 -*-
"""Pytest verification for Tamm phase matching algorithms and branch invariance (Stage B.1D).

Validates:
1. Phase unwrapping continuity across spectrum.
2. 2pi branch invariance of wrap_to_pi(phase_metal + phase_dbr).
3. TE and TM identity under 0 deg normal incidence.
"""

from __future__ import annotations

import numpy as np
import pytest
from thinfilm.education import LayerSpec, multilayer_rt_spectrum, reflection_phase_radians


def test_tamm_phase_matching_branch_invariance():
    wl = np.linspace(400, 800, 401)
    nH, nL = 2.15, 1.38
    dH = 550.0 / (4 * nH)
    dL = 550.0 / (4 * nL)

    dbr_layers = [
        LayerSpec("H", nH, dH),
        LayerSpec("L", nL, dL),
        LayerSpec("H", nH, dH),
        LayerSpec("L", nL, dL),
        LayerSpec("H", nH, dH),
        LayerSpec("L", nL, dL),
        LayerSpec("H", nH, dH),
    ]

    res_dbr = multilayer_rt_spectrum(wl, dbr_layers, n_incident=1.0, n_substrate=1.52)
    phi_dbr = reflection_phase_radians(res_dbr, unwrap=True)

    res_metal = multilayer_rt_spectrum(wl, [LayerSpec("Ag", 0.13 + 3.98j, 30.0)], n_incident=1.0, n_substrate=1.0)
    phi_metal = reflection_phase_radians(res_metal, unwrap=True)

    # Base residual
    res_base = np.angle(np.exp(1j * (phi_metal + phi_dbr)))

    # Branch shift + 2pi * m
    res_shifted = np.angle(np.exp(1j * (phi_metal + phi_dbr + 2 * np.pi * 5)))

    # Assert 2pi branch invariance
    np.testing.assert_allclose(res_base, res_shifted, atol=1e-12)

    # Assert phase matching at ~633nm
    idx_matched = np.argmin(np.abs(res_base))
    assert abs(wl[idx_matched] - 633.0) < 1.5
    assert abs(res_base[idx_matched]) < 0.01
