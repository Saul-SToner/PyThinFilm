# PyThinFilm 全案例 3D 动态可视化 — Stage A.1 对账与证据修正报告

本报告响应《Stage A.1：案例注册表对账与证据修正》指令，对全仓库案例集合进行准确的 ID 级算术与逻辑对账，核查并纠正了 4 个已有 3D 原型的状态维度，加固了注册表 JSON 模式与字段完整性，并补充了自动化测试与命令行执行日志证据。

---

## 一、 案例数量 ID 级集合对账 (Set Math & Reconciliation)

针对此前报告出现的 `18+1+5+16=40` 算术矛盾，以及与冻结总账 `19+22` 的对应关系，本次通过 Python 脚本 `scripts/validate_case_registry.py` 进行了全量 ID 集合演算。结果如下：

### 1. 各分类集合清单与数量
* **`teaching_case_ids`**（经典薄膜教学案例，共 **18 项**）：
  `quarter_wave_single_layer`, `half_wave_single_layer`, `single_ar`, `porous_sio2_layer`, `porous_double_ar`, `moth_eye_effective_gradient`, `double_ar`, `quarter_wave_double_layer`, `triple_ar`, `high_reflector`, `quarter_wave_stack`, `bragg_reflector`, `fp_single_halfwave`, `fp_filter`, `fp_double_halfwave`, `narrowband_filter`, `rugate_filter`, `neutral_beamsplitter`.
* **`emt_case_ids`**（光栅波导 EMT 教学案例，共 **1 项**）：
  `guided_grating_emt`（教学主展示 3）。
  $\to$ **教学案例集合小计 = 18 + 1 = 19 项**。
* **`engineering_case_ids`**（TMM 工程应用案例，共 **5 项**）：
  `app_solar_cell_ar`, `app_wdm_filter`, `app_laser_mirror`, `app_phone_lens_ar`, `app_smart_window`.
* **`research_extension_case_ids`**（真实材料与拓展研究案例，共 **16 项**）：
  `mat_library_demo`, `tamm_interface_priority`, `tamm_phase_bundle`, `tamm_phase_candidates`, `tamm_phase_focus`, `tamm_reflection_phase_screen`, `tamm_interface_window_bundle`, `tamm_interface_window_scan`, `pdrc_cooling_bundle`, `absorbing_baseline_template`, `absorbing_surface_bundle`, `absorbing_surface_gain`, `absorbing_surface_gain_trend`, `rugate_80layer_table`, `advanced_ar_bundle`, `porous_double_ar_topic_bundle`.
* **`non_teaching_runner_id`**（非教学 Runner 入口，共 **1 项**）：
  `guided_grating_demo`（作为 `guided_grating_emt` 在非教学例程中的 CLI 启动入口）。

### 2. 算术公式与全量唯一 ID 集合
$$\text{全量唯一 ID 集合 } \text{final\_unique\_case\_ids} = 18 + 1 + 5 + 16 + 1 = \mathbf{41\text{ 项}}$$
* **物理唯一案例数**：**40 项**（`narrowband_filter` 在 `thinfilm/education.py:L280` 中拥有 `periods=5` 独立参数；`guided_grating_demo` 作为 `guided_grating_emt` 的 Runner 入口）。
* **注册表条目总数**：**41 项**（100% 覆盖全仓库所有例程与 Runner 入口）。
* **条目类型划分**：`case`: 40, `alias`: 0, `runner`: 1 (`guided_grating_demo`)。

---

## 二、 6 个冲突案例的精细化证据状态 (Evidence Statuses)

对于依赖外部桌面 CSV 文件或 CLI 路径参数的 6 个案例，不再简单标注为 `READY` 或“隐藏曲线即解决”，而是严格区分**结构就绪**与**物理数据准备**：

