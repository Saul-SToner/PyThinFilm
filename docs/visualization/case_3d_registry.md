# PyThinFilm 全案例 3D 可视化注册表与设计文档 (Stage A.1 纠偏版)

本文档记录 PyThinFilm 代码库中全部 **41 项注册案例（40 项物理唯一案例 + 1 项别名/Runner 入口）** 的 3D 可视化注册表、4 项已有 Three.js 原型多维状态评估、8 大可复用物理渲染模板映射以及参数冲突与证据状态。

---

## 一、 统计概览与集合对账 (Reconciliation Summary)

* **注册表总条目数**：**41 项**
* **物理唯一案例数**：**40 项**
* **分类精确拆解 (Sum = 41)**：
  1. 经典薄膜教学案例 (`teaching_thinfilm`)：**18 项**
  2. 亚波长光栅 EMT 教学案例 (`teaching_emt`)：**1 项**（`guided_grating_emt`，主展示 3）
  3. TMM 工程应用案例 (`engineering_applications`)：**5 项**
  4. 真实材料与拓展研究案例 (`research_extension`)：**16 项**
  5. 非教学 Runner 入口 (`non_teaching_runner`)：**1 项**（`guided_grating_demo`，映射至 `guided_grating_emt`）
* **已有 3D 原型对齐**：**4 项** (`single_ar`, `bragg_reflector`, `fp_filter`, `tamm_phase_bundle`)
* **物理数据准备就绪 (`PHYSICS_DATA_READY`)**：**31 项**
* **需外部数据 (`EXTERNAL_DATA_REQUIRED`)**：**6 项**

---

## 二、 4 项已有 3D 原型多维状态评估 (Prototype Multi-Dimensional Status)

来自 `visualizations/` 目录的 4 个独立 Vite/Three.js 原型，经 4 维独立核查评估如下：

1. **`single_ar_3d` ($\to$ `single_ar`)**：
   * 45° 斜入射支持：**YES** | TE/TM 偏振支持：**YES** | 真实计算：**YES** | 动画示意：**YES**
   * 评估结论：**`READY_FOR_MIGRATION`**（可直接迁移至统一引擎）。
2. **`bragg_reflector_3d` ($\to$ `bragg_reflector`)**：
   * 45° 斜入射支持：**YES** | TE/TM 偏振支持：**YES** | 真实计算：**YES** | 动画示意：**YES**
   * 评估结论：**`READY_FOR_MIGRATION`**（周期层展开几何无缝）。
3. **`fp_filter_3d` ($\to$ `fp_filter`)**：
   * 45° 斜入射支持：**YES** | TE/TM 偏振支持：**YES** | 真实计算：**YES** | 动画示意：**YES**
   * 评估结论：**`READY_FOR_MIGRATION`**（已确认采用 $(HL)^4 2L (LH)^4$ 修正对称腔体）。
4. **`tamm_state_3d` ($\to$ `tamm_phase_bundle`)**：
   * 45° 斜入射支持：**NO** (仅正入射) | TE/TM 偏振支持：**YES** | 真实计算：**PARTIAL** (界面局域场需绑定 Python json) | 动画示意：**YES**
   * 评估结论：**`GEOMETRY_VERIFIED`**（具备迁移条件，但须绑定 Python 导出 json，不得伪装为前端实时求解）。

---

## 三、 8 大可复用物理渲染模板 (Physical Templates)

1. `single-interface`（单界面/少层干涉）；
2. `periodic-stack`（周期多层膜）；
3. `defect-cavity`（缺陷腔）；
4. `metal-dbr-interface`（金属/DBR 界面）；
5. `absorber-stack`（吸收与有损介质）；
6. `spectral-weighting`（光谱加权与选择性辐射）；
7. `engineering-device`（工程器件综合）；
8. `grating-emt`（光栅有效介质）。

---

## 四、 41 项案例全量注册表

