# -*- coding: utf-8 -*-
"""Automated smoke and invariant tests for non-teaching case audit."""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from PIL import Image
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_all_non_teaching_cases import NON_TEACHING_CASES
from examples.applications import (
    run_solar_cell_ar,
    run_wdm_filter,
    run_laser_mirror,
    run_phone_lens_ar,
    run_smart_window,
)


class TestNonTeachingCaseInvariants:
    """Test suite for dataset and registry invariants."""

    def test_case_list_invariants(self):
        case_ids = [c["id"] for c in NON_TEACHING_CASES]
        assert len(case_ids) == 22, f"Expected 22 total non-teaching cases, got {len(case_ids)}"
        assert len(case_ids) == len(set(case_ids)), "Duplicate case_id found in NON_TEACHING_CASES"

    def test_category_counts(self):
        cats = {}
        for c in NON_TEACHING_CASES:
            cat = c["category"]
            cats[cat] = cats.get(cat, 0) + 1

        assert cats.get("engineering") == 5
        assert cats.get("material") == 1
        assert cats.get("research_tamm") == 7
        assert cats.get("research_pdrc") == 1
        assert cats.get("research_absorbing") == 4
        assert cats.get("research_ar") == 3
        assert cats.get("research_grating") == 1


class TestEngineeringApplicationsSmoke:
    """Test suite for the 5 TMM-only engineering application cases."""

    def test_solar_cell_ar(self):
        res = run_solar_cell_ar()
        assert "wavelengths_nm" in res
        assert "R" in res
        assert "T" in res
        assert "A" in res
        assert len(res["R"]) == len(res["wavelengths_nm"])
        assert not np.any(np.isnan(res["R"]))
        assert not np.any(np.isinf(res["R"]))
        assert "metrics" in res
        assert "structure" in res

    def test_wdm_filter(self):
        res = run_wdm_filter()
        assert "wavelengths_nm" in res
        assert "R" in res
        assert "T" in res
        assert len(res["R"]) == len(res["wavelengths_nm"])
        assert not np.any(np.isnan(res["T"]))
        assert not np.any(np.isinf(res["T"]))
        assert "metrics" in res
        assert "fwhm_nm" in res["metrics"]

    def test_laser_mirror(self):
        res = run_laser_mirror()
        assert "wavelengths_nm" in res
        assert "R" in res
        assert len(res["R"]) == len(res["wavelengths_nm"])
        assert not np.any(np.isnan(res["R"]))
        assert not np.any(np.isinf(res["R"]))
        assert "metrics" in res
        assert "R_at_1064nm" in res["metrics"]

    def test_phone_lens_ar(self):
        res = run_phone_lens_ar()
        assert "wavelengths_nm" in res
        assert "R" in res
        assert len(res["R"]) == len(res["wavelengths_nm"])
        assert not np.any(np.isnan(res["R"]))
        assert not np.any(np.isinf(res["R"]))
        assert "metrics" in res

    def test_smart_window(self):
        res = run_smart_window()
        assert "wavelengths_nm" in res
        assert "R" in res
        assert "T" in res
        assert "A" in res
        assert len(res["R"]) == len(res["wavelengths_nm"])
        assert not np.any(np.isnan(res["R"]))
        assert not np.any(np.isinf(res["R"]))
        assert "metrics" in res
        assert "SHGC" in res["metrics"]


class TestAuditSummaryAndFileValidity:
    """Test suite for batch audit summary JSON & generated file integrity."""

    @pytest.fixture(autouse=True)
    def summary_data(self):
        summary_path = ROOT / "outputs" / "non_teaching_audit" / "case_run_summary.json"
        assert summary_path.exists(), "case_run_summary.json must exist before testing"
        return json.loads(summary_path.read_text(encoding="utf-8"))

    def test_summary_totals(self, summary_data):
        assert summary_data["total_cases"] == 22
        assert summary_data["passed_cases"] == 19
        assert summary_data["expected_external_input_cases"] == 3
        assert summary_data["failed_cases"] == 0
        assert summary_data["output_invalid_cases"] == 0

    def test_output_files_integrity(self):
        # Verify generated output files for application cases
        app_ids = ["solar_cell_ar", "wdm_filter", "laser_mirror", "phone_lens_ar", "smart_window"]
        for app_id in app_ids:
            out_dir = ROOT / "outputs" / app_id
            png_file = out_dir / "spectrum.png"
            json_file = out_dir / "metrics.json"
            csv_file = out_dir / "spectrum.csv"

            # Check existence and non-zero size
            assert png_file.exists() and png_file.stat().st_size > 500, f"{png_file} missing or small"
            assert json_file.exists() and json_file.stat().st_size > 10, f"{json_file} missing or small"
            assert csv_file.exists() and csv_file.stat().st_size > 50, f"{csv_file} missing or small"

            # Verify PNG is valid readable image using Pillow
            with Image.open(png_file) as img:
                assert img.format == "PNG"
                assert img.width > 100 and img.height > 100

            # Verify JSON parsing
            j_data = json.loads(json_file.read_text(encoding="utf-8"))
            assert isinstance(j_data, dict)

            # Verify CSV parsing and numeric validity
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                assert header == ["wavelength_nm", "R", "T", "A"]
                rows = list(reader)
                assert len(rows) >= 50
                r_vals = [float(row[1]) for row in rows]
                assert not any(np.isnan(r_vals))
                assert not any(np.isinf(r_vals))
