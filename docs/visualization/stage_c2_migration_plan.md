# Stage C.2 Web3D 30-Case Batch Migration Roadmap

> **Baseline Tag**: `v1.2-web3d-dynamic-foundation-freeze`
> **Reconciliation Baseline**: `case_registry.json` Audit Clean
> **Active Migrated Cases (Stage C.1)**: 10 entries (8 unique physical configs)
> **Remaining Migration Target (Stage C.2)**: 30 unique physical configurations

---

## Accounting & Status Summary

| Metric | Count | Notes |
|---|---|---|
| `registry_entry_count` | 41 | Total entries in case_registry.json |
| `visualization_entry_count` | 40 | Visualization cases + aliases |
| `runner_entry_count` | 1 | `guided_grating_demo` CLI runner |
| `active_visualization_entry_count` | 10 | Migrated and active in Web3D app |
| `active_unique_physical_configuration_count` | 8 | Active physical configuration groups |
| `remaining_visualization_entry_count` | 30 | Target entries for Stage C.2 |
| `remaining_unique_physical_configuration_count` | 30 | Target physical configurations for Stage C.2 |

---

## Sub-Stage Breakdown & Detailed Case Schedule

### Stage C.2.1: Engineering Application Showcase (5 Cases)
*High-impact engineering application cases for competition demonstration.*

| Case ID | Category | Template Requirement | Variant Of / Equivalence | Data Dependencies |
|---|---|---|---|---|
| `app_smart_window` | `engineering_applications` | NEW_TEMPLATE (`engineering-device`) | `UNIQUE` | `NONE` |

### Stage C.2.2: Advanced Anti-Reflection & Periodic Multi-layers (10 Cases)
*Core educational film structures (single, double, triple AR, porous, Rugate, moth-eye).*

| Case ID | Category | Template Requirement | Variant Of / Equivalence | Data Dependencies |
|---|---|---|---|---|
| `double_ar` | `teaching_thinfilm` | REUSE (`single-interface`) | `UNIQUE` | `NONE` |
| `quarter_wave_double_layer` | `teaching_thinfilm` | REUSE (`single-interface`) | `UNIQUE` | `NONE` |
| `porous_sio2_layer` | `teaching_thinfilm` | REUSE (`single-interface`) | `UNIQUE` | `NONE` |
| `porous_double_ar` | `teaching_thinfilm` | REUSE (`single-interface`) | `UNIQUE` | `NONE` |
| `triple_ar` | `teaching_thinfilm` | REUSE (`single-interface`) | `UNIQUE` | `NONE` |
| `mat_library_demo` | `research_extension` | REUSE (`single-interface`) | `UNIQUE` | `NONE` |
| `fp_double_halfwave` | `teaching_thinfilm` | REUSE (`defect-cavity`) | `UNIQUE` | `NONE` |
| `neutral_beamsplitter` | `teaching_thinfilm` | REUSE (`single-interface`) | `UNIQUE` | `NONE` |
| `rugate_filter` | `teaching_thinfilm` | REUSE (`periodic-stack`) | `UNIQUE` | `NONE` |
| `moth_eye_effective_gradient` | `teaching_thinfilm` | REUSE (`periodic-stack`) | `UNIQUE` | `NONE` |

### Stage C.2.3: Educational Topic Bundles & High-Reflector Scenarios (3 Cases)
*Aggregated educational topic views and multi-layer table breakdowns.*

| Case ID | Category | Template Requirement | Variant Of / Equivalence | Data Dependencies |
|---|---|---|---|---|
| `advanced_ar_bundle` | `research_extension` | REUSE (`single-interface`) | `UNIQUE` | `Desktop COMSOL comparison CSVs` |
| `porous_double_ar_topic_bundle` | `research_extension` | REUSE (`single-interface`) | `UNIQUE` | `Desktop COMSOL theta CSVs` |
| `rugate_80layer_table` | `research_extension` | REUSE (`periodic-stack`) | `UNIQUE` | `NONE` |

### Stage C.2.4: Tamm Plasmon Variants & Absorbing Surface Stacks (10 Cases)
*Metal-DBR Tamm state variants and solar/thermal absorbing film stacks.*

| Case ID | Category | Template Requirement | Variant Of / Equivalence | Data Dependencies |
|---|---|---|---|---|
| `tamm_interface_priority` | `research_extension` | REUSE (`metal-dbr-interface`) | `UNIQUE` | `NONE` |
| `tamm_phase_candidates` | `research_extension` | REUSE (`metal-dbr-interface`) | `UNIQUE` | `NONE` |
| `tamm_phase_focus` | `research_extension` | REUSE (`metal-dbr-interface`) | `UNIQUE` | `NONE` |
| `tamm_reflection_phase_screen` | `research_extension` | REUSE (`metal-dbr-interface`) | `UNIQUE` | `NONE` |
| `tamm_interface_window_bundle` | `research_extension` | REUSE (`metal-dbr-interface`) | `UNIQUE` | `COMSOL E3.csv, E4.csv, E5.csv` |
| `tamm_interface_window_scan` | `research_extension` | REUSE (`metal-dbr-interface`) | `UNIQUE` | `COMSOL E3.csv, E4.csv` |
| `pdrc_cooling_bundle` | `research_extension` | REUSE_EXISTING | `UNIQUE` | `NONE` |
| `absorbing_baseline_template` | `research_extension` | NEW_TEMPLATE (`absorber-stack`) | `UNIQUE` | `NONE` |
| `absorbing_surface_bundle` | `research_extension` | NEW_TEMPLATE (`absorber-stack`) | `UNIQUE` | `NONE` |
| `absorbing_surface_gain` | `research_extension` | NEW_TEMPLATE (`absorber-stack`) | `UNIQUE` | `CLI --rough-csv & --baseline-csv` |

### Stage C.2.5: Guided Grating & RCWA Electromagnetic Solvers (2 Cases)
*2D guided-wave grating and effective medium theory sub-branch cases.*

| Case ID | Category | Template Requirement | Variant Of / Equivalence | Data Dependencies |
|---|---|---|---|---|
| `guided_grating_emt` | `teaching_emt` | NEW_TEMPLATE (`grating-emt`) | `UNIQUE` | `NONE` |
| `absorbing_surface_gain_trend` | `research_extension` | NEW_TEMPLATE (`absorber-stack`) | `UNIQUE` | `Desktop deg.p sample CSVs` |

---

## Verification Requirements Prior to Sub-stage Execution
1. **Source Layer Stack Audit**: Read full layer_stack in Python before deciding template.
2. **Python Export**: Run `tools/export_visualization_cases.py` to generate JSON.
3. **Vitest Binding**: Add metric binding unit tests in `web3d/tests/`.
4. **Playwright E2E**: Add headless browser E2E tests verifying canvas, waves, and context loss.
5. **Accounting Re-run**: Run `py scripts/validate_case_registry.py` after each sub-stage.