| 序号 | 案例 ID | 中文名称 | 分类 | 结构/膜系摘要 | 对应 3D 模板 | 证据状态 (`evidence_status`) | 冲突状态 (`conflict_status`) | 来源位置 |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **1** | `quarter_wave_single_layer` | 1/4波长单层减反射膜 | `teaching_thinfilm` | Air / MgF2(99.6nm) / Glass | `single-interface` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L60` |
| **2** | `half_wave_single_layer` | 1/2波长单层相位膜(虚设层) | `teaching_thinfilm` | Air / MgF2(199.3nm) / Glass | `single-interface` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L73` |
| **3** | `single_ar` | 单层减反射膜(任意参数) | `teaching_thinfilm` | Air / MgF2(111.5nm) / Glass | `single-interface` | `PROTOTYPE_EXIST` | `NONE` | 原型 1: `single_ar_3d` |
| **4** | `porous_sio2_layer` | 多孔二氧化硅减反结构 | `teaching_thinfilm` | Air / Porous-SiO2(104.2nm) / Glass | `single-interface` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L99` |
| **5** | `porous_double_ar` | 多孔双层减反膜 | `teaching_thinfilm` | Air / Porous-SiO2 / TiO2 / Glass | `single-interface` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L112` |
| **6** | `moth_eye_effective_gradient` | 蛾眼等效渐变层减反膜 | `teaching_thinfilm` | Air / 5-Graded-Layers / Glass | `periodic-stack` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L126` |
| **7** | `double_ar` | 双层减反射膜(任意参数) | `teaching_thinfilm` | Air / SiO2 / TiO2 / Glass | `single-interface` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L145` |
| **8** | `quarter_wave_double_layer` | 四分之一波长双层减反膜(V形) | `teaching_thinfilm` | Air / MgF2 / ZrO2 / Glass | `single-interface` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L159` |
| **9** | `triple_ar` | 三层渐变折射率减反膜 | `teaching_thinfilm` | Air / MgF2 / Al2O3 / ZrO2 / Glass | `single-interface` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L173` |
| **10** | `high_reflector` | 高反射膜 | `teaching_thinfilm` | Air / (TiO2/SiO2)^6 / Glass | `periodic-stack` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L188` |
| **11** | `quarter_wave_stack` | 1/4波长QW膜堆 | `teaching_thinfilm` | Air / (TiO2/SiO2)^6 / Glass | `periodic-stack` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L203` |
| **12** | `bragg_reflector` | 布拉格反射镜(DBR) | `teaching_thinfilm` | Air / (TiO2/SiO2)^6 / Glass | `periodic-stack` | `PROTOTYPE_EXIST` | `NONE` | 原型 2: `bragg_reflector_3d` |
| **13** | `fp_single_halfwave` | 单半波型 F-P 滤光片 | `teaching_thinfilm` | Air / (HL)^3 2L (LH)^3 / Glass | `defect-cavity` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L233` |
| **14** | `fp_filter` | F-P 腔窄带透射滤光片 | `teaching_thinfilm` | Air / (HL)^4 2L (LH)^4 / Glass | `defect-cavity` | `PROTOTYPE_EXIST` | `NONE` | 原型 3: `fp_filter_3d` |
| **15** | `narrowband_filter` | 窄带透射滤光片(别名) | `teaching_thinfilm` | Air / (HL)^4 2L (LH)^4 / Glass | `defect-cavity` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L255` |
| **16** | `fp_double_halfwave` | 双半波型 F-P 滤光片 | `teaching_thinfilm` | Air / (HL)^2 2L (LH)^2 L ... / Glass | `defect-cavity` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L265` |
| **17** | `rugate_filter` | Rugate 褶皱渐变折射率滤光片 | `teaching_thinfilm` | Air / 80-Sinusoidal-Layers / Glass | `periodic-stack` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L303` |
| **18** | `neutral_beamsplitter` | 中性分束膜 | `teaching_thinfilm` | Air / Ag-TiO2-Stack / Glass | `single-interface` | `PHYSICS_DATA_READY` | `NONE` | `thinfilm/education.py:L325` |
| **19** | `guided_grating_emt` | 一维亚波长光栅 EMT | `teaching_emt` | Air / 1D-Si-Grating / Substrate | `grating-emt` | `PHYSICS_DATA_READY` | `NONE` | 教学主展示 3; `guided_grating/emt.py` |
| **20** | `app_solar_cell_ar` | 太阳能电池三层增透膜 | `engineering_applications` | Air / MgF2 / TiO2 / SiO2 / Si | `engineering-device` | `PHYSICS_DATA_READY` | `NONE` | `examples/applications/solar_cell_ar.py` |
| **21** | `app_wdm_filter` | WDM 光通信滤光片 | `engineering_applications` | Air / (HL)^4 2L (LH)^4 / Glass | `engineering-device` | `PHYSICS_DATA_READY` | `NONE` | `examples/applications/wdm_filter.py` |
| **22** | `app_laser_mirror` | 1064nm 激光高反镜 | `engineering_applications` | Air / (TiO2/SiO2)^10 / Substrate | `engineering-device` | `PHYSICS_DATA_READY` | `NONE` | `examples/applications/laser_mirror.py` |
| **23** | `app_phone_lens_ar` | 手机镜头多层增透膜 | `engineering_applications` | Air / MgF2/TiO2/SiO2/Al2O3 / Glass | `engineering-device` | `PHYSICS_DATA_READY` | `NONE` | `examples/applications/phone_lens_ar.py` |
| **24** | `app_smart_window` | 智能调温窗 Low-E 膜 | `engineering_applications` | Air / WO3 / NiO / Ag / Glass | `engineering-device` | `PHYSICS_DATA_READY` | `NONE` | `examples/applications/smart_window.py` |
| **25** | `mat_library_demo` | 真实材料库与色散插值 | `research_extension` | Air / Real-NK-Material / Substrate | `single-interface` | `PHYSICS_DATA_READY` | `NONE` | `cases/materials/run_material_library_demo.py` |
| **26** | `tamm_interface_priority` | Tamm 界面态优先极化筛选 | `research_extension` | Air / 30nm Ag / DBR | `metal-dbr-interface` | `PHYSICS_DATA_READY` | `NONE` | `cases/tamm/run_tamm_interface_priority.py` |
| **27** | `tamm_phase_bundle` | Tamm 反射相位相干匹配束 | `research_extension` | Air / 30nm Ag / DBR | `metal-dbr-interface` | `PROTOTYPE_EXIST` | `NONE` | 原型 4: `tamm_state_3d` |
| **28** | `tamm_phase_candidates` | Tamm 相位匹配候选点搜寻 | `research_extension` | Air / 30nm Ag / DBR | `metal-dbr-interface` | `PHYSICS_DATA_READY` | `NONE` | `cases/tamm/run_tamm_phase_candidates.py` |
| **29** | `tamm_phase_focus` | Tamm 相位聚焦与吸收增强 | `research_extension` | Air / 30nm Ag / DBR | `metal-dbr-interface` | `PHYSICS_DATA_READY` | `NONE` | `cases/tamm/run_tamm_phase_focus.py` |
| **30** | `tamm_reflection_phase_screen` | Tamm 反射相位多波长筛选 | `research_extension` | Air / 30nm Ag / DBR | `metal-dbr-interface` | `PHYSICS_DATA_READY` | `NONE` | `cases/tamm/run_tamm_reflection_phase_screen.py` |
| **31** | `tamm_interface_window_bundle` | Tamm 界面窗口束 | `research_extension` | Air / Ag / DBR | `metal-dbr-interface` | `EXTERNAL_DATA_REQUIRED` | `EXTERNAL_CSV_MISSING` | 需外部 COMSOL E3.csv |
| **32** | `tamm_interface_window_scan` | Tamm 界面窗口扫描 | `research_extension` | Air / Ag / DBR | `metal-dbr-interface` | `EXTERNAL_DATA_REQUIRED` | `EXTERNAL_CSV_MISSING` | 需外部 COMSOL E4.csv |
| **33** | `pdrc_cooling_bundle` | PDRC 被动辐射制冷评估束 | `research_extension` | Air / TiO2/SiO2/Ag / Substrate | `spectral-weighting` | `PHYSICS_DATA_READY` | `NONE` | `cases/pdrc/run_pdrc_cooling_bundle.py` |
| **34** | `absorbing_baseline_template` | 吸收表面基线模板 | `research_extension` | Air / Absorbing-Layer / Substrate | `absorber-stack` | `PHYSICS_DATA_READY` | `NONE` | `cases/absorbing_surface/run_absorbing_surface_baseline_template.py` |
| **35** | `absorbing_surface_bundle` | 吸收表面综合计算束 | `research_extension` | Air / Complex-Absorbing-Stack | `absorber-stack` | `PHYSICS_DATA_READY` | `NONE` | `cases/absorbing_surface/run_absorbing_surface_bundle.py` |
| **36** | `absorbing_surface_gain` | 吸收表面增益模型 | `research_extension` | Air / Rough-Absorber / Substrate | `absorber-stack` | `EXTERNAL_DATA_REQUIRED` | `EXTERNAL_CSV_MISSING` | 需 CLI --rough-csv 参数 |
| **37** | `absorbing_surface_gain_trend` | 吸收表面增益趋势 | `research_extension` | Air / Rough-Absorber / Substrate | `absorber-stack` | `EXTERNAL_DATA_REQUIRED` | `HARDCODED_PATH_DEPENDENCY` | 依赖桌面 deg.p 样本路径 |
| **38** | `rugate_80layer_table` | 80层 Rugate 褶皱滤光片列表 | `research_extension` | Air / 80-Layers / Glass | `periodic-stack` | `PHYSICS_DATA_READY` | `NONE` | `cases/advanced_ar/run_rugate_80layer_table.py` |
| **39** | `advanced_ar_bundle` | 高级增透膜计算束 | `research_extension` | Air / Multi-AR-Stack / Glass | `single-interface` | `EXTERNAL_DATA_REQUIRED` | `HARDCODED_PATH_DEPENDENCY` | 依赖桌面 COMSOL CSV |
| **40** | `porous_double_ar_topic_bundle` | 多孔双层增透专题 | `research_extension` | Air / Porous-Double-AR / Glass | `single-interface` | `EXTERNAL_DATA_REQUIRED` | `HARDCODED_PATH_DEPENDENCY` | 依赖桌面 COMSOL CSV |
| **41** | `guided_grating_demo` | 光栅非教学 Runner 入口 | `non_teaching_runner` | Air / 1D-Si-Grating / Substrate | `grating-emt` | `PHYSICS_DATA_READY` | `NONE` | `cases/guided_grating/run_guided_grating_demo.py` (映射至 `guided_grating_emt`) |
