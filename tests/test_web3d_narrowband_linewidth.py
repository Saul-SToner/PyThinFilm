# -*- coding: utf-8 -*-
"""Pytest verification for exported narrowband_filter and fp_single_halfwave JSON fine linewidths (Stage C.1.3).

Physical structure comparison:
  fp_single_halfwave  = (HL)^3 C (LH)^3   13 layers  — same as fp_filter via shared physics
  narrowband_filter   = (HL)^4 C (LH)^4   17 layers  — genuinely distinct, must show narrower FWHM

Validates:
1. Exported JSON files contain audited TE/TM fine-grid linewidth metrics with FWHM status AVAILABLE.
2. 17-layer narrowband_filter has strictly narrower TE and TM FWHM than 13-layer fp_single_halfwave.
3. 17-layer narrowband_filter has strictly higher TE and TM Q-factor than 13-layer fp_single_halfwave.
4. narrowband_filter JSON has 17 layers; fp_single_halfwave JSON has 13 layers.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_narrowband_filter_has_17_layers():
    nb_json = ROOT / "web3d" / "public" / "results" / "narrowband_filter.json"
    assert nb_json.exists(), f"narrowband_filter.json missing at {nb_json}"
    data = json.loads(nb_json.read_text(encoding="utf-8"))
    assert len(data["layers"]) == 17, f"Expected 17 layers, got {len(data['layers'])}"


def test_fp_single_halfwave_has_13_layers():
    fp_json = ROOT / "web3d" / "public" / "results" / "fp_single_halfwave.json"
    assert fp_json.exists(), f"fp_single_halfwave.json missing at {fp_json}"
    data = json.loads(fp_json.read_text(encoding="utf-8"))
    assert len(data["layers"]) == 13, f"Expected 13 layers, got {len(data['layers'])}"


def test_exported_json_linewidth_verification():
    """17-layer narrowband_filter must have narrower FWHM and higher Q than 13-layer fp_single_halfwave."""
    fp_json = ROOT / "web3d" / "public" / "results" / "fp_single_halfwave.json"
    nb_json = ROOT / "web3d" / "public" / "results" / "narrowband_filter.json"

    assert fp_json.exists()
    assert nb_json.exists()

    fp_data = json.loads(fp_json.read_text(encoding="utf-8"))
    nb_data = json.loads(nb_json.read_text(encoding="utf-8"))

    fp_te = fp_data["case_specific_metrics"]["audited_linewidth_TE"]
    fp_tm = fp_data["case_specific_metrics"]["audited_linewidth_TM"]

    nb_te = nb_data["case_specific_metrics"]["audited_linewidth_TE"]
    nb_tm = nb_data["case_specific_metrics"]["audited_linewidth_TM"]

    # FWHM status assertions
    assert fp_te["fwhm_status"] == "AVAILABLE", f"fp_single_halfwave TE FWHM not available: {fp_te}"
    assert fp_tm["fwhm_status"] == "AVAILABLE", f"fp_single_halfwave TM FWHM not available: {fp_tm}"
    assert nb_te["fwhm_status"] == "AVAILABLE", f"narrowband_filter TE FWHM not available: {nb_te}"
    assert nb_tm["fwhm_status"] == "AVAILABLE", f"narrowband_filter TM FWHM not available: {nb_tm}"

    # Linewidth narrowing assertions (17-layer must be < 13-layer)
    assert nb_te["fwhm_nm"] < fp_te["fwhm_nm"], (
        f"narrowband TE FWHM ({nb_te['fwhm_nm']}) must be < fp_single_halfwave TE FWHM ({fp_te['fwhm_nm']})"
    )
    assert nb_tm["fwhm_nm"] < fp_tm["fwhm_nm"], (
        f"narrowband TM FWHM ({nb_tm['fwhm_nm']}) must be < fp_single_halfwave TM FWHM ({fp_tm['fwhm_nm']})"
    )

    # Q-factor increase assertions
    assert nb_te["q_factor"] > fp_te["q_factor"], (
        f"narrowband TE Q ({nb_te['q_factor']}) must be > fp_single_halfwave TE Q ({fp_te['q_factor']})"
    )
    assert nb_tm["q_factor"] > fp_tm["q_factor"], (
        f"narrowband TM Q ({nb_tm['q_factor']}) must be > fp_single_halfwave TM Q ({fp_tm['q_factor']})"
    )
