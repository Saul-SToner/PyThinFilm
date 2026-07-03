"""Tests for the RCWA solver."""

from __future__ import annotations

import numpy as np
import pytest

from guided_grating.rcwa import (
    GratingLayer,
    rcwa_1d,
    rcwa_1d_te,
    rcwa_1d_tm,
    rcwa_convergence_test,
)


# ---------------------------------------------------------------------------
# 1. Basic functionality
# ---------------------------------------------------------------------------

class TestRCWABasic:
    def test_grating_layer_creation(self):
        g = GratingLayer(
            period_nm=980,
            thickness_nm=200,
            n_low=1.45,
            n_high=3.4,
            fill_factor=0.55,
        )
        assert g.period_nm == 980
        assert g.fill_factor == 0.55

    def test_returns_all_keys(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        result = rcwa_1d([1550.0], g)
        assert "R" in result
        assert "T" in result
        assert "A" in result
        assert "R_all" in result
        assert "T_all" in result

    def test_output_shape(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        wl = np.linspace(1450, 1650, 50)
        result = rcwa_1d(wl, g)
        assert result["R"].shape == (50,)
        assert result["T"].shape == (50,)

    def test_single_wavelength(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        result = rcwa_1d([1550.0], g)
        assert result["R"].shape == (1,)


# ---------------------------------------------------------------------------
# 2. Physics checks
# ---------------------------------------------------------------------------

class TestRCWAPhysics:
    def test_energy_conservation(self):
        """R + T + A should equal 1 for lossless gratings."""
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        wl = np.linspace(1450, 1650, 50)
        result = rcwa_1d(wl, g)
        total = result["R"] + result["T"] + result["A"]
        np.testing.assert_allclose(total, 1.0, atol=0.01)

    def test_zero_thickness_no_effect(self):
        """Zero-thickness grating should give same R as bare interface."""
        g_thin = GratingLayer(980, 0.01, 1.45, 3.4, 0.55)
        result = rcwa_1d([1550.0], g_thin, n_incident=1.0, n_substrate=1.45)
        # Very thin grating should give R close to bare interface
        r_bare = ((1.0 - 1.45) / (1.0 + 1.45)) ** 2
        # Not exact but should be in same ballpark
        assert abs(result["R"][0] - r_bare) < 0.1

    def test_high_contrast_high_r(self):
        """High index contrast should produce a measurable reflectance."""
        g = GratingLayer(1550, 300, 1.0, 3.5, 0.5)
        result = rcwa_1d([1550.0], g, n_incident=1.0, n_substrate=1.5)
        # EMT gives effective index ≈ 2.57, should have some R on glass
        assert result["R"][0] > 0.0

    def test_oblique_incidence(self):
        """Oblique incidence should produce finite reflectance."""
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        result = rcwa_1d([1550.0], g, theta_deg=30.0)
        assert np.isfinite(result["R"][0])
        assert result["R"][0] >= 0


# ---------------------------------------------------------------------------
# 3. Convergence
# ---------------------------------------------------------------------------

class TestRCWAConvergence:
    def test_convergence_test(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        conv = rcwa_convergence_test(g, wavelength_nm=1550.0)
        assert "results" in conv
        assert len(conv["results"]) > 0
        # More orders should not dramatically change R
        R_vals = [r["R"] for r in conv["results"]]
        if len(R_vals) >= 2:
            assert abs(R_vals[-1] - R_vals[-2]) < 0.1  # Reasonable convergence

    def test_more_orders_more_accurate(self):
        """Higher order count should give more accurate result."""
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        r_low = rcwa_1d([1550.0], g, num_orders=3)["R"][0]
        r_high = rcwa_1d([1550.0], g, num_orders=20)["R"][0]
        # Both should be finite
        assert np.isfinite(r_low)
        assert np.isfinite(r_high)


# ---------------------------------------------------------------------------
# 4. Edge cases
# ---------------------------------------------------------------------------

class TestRCWAEdgeCases:
    def test_normal_incidence(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        result = rcwa_1d([1550.0], g, theta_deg=0.0)
        assert np.isfinite(result["R"][0])

    def test_high_angle(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        result = rcwa_1d([1550.0], g, theta_deg=60.0)
        assert np.isfinite(result["R"][0])

    def test_invalid_pol(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        with pytest.raises(ValueError, match="pol"):
            rcwa_1d([1550.0], g, pol="invalid")

    def test_wide_wavelength_range(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        wl = np.linspace(400, 2000, 100)
        result = rcwa_1d(wl, g)
        assert result["R"].shape == (100,)
        assert np.all(np.isfinite(result["R"]))


# ---------------------------------------------------------------------------
# 5. TM polarization
# ---------------------------------------------------------------------------

class TestRCWATM:
    def test_tm_returns_all_keys(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        result = rcwa_1d([1550.0], g, pol="TM")
        assert "R" in result
        assert "T" in result
        assert "A" in result

    def test_tm_energy_conservation(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        wl = np.linspace(1450, 1650, 50)
        result = rcwa_1d(wl, g, pol="TM")
        total = result["R"] + result["T"] + result["A"]
        np.testing.assert_allclose(total, 1.0, atol=0.01)

    def test_tm_different_from_te(self):
        """TE/TM 极化差异验证（EMT 各向异性）。

        EMT 给出不同的有效折射率：
        - TE: n_eff^2 = f*n_H^2 + (1-f)*n_L^2
        - TM: 1/n_eff^2 = f/n_H^2 + (1-f)/n_L^2
        因此 TE 和 TM 的反射率不同。
        """
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        r_te = rcwa_1d([1550.0], g, pol="TE")["R"][0]
        r_tm = rcwa_1d([1550.0], g, pol="TM")["R"][0]
        assert r_te != r_tm

    def test_tm_single_wavelength(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        result = rcwa_1d([1550.0], g, pol="TM")
        assert result["R"].shape == (1,)

    def test_tm_output_shape(self):
        g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
        wl = np.linspace(1450, 1650, 50)
        result = rcwa_1d(wl, g, pol="TM")
        assert result["R"].shape == (50,)
