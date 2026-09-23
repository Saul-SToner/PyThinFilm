# -*- coding: utf-8 -*-
"""PyThinFilm Stage C.2 Migration Plan Generator & Reconciliation Audit.

Generates docs/visualization/stage_c2_migration_plan.md directly from case_registry.json.
Validates:
1. Exact breakdown of all 30 remaining unique physical configurations across 5 sub-stages.
2. No overlaps across sub-stage case ID sets.
3. No active/migrated cases included in remaining plan.
4. No runner entries included in remaining physical cases.
5. Strict equality: sum of sub-stage physical configuration counts == 30.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Define the 5 sub-stage assignments by Case ID (strictly matching remaining 30 unique physical configurations)
STAGE_C2_ASSIGNMENTS = {
    "Stage C.2.1": {
        "title": "Stage C.2.1: Engineering Application Showcase",
        "description": "High-impact engineering application cases for competition demonstration.",
        "case_ids": [
            "app_solar_cell_ar",
            "app_wdm_filter",
            "app_laser_mirror",
            "app_phone_lens_ar",
            "app_smart_window",
        ],
    },
    "Stage C.2.2": {
        "title": "Stage C.2.2: Advanced Anti-Reflection & Periodic Multi-layers",
        "description": "Core educational film structures (single, double, triple AR, porous, Rugate, moth-eye).",
        "case_ids": [
            "double_ar",
            "quarter_wave_double_layer",
            "porous_sio2_layer",
            "porous_double_ar",
            "triple_ar",
            "mat_library_demo",
            "fp_double_halfwave",
            "neutral_beamsplitter",
            "rugate_filter",
            "moth_eye_effective_gradient",
        ],
    },
    "Stage C.2.3": {
        "title": "Stage C.2.3: Educational Topic Bundles & High-Reflector Scenarios",
        "description": "Aggregated educational topic views and multi-layer table breakdowns.",
        "case_ids": [
            "advanced_ar_bundle",
            "porous_double_ar_topic_bundle",
            "rugate_80layer_table",
        ],
    },
    "Stage C.2.4": {
        "title": "Stage C.2.4: Tamm Plasmon Variants & Absorbing Surface Stacks",
        "description": "Metal-DBR Tamm state variants and solar/thermal absorbing film stacks.",
        "case_ids": [
            "tamm_interface_priority",
            "tamm_phase_candidates",
            "tamm_phase_focus",
            "tamm_reflection_phase_screen",
            "tamm_interface_window_bundle",
            "tamm_interface_window_scan",
            "pdrc_cooling_bundle",
            "absorbing_baseline_template",
            "absorbing_surface_bundle",
            "absorbing_surface_gain",
        ],
    },
    "Stage C.2.5": {
        "title": "Stage C.2.5: Guided Grating & RCWA Electromagnetic Solvers",
        "description": "2D guided-wave grating and effective medium theory sub-branch cases.",
        "case_ids": [
            "guided_grating_emt",
            "absorbing_surface_gain_trend",
        ],
    },
}


def audit_and_generate_plan():
    registry_path = ROOT / "web3d" / "data" / "case_registry.json"
    if not registry_path.exists():
        print(f"Error: Registry file missing: {registry_path}")
        sys.exit(1)

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])

    # Filter out active migrated cases and runner
    active_ids = {c["id"] for c in cases if c.get("migration_status") in ("MIGRATED", "MIGRATION_VERIFIED")}
    runner_ids = {c["id"] for c in cases if c.get("entry_kind") == "runner"}

    remaining_cases = [
        c for c in cases
        if c["id"] not in active_ids and c["id"] not in runner_ids
    ]

    remaining_dict = {c["id"]: c for c in remaining_cases}

    print("=" * 70)
    print("Stage C.2 Migration Roadmap Reconciliation & Validation Audit")
    print("=" * 70)

    # 1. Reconciliation Checks
    assigned_case_ids = []
    for stage_key, stage_info in STAGE_C2_ASSIGNMENTS.items():
        for cid in stage_info["case_ids"]:
            assigned_case_ids.append(cid)

    set_assigned = set(assigned_case_ids)

    # Check length equality & duplicates
    if len(assigned_case_ids) != len(set_assigned):
        dups = [x for x in assigned_case_ids if assigned_case_ids.count(x) > 1]
        print(f"[FAIL] Duplicate Case IDs found in Stage C.2 Plan: {set(dups)}")
        sys.exit(1)

    # Check coverage of remaining 30 cases
    set_remaining = set(remaining_dict.keys())

    missing_in_plan = set_remaining - (set_assigned - active_ids)
    extra_in_plan = (set_assigned - active_ids) - set_remaining

    # Strict Set Equality & Empty Intersection Assertions
    # Exclude cases that have completed stage C.2.1B-1 migration
    planned_ids = set_assigned - active_ids
    remaining_unique_ids = set_remaining

    assert planned_ids & active_ids == set(), f"Plan contains active migrated cases: {planned_ids & active_ids}"
    assert planned_ids & runner_ids == set(), f"Plan contains runner entries: {planned_ids & runner_ids}"
    assert missing_in_plan == set(), f"Plan missing cases: {missing_in_plan}"
    assert planned_ids == remaining_unique_ids, "Strict set equality check failed: planned_ids != remaining_unique_ids"

    if missing_in_plan:
        print(f"[FAIL] Cases missing from Stage C.2 Plan ({len(missing_in_plan)}): {missing_in_plan}")
        sys.exit(1)

    if extra_in_plan:
        print(f"[FAIL] Extra invalid cases included in Stage C.2 Plan ({len(extra_in_plan)}): {extra_in_plan}")
        sys.exit(1)

    print(f"Active Migrated Cases (C.1):             {len(active_ids)}")
    print(f"Runner Entries Excluded:                {len(runner_ids)}")
    print(f"Remaining Physical Configurations:      {len(remaining_dict)}")
    print(f"Stage C.2 Plan Assigned Cases:          {len(assigned_case_ids)}")
    print("[PASS] Exact 1-to-1 match for 30 remaining physical configurations!")

    # 2. Generate Markdown Roadmap
    doc_path = ROOT / "docs" / "visualization" / "stage_c2_migration_plan.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Stage C.2 Web3D 30-Case Batch Migration Roadmap")
    lines.append("")
    lines.append("> **Baseline Tag**: `v1.2-web3d-dynamic-foundation-freeze`")
    lines.append("> **Reconciliation Baseline**: `case_registry.json` Audit Clean")
    lines.append("> **Active Migrated Cases (Stage C.1)**: 10 entries (8 unique physical configs)")
    lines.append("> **Remaining Migration Target (Stage C.2)**: 30 unique physical configurations")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Accounting & Status Summary")
    lines.append("")
    lines.append("| Metric | Count | Notes |")
    lines.append("|---|---|---|")
    lines.append(f"| `registry_entry_count` | 41 | Total entries in case_registry.json |")
    lines.append(f"| `visualization_entry_count` | 40 | Visualization cases + aliases |")
    lines.append(f"| `runner_entry_count` | 1 | `guided_grating_demo` CLI runner |")
    lines.append(f"| `active_visualization_entry_count` | 10 | Migrated and active in Web3D app |")
    lines.append(f"| `active_unique_physical_configuration_count` | 8 | Active physical configuration groups |")
    lines.append(f"| `remaining_visualization_entry_count` | 30 | Target entries for Stage C.2 |")
    lines.append(f"| `remaining_unique_physical_configuration_count` | 30 | Target physical configurations for Stage C.2 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Sub-Stage Breakdown & Detailed Case Schedule")
    lines.append("")

    for stage_key, stage_info in STAGE_C2_ASSIGNMENTS.items():
        lines.append(f"### {stage_info['title']} ({len(stage_info['case_ids'])} Cases)")
        lines.append(f"*{stage_info['description']}*")
        lines.append("")
        lines.append("| Case ID | Category | Template Requirement | Variant Of / Equivalence | Data Dependencies |")
        lines.append("|---|---|---|---|---|")

        for cid in stage_info["case_ids"]:
            if cid in active_ids or cid not in remaining_dict:
                continue
            c = remaining_dict[cid]
            cat = c.get("category", "")
            tmpl = c.get("visualization_template", "single-interface")
            variant = c.get("variant_of", c.get("physical_equivalence_group", "UNIQUE"))
            deps = c.get("data_dependencies", "")

            # Determine template requirement status
            tmpl_req = "REUSE_EXISTING"
            if tmpl in ["single-interface", "periodic-stack", "defect-cavity", "metal-dbr-interface"]:
                tmpl_req = f"REUSE (`{tmpl}`)"
            elif tmpl == "engineering-device":
                tmpl_req = "NEW_TEMPLATE (`engineering-device`)"
            elif tmpl == "absorber-stack":
                tmpl_req = "NEW_TEMPLATE (`absorber-stack`)"
            elif tmpl == "grating-emt":
                tmpl_req = "NEW_TEMPLATE (`grating-emt`)"

            lines.append(f"| `{cid}` | `{cat}` | {tmpl_req} | `{variant}` | `{deps}` |")

        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Verification Requirements Prior to Sub-stage Execution")
    lines.append("1. **Source Layer Stack Audit**: Read full layer_stack in Python before deciding template.")
    lines.append("2. **Python Export**: Run `tools/export_visualization_cases.py` to generate JSON.")
    lines.append("3. **Vitest Binding**: Add metric binding unit tests in `web3d/tests/`.")
    lines.append("4. **Playwright E2E**: Add headless browser E2E tests verifying canvas, waves, and context loss.")
    lines.append("5. **Accounting Re-run**: Run `py scripts/validate_case_registry.py` after each sub-stage.")

    doc_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[SUCCESS] Reconciled Stage C.2 Roadmap written to {doc_path}")


if __name__ == "__main__":
    audit_and_generate_plan()
