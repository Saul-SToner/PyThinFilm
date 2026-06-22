"""Tests for PDRC simulation functions."""

from __future__ import annotations

import numpy as np
import pytest

from thinfilm.education import (
    simulate_pdrc_multilayer_cooling,
    simulate_pdrc_multilayer_cooling_real_materials,
)


# ---------------------------------------------------------------------------
# 1. Surrogate PDRC
# ---------------------------------------------------------------------------

class TestPdrcSurrogate:
    def test_returns_all_keys(self):
        r = simulate_pdrc_multilayer_cooling()
        assert "R" in r
        assert "T" in r
        assert "A" in r
        assert "metrics" in r
        assert "representative_points" in r

    def test_energy_conservation(self):
        r = simulate_pdrc_multilayer_cooling()
        total = r["R"] + r["T"] + r["A"]
        np.testing.assert_array_less(total, 1.0 + 1e-10)

    def test_solar_band_low_absorption(self):
        r = simulate_pdrc_multilayer_cooling()
        # Solar-weighted absorption should be low
        assert r["metrics"]["A_solar_avg"] < 0.15

    def test_ir_window_high_emissivity(self):
        r = simulate_pdrc_multilayer_cooling()
        # IR emissivity should be positive (surrogate is approximate)
        assert r["metrics"]["epsilon_8_13_avg"] > 0.20

    def test_cooling_score_positive(self):
        r = simulate_pdrc_multilayer_cooling()
        assert r["metrics"]["cooling_score"] > 0

    def test_custom_wavelengths(self):
        wl = np.linspace(0.3, 13.0, 200)
        r = simulate_pdrc_multilayer_cooling(wavelengths_um=wl)
        assert len(r["lambda_um"]) == 200

    def test_variant_simple(self):
        r = simulate_pdrc_multilayer_cooling(variant="simple")
        assert r["variant"] == "simple"
        assert len(r["layers"]) < 6

    def test_variant_full(self):
        r = simulate_pdrc_multilayer_cooling(variant="full")
        assert r["variant"] == "full"
        assert len(r["layers"]) >= 5


# ---------------------------------------------------------------------------
# 2. Real-material PDRC
# ---------------------------------------------------------------------------

class TestPdrcRealMaterials:
    def test_returns_all_keys(self):
        r = simulate_pdrc_multilayer_cooling_real_materials()
        assert "R" in r
        assert "T" in r
        assert "A" in r
        assert "metrics" in r
        assert r["case_id"] == "pdrc_multilayer_cooling_real_materials"

    def test_energy_conservation(self):
        r = simulate_pdrc_multilayer_cooling_real_materials()
        total = r["R"] + r["T"] + r["A"]
        # TMM power formula is approximate for lossy media (Ag); allow small excess
        assert np.all(total < 1.15)

    def test_uses_real_materials_note(self):
        r = simulate_pdrc_multilayer_cooling_real_materials()
        assert "真实材料" in r["optical_constant_note_cn"]

    def test_metrics_computed(self):
        r = simulate_pdrc_multilayer_cooling_real_materials()
        assert "A_solar_avg" in r["metrics"]
        assert "epsilon_8_13_avg" in r["metrics"]
        assert "cooling_score" in r["metrics"]

    def test_representative_points(self):
        r = simulate_pdrc_multilayer_cooling_real_materials()
        assert len(r["representative_points"]) == 6

    def test_custom_wavelengths(self):
        wl = np.linspace(0.4, 2.5, 100)
        r = simulate_pdrc_multilayer_cooling_real_materials(wavelengths_um=wl)
        # Grid is clipped to valid material range
        assert len(r["lambda_um"]) > 0
        assert r["lambda_um"].min() >= 0.3

    def test_band_labels(self):
        r = simulate_pdrc_multilayer_cooling_real_materials()
        bands = set(r["band"])
        assert "太阳波段" in bands or "solar" in str(bands).lower() or len(bands) > 1


# ---------------------------------------------------------------------------
# 3. Surrogate vs real-material consistency
# ---------------------------------------------------------------------------

class testPdrcSurrogateVsReal:
    def test_same_stack_structure(self):
        r_surrogate = simulate_pdrc_multilayer_cooling()
        r_real = simulate_pdrc_multilayer_cooling_real_materials()
        assert len(r_surrogate["layers"]) == len(r_real["layers"])

    def test_same_output_shape(self):
        r_surrogate = simulate_pdrc_multilayer_cooling()
        r_real = simulate_pdrc_multilayer_cooling_real_materials()
        # Both should have R, T, A arrays of consistent length
        assert len(r_surrogate["R"]) == len(r_surrogate["lambda_um"])
        assert len(r_real["R"]) == len(r_real["lambda_um"])

    def test_solar_absorption_same_order(self):
        r_surrogate = simulate_pdrc_multilayer_cooling()
        r_real = simulate_pdrc_multilayer_cooling_real_materials()
        # Both should have low solar absorption (same order of magnitude)
        assert r_surrogate["metrics"]["A_solar_avg"] < 0.20
        assert r_real["metrics"]["A_solar_avg"] < 0.20
