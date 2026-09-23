# Stage C.V1D：Python 教学案例正式导出与独立 App 推广

## 1. 范围

经人工批准，本阶段从现有 Python 教学预设确定性生成九份 Three.js 正式逐案例 JSON，并按 Stage C.V1A–C 的相同架构建立独立 App：

| 案例 | 独立入口 | 正式层数 |
|---|---|---:|
| `porous_sio2_layer` | `/apps/porous-sio2-layer/` | 1 |
| `porous_double_ar` | `/apps/porous-double-ar/` | 2 |
| `moth_eye_effective_gradient` | `/apps/moth-eye-gradient/` | 5 |
| `double_ar` | `/apps/double-ar/` | 2 |
| `quarter_wave_double_layer` | `/apps/quarter-wave-double-layer/` | 2 |
| `triple_ar` | `/apps/triple-ar/` | 3 |
| `fp_double_halfwave` | `/apps/fp-double-halfwave/` | 21 |
| `rugate_filter` | `/apps/rugate-filter/` | 80 |
| `neutral_beamsplitter` | `/apps/neutral-beamsplitter/` | 4 |

加上此前十四个入口，当前共有二十三个独立可运行 App。

## 2. Python 导出链

导出适配器位于 `tools/export_visualization_cases.py`。新增案例通过 `thinfilm.education.simulate_report_case` 调用教学目录中各自的正式默认设计类型和参数，并统一在 45° 下生成 TE (`s`) 与 TM (`p`) 光谱。

每份 JSON 包含：

- `case_id`、标题、Python 来源和计算来源；
- 环境、正式膜层、基底和真实厚度；
- 波长轴及 TE/TM 的 R、T、A；
- 550 nm 设计点与案例光谱极值；
- 能量守恒状态；
- 输入、物理结果和完整文件哈希。

本阶段没有修改 TMM、膜层构造器、默认参数或正式计算数值。新增 JSON 不是手工录入结果。

## 3. 数值验证

`tests/test_visualization_teaching_exports.py` 对九个案例逐一重新调用 Python：

- 导出波长轴与 Python 波长轴一致；
- TE/TM 的 R、T、A 在六位小数导出精度内逐点一致；
- R + T + A 满足能量守恒；
- 层名、层数和四位小数厚度与 Python 返回结构一致；
- `physics_input_hash`、`physics_result_hash` 和 `result_hash` 可重算一致。

九个 Python 契约测试全部通过。

## 4. 场景语义

- 所有页面继续使用当前 R/T 驱动的教学示意波，不称作定量空间电场；
- AR 案例提供最低反射、550 nm 和相对高反对照；
- 双半波 F-P 提供透射峰、550 nm 和最深阻带对照；
- Rugate 提供设计点、反射峰和带外对照；
- 中性分束膜以正式 R/T 数值判断是否接近 50/50，不以波形宽度代替定量结论；
- `moth_eye_effective_gradient` 只显示五层等效梯度，不绘制不存在于 TMM 模型中的微结构；
- Rugate 完整保留八十层离散结构。

## 5. 视觉与运行时适配

八十层 Rugate 的结构包围盒导致默认固定雾距离遮蔽远处模型。修复仅使学术浅色雾的 near/far 随相机距离扩展；没有压缩、删除或合并任何正式膜层。其他相机预设和浅色主题保持不变。

每个页面仍拥有独立 HTML 文档、Canvas、Renderer、相机、选择状态与动画状态。共享模块中不保存 Three.js 业务对象。

## 6. 真实浏览器证据

`docs/visualization/runtime/stage_cv1d/`：

- `porous_single.png`；
- `moth_eye_gradient.png`；
- `fp_double_halfwave.png`；
- `rugate_80_layers.png`；
- `neutral_beamsplitter.png`。

截图由 Playwright 驱动真实 Chromium 生成。视觉验收不使用像素完全相等判断。

## 7. 边界

- 未修改 Python 物理计算；
- 未修改既有正式 JSON；
- 未修改 `case_registry.json` 或任何 `migration_status`；
- 未实施 WorkspaceShell、VisualizationRouter、热力图、智能窗或场工作区；
- 尚未拥有 Three.js 正式逐案例契约的研究案例继续保持原状态。
