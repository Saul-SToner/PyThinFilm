# PyThinFilm 全案例 3D 动态可视化 — Stage C.1 第一批 6 个教学案例注册表与模板映射报告

本报告记录对 **Stage C.1 第一批 6 个教学案例** 的结构提取、模板映射与注册表升级。

---

## 一、 6 个教学案例模板映射与来源表

| 案例 ID | 正式 Python 来源入口 (`thinfilm/education.py`) | 3D 模板组件 (`web3d/src/templates/`) | 膜层结构 | 偏振支持 | 等价关系与复用策略 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`quarter_wave_single_layer`** | `build_quarter_wave_single_layer_layers` | `single-interface` | Air / MgF2 99.64nm / Glass | TE, TM | 独立物理模型 |
| **`half_wave_single_layer`** | `build_half_wave_single_layer_layers` | `single-interface` | Air / SiO2 199.28nm / Glass | TE, TM | 独立物理模型 |
| **`high_reflector`** | `build_high_reflector_layers` | `periodic-stack` | Air / (HL)^3 H 7层 / Glass | TE, TM | 教学别名 (`variant_of: bragg_reflector`) |
| **`quarter_wave_stack`** | `build_quarter_wave_stack_layers` | `periodic-stack` | Air / (HL)^3 H 7层 / Glass | TE, TM | 独立物理模型 ((HL)^3 H 7层) |
| **`fp_single_halfwave`** | `build_fp_single_halfwave_layers` | `defect-cavity` | Air / (HL)^3 C (LH)^3 13层 / Glass | TE, TM | 教学别名 (`variant_of: fp_filter`) |
| **`narrowband_filter`** | `build_narrowband_filter_layers` | `defect-cavity` | Air / (HL)^4 C (LH)^4 17层 / Glass | TE, TM | 独立物理模型 (17层高品质因子滤光片) |

---

## 二、 注册表权威状态与等价属性

所有 6 个案例均在 `web3d/data/case_registry.json` 中配置为规范 `MIGRATION_VERIFIED` 状态，并且 `high_reflector` 与 `fp_single_halfwave` 标记有 `result_reuse_policy = "SHARED_PHYSICS_DISTINCT_PEDAGOGY"` 字段。
