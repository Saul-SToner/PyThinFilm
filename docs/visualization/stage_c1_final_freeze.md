# PyThinFilm 全案例 3D 动态可视化 — Stage C.1 最终冻结与权威统计归档报告

本报告记录 **Stage C.1.2（权威注册表等价字段写入、窄带精细线宽审计、10 案例全量物理与运行态归档）** 的最终冻结状态。

---

## 一、 权威注册表物理等价性字段

在 `web3d/data/case_registry.json` 中已显式固化物理等价组与复用策略：

- `high_reflector`:
  - `physical_equivalence_group` = `"dbr_7layer_hlh"`
  - `variant_of` = `"bragg_reflector"`
  - `result_reuse_policy` = `"SHARED_PHYSICS_DISTINCT_PEDAGOGY"`
  - `pedagogical_role` = `"高反射膜教学展示案例 (复用 bragg_reflector 7层物理结构)"`
  - `physical_equivalence_status` = `"EXACT"`

- `fp_single_halfwave`:
  - `physical_equivalence_group` = `"fp_13layer_defect_cavity"`
  - `variant_of` = `"fp_filter"`
  - `result_reuse_policy` = `"SHARED_PHYSICS_DISTINCT_PEDAGOGY"`
  - `pedagogical_role` = `"单半波长 F-P 滤光片教学展示案例 (复用 fp_filter 13层物理结构)"`
  - `physical_equivalence_status` = `"EXACT"`

---

## 二、 严格一致性与哈希匹配断言

两组等价案例经由 `tests/test_web3d_equivalence_audit.py` 验证：
- 光谱最大绝对残差：$\max|R_{\text{TE}}| = 0.0$, $\max|T_{\text{TE}}| = 0.0$, $\max|A_{\text{TE}}| = 0.0$, $\max|R_{\text{TM}}| = 0.0$, $\max|T_{\text{TM}}| = 0.0$, $\max|A_{\text{TM}}| = 0.0$；
- 物理输入与输出哈希 100% 匹配。

---

## 三、 权威统计口径账本 (`py scripts/validate_case_registry.py`)

```text
======================================================================
PyThinFilm 3D Case Registry Evidence Audit (Stage C.1.2 Final Accounting)
======================================================================
registry_entry_count:                           41
visualization_entry_count:                      40
runner_entry_count:                             1
migrated_verified_entry_count:                  9
migrated_candidate_entry_count:                 1
result_reuse_entry_count:                       2
unique_physical_configuration_count:            38
unique_migrated_verified_configuration_count:   7
unique_migrated_candidate_configuration_count:  1
unique_active_physical_configuration_count:     8
remaining_unique_physical_configuration_count:  30
======================================================================
```
