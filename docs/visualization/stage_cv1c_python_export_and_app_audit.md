# Stage C.V1C：Python 导出与独立 App 推广审计

## 结论修正

“没有 `web3d/public/results/{case_id}.json`”不等于“Python 没有导出”。此前使用“伪造”描述这一差异不准确。实际存在三层不同的产物：

1. Python 可计算案例：由 `thinfilm.education`、各专题模块和 runner 提供；
2. Python 教学目录或专题输出：例如 `~/thinfilm_outputs/teaching_main_branch_catalog.json`、CSV、metrics JSON 和专题 manifest；
3. Three.js 正式逐案例契约：当前位于 `web3d/public/results/{case_id}.json`，包含统一膜层、波长轴、TE/TM R/T/A 和前端绑定元数据。

独立 Three.js App 需要第 3 类契约。第 1、2 类数据需要经过确定性的契约转换和校验后才能直接接入，但这属于“尚未同步/转换”，不是“没有 Python 导出”。

## 已核验证据

- `thinfilm/api.py` 提供 `get_teaching_main_branch_catalog`、`simulate_teaching_case`、`export_teaching_case_outputs` 和 `export_teaching_main_branch_catalog`；
- `C:/Users/L2791/thinfilm_outputs/teaching_main_branch_catalog.json` 已存在，包含 18 个去重教学案例；
- `tools/export_visualization_cases.py` 当前只生成 14 份 Three.js 正式逐案例 JSON：4 个工程案例、9 个教学案例和 1 个 Tamm 案例；
- 教学目录中的 9 个案例尚未生成对应 Three.js 逐案例 JSON：
  `porous_sio2_layer`、`porous_double_ar`、`moth_eye_effective_gradient`、`double_ar`、`quarter_wave_double_layer`、`triple_ar`、`fp_double_halfwave`、`rugate_filter`、`neutral_beamsplitter`；
- `outputs/smart_window` 等目录也已有 CSV/metrics 产物，但尚未转换为当前 Three.js 正式契约；
- 部分研究案例声明外部 CSV 依赖，应区分“已有本地专题产物”和“可在任意离线安装中重建”。

本阶段没有重新运行或修改 Python 物理计算，没有复制专题输出冒充正式前端 JSON，也没有修改 `migration_status`。

## 本阶段独立化结果

在已有正式逐案例 JSON 的基础上新增 10 个独立入口：

| 类型 | 案例入口 |
|---|---|
| 单层膜 | `/apps/quarter-wave-single-layer/`、`/apps/half-wave-single-layer/`、`/apps/single-ar/` |
| DBR/QW | `/apps/high-reflector/`、`/apps/quarter-wave-stack/`、`/apps/bragg-reflector/` |
| F-P | `/apps/fp-single-halfwave/`、`/apps/fp-filter/`、`/apps/narrowband-filter/` |
| Tamm | `/apps/tamm-phase-bundle/` |

加上 Stage C.V1A/B 的四个工程入口，当前共有 14 个独立可运行 App。每个入口使用独立 HTML 文档和 Renderer；运行代码按单层膜、DBR、F-P、Tamm 与工程配置共享底层场景基座。

旧 JSON 中 `H/L/C/QW` 作为光学层角色显示，不被强制解释成具体化学材料。正式 `type`、折射率、厚度和层序均未改写。

## 后续数据工作边界

剩余案例不应被简单标记为“无数据”。后续应逐项建立映射表：Python 计算入口 → 已存在输出 → Three.js 契约缺口 → 所需校验。只有在逐案例契约生成并通过物理、哈希和前端绑定检查后，才开放相应独立入口。
