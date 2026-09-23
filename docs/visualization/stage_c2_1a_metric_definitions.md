# Stage C.2.1A.1 五个工程应用案例指标定义与降级说明明细 (修订版)

---

## 1. 工程指标分类、语义降级与有效性规则

指标状态只能为以下 4 种：
1. `FORMAL_SOURCE`: 源码公式中直接计算并导出的正式数值；
2. `DERIVED_FROM_FORMAL_OUTPUT`: 由正式导出光谱曲线在后处理中严格导出的衍生指标；
3. `NOT_AVAILABLE`: 源码中未计算或不存在的指标（禁止凭空捏造）；
4. `EXTERNAL_DATA_REQUIRED`: 依赖未包含的外部数据库或试剂测试数据。

---

## 2. 逐案例工程指标规范重命名与降级明细

### 2.1 `app_solar_cell_ar` (太阳能电池增透膜)
| 规范指标名称 | 原字段名 (兼容保留) | 状态 | 单位 | 物理定义 / 计算公式 | 降级与边界说明 |
|---|---|---|---|---|---|
| `avg_R_300_1100nm` | `avg_R_300_1100nm` | `FORMAL_SOURCE` | fraction | 300–1100nm 波段算术平均反射率 | 正式 TMM 解算 |
| `R_at_550nm` | `R_at_550nm` | `FORMAL_SOURCE` | fraction | 550nm 设计中心波长处反射率 | 线性插值 |
| `bandwidth_R_lt_2pct_nm` | `bandwidth_R_lt_2pct_nm` | `FORMAL_SOURCE` | nm | $R < 2\%$ 的连续波长宽度 | 掩码累加 |
| `avg_R_bare_Si` | `avg_R_bare_Si` | `FORMAL_SOURCE` | fraction | 裸硅衬底波段平均反射率基线 | 光学单界面公式 |
| `optical_coupling_gain_estimate_pct` | `efficiency_improvement_pct` | `DERIVED_FROM_FORMAL_OUTPUT` | % | 光耦合相对改善率 $((1-\bar{R})/(1-\bar{R}_{\text{bare}})-1) \times 100$ | **非太阳电池伏安特性/PCE/EQE 转换效率** |

---

### 2.2 `app_wdm_filter` (WDM 通信滤光片)
| 指标名称 | 状态 | 指标有效性状态 (`metric_validity_status`) | 单位 | 物理定义 / 计算公式 | 边界与局限说明 |
|---|---|---|---|---|---|
| `peak_transmittance` | `FORMAL_SOURCE` | `PASSED` | fraction | 1550nm 处的峰值透射率 | 正式 TMM 峰值 |
| `fwhm_nm` | `FORMAL_SOURCE` | `PASSED` | nm | 半高全宽（FWHM） | $T \ge T_{\text{peak}}/2$ 跨度 |
| `fsr_nm` | `DERIVED_FROM_FORMAL_OUTPUT` | `SCAN_RANGE_INSUFFICIENT` | nm | 自由光谱范围 $\text{FSR} = \lambda_0^2 / (2 n_{\text{cavity}} d_{\text{cavity}})$ | **在当前 1500–1600nm 区间内仅有 1 个透射峰，无法由实际光谱直接双峰提取** |
| `finesse` | `DERIVED_FROM_FORMAL_OUTPUT` | `NOT_AVAILABLE` | dimensionless | 精细度 $F = \text{FSR} / \text{FWHM}$ | FSR 缺失，故精细度设为不可用 |
| `isolation_dB` | `FORMAL_SOURCE` | `PASSED` | dB | 偏离峰值 2*FWHM 处抑制度 $-10 \log_{10}(T_{\text{off-peak}})$ | 线性转 dB |

---

### 2.3 `app_laser_mirror` (1064nm 激光高反镜)
| 指标名称 | 状态 | 单位 | 物理定义 / 计算公式 | 边界与局限说明 |
|---|---|---|---|---|
| `peak_reflectance` | `FORMAL_SOURCE` | fraction | 1064nm 处峰值反射率 | 正式 TMM 解算 |
| `R_at_1064nm` | `FORMAL_SOURCE` | fraction | 1064nm 中心波长反射率 | 线性插值 |
| `stopband_width_nm` | `FORMAL_SOURCE` | nm | 高反射带宽度 ($R > 99\%$) | 连续波段跨度 |
| `index_ratio` | `FORMAL_SOURCE` | ratio | 高低折射率对比度 $n_H / n_L$ | 膜系常数 |

---

### 2.4 `app_phone_lens_ar` (手机镜头多层 AR)
| 规范指标名称 | 原字段名 | 状态 | 单位 | 物理定义 / 计算公式 | 降级与边界说明 |
|---|---|---|---|---|---|
| `avg_R_visible` | `avg_R_visible` | `FORMAL_SOURCE` | fraction | 可见光 380–780nm 平均反射率 | 正式 TMM 解算 |
| `avg_R_single_layer` | `avg_R_single_layer` | `FORMAL_SOURCE` | fraction | 单层 MgF2 对比反射率 | 对照组平均值 |
| `R_improvement_vs_single` | `R_improvement_vs_single` | `DERIVED_FROM_FORMAL_OUTPUT` | % | 相对单层 AR 改善百分比 | 衍生百分比 |
| `R_blue_450nm` / `R_green_550nm` / `R_red_650nm` | - | `FORMAL_SOURCE` | fraction | 450/550/650nm 各通道反射率 | 插值获取 |
| `HEURISTIC_COLOR_FLATNESS_SCORE` | `color_uniformity` | `DERIVED_FROM_FORMAL_OUTPUT` | score | 启发式 RGB 平坦度评分 $1 - (\max - \min)$ | **三点采样平坦度评分，非国际标准 CIE 色差** |

---

### 2.5 `app_smart_window` (智能调温窗 Low-E)
| 规范指标名称 | 原字段名 | 状态 | 单位 | 物理定义 / 计算公式 | 降级与边界说明 |
|---|---|---|---|---|---|
| `T_visible` | `T_visible` | `FORMAL_SOURCE` | fraction | 可见光 (400–700nm) 平均透射率 | 波段平均 |
| `T_NIR` / `R_NIR` | `T_NIR` / `R_NIR` | `FORMAL_SOURCE` | fraction | 近红外 (700–2500nm) 平均透射/反射率 | 波段平均 |
| `T_solar_weighted` / `R_solar_weighted` | - | `DERIVED_FROM_FORMAL_OUTPUT` | fraction | 500nm 峰值高斯拟合太阳辐射加权 | **解析高斯加权，非 ASTM G173 规范全光谱积分** |
| `SHGC_PROXY` | `SHGC` | `DERIVED_FROM_FORMAL_OUTPUT` | ratio | 估算太阳得热系数 $T_{\text{solar}} + 0.5 \times A_{\text{solar}}$ | **基于高斯加权的估计值，非建筑能效标准 SHGC 认证值** |
| `visible_transmittance_proxy` | `luminous_efficacy` | `DERIVED_FROM_FORMAL_OUTPUT` | fraction | 可见光透射率估计 | **非 CIE 人眼光视效率加权 (lm/W)** |
| `NIR_rejection_ratio` | `NIR_rejection_ratio` | `DERIVED_FROM_FORMAL_OUTPUT` | ratio | 近红外抑制比 $T_{\text{vis}} / T_{\text{NIR}}$ | 衍生比值 |
