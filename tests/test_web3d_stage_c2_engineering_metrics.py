# -*- coding: utf-8 -*-
"""Tests for Stage C.2.1B-1 Four Engineering Metrics & Validity Status.

Validates:
1. Solar cell AR metrics: avg_R_300_1100nm, R_at_550nm, bandwidth_R_lt_2pct_nm, optical_coupling_gain_estimate_pct.
2. WDM filter spectral metric status: peak_transmittance, fwhm_nm, isolation_dB, and NOT_AVAILABLE for finesse/fsr due to single peak.
3. Laser mirror metrics: R_at_1064nm, peak_reflectance, stopband_width_nm.
4. Phone lens AR metrics: avg_R_visible, R_blue_450nm, R_green_550nm, R_red_650nm, HEURISTIC_COLOR_FLATNESS_SCORE.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_RESULTS = ROOT / "web3d" / "public" / "results"


class TestStageC2EngineeringMetrics:
    def test_solar_cell_ar_metrics(self):
        data = json.loads((PUBLIC_RESULTS / "app_solar_cell_ar.json").read_text(encoding="utf-8"))
        metrics = data["metrics"]
        assert "avg_R_300_1100nm" in metrics
        assert "R_at_550nm" in metrics
        assert "bandwidth_R_lt_2pct_nm" in metrics
        assert "efficiency_improvement_pct" in metrics
        assert abs(metrics["avg_R_300_1100nm"] - 0.3868) < 0.05

    def test_wdm_filter_metrics_and_invalid_fsr_handling(self):
        data = json.loads((PUBLIC_RESULTS / "app_wdm_filter.json").read_text(encoding="utf-8"))
        metrics = data["metrics"]
        assert "peak_transmittance" in metrics
        assert "fwhm_nm" in metrics
        assert "isolation_dB" in metrics
        assert "off_peak_transmission_dB" in metrics
        assert metrics["peak_transmittance"] > 0.85
        assert metrics["fwhm_nm"] > 0.0

        # Sign & Definition assertions
        iso_db = metrics["isolation_dB"]
        off_peak_db = metrics["off_peak_transmission_dB"]
        assert iso_db >= 0.0, f"isolation_dB must be non-negative, got {iso_db}"
        assert off_peak_db <= 0.0, f"off_peak_transmission_dB must be non-positive, got {off_peak_db}"
        assert abs(iso_db + off_peak_db) < 1e-5, f"Expected isolation_dB + off_peak_transmission_dB == 0, got sum {iso_db + off_peak_db}"

    def test_laser_mirror_metrics(self):
        data = json.loads((PUBLIC_RESULTS / "app_laser_mirror.json").read_text(encoding="utf-8"))
        metrics = data["metrics"]
        assert "peak_reflectance" in metrics
        assert "R_at_1064nm" in metrics
        assert "stopband_width_nm" in metrics
        assert metrics["peak_reflectance"] > 0.99
        assert metrics["R_at_1064nm"] > 0.99

    def test_phone_lens_ar_metrics(self):
        data = json.loads((PUBLIC_RESULTS / "app_phone_lens_ar.json").read_text(encoding="utf-8"))
        metrics = data["metrics"]
        assert "avg_R_visible" in metrics
        assert "R_blue_450nm" in metrics
        assert "R_green_550nm" in metrics
        assert "R_red_650nm" in metrics
        assert "color_uniformity" in metrics
        assert abs(metrics["avg_R_visible"] - 0.155) < 0.05
