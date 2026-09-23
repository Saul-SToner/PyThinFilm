# Stage C.V1E：可复现扩展案例独立 App 推广

## 1. 本阶段范围

本阶段在已有二十三个独立入口基础上，新增五个不依赖仓库外 CSV、可由当前 Python 确定性重算的独立入口：

| 案例 | 独立入口 | 显示层数 | 正式计算来源 |
|---|---|---:|---|
| `app_smart_window` | `/apps/smart-window/` | 3 | `build_smart_window_layers` + `multilayer_rt_spectrum` |
| `guided_grating_emt` | `/apps/guided-grating-emt/` | 1 个等效层 | `emt_layer_spectrum` |
| `mat_library_demo` | `/apps/material-library/` | 1 | `simulate_teaching_design_real_materials` |
| `pdrc_cooling_bundle` | `/apps/pdrc-cooling/` | 6 | `simulate_pdrc_multilayer_cooling` |
| `rugate_80layer_table` | `/apps/rugate-80layer-table/` | 80 | `build_rugate_filter_layers` + TMM |

当前共有二十八份正式前端 JSON 和二十八个物理唯一案例入口。`guided_grating_demo` 是 `guided_grating_emt` 的 Runner 复用入口，不重复建立第二个物理场景。

## 2. 数据契约

导出适配器位于 `tools/export_visualization_extension_cases.py`。每份 JSON 包含：

- 案例、源文件、源符号和计算来源；
- 环境、正式膜层、基底与真实厚度；
- 45° 下的 TE/TM 波长轴以及 R/T/A；
- 模型适用范围或语义限制；
- 能量守恒状态；
- 物理输入、物理结果和完整文件哈希。

光谱数值保留八位小数，以避免序列化舍入使 `R + T + A` 超出前端契约容差。该处理不修改 Python 计算值。

## 3. 案例语义边界

### 智能窗

页面只表示一个固定的 `WO3/NiO/Ag` 光谱状态。它没有实现材料状态切换，因此不称作已完成的电致变色动画或智能窗控制器。

### 光栅 EMT

场景中的单层方块是 TE/TM 各向异性等效层，不是光栅齿几何。当前仓库代表参数的归一化周期指标 `rho >= 1`，正式 JSON 保留 `status = rejected`，页面明确标注零级 EMT 失效边界，不把结果称作全波衍射或严格 RCWA。

### 真实材料库

材料库包含多个材料和三个示范膜系。独立 Three.js 场景选择 `MgF2 / SiO2` 单层代表例，并通过真实 `n,k` 插值计算；没有把材料目录错误拼接为一个多层膜。

### PDRC

页面使用当前 Python 内置有效光学常数进行第一版宽谱筛选。它不替代真实材料色散或 COMSOL 代表点验证。

### Rugate 表

完整保留八十个离散切片。光谱由同一 Python 层表送入 TMM 获得，不复用另一案例的文件，也不压缩、合并或删除层。

## 4. 测试与证据

- Python 正式导出契约：7 项通过；
- 前端单元测试：89 项通过；
- 本阶段 Chromium E2E：5 项通过；
- Vite 二十八入口构建：通过；
- 每个页面保持一个 Renderer、三条教学示意波和独立选择状态；
- 控制台无错误。

真实浏览器截图位于 `docs/visualization/runtime/stage_cv1e/`：

- `smart_window.png`；
- `guided_grating_emt.png`；
- `pdrc_cooling.png`；
- `rugate_table.png`。

## 5. 未在本阶段推广的案例

以下专题的现有 Python Runner 读取仓库外 COMSOL CSV 或只导出数据模板，不能安全套用普通 TMM JSON：

- `tamm_interface_priority`、`tamm_phase_candidates`、`tamm_phase_focus`、`tamm_reflection_phase_screen`；
- `tamm_interface_window_bundle`、`tamm_interface_window_scan`；
- `absorbing_baseline_template`、`absorbing_surface_bundle`、`absorbing_surface_gain`、`absorbing_surface_gain_trend`；
- `advanced_ar_bundle`、`porous_double_ar_topic_bundle`。

这些案例需要下一阶段建立显式的 `external_data_provenance`、输入文件哈希、降级模式和专题视图契约。本阶段没有使用 `tamm_phase_bundle` 或教学 Rugate 数据冒充它们。

## 6. 修改边界

- 未修改 `thinfilm/` 或 `guided_grating/` 物理实现；
- 未修改既有正式 JSON；
- 未修改 `case_registry.json` 或任何 `migration_status`；
- 未实施 WorkspaceShell、路由架构或热力图；
- 未开发智能窗状态切换；
- 未把 EMT 等效层画成未经计算支持的微结构。
