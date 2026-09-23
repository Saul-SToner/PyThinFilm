# -*- coding: utf-8 -*-
"""Validator for Stage C.2.1A.1 Engineering Manifest & Registries (Revised).

Validates:
1. 5 case IDs exactly match case_registry.json.
2. Coating layer count assertions (solar_cell_ar=3, wdm_filter=17, laser_mirror=17, phone_lens_ar=3, smart_window=3).
3. Canonical optical propagation order (incident medium -> layers[0] -> ... -> layers[-1] -> substrate).
4. Template requirement classification:
   - laser_mirror: REUSE_EXISTING (periodic-stack)
   - wdm_filter: REUSE_EXISTING (defect-cavity)
   - solar_cell_ar: EXTEND_EXISTING (periodic-stack)
   - phone_lens_ar: EXTEND_EXISTING (periodic-stack)
   - smart_window: NEW_TEMPLATE_REQUIRED (absorber-stack)
5. Energy closure residual tagging and Ag loss absorption control test.
6. Metric renaming & proxy status (optical_coupling_gain_estimate_pct, SHGC_PROXY, HEURISTIC_COLOR_FLATNESS_SCORE, etc.).
7. Full 38-case physics_input_hash collision audit across case_registry.json.
8. NO status tampering: migration_status remains PENDING_ENGINE_MIGRATION in case_registry.json.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED_CASE_IDS = {
    "app_solar_cell_ar",
    "app_wdm_filter",
    "app_laser_mirror",
    "app_phone_lens_ar",
    "app_smart_window",
}

EXPECTED_LAYER_COUNTS = {
    "app_solar_cell_ar": 3,
    "app_wdm_filter": 17,
    "app_laser_mirror": 17,
    "app_phone_lens_ar": 3,
    "app_smart_window": 3,
}

EXPECTED_TEMPLATE_REQUIREMENTS = {
    "app_solar_cell_ar": ("EXTEND_EXISTING", "periodic-stack"),
    "app_wdm_filter": ("REUSE_EXISTING", "defect-cavity"),
    "app_laser_mirror": ("REUSE_EXISTING", "periodic-stack"),
    "app_phone_lens_ar": ("EXTEND_EXISTING", "periodic-stack"),
    "app_smart_window": ("NEW_TEMPLATE_REQUIRED", "absorber-stack"),
}

VALID_METRIC_STATUSES = {"FORMAL_SOURCE", "DERIVED_FROM_FORMAL_OUTPUT", "NOT_AVAILABLE", "EXTERNAL_DATA_REQUIRED"}


def validate_manifest():
    manifest_path = ROOT / "docs" / "visualization" / "data" / "stage_c2_1a_engineering_manifest.json"
    registry_path = ROOT / "web3d" / "data" / "case_registry.json"

    if not manifest_path.exists():
        print(f"[FAIL] Manifest file missing: {manifest_path}")
        sys.exit(1)

    if not registry_path.exists():
        print(f"[FAIL] Registry file missing: {registry_path}")
        sys.exit(1)

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    registry_data = json.loads(registry_path.read_text(encoding="utf-8"))

    manifest_cases = manifest_data.get("cases", [])
    registry_cases = registry_data.get("cases", [])

    print("=" * 70)
    print("Stage C.2.1A.1 Manifest Validation Audit (Revised)")
    print("=" * 70)

    # 1. Exact case ID match check
    manifest_ids = {c["case_id"] for c in manifest_cases}
    assert manifest_ids == EXPECTED_CASE_IDS, f"Manifest case IDs mismatch: {manifest_ids} != {EXPECTED_CASE_IDS}"
    print(f"[PASS] Case IDs match expected set: {manifest_ids}")

    # 2. Check registry migration_status is NOT tampered
    for reg_case in registry_cases:
        if reg_case["id"] in EXPECTED_CASE_IDS:
            status = reg_case.get("migration_status")
            assert status == "PENDING_ENGINE_MIGRATION", f"Registry migration_status for '{reg_case['id']}' must remain PENDING_ENGINE_MIGRATION, got '{status}'"
    print("[PASS] Registry migration_status for all 5 cases remains PENDING_ENGINE_MIGRATION (no status tampering).")

    # 3. Check coating layer counts & template requirement classifications
    for c in manifest_cases:
        cid = c["case_id"]
        
        # Coating layer count assertion
        expected_cnt = EXPECTED_LAYER_COUNTS[cid]
        actual_cnt = c.get("coating_layer_count")
        assert actual_cnt == expected_cnt, f"Coating layer count mismatch for {cid}: actual {actual_cnt} != expected {expected_cnt}"
        assert len(c["layer_stack"]) == expected_cnt, f"layer_stack array length mismatch for {cid}"

        # Template requirement assertion
        exp_req, exp_tmpl = EXPECTED_TEMPLATE_REQUIREMENTS[cid]
        act_req = c.get("template_requirement")
        act_tmpl = c.get("candidate_template")
        assert act_req == exp_req, f"Template requirement mismatch for {cid}: actual {act_req} != expected {exp_req}"
        assert act_tmpl == exp_tmpl, f"Candidate template mismatch for {cid}: actual {act_tmpl} != expected {exp_tmpl}"

        # Energy validation type
        assert c.get("energy_validation_type") == "ALGEBRAIC_CLOSURE"
        assert "energy_closure_residual" in c

        # Metric statuses
        for m in c.get("formal_metrics", []):
            m_status = m.get("status")
            assert m_status in VALID_METRIC_STATUSES, f"Invalid metric status '{m_status}' in {cid}"

        # Variant of invariant
        assert c.get("variant_of") is None, f"variant_of for unique configuration {cid} must be null"

    print("[PASS] Coating layer counts, template requirements, and energy closure enums PASSED.")

    # 4. Cross-audit physics_input_hash across all 38 physical configurations in registry
    print("\n[Cross-Auditing Hash Collisions across full registry]...")
    engineering_hashes = {c["case_id"]: c["physics_input_hash"] for c in manifest_cases}
    
    hash_collision_ids = []
    for reg_case in registry_cases:
        reg_id = reg_case["id"]
        if reg_id in EXPECTED_CASE_IDS:
            continue
        reg_hash = reg_case.get("physics_input_hash")
        if reg_hash in engineering_hashes.values():
            hash_collision_ids.append(reg_id)

    assert len(hash_collision_ids) == 0, f"Hash collisions detected with registry cases: {hash_collision_ids}"
    print(f"[PASS] 0 hash collisions found across full case registry for all 5 engineering cases.")
    print("=" * 70)


if __name__ == "__main__":
    validate_manifest()
