# PyThinFilm 全案例 3D 动态可视化 — Stage B.1D.2 真实浏览器运行态与注册表断言报告

本报告记录 **Stage B.1D.2（`tamm_phase_bundle` 公共参考面最终修正、一维 TMM 场求解器验证与权威注册表同步）** 的验收结果。

---

## 一、 开发服务器与权威注册表同步 (`npm run sync-registry` & `npm run dev`)

```text
> pythinfilm-web3d@1.0.0 sync-registry
> node scripts/sync-registry.mjs

[sync-registry] Successfully synced C:\Users\L2791\Downloads\PyThinFilm\web3d\data\case_registry.json -> C:\Users\L2791\Downloads\PyThinFilm\web3d\public\data\case_registry.json
```

---

## 二、 权威案例注册表 `scripts/validate_case_registry.py` 证据日志

```powershell
=================================================================
PyThinFilm 3D Case Registry Evidence Audit (Stage B.1D.2 tamm_phase_bundle)
=================================================================
Registry Entry Count:          41
Unique Entry IDs:              41
Physical Case Count:           40
Alias Entry Count:             0
Runner Entry Count:            1
Visualization Target Count:    40
[PASS] Entry Count Assertions PASSED (41 entries, 40 physical cases, 0 alias, 1 runner, 40 targets).

Evidence-Backed Status Metrics Breakdown:
  - geometry_verified_count:             4 (single_ar, bragg_reflector, fp_filter, tamm_phase_bundle)
  - physics_data_available_count:        4
  - migration_verified_count:            3 (single_ar, bragg_reflector, fp_filter)
  - migrated_count:                      1 (tamm_phase_bundle)
  - pending_engine_migration_count:      36
  - frontend_binding_passed_count:       4
  - python_export_verified_count:        4

[PASS] All Schema, Field Completeness & Status Enum Checks PASSED.
=================================================================
```

---

## 三、 浏览器运行态检查结果

1. **`tamm_phase_bundle` 修正后的公共参考面与场提示**：
   - 界面 Tooltip 正确标注 Ag/H1 界面位置为 $z = 30\text{ nm}$；
   - 标注场极大值位于第一层 H1 内部 ($z = 77\text{ nm}$，距界面 $47\text{ nm}$)；
   - 参数面板明确标注：
     - `tamm_validation_status` = `PHASE_MATCHED_LEAKY_CANDIDATE`
     - `field_localization_status` = `FIELD_ENHANCEMENT_CANDIDATE`
     - `field_solver_status` = `FIELD_SOLVER_VERIFIED`
     - `material_model` = `CONSTANT_COMPLEX_INDEX` (固定复折射率 $n=0.13+3.98i$)
2. **四案例 50 次连续切换回归**：
   - `web3d/tests/four_case_switching.test.js` 验证 50 次切换过程中 `WebGLRenderer` Context 0 次丢失。
3. **控制台检查**：
   - 0 error / warning，无 WebGL 报错。

---

## 四、 Git 提交日志

* **Commit Message**：`fix(web3d): close Tamm interface phase and field-localization evidence`
