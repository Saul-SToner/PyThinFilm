# Stage C.2.1A.1 五个工程应用案例权威来源与结构审计报告 (修订版)

> **审计基线**: `examples/applications/` 源码解算器及入口函数  
> **审计状态**: `SOURCE_AUDIT_PASSED`  
> **光传播层序规范**: `incident medium → layers[0] → ... → layers[-1] → substrate`（严格禁止混用沉积顺序或倒置）  
> **模板适配结论**: 2 个案例直接复用、2 个案例需要通用多层扩展 (`GENERIC_MULTILAYER_MODE`)、1 个案例需要 `absorber-stack` 新模板  
> **状态锁定规则**: 保持 `migration_status = PENDING_ENGINE_MIGRATION`（不进行前端绑定修改与状态改写）

---

## 1. 案例权威来源定位与调用链

| Case ID | 展示名称 | 正式源文件 | 权威入口函数 | 依赖项 | 物理模型 |
|---|---|---|---|---|---|
| `app_solar_cell_ar` | 太阳能电池三层增透膜 | `examples/applications/solar_cell_ar.py` | `run_solar_cell_ar` | `thinfilm.education` | TMM + 常数折射率 |
| `app_wdm_filter` | WDM 光通信密集波分复用滤光片 | `examples/applications/wdm_filter.py` | `run_wdm_filter` | `thinfilm.education` | TMM 1550nm C波段 |
| `app_laser_mirror` | 1064nm 激光高反镜 | `examples/applications/laser_mirror.py` | `run_laser_mirror` | `thinfilm.education` | TMM 1064nm DBR |
| `app_phone_lens_ar` | 手机镜头多层增透膜 | `examples/applications/phone_lens_ar.py` | `run_phone_lens_ar` | `thinfilm.education` | TMM 可见光平坦增透 |
| `app_smart_window` | 智能调温窗 Low-E 膜 | `examples/applications/smart_window.py` | `run_smart_window` | `thinfilm.education` | TMM + 金属 Ag 复折射率 |

---

## 2. 详细结构、层数断言与物理输入哈希 (`physics_input_hash`)

### 2.1 `app_solar_cell_ar` (太阳能电池增透膜)
- **光传播顺序**: `Air → SiO2(94.18nm) → TiO2(59.78nm) → MgF2(99.64nm) → Si(n=3.5)`
- **沉积顺序状态**: `NOT_DEFINED`
- **膜层数**: `coating_layer_count = 3`
- **材料折射率模型**: `CONSTANT_REAL_INDEX` (\(n_{\text{SiO2}}=1.46, n_{\text{TiO2}}=2.30, n_{\text{MgF2}}=1.38, n_{\text{Si}}=3.5+0.0j\))
- **`physics_input_hash`**: `4e892c9ff50672e8`
- **能量闭合**: `ALGEBRAIC_CLOSURE` (\(A = 1.0 - R - T\)，`energy_closure_residual < 1e-15`)

### 2.2 `app_wdm_filter` (WDM 通信滤光片)
- **光传播顺序**: `Air → (TiO2/SiO2)^4 → 2L(SiO2 cavity) → (SiO2/TiO2)^4 → Glass(n=1.46)`
- **膜层拆解**: `left_mirror_layers = 8`, `cavity_layers = 1`, `right_mirror_layers = 8`
- **膜层数**: `coating_layer_count = 17`
- **材料折射率模型**: `CONSTANT_REAL_INDEX` (\(n_{\text{TiO2}}=2.30, n_{\text{SiO2}}=1.46\))
- **`physics_input_hash`**: `9c916c228ca666fa`
- **能量闭合**: `ALGEBRAIC_CLOSURE` (`energy_closure_residual < 1e-15`)

### 2.3 `app_laser_mirror` (1064nm 激光高反镜)
- **光传播顺序**: `Air → (TiO2/SiO2)^8 H → Glass(n=1.46)`
- **膜层拆解**: `complete_HL_periods = 8`, `terminal_layer = H`
- **膜层数**: `coating_layer_count = 17`
- **材料折射率模型**: `CONSTANT_REAL_INDEX` (\(n_{\text{TiO2}}=2.30, n_{\text{SiO2}}=1.46\))
- **`physics_input_hash`**: `de5ec15fa2aefd57`
- **能量闭合**: `ALGEBRAIC_CLOSURE` (`energy_closure_residual < 1e-15`)

### 2.4 `app_phone_lens_ar` (手机镜头多层 AR)
- **光传播顺序**: `Air → SiO2(94.18nm) → ZrO2(65.48nm) → MgF2(99.64nm) → LaSFN9 Glass(n=1.80)`
- **膜层数**: `coating_layer_count = 3`
- **材料折射率模型**: `CONSTANT_REAL_INDEX` (\(n_{\text{SiO2}}=1.46, n_{\text{ZrO2}}=2.10, n_{\text{MgF2}}=1.38\))
- **`physics_input_hash`**: `9a0dbdb88c3aeb1a`
- **能量闭合**: `ALGEBRAIC_CLOSURE` (`energy_closure_residual < 1e-15`)

### 2.5 `app_smart_window` (智能调温窗 Low-E)
- **光传播顺序**: `Air → WO3(80nm) → NiO(50nm) → Ag(15nm) → Glass(n=1.52)`
- **膜层数**: `coating_layer_count = 3`
- **材料折射率模型**: `CONSTANT_COMPLEX_INDEX` (\(n_{\text{WO3}}=2.10, n_{\text{NiO}}=2.00, \tilde{n}_{\text{Ag}}=0.05 + 3.20j\))
- **`physics_input_hash`**: `1c1084bad123ae7b`
- **能量闭合**: `ALGEBRAIC_CLOSURE` (`energy_closure_residual < 1e-15`)
- **吸收验证对照测试**: 当把 Ag 虚部设为 0.0 时，最大吸收 \(A_{\text{lossless}} \equiv 0.00\)，证明吸收确实来自于 15nm 薄银层的虚部消光。

---

## 3. 模板能力适配决策表

1. **`app_laser_mirror`**: **`REUSE_EXISTING`** (`candidate_template = periodic-stack`)；
2. **`app_wdm_filter`**: **`REUSE_EXISTING`** (`candidate_template = defect-cavity`)；
3. **`app_solar_cell_ar`**: **`EXTEND_EXISTING`** (`candidate_template = periodic-stack`, `required_extension = GENERIC_MULTILAYER_MODE`)；
4. **`app_phone_lens_ar`**: **`EXTEND_EXISTING`** (`candidate_template = periodic-stack`, `required_extension = GENERIC_MULTILAYER_MODE`)；
5. **`app_smart_window`**: **`NEW_TEMPLATE_REQUIRED`** (`candidate_template = absorber-stack`，**严禁使用带有错误 Tamm 界面局域态语义的 `metal-dbr-interface` 模板**)。

---

## 4. 动态正弦波适配边界

- **`app_solar_cell_ar`**, **`app_phone_lens_ar`**, **`app_laser_mirror`**, **`app_smart_window`**: `FORWARD_RAY_PROPAGATION`；
- **`app_wdm_filter`**: `FORWARD_BACKWARD_WAVE_ILLUSTRATION`（腔内提供前/后向波等振幅驻波示意）。
