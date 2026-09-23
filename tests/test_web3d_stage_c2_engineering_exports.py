# -*- coding: utf-8 -*-
"""Tests for Stage C.2.1B-1 Four Lossless Engineering Export JSONs.

Validates:
1. Exported JSON files exist in web3d/public/results/.
2. JSON structure contains mandatory fields: schema_version, case_id, coating_layer_count, physics_input_hash, TE, TM, metrics.
3. Layer ordering is NOT reversed (optical propagation order).
4. Laser mirror has exactly 17 layers.
5. WDM filter has exactly 17 layers and cavity layer is layer index 8 (0-indexed).
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_RESULTS = ROOT / "web3d" / "public" / "results"


class TestStageC2EngineeringExports:
    @pytest.mark.parametrize("case_id, expected_layer_cnt", [
        ("app_solar_cell_ar", 3),
        ("app_wdm_filter", 17),
        ("app_laser_mirror", 17),
        ("app_phone_lens_ar", 3),
    ])
    def test_exported_json_completeness_and_layer_counts(self, case_id, expected_layer_cnt):
        json_path = PUBLIC_RESULTS / f"{case_id}.json"
        assert json_path.exists(), f"Missing exported JSON: {json_path}"

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["case_id"] == case_id
        assert "schema_version" in data
        assert "physics_input_hash" in data
        assert "physics_result_hash" in data
        assert data["coating_layer_count"] == expected_layer_cnt
        assert len(data["layers"]) == expected_layer_cnt
        assert "TE" in data and "TM" in data
        assert "metrics" in data

    def test_solar_cell_ar_optical_propagation_order(self):
        data = json.loads((PUBLIC_RESULTS / "app_solar_cell_ar.json").read_text(encoding="utf-8"))
        layer_names = [l["name"] for l in data["layers"]]
        assert layer_names == ["SiO2", "TiO2", "MgF2"]

    def test_phone_lens_ar_optical_propagation_order(self):
        data = json.loads((PUBLIC_RESULTS / "app_phone_lens_ar.json").read_text(encoding="utf-8"))
        layer_names = [l["name"] for l in data["layers"]]
        assert layer_names == ["SiO2", "ZrO2", "MgF2"]

    def test_wdm_filter_cavity_layer_position(self):
        data = json.loads((PUBLIC_RESULTS / "app_wdm_filter.json").read_text(encoding="utf-8"))
        layers = data["layers"]
        assert len(layers) == 17
        # 8 left DBR layers (indices 0..7), 1 cavity layer (index 8, d ~ 530.8nm SiO2), 8 right DBR layers
        cavity_layer = layers[8]
        assert cavity_layer["name"] == "C"
        assert abs(cavity_layer["thickness_nm"] - 530.8219) < 0.1
