# PyThinFilm 全案例 3D 动态可视化 — Stage A.2 语义与证据状态修正报告

本报告响应《Stage A.2 证据状态修正》指令，清除了未经验证的批量 `PASSED` 与 `GEOMETRY_READY` 赋值，按代码与原型事实重置了状态与比较日志，并排除了 Runner 入口对几何就绪场景计数的污染。

---

## 一、 核心修正：消除无证据的状态赋值

1. **未核查案例状态重置**：
   * 所有未进行逐案例几何/物理对照的案例，默认重置为：
     * `geometry_status` = `"NOT_AUDITED"`
     * `physics_data_status` = `"NOT_AUDITED"`
     * `python_reference_comparison` = `"NOT_RUN"`
     * `migration_status` = `"PENDING_ENGINE_MIGRATION"`
   * 结果：`python_reference_passed_count` 归零 (**0**)，防止未经逐点对照的数值误标为 `PASSED`。

2. **Runner 条目解耦**：
   * `guided_grating_demo`（`entry_kind = "runner"`）复用 `guided_grating_emt` 的场景，不再作为独立“几何就绪场景”重复计数。

3. **四个 Three.js 原型状态重置**：
   * **`single_ar`**：`geometry_status` = `GEOMETRY_READY`, `migration_status` = `READY_FOR_MIGRATION`, `python_reference_comparison` = `NOT_RUN`；
   * **`bragg_reflector`**：`geometry_status` = `GEOMETRY_READY`, `migration_status` = `READY_FOR_MIGRATION`, `python_reference_comparison` = `NOT_RUN`；
   * **`fp_filter`**：`geometry_status` = `GEOMETRY_MISMATCH` (原型 3 周期 vs 官方 4 周期), `migration_status` = `PROTOTYPE_ONLY`, `conflict_status` = `PROTOTYPE_GEOMETRY_MISMATCH`, `python_reference_comparison` = `NOT_RUN`；
   * **`tamm_phase_bundle`**：`geometry_status` = `GEOMETRY_READY`, `physics_data_status` = `ILLUSTRATIVE_ONLY`, `calculation_source` = `illustrative_only`, `migration_status` = `PROTOTYPE_ONLY`, `python_reference_comparison` = `NOT_RUN`。

---

## 二、 证据驱动的状态统计拆解 (Evidence-Backed Metrics)

经过 `scripts/validate_case_registry.py` 自动化核验，结果如下：

| 统计指标 | 真实数量 | 备注与事实依据 |
| :--- | :---: | :--- |
| **`registry_entry_count`** | **41** | 注册表全量条目总数 |
| **`physical_case_count`** | **40** | 物理独立案例总数 (`narrowband_filter` 具 5 周期独立参数) |
| **`alias_entry_count`** | **0** | 0 项别名条目 |
| **`runner_entry_count`** | **1** | `guided_grating_demo`（非教学 Runner 入口） |
| **`visualization_target_count`** | **40** | 独立 3D 渲染目标场景总数 |
| **`geometry_ready_count` (excl. runner)** | **3** | 仅核对过的 3 个原型 (`single_ar`, `bragg_reflector`, `tamm`) |
| **`geometry_mismatch_count`** | **1** | `fp_filter` (原型 3 周期 vs 官方 4 周期) |
| **`geometry_not_audited_count`** | **36** | 未完成逐案例 3D 几何核查的案例 |
| **`physics_data_ready_count`** | **3** | `single_ar`, `bragg_reflector`, `fp_filter` 具备计算数据 |
| **`illustrative_only_count`** | **1** | `tamm_phase_bundle`（原型教学示意） |
| **`external_data_required_count`** | **6** | 需桌面外部 CSV 数据脚本 |
| **`ready_for_migration_count`** | **2** | 仅 `single_ar` 与 `bragg_reflector` |
| **`prototype_only_count`** | **2** | `fp_filter` (结构失配) 与 `tamm_phase_bundle` (数据示意) |
| **`pending_engine_migration_count`** | **37** | 待统一引擎 Stage B.0 搭建后接入 |
| **`python_reference_passed_count`** | **0** | **0 项**（严禁在无逐点误差比较报告前标记 PASSED） |
| **`python_reference_not_run_count`** | **41** | 全部 41 项均标注为 NOT_RUN |

---

## 三、 Git 提交与固化

* **Git Branch**：`national/v1.1-dev`
* **Commit Message**：`fix(web3d): remove unverified ready and comparison statuses`
