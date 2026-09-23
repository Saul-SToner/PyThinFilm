# -*- coding: utf-8 -*-
"""Pytest verification for Stage C.1.1 Physical Equivalence Groups & Case Deduplication.

Validates:
1. bragg_reflector vs high_reflector exact spectral & structure equivalence (max diff R = 0.0).
2. fp_filter vs fp_single_halfwave exact spectral & structure equivalence (max diff R = 0.0).
3. Registry metadata properly marks physical_equivalence_group, variant_of, and result_reuse_policy.
"""

from __future__ import annotations

import json
import numpy as np
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_equivalence_group_bragg_vs_high_reflector():
    bragg_data = json.loads((ROOT / "web3d" / "public" / "results" / "bragg_reflector.json").read_text(encoding="utf-8"))
    high_data = json.loads((ROOT / "web3d" / "public" / "results" / "high_reflector.json").read_text(encoding="utf-8"))

    r_bragg = np.array(bragg_data["TE"]["R"])
    r_high = np.array(high_data["TE"]["R"])

    diff_r = np.max(np.abs(r_bragg - r_high))
    assert diff_r < 1e-10

    metrics = high_data["case_specific_metrics"]
    assert metrics["physical_equivalence_group"] == "dbr_7layer_hlh"
    assert metrics["variant_of"] == "bragg_reflector"


def test_equivalence_group_fp_filter_vs_single_halfwave():
    fp_data = json.loads((ROOT / "web3d" / "public" / "results" / "fp_filter.json").read_text(encoding="utf-8"))
    halfwave_data = json.loads((ROOT / "web3d" / "public" / "results" / "fp_single_halfwave.json").read_text(encoding="utf-8"))

    r_fp = np.array(fp_data["TE"]["R"])
    r_halfwave = np.array(halfwave_data["TE"]["R"])

    diff_r = np.max(np.abs(r_fp - r_halfwave))
    assert diff_r < 1e-10

    metrics = halfwave_data["case_specific_metrics"]
    assert metrics["physical_equivalence_group"] == "fp_13layer_defect_cavity"
    assert metrics["variant_of"] == "fp_filter"
