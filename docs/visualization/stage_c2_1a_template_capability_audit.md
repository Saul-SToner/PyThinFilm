# Stage C.2.1A.1 Web3D 模板能力静态审计与适配决策报告

---

## 1. 审计目的

对现有 4 个 Web3D 模板（`single-interface`, `periodic-stack`, `defect-cavity`, `metal-dbr-interface`）进行静态能力审查，评估 5 个工程应用案例的实际物理结构与显示需求，明确给出 **`REUSE_EXISTING`**, **`EXTEND_EXISTING`** 或 **`NEW_TEMPLATE_REQUIRED`** 结论，避免盲目继承误导性教学语义（如 Tamm 界面局域态）。

---

## 2. 现存 Web3D 模板能力审计矩阵

| 模板名称 | 核心渲染 Primitives | 硬编码/特化假设 | 是否支持非周期任意多层 | 是否支持金属/有损复折射率 |
|---|---|---|---|---|
| `single-interface` | 单平面介质/折射光线 | 仅限单界面 (Air/Substrate) | 否 | 否 (仅显示标量 R/T) |
| `periodic-stack` | 周期性 H/L 介质块, 阻带光谱 | **假定 1/4 波长 H/L 周期堆栈**, 自动计算周期数并显示 DBR 阻带 | 否 (当前UI硬编码周期与高反带) | 否 (假设无损介质) |
| `defect-cavity` | DBR 镜像块 + 腔层 + 腔内驻波 | **假定对称 DBR 镜像 + 2L 腔**, 渲染腔内驻波示意 | 否 (特定 F-P 腔模型) | 否 |
| `metal-dbr-interface` | 金属层 + DBR 镜像 + Tamm 界面场包络 | **硬编码 Ag/DBR Tamm 界面**, 强绑定 Tamm 相位条件与 Python 场分布包络 | 否 (特化 Tamm 界面) | **是 (支持 Ag 金属层)** |

---

## 3. 逐案例模板适配决策与理由

### 3.1 `app_laser_mirror` (1064nm 激光高反镜)
- **结构特征**: `Air / (TiO2/SiO2)^8 H / Glass` (17 层 1/4 波长堆栈)
- **适配决策**: **`REUSE_EXISTING`**
- **目标模板**: `periodic-stack`
- **理由**: 完全满足 `periodic-stack` 的周期性 HL 堆栈与 DBR 高反禁带显示逻辑。

---

### 3.2 `app_wdm_filter` (WDM 1550nm 密集波分复用滤光片)
- **结构特征**: `Air / (TiO2/SiO2)^4 2L (SiO2/TiO2)^4 / Glass` (8层DBR + 1层半波 2L 腔)
- **适配决策**: **`REUSE_EXISTING`**
- **目标模板**: `defect-cavity`
- **理由**: 属于标准的 1550nm C 波段单腔 F-P 滤光片结构，完全匹配 `defect-cavity` 模板的镜像+缺陷腔与驻波示意 primitives。

---

### 3.3 `app_solar_cell_ar` (太阳能电池增透膜)
- **结构特征**: `Air / SiO2(94.18nm) / TiO2(59.78nm) / MgF2(99.64nm) / Si` (3 层渐变折射率)
- **适配决策**: **`EXTEND_EXISTING`**
- **目标模板**: `periodic-stack`
- **扩展需求**: **`GENERIC_MULTILAYER_MODE`**
- **理由**: 案例为 3 层非周期任意增透膜。直接复用 `periodic-stack` 会错误展示“周期数”和“DBR 阻带”；需在 `periodic-stack` 中增加通用多层模式（支持任意材质与非周期厚度），或在未来抽象为 `generic-multilayer` 模板。

---

### 3.4 `app_phone_lens_ar` (手机镜头多层增透膜)
- **结构特征**: `Air / SiO2(94.18nm) / ZrO2(65.48nm) / MgF2(99.64nm) / Glass` (3 层 AR)
- **适配决策**: **`EXTEND_EXISTING`**
- **目标模板**: `periodic-stack`
- **扩展需求**: **`GENERIC_MULTILAYER_MODE`**
- **理由**: 与太阳电池 AR 类似，属于 3 层非周期增透膜，需扩展通用多层渲染模式。

---

### 3.5 `app_smart_window` (智能调温窗 Low-E 膜)
- **结构特征**: `Air / WO3(80nm) / NiO(50nm) / Ag(15nm) / Glass` (3 层，含 15nm 银薄膜)
- **适配决策**: **`NEW_TEMPLATE_REQUIRED`**
- **目标模板**: `absorber-stack` (或扩展为 `generic-multilayer` 带有有损介质/金属吸收控制面板)
- **拒绝 `metal-dbr-interface` 理由**:
  - `metal-dbr-interface` 绑定了 Ag/DBR Tamm 界面匹配条件、相位关系与局域场包络；
  - 智能调温窗中 15nm 薄 Ag 层作用为**近红外高反射与吸收**，不存在 Tamm 界面共振；
  - 若强行复用 `metal-dbr-interface`，将导致页面继承错误的 Tamm 相位面板与不存在的界面态语义。因此判定需要 `absorber-stack` 新模板或受控扩展。
