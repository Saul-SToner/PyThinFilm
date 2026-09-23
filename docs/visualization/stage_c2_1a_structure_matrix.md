# Stage C.2.1A.1 五个工程应用案例物理结构矩阵 (修订版)

---

## 1. 结构与参数比较矩阵

| Case ID | 案例名称 | 膜层光传播顺序 (从入射侧到基底) | 膜层数 (`coating_layer_count`) | 材料体系 | 物理输入哈希 (`physics_input_hash`) | 案例物理等价性 | 推荐模板需求 |
|---|---|---|---|---|---|---|---|
| `app_solar_cell_ar` | 太阳能电池三层增透膜 | SiO2 / TiO2 / MgF2 | 3 | SiO2, TiO2, MgF2, Si | `4e892c9ff50672e8` | `UNIQUE_PHYSICAL_CONFIGURATION` | `EXTEND_EXISTING` (periodic-stack) |
| `app_wdm_filter` | WDM 光通信滤光片 | (TiO2/SiO2)^4 2L (SiO2/TiO2)^4 | 17 (8+1+8) | TiO2, SiO2, Glass | `9c916c228ca666fa` | `UNIQUE_PHYSICAL_CONFIGURATION` | `REUSE_EXISTING` (defect-cavity) |
| `app_laser_mirror` | 1064nm 激光高反镜 | (TiO2/SiO2)^8 H | 17 (16+1) | TiO2, SiO2, Glass | `de5ec15fa2aefd57` | `UNIQUE_PHYSICAL_CONFIGURATION` | `REUSE_EXISTING` (periodic-stack) |
| `app_phone_lens_ar` | 手机镜头多层增透膜 | SiO2 / ZrO2 / MgF2 | 3 | SiO2, ZrO2, MgF2, LaSFN9 | `9a0dbdb88c3aeb1a` | `UNIQUE_PHYSICAL_CONFIGURATION` | `EXTEND_EXISTING` (periodic-stack) |
| `app_smart_window` | 智能调温窗 Low-E 膜 | WO3 / NiO / Ag | 3 | WO3, NiO, Ag, Glass | `1c1084bad123ae7b` | `UNIQUE_PHYSICAL_CONFIGURATION` | `NEW_TEMPLATE_REQUIRED` (absorber-stack) |

---

## 2. 详细膜层参数明细

### 2.1 `app_solar_cell_ar`
- Layer 1: `SiO2` ($n=1.46$, $d=94.18\,\text{nm}$)
- Layer 2: `TiO2` ($n=2.30$, $d=59.78\,\text{nm}$)
- Layer 3: `MgF2` ($n=1.38$, $d=99.64\,\text{nm}$)
- Substrate: `Si` ($n=3.50 + 0.00j$)

### 2.2 `app_wdm_filter`
- 8 层 DBR (TiO2/SiO2) + 1 层 SiO2 2L 腔 ($d = 530.82\,\text{nm}$) + 8 层 DBR (SiO2/TiO2)
- Substrate: `SiO2 Glass` ($n=1.46$)

### 2.3 `app_laser_mirror`
- 16 层 TiO2/SiO2 周期 1/4 波长堆栈 ($1064\,\text{nm}$) + 1 层 H 匹配层 (TiO2, $d=115.65\,\text{nm}$)
- Substrate: `SiO2 Glass` ($n=1.46$)

### 2.4 `app_phone_lens_ar`
- Layer 1: `SiO2` ($n=1.46$, $d=94.18\,\text{nm}$)
- Layer 2: `ZrO2` ($n=2.10$, $d=65.48\,\text{nm}$)
- Layer 3: `MgF2` ($n=1.38$, $d=99.64\,\text{nm}$)
- Substrate: `LaSFN9 Glass` ($n=1.80$)

### 2.5 `app_smart_window`
- Layer 1: `WO3` ($n=2.10$, $d=80.0\,\text{nm}$)
- Layer 2: `NiO` ($n=2.00$, $d=50.0\,\text{nm}$)
- Layer 3: `Ag` ($\tilde{n}=0.05 + 3.20j$, $d=15.0\,\text{nm}$)
- Substrate: `Glass` ($n=1.52$)
