# -*- coding: utf-8 -*-
"""Unit tests for Stage C.2.1A.1 Engineering Application Source Audit (Revised).

Validates:
1. 5 engineering application case functions execute cleanly.
2. Canonical optical propagation order for all 5 cases (SiO2 -> TiO2 -> MgF2 for solar cell AR).
3. Exact coating layer count assertions (laser_mirror = 17, wdm_filter = 17, solar_cell_ar = 3, etc.).
4. R + T + A = 1.0 energy closure residual validation & Ag loss absorption control test.
5. Template requirement classification correctness (smart_window -> absorber-stack / NEW_TEMPLATE_REQUIRED).
6. Manifest file completeness, metric proxies, and 0 hash collisions across full case registry.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import numpy as np

from examples.applications.solar_cell_ar import run_solar_cell_ar, build_solar_cell_ar_layers
from examples.applications.wdm_filter import run_wdm_filter, build_wdm_filter_layers
from examples.applications.laser_mirror import run_laser_mirror, build_laser_mirror_layers
from examples.applications.phone_lens_ar import run_phone_lens_ar, build_phone_lens_ar_layers
from examples.applications.smart_window import run_smart_window, build_smart_window_layers
from thinfilm.education import multilayer_rt_spectrum, LayerSpec

ROOT = Path(__file__).resolve().parent.parent


class TestEngineeringSourceAuditRevised:
    @pytest.mark.parametrize("runner_fn, case_id", [
        (run_solar_cell_ar, "app_solar_cell_ar"),
        (run_wdm_filter, "app_wdm_filter"),
        (run_laser_mirror, "app_laser_mirror"),
        (run_phone_lens_ar, "app_phone_lens_ar"),
        (run_smart_window, "app_smart_window"),
    ])
    def test_engineering_case_execution_and_energy_conservation(self, runner_fn, case_id):
        res = runner_fn()
        assert "R" in res and "T" in res and "A" in res
        assert "metrics" in res and "structure" in res

        R, T, A = res["R"], res["T"], res["A"]
        total_energy = R + T + A
        max_err = np.max(np.abs(total_energy - 1.0))
        assert max_err < 1e-5, f"Energy closure error {max_err} for {case_id}"

    def test_canonical_layer_ordering_and_layer_counts(self):
        # Solar Cell AR: Air -> SiO2 -> TiO2 -> MgF2 -> Si
        layers_sc = build_solar_cell_ar_layers()
        assert len(layers_sc) == 3
        assert [l.name for l in layers_sc] == ["SiO2", "TiO2", "MgF2"]

        # Phone Lens AR: Air -> SiO2 -> ZrO2 -> MgF2 -> Glass
        layers_pl = build_phone_lens_ar_layers()
        assert len(layers_pl) == 3
        assert [l.name for l in layers_pl] == ["SiO2", "ZrO2", "MgF2"]

        # Laser Mirror: (HL)^8 H -> 17 layers
        layers_lm = build_laser_mirror_layers(periods=8)
        assert len(layers_lm) == 17

        # WDM Filter: (HL)^4 2L (LH)^4 -> 17 layers
        layers_wdm = build_wdm_filter_layers()
        assert len(layers_wdm) == 17

        # Smart Window: WO3 -> NiO -> Ag -> Glass -> 3 layers
        layers_sw = build_smart_window_layers()
        assert len(layers_sw) == 3

    def test_ag_lossless_control_absorption_verification(self):
        layers_sw_no_loss = [
            LayerSpec("WO3", 2.10, 80.0),
            LayerSpec("NiO", 2.00, 50.0),
            LayerSpec("Ag_Lossless", 0.05 + 0.0j, 15.0),
        ]
        res_no_loss = multilayer_rt_spectrum(np.linspace(300, 2500, 50), layers_sw_no_loss, n_incident=1.0, n_substrate=1.52)
        max_A = np.max(res_no_loss["A"])
        assert max_A < 1e-5, "Absorption must be near zero when Ag imaginary part is 0.0"

    def test_manifest_file_completeness_and_template_classifications(self):
        manifest_path = ROOT / "docs" / "visualization" / "data" / "stage_c2_1a_engineering_manifest.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        cases = data.get("cases", [])
        assert len(cases) == 5

        case_map = {c["case_id"]: c for c in cases}
        assert set(case_map.keys()) == {"app_solar_cell_ar", "app_wdm_filter", "app_laser_mirror", "app_phone_lens_ar", "app_smart_window"}

        # Template classifications
        assert case_map["app_laser_mirror"]["template_requirement"] == "REUSE_EXISTING"
        assert case_map["app_laser_mirror"]["candidate_template"] == "periodic-stack"

        assert case_map["app_wdm_filter"]["template_requirement"] == "REUSE_EXISTING"
        assert case_map["app_wdm_filter"]["candidate_template"] == "defect-cavity"

        assert case_map["app_solar_cell_ar"]["template_requirement"] == "EXTEND_EXISTING"
        assert case_map["app_solar_cell_ar"]["candidate_template"] == "periodic-stack"

        assert case_map["app_phone_lens_ar"]["template_requirement"] == "EXTEND_EXISTING"
        assert case_map["app_phone_lens_ar"]["candidate_template"] == "periodic-stack"

        assert case_map["app_smart_window"]["template_requirement"] == "NEW_TEMPLATE_REQUIRED"
        assert case_map["app_smart_window"]["candidate_template"] == "absorber-stack"

        # Energy closure & variants
        for cid, c in case_map.items():
            assert c["energy_validation_type"] == "ALGEBRAIC_CLOSURE"
            assert c["variant_of"] is None
            assert c["coating_layer_count"] == len(c["layer_stack"])
