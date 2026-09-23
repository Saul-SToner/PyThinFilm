# Stage C.V1F：外部数据证据 App

## 结论

本阶段将剩余 12 个案例拆成独立 Three.js 入口，但没有把 COMSOL 扫描、粗糙表面结果或验证汇总伪装成平面膜层。每个入口读取一份由现有 Python 分析函数生成的静态证据契约，使用数据驱动 Three.js 科研场景、SVG 曲线、结果表和来源哈希呈现。

本阶段未修改 TMM/RCWA 物理计算、正式输入数值、案例注册表、`migration_status`、通用页面路由或既有 Three.js 视觉。

## 独立入口

| 类别 | case_id | 入口 | 状态 |
| --- | --- | --- | --- |
| Tamm | `tamm_interface_priority` | `/apps/tamm-interface-priority/` | 外部证据就绪 |
| Tamm | `tamm_phase_candidates` | `/apps/tamm-phase-candidates/` | 外部证据就绪 |
| Tamm | `tamm_phase_focus` | `/apps/tamm-phase-focus/` | 外部证据就绪 |
| Tamm | `tamm_reflection_phase_screen` | `/apps/tamm-reflection-phase-screen/` | 外部证据就绪 |
| Tamm | `tamm_interface_window_bundle` | `/apps/tamm-interface-window-bundle/` | 降级：部分输入缺失 |
| Tamm | `tamm_interface_window_scan` | `/apps/tamm-interface-window-scan/` | 降级：部分输入缺失 |
| 吸收表面 | `absorbing_baseline_template` | `/apps/absorbing-baseline-template/` | 仅输入模板 |
| 吸收表面 | `absorbing_surface_bundle` | `/apps/absorbing-surface-bundle/` | 外部证据就绪 |
| 吸收表面 | `absorbing_surface_gain` | `/apps/absorbing-surface-gain/` | 外部证据就绪 |
| 吸收表面 | `absorbing_surface_gain_trend` | `/apps/absorbing-surface-gain-trend/` | 外部证据就绪 |
| 增透验证 | `advanced_ar_bundle` | `/apps/advanced-ar-bundle/` | 外部证据就绪 |
| 增透专题 | `porous_double_ar_topic_bundle` | `/apps/porous-double-ar-topic/` | 就绪：有解释限制 |

## 数据边界

- 证据 JSON 只保存外部文件名、字节数和 SHA-256，不保存用户目录或 OneDrive 绝对路径。
- `evidence_hash` 覆盖可视化证据载荷；`result_hash` 覆盖完整导出契约。
- 页面直接展示 Python 分析语义，不在 JavaScript 中重算物理量。
- 每个入口创建且仅创建一个 Three.js Renderer，并提供轨道观察与重置视角。
- Three.js 场景表达相位轨迹、局域样本、光谱轨迹、参数趋势或验证指标；页面明确标注它们不是未提供几何或场分布的复原。
- Tamm 窗口现存三份输入均为单一 y 截面，明确不称为二维热力图。
- `E3.csv`、`E4.csv`、`tamm_interface_test_111nm_455um.csv` 缺失，两个窗口入口保持 `DEGRADED_PARTIAL_INPUT`。
- 吸收基线模板不生成虚构光谱；它只呈现所需列与几何语义。

## 生成与验证

生成命令：

```powershell
py -3.13 tools/export_visualization_external_evidence_cases.py
```

验证包括：12 份契约完整性、证据哈希、外部输入 SHA-256、私人路径清理、降级状态、模板不伪造曲线、12 个独立入口加载、控制台无错误、每页 Renderer 为 1，以及重置视角有效。

## 浏览器证据

代表性真实浏览器截图位于：

- `docs/visualization/runtime/stage_cv1f/tamm_phase_candidates.png`
- `docs/visualization/runtime/stage_cv1f/tamm_window_degraded.png`
- `docs/visualization/runtime/stage_cv1f/absorbing_surface_gain.png`
- `docs/visualization/runtime/stage_cv1f/advanced_ar_bundle.png`

截图用于人工检查布局与语义，不作为像素完全相同的自动验收标准。
