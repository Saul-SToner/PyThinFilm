"""Tests for simulate_report_design covering all design_type branches."""

from __future__ import annotations

import numpy as np
import pytest

from thinfilm.education import (
    ReportDesignParams,
    simulate_report_design,
    simulate_report_design_from_params,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_result(design_type: str, **overrides) -> dict:
    """Run simulate_report_design with given type and return result."""
    return simulate_report_design(design_type=design_type, **overrides)


def _check_result(result: dict, design_type: str) -> None:
    """Common assertions for any simulate_report_design result."""
    assert result["design_type"] == design_type
    assert "wavelength_nm" in result
    assert "R" in result
    assert "T" in result
    assert "A" in result
    assert len(result["R"]) == len(result["wavelength_nm"])
    assert np.all(result["R"] >= 0)
    assert np.all(result["R"] <= 1)
    assert np.all(result["T"] >= 0)
    assert np.all(result["T"] <= 1)
    assert "summary" in result
    assert "layers" in result


# ---------------------------------------------------------------------------
# 1. Single-layer designs
# ---------------------------------------------------------------------------

class TestSingleLayerDesigns:
    def test_quarter_wave_single_layer(self):
        r = _base_result("quarter_wave_single_layer")
        _check_result(r, "quarter_wave_single_layer")

    def test_half_wave_single_layer(self):
        r = _base_result("half_wave_single_layer")
        _check_result(r, "half_wave_single_layer")

    def test_single_ar(self):
        r = _base_result("single_ar")
        _check_result(r, "single_ar")
        # Single AR should reduce R at design wavelength
        assert r["summary"]["R_at_lambda0"] < 0.05

    def test_single_ar_alias(self):
        r = _base_result("single_antireflection")
        _check_result(r, "single_antireflection")

    def test_qw_alias(self):
        r = _base_result("qw_single_layer")
        _check_result(r, "qw_single_layer")


# ---------------------------------------------------------------------------
# 2. Multi-layer AR
# ---------------------------------------------------------------------------

class TestMultiLayerAR:
    def test_double_ar(self):
        r = _base_result("double_ar")
        _check_result(r, "double_ar")

    def test_double_ar_alias(self):
        r = _base_result("quarter_wave_double_layer")
        _check_result(r, "quarter_wave_double_layer")

    def test_triple_ar(self):
        r = _base_result("triple_ar")
        _check_result(r, "triple_ar")

    def test_porous_double_ar(self):
        r = _base_result("porous_double_ar")
        _check_result(r, "porous_double_ar")


# ---------------------------------------------------------------------------
# 3. High-reflectance designs
# ---------------------------------------------------------------------------

class TestHighReflector:
    def test_high_reflector(self):
        r = _base_result("high_reflector")
        _check_result(r, "high_reflector")
        # High reflector should have high R near design wavelength
        wl = r["wavelength_nm"]
        center_mask = np.abs(wl - 550) < 30
        assert np.mean(r["R"][center_mask]) > 0.90

    def test_quarter_wave_stack(self):
        r = _base_result("quarter_wave_stack")
        _check_result(r, "quarter_wave_stack")

    def test_bragg_reflector(self):
        r = _base_result("bragg_reflector")
        _check_result(r, "bragg_reflector")

    def test_more_periods_increase_r(self):
        r3 = _base_result("high_reflector", periods=3)
        r6 = _base_result("high_reflector", periods=6)
        # More periods should give higher peak R
        assert np.max(r6["R"]) > np.max(r3["R"])


# ---------------------------------------------------------------------------
# 4. F-P filter designs
# ---------------------------------------------------------------------------

class TestFPFilter:
    def test_fp_single_halfwave(self):
        r = _base_result("fp_single_halfwave")
        _check_result(r, "fp_single_halfwave")

    def test_fp_filter(self):
        r = _base_result("fp_filter")
        _check_result(r, "fp_filter")

    def test_narrowband_filter(self):
        r = _base_result("narrowband_filter")
        _check_result(r, "narrowband_filter")

    def test_fp_double_halfwave(self):
        r = _base_result("fp_double_halfwave")
        _check_result(r, "fp_double_halfwave")

    def test_fp_filter_has_transmission_peak(self):
        r = _base_result("fp_filter")
        # F-P filter should have a narrow transmission peak
        max_t_idx = np.argmax(r["T"])
        assert r["T"][max_t_idx] > 0.3


# ---------------------------------------------------------------------------
# 5. Gradient / moth-eye
# ---------------------------------------------------------------------------

class TestGradientDesigns:
    def test_moth_eye(self):
        r = _base_result("moth_eye_effective_gradient")
        _check_result(r, "moth_eye_effective_gradient")

    def test_moth_eye_alias(self):
        r = _base_result("moth_eye_gradient")
        _check_result(r, "moth_eye_gradient")


# ---------------------------------------------------------------------------
# 6. Rugate filter
# ---------------------------------------------------------------------------

class TestRugateFilter:
    def test_rugate_filter(self):
        r = _base_result("rugate_filter")
        _check_result(r, "rugate_filter")

    def test_rugate_with_total_layers(self):
        r = _base_result("rugate_filter", total_layers=48, periods=6)
        _check_result(r, "rugate_filter")

    def test_rugate_invalid_total_layers(self):
        with pytest.raises(ValueError, match="divisible"):
            _base_result("rugate_filter", total_layers=50, periods=6)


# ---------------------------------------------------------------------------
# 7. Beamsplitter
# ---------------------------------------------------------------------------

class TestBeamsplitter:
    def test_neutral_beamsplitter(self):
        r = _base_result("neutral_beamsplitter")
        _check_result(r, "neutral_beamsplitter")

    def test_beamsplitter_alias(self):
        r = _base_result("beamsplitter")
        _check_result(r, "beamsplitter")

    def test_beamsplitter_has_moderate_r(self):
        r = _base_result("neutral_beamsplitter")
        # Beamsplitter should have R around 0.5
        assert 0.2 < r["summary"]["R_at_lambda0"] < 0.8


# ---------------------------------------------------------------------------
# 8. Oblique incidence
# ---------------------------------------------------------------------------

class TestObliqueIncidence:
    def test_30deg(self):
        r = _base_result("single_ar", theta_deg=30.0)
        _check_result(r, "single_ar")

    def test_60deg_s_pol(self):
        r = _base_result("single_ar", theta_deg=60.0, pol="s")
        _check_result(r, "single_ar")


# ---------------------------------------------------------------------------
# 9. Energy conservation
# ---------------------------------------------------------------------------

class TestEnergyConservation:
    @pytest.mark.parametrize("design_type", [
        "single_ar",
        "double_ar",
        "high_reflector",
        "fp_filter",
        "neutral_beamsplitter",
    ])
    def test_r_plus_t_leq_1(self, design_type):
        r = _base_result(design_type)
        np.testing.assert_array_less(r["R"] + r["T"], 1.0 + 1e-10)


# ---------------------------------------------------------------------------
# 10. ReportDesignParams dataclass
# ---------------------------------------------------------------------------

class TestReportDesignParams:
    def test_default_values(self):
        p = ReportDesignParams()
        assert p.design_type == "single_ar"
        assert p.lambda0_nm == 550.0
        assert p.pol == "p"

    def test_from_params(self):
        p = ReportDesignParams(design_type="single_ar", lambda0_nm=600)
        r = simulate_report_design_from_params(p)
        _check_result(r, "single_ar")

    def test_params_matches_positional(self):
        r1 = simulate_report_design("single_ar", lambda0_nm=600, n_low=1.45)
        p = ReportDesignParams(design_type="single_ar", lambda0_nm=600, n_low=1.45)
        r2 = simulate_report_design_from_params(p)
        np.testing.assert_allclose(r1["R"], r2["R"], rtol=1e-12)

    def test_invalid_design_type(self):
        p = ReportDesignParams(design_type="nonexistent")
        with pytest.raises(ValueError, match="Unsupported"):
            simulate_report_design_from_params(p)


# ---------------------------------------------------------------------------
# 11. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_custom_wavelength_grid(self):
        wl = np.linspace(400, 800, 50)
        r = _base_result("single_ar", wavelengths_nm=wl)
        assert len(r["wavelength_nm"]) == 50

    def test_single_wavelength(self):
        r = _base_result("single_ar", wavelengths_nm=[550.0])
        assert len(r["R"]) == 1

    def test_output_keys(self):
        r = _base_result("single_ar")
        expected_keys = {
            "design_type", "theta_deg", "pol", "lambda0_nm",
            "n_incident", "n_substrate", "layers",
            "wavelength_nm", "R", "T", "A",
            "r_complex", "t_complex", "summary",
        }
        assert expected_keys.issubset(set(r.keys()))