| 案例 ID | 分类 | 证据状态 (`evidence_status`) | 冲突状态 (`conflict_status`) | 降级策略 (`notes`) |
| :--- | :--- | :--- | :--- | :--- |
| `tamm_interface_window_bundle` | 拓展研究 | `EXTERNAL_DATA_REQUIRED` | `EXTERNAL_CSV_MISSING` | 缺失 E3.csv 时 3D 渲染结构，2D 光谱以降级模式运行 |
| `tamm_interface_window_scan` | 拓展研究 | `EXTERNAL_DATA_REQUIRED` | `EXTERNAL_CSV_MISSING` | 缺失 E4.csv 时 3D 渲染结构，2D 扫描降级为示意 |
| `absorbing_surface_gain` | 拓展研究 | `EXTERNAL_DATA_REQUIRED` | `EXTERNAL_CSV_MISSING` | 缺失 CLI 参数时 3D 渲染平面基线，隐藏增益线 |
| `absorbing_surface_gain_trend` | 拓展研究 | `EXTERNAL_DATA_REQUIRED` | `HARDCODED_PATH_DEPENDENCY` | 依赖桌面 deg.p 路径，缺失时结构就绪但降级曲线 |
| `advanced_ar_bundle` | 拓展研究 | `EXTERNAL_DATA_REQUIRED` | `HARDCODED_PATH_DEPENDENCY` | 依赖桌面 COMSOL CSV，缺失时结构就绪 |
| `porous_double_ar_topic_bundle` | 拓展研究 | `EXTERNAL_DATA_REQUIRED` | `HARDCODED_PATH_DEPENDENCY` | 依赖桌面灵敏度 CSV，缺失时结构就绪 |

---

## 三、 4 个已有 Three.js 原型的多维状态核查

针对 `C:\Users\L2791\Downloads\visualizations` 目录下的 4 个原型，按照 4 维独立状态进行审查：

| 原型目录 / 对应案例 ID | 真实存在 | 最新修正版 | 支持 45° 斜入射 | 支持 TE/TM | 真实数值计算 | 动画教学示意 | 几何物理正确性 | 综合状态评估 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `single_ar_3d` (`single_ar`) | 是 | 是 | 是 | 是 | 是 (TMM算子) | 是 | 已确认几何无重叠 | `READY_FOR_MIGRATION` |
| `bragg_reflector_3d` (`bragg_reflector`) | 是 | 是 | 是 | 是 | 是 (TMM带隙) | 是 | 周期层展开无重叠 | `READY_FOR_MIGRATION` |
| `fp_filter_3d` (`fp_filter`) | 是 | 是 (对称版) | 是 | 是 | 是 (谐振峰) | 是 | 已修正为 $(HL)^4 2L (LH)^4$ 对称腔 | `READY_FOR_MIGRATION` |
| `tamm_state_3d` (`tamm_phase_bundle`) | 是 | 是 | 否 (仅正入射) | 是 | 否 (示意) | 是 | 需绑定 Python 导出结果 json | `GEOMETRY_VERIFIED` *(须绑定 Python json)* |

---

## 四、 自动化测试与校验脚本执行证据

### 1. Pytest 全量测试回归结果
* **执行命令**：`py -m pytest tests/ -q`
* **退出码**：`0` (Success)
* **执行时间**：`3.05s`
* **结果汇总**：**`334 passed, 0 failed, 0 skipped`** (261 warnings)

### 2. JSON 语法与模式校验结果
* **执行命令**：`py -m json.tool web3d/data/case_registry.json > $null`
* **退出码**：`0` (JSON 语法 100% 合法)
* **专用校验脚本**：`py scripts/validate_case_registry.py`
  ```text
  ============================================================
  PyThinFilm 3D Case Registry Reconciliation Audit
  ============================================================
  Total Registered Cases: 41
  Unique Case IDs:       41
  [PASS] Case ID Uniqueness Check PASSED.

  Category Breakdown:
    - engineering_applications : 5 cases
    - non_teaching_runner      : 1 cases
    - research_extension       : 16 cases
    - teaching_emt             : 1 cases
    - teaching_thinfilm        : 18 cases

  [PASS] Schema Completeness & Enum Validation PASSED.

  Reconciliation Summary:
    - Total Unique Cases Registered: 41
    - Prototype Aligned:             4
    - Structure Ready:               0
    - External Data Required:        6
  ============================================================
  ```

---

## 五、 Git 状态与版本归档

* **当前分支**：`national/v1.1-dev`
* **Stage A 开始前提交号**：`da5cf9ef3ae5425e26427fbb54e3a050c4796e32`
* **当前提交号**：待本次提交固化
* **新增与修改文件清单**：
  * `docs/visualization/case_3d_registry.md` (修改：更新 41 项对账与多维原型状态)
  * `web3d/data/case_registry.json` (修改：包含全量 41 项案例及全必填字段)
  * `scripts/validate_case_registry.py` (新增：案例注册表模式与不变量校验脚本)
  * `docs/visualization/stage_a_reconciliation_report.md` (新增：Stage A.1 对账报告)
