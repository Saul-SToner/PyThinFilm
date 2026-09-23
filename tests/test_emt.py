# -*- coding: utf-8 -*-
"""Tests for the Effective Medium Theory (EMT) module."""

from __future__ import annotations

import numpy as np
import pytest

from guided_grating.emt import (
    GratingLayer,
    emt_effective_index_te,
    emt_effective_index_tm,
    check_emt_applicability,
    emt_layer_spectrum,
    rcwa_1d,
)


class TestEMTBasic:
    def test_grating_layer_creation(self):
        g = GratingLayer(
            period_nm=200.0,
            thickness_nm=400.0,
            n_low=1.0,
            n_high=1.5,
            fill_factor=0.5,
        )
        assert g.period_nm == 200.0
        assert g.fill_factor == 0.5
        assert g.n_low == 1.0

    def test_effective_index_equations_lossless(self):
        # TE: n_eff = sqrt(0.5 * 1.5^2 + 0.5 * 1.0^2) = sqrt(1.125 + 0.5) = sqrt(1.625) ≈ 1.27475
        n_te = emt_effective_index_te(1.0, 1.5, 0.5)
        np.testing.assert_allclose(np.real(n_te), np.sqrt(1.625), atol=1e-6)
        
        # TM: 1/n_eff^2 = 0.5/1.5^2 + 0.5/1.0^2 = 0.5/2.25 + 0.5 = 0.22222 + 0.5 = 0.72222
        # n_eff = sqrt(1 / 0.72222) = sqrt(1.3846) ≈ 1.1767
        n_tm = emt_effective_index_tm(1.0, 1.5, 0.5)
        np.testing.assert_allclose(np.real(n_tm), 1.0 / np.sqrt(0.5 / 2.25 + 0.5), atol=1e-6)

    def test_applicability_check(self):
        # Case 1: conservative teaching (rho <= 0.1)
        res1 = check_emt_applicability(200.0, 1.0, 1.5, 3000.0)
        assert res1["status"] == "conservative_teaching"
        assert res1["is_valid"] is True
        assert res1["rho"] == 1.5 * 200.0 / 3000.0
        
        # Case 2: moderate error (0.1 < rho < 0.5)
        res2 = check_emt_applicability(200.0, 1.0, 1.5, 1550.0)
        assert res2["status"] == "moderate_error"
        assert res2["is_valid"] is True

        # Case 3: high risk (0.5 <= rho < 1.0)
        res3 = check_emt_applicability(600.0, 1.0, 1.5, 1550.0)
        assert res3["status"] == "high_risk"
        assert res3["is_valid"] is False

        # Case 4: rejected (rho >= 1.0)
        res4 = check_emt_applicability(1200.0, 1.0, 1.5, 1550.0)
        assert res4["status"] == "rejected"
        assert res4["is_valid"] is False

    def test_emt_layer_spectrum_te_returns_keys(self):
        g = GratingLayer(200.0, 400.0, 1.0, 1.5, 0.5)
        res = emt_layer_spectrum([1550.0], g, pol="TE")
        assert "R" in res
        assert "T" in res
        assert "A" in res
        assert "energy_residue" in res
        assert res["R"].shape == (1,)
        assert res["T"].shape == (1,)
        assert res["A"].shape == (1,)
        assert res["energy_residue"].shape == (1,)

    def test_emt_layer_spectrum_lossless_conservation(self):
        g = GratingLayer(200.0, 400.0, 1.0, 1.5, 0.5)
        wl = np.linspace(1450.0, 1650.0, 50)
        res = emt_layer_spectrum(wl, g, pol="TE")
        
        # Lossless means A should be exactly 0
        np.testing.assert_allclose(res["A"], 0.0, atol=1e-12)
        # Check raw residue (R + T - 1)
        np.testing.assert_allclose(res["energy_residue"], 0.0, atol=1e-5)
        # R + T should be exactly 1.0
        np.testing.assert_allclose(res["R"] + res["T"], 1.0, atol=1e-5)


class TestEMTBackwardsCompatibility:
    def test_legacy_rcwa_alias_warns_and_matches_emt(self):
        g = GratingLayer(200.0, 400.0, 1.0, 1.5, 0.5)
        with pytest.deprecated_call():
            res = rcwa_1d([1550.0], g, pol="TE", num_orders=15)
        
        # Verify returned structures required by older tests
        assert res.get("model") == "EMT"
        assert "R_all" in res
        assert "T_all" in res
        assert "num_orders" in res
        assert res["num_orders"] == 15
        assert res["R_all"].shape == (31, 1)
        assert res["T_all"].shape == (31, 1)
        np.testing.assert_allclose(res["R_all"][15, 0], res["R"][0])
        np.testing.assert_allclose(res["T_all"][15, 0], res["T"][0])


class TestEMTExtraPhysics:
    def test_oblique_incidence_and_high_angle(self):
        g = GratingLayer(200.0, 400.0, 1.0, 1.5, 0.5)
        # Test oblique angles
        res30 = emt_layer_spectrum([1550.0], g, theta_deg=30.0, pol="TE")
        res60 = emt_layer_spectrum([1550.0], g, theta_deg=60.0, pol="TE")
        assert np.isfinite(res30["R"][0])
        assert np.isfinite(res60["R"][0])
        assert res30["R"][0] >= 0.0
        assert res60["R"][0] >= 0.0

    def test_invalid_pol(self):
        g = GratingLayer(200.0, 400.0, 1.0, 1.5, 0.5)
        with pytest.raises(ValueError, match="pol must be 'TE' or 'TM'"):
            # For emt_layer_spectrum, pol takes 's' or 'p' (or 'TE'/'TM' mapped internally)
            emt_layer_spectrum([1550.0], g, pol="invalid")

    def test_wide_wavelength_range(self):
        g = GratingLayer(200.0, 400.0, 1.0, 1.5, 0.5)
        wl = np.linspace(400.0, 2000.0, 100)
        res = emt_layer_spectrum(wl, g, pol="TE")
        assert res["R"].shape == (100,)
        assert np.all(np.isfinite(res["R"]))

    def test_tm_polarization_properties(self):
        g = GratingLayer(200.0, 400.0, 1.0, 1.5, 0.5)
        wl = np.linspace(1450.0, 1650.0, 50)
        
        # Runs TM
        res_tm = emt_layer_spectrum(wl, g, pol="TM")
        assert "R" in res_tm
        assert "T" in res_tm
        assert "A" in res_tm
        
        # Energy conservation
        np.testing.assert_allclose(res_tm["A"], 0.0, atol=1e-12)
        np.testing.assert_allclose(res_tm["energy_residue"], 0.0, atol=1e-5)
        np.testing.assert_allclose(res_tm["R"] + res_tm["T"], 1.0, atol=1e-5)
        
        # TE and TM difference (anisotropy)
        res_te = emt_layer_spectrum(wl, g, pol="TE")
        assert not np.allclose(res_te["R"], res_tm["R"])

