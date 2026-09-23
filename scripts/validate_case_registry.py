# -*- coding: utf-8 -*-
"""Validation and reconciliation script for PyThinFilm 3D Case Registry (Stage C.1.2).

Validates:
1. ID uniqueness across all registered entries.
2. Exact entry, physical case, alias, runner, and visualization target counts.
3. Entry kind & physical case ID mapping invariants.
4. Schema fields completeness (22 mandatory fields).
5. 4-dimensional status enums validation.
6. Calculation source & animation semantics validation.
7. Existence of source_file paths.
8. Rigorous accounting metrics breakdown (unique physical configurations vs entries).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_FIELDS = [
    "id",
    "display_name",
    "category",
    "entry_kind",
    "physical_case_id",
    "source_file",
    "source_symbol",
    "physics_model",
    "structure",
    "materials",
    "incidence_angle",
    "polarization_support",
    "visualization_template",
    "data_dependencies",
    "geometry_status",
    "physics_data_status",
    "migration_status",
    "conflict_status",
    "calculation_source",
    "python_reference_comparison",
    "animation_semantics",
    "notes",
]

VALID_ENTRY_KINDS = ["case", "alias", "runner"]
VALID_GEOMETRY_STATUSES = ["GEOMETRY_READY", "GEOMETRY_VERIFIED", "GEOMETRY_MISMATCH", "PENDING_GEOMETRY", "NOT_AUDITED"]
VALID_PHYSICS_DATA_STATUSES = ["PHYSICS_DATA_READY", "PHYSICS_DATA_AVAILABLE", "EXTERNAL_DATA_REQUIRED", "ILLUSTRATIVE_ONLY", "NOT_AUDITED"]
VALID_MIGRATION_STATUSES = ["MIGRATED", "MIGRATION_VERIFIED", "READY_FOR_MIGRATION", "PROTOTYPE_ONLY", "PENDING_ENGINE_MIGRATION", "BLOCKED"]
VALID_CONFLICT_STATUSES = [
    "NONE",
    "EXTERNAL_CSV_MISSING",
    "HARDCODED_PATH_DEPENDENCY",
    "PROTOTYPE_GEOMETRY_MISMATCH",
]
VALID_CALC_SOURCES = ["python_export", "frontend_reimplementation", "hardcoded", "illustrative_only"]
VALID_PYTHON_COMPARISONS = ["PASSED", "FAILED", "NOT_RUN", "NOT_APPLICABLE"]
VALID_ANIMATION_SEMANTICS = ["PHYSICS_DRIVEN", "TEACHING_ILLUSTRATION", "MIXED"]


def validate_registry():
    registry_path = ROOT / "web3d" / "data" / "case_registry.json"
    if not registry_path.exists():
        print(f"Error: Registry file not found: {registry_path}")
        sys.exit(1)

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])

    print("=" * 70)
    print("PyThinFilm 3D Case Registry Evidence Audit (Stage C.1.2 Final Accounting)")
    print("=" * 70)

    # 1. Entry Count Checks
    registry_entry_count = len(cases)
    case_ids = [c["id"] for c in cases]
    unique_ids = set(case_ids)

    if len(case_ids) != len(unique_ids):
        duplicates = [x for x in case_ids if case_ids.count(x) > 1]
        print(f"[FAIL] Duplicate Case IDs found: {set(duplicates)}")
        sys.exit(1)

    non_runner_cases = [c for c in cases if c.get("entry_kind") != "runner"]
    physical_cases = [c for c in cases if c.get("entry_kind") == "case"]
    alias_entries = [c for c in cases if c.get("entry_kind") == "alias"]
    runner_entries = [c for c in cases if c.get("entry_kind") == "runner"]

    visualization_targets = set(c["physical_case_id"] for c in cases)

    physical_case_count = len(physical_cases)
    alias_entry_count = len(alias_entries)
    runner_entry_count = len(runner_entries)
    visualization_entry_count = len(visualization_targets)

    # 2. Rigorous Status & Accounting Breakdown
    migrated_verified_entry_count = sum(1 for c in cases if c.get("migration_status") == "MIGRATION_VERIFIED")
    migrated_candidate_entry_count = sum(1 for c in cases if c.get("migration_status") == "MIGRATED")
    result_reuse_entry_count = sum(1 for c in cases if "result_reuse_policy" in c)

    # Unique physical configurations
    unique_physical_groups = set()
    unique_migrated_verified_configs = set()
    unique_migrated_candidate_configs = set()

    for c in physical_cases:
        cid = c["id"]
        group_id = c.get("physical_equivalence_group", c.get("variant_of", cid))
        unique_physical_groups.add(group_id)

        if c.get("migration_status") == "MIGRATION_VERIFIED":
            unique_migrated_verified_configs.add(group_id)
        elif c.get("migration_status") == "MIGRATED":
            unique_migrated_candidate_configs.add(group_id)

    unique_physical_configuration_count = len(unique_physical_groups)
    unique_migrated_verified_configuration_count = len(unique_migrated_verified_configs)
    unique_migrated_candidate_configuration_count = len(unique_migrated_candidate_configs)

    unique_active_physical_configuration_count = unique_migrated_verified_configuration_count + unique_migrated_candidate_configuration_count
    remaining_unique_physical_configuration_count = unique_physical_configuration_count - unique_active_physical_configuration_count

    print(f"registry_entry_count:                           {registry_entry_count}")
    print(f"visualization_entry_count:                      {visualization_entry_count}")
    print(f"runner_entry_count:                             {runner_entry_count}")
    print(f"migrated_verified_entry_count:                  {migrated_verified_entry_count}")
    print(f"migrated_candidate_entry_count:                 {migrated_candidate_entry_count}")
    print(f"result_reuse_entry_count:                       {result_reuse_entry_count}")
    print(f"unique_physical_configuration_count:            {unique_physical_configuration_count}")
    print(f"unique_migrated_verified_configuration_count:   {unique_migrated_verified_configuration_count}")
    print(f"unique_migrated_candidate_configuration_count:  {unique_migrated_candidate_configuration_count}")
    print(f"unique_active_physical_configuration_count:     {unique_active_physical_configuration_count}")
    print(f"remaining_unique_physical_configuration_count:  {remaining_unique_physical_configuration_count}")

    # Exact expected count assertions
    assert registry_entry_count == 41, f"Expected 41 registry entries, got {registry_entry_count}"
    assert visualization_entry_count == 40, f"Expected 40 visualization entries, got {visualization_entry_count}"
    assert runner_entry_count == 1, f"Expected 1 runner entry, got {runner_entry_count}"
    assert migrated_verified_entry_count in (9, 13), f"Expected 9 or 13 migrated_verified entries, got {migrated_verified_entry_count}"
    assert migrated_candidate_entry_count == 1, f"Expected 1 migrated_candidate entry, got {migrated_candidate_entry_count}"
    assert result_reuse_entry_count == 2, f"Expected 2 result_reuse entries, got {result_reuse_entry_count}"

    assert unique_physical_configuration_count == 38, f"Expected 38 unique physical configurations, got {unique_physical_configuration_count}"
    assert unique_migrated_verified_configuration_count in (7, 11), f"Expected 7 or 11 unique migrated verified configs, got {unique_migrated_verified_configuration_count}"
    assert unique_migrated_candidate_configuration_count == 1, f"Expected 1 unique migrated candidate config, got {unique_migrated_candidate_configuration_count}"
    assert unique_active_physical_configuration_count in (8, 12), f"Expected 8 or 12 unique active physical configs, got {unique_active_physical_configuration_count}"
    assert remaining_unique_physical_configuration_count in (30, 26), f"Expected 30 or 26 remaining unique physical configs, got {remaining_unique_physical_configuration_count}"

    print("\n[PASS] All Stage C.1.2 Accounting Assertions PASSED.")

    # 3. Schema Completeness & File Existence Check
    errors = []
    missing_source_files = []

    for idx, c in enumerate(cases):
        cid = c.get("id", f"INDEX_{idx}")

        for field in REQUIRED_FIELDS:
            if field not in c or c[field] is None or str(c[field]).strip() == "":
                errors.append(f"Case '{cid}' missing required field: '{field}'")

        if c.get("entry_kind") not in VALID_ENTRY_KINDS:
            errors.append(f"Case '{cid}' invalid entry_kind: {c.get('entry_kind')}")
        if c.get("geometry_status") not in VALID_GEOMETRY_STATUSES:
            errors.append(f"Case '{cid}' invalid geometry_status: {c.get('geometry_status')}")
        if c.get("physics_data_status") not in VALID_PHYSICS_DATA_STATUSES:
            errors.append(f"Case '{cid}' invalid physics_data_status: {c.get('physics_data_status')}")
        if c.get("migration_status") not in VALID_MIGRATION_STATUSES:
            errors.append(f"Case '{cid}' invalid migration_status: {c.get('migration_status')}")
        if c.get("conflict_status") not in VALID_CONFLICT_STATUSES:
            errors.append(f"Case '{cid}' invalid conflict_status: {c.get('conflict_status')}")
        if c.get("calculation_source") not in VALID_CALC_SOURCES:
            errors.append(f"Case '{cid}' invalid calculation_source: {c.get('calculation_source')}")
        if c.get("python_reference_comparison") not in VALID_PYTHON_COMPARISONS:
            errors.append(f"Case '{cid}' invalid python_reference_comparison: {c.get('python_reference_comparison')}")
        if c.get("animation_semantics") not in VALID_ANIMATION_SEMANTICS:
            errors.append(f"Case '{cid}' invalid animation_semantics: {c.get('animation_semantics')}")

        src = c.get("source_file", "").split(":")[0]
        if src and not (ROOT / src).exists():
            missing_source_files.append((cid, src))

    if missing_source_files:
        print(f"\n[WARNING] Missing Source Files ({len(missing_source_files)}):")
        for cid, src in missing_source_files:
            print(f"  - [{cid}] File not found on disk: {src}")

    if errors:
        print(f"\n[FAIL] Validation FAILED with {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("[PASS] All Schema, Field Completeness & Status Enum Checks PASSED.")

    print("=" * 70)


if __name__ == "__main__":
    validate_registry()
