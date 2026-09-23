# Stage C.V1B：工程案例独立 App 推广复核

## 范围

在人工批准解除“仅 `app_solar_cell_ar`”限制后，将相同的独立页面架构推广到另外三个已迁移工程案例：

| 案例 | 独立入口 | 正式膜层 | 专属判读预设 |
|---|---|---:|---|
| `app_solar_cell_ar` | `/apps/solar-ar/` | 3 | 最低反射、550 nm、相对高反 |
| `app_wdm_filter` | `/apps/wdm-filter/` | 17 | 通带峰值、1550 nm、最深阻带 |
| `app_laser_mirror` | `/apps/laser-mirror/` | 17 | 1064 nm、反射峰值、低反射对照 |
| `app_phone_lens_ar` | `/apps/phone-lens-ar/` | 3 | 蓝光 450、绿光 550、红光 650 nm |

每个入口拥有独立 HTML 文档、启动模块、Three.js Renderer 和页面状态。三个新增入口共享 `EngineeringCaseApp`、`EngineeringCaseScene`、光谱取样与视觉样式，但不共享运行中的 DOM、Three.js 对象或选择状态。通用案例浏览器 `/` 保持不变。

## 数据与物理边界

- 每个 App 只读取自己的 `web3d/public/results/{case_id}.json`；
- 启动时校验 `case_id` 和正式膜层数量；
- R/T/A、波长插值和示意振幅继续使用既有 `spectrumWaveAmp.js`；
- 未修改 Python TMM、正式 JSON、层序、膜层数、TE/TM 基、传播公式或 `migration_status`；
- H/L/C 仅在视觉调色板中稳定映射为 TiO2/SiO2/SiO2 色，不改写正式材料数据；
- 极小非零波仍遵守最小可见值放大并在页面标记，零功率波仍被抑制。

## 真实浏览器证据

`docs/visualization/runtime/stage_cv1b/`：

- `wdm_default.png`：WDM 通带峰值，透射波占主导；
- `wdm_stopband.png`：WDM 最深阻带，反射波占主导；
- `laser_default.png`：1064 nm 高反射状态；
- `laser_low_reflection.png`：带外低反射对照；
- `phone_default.png`：手机镜头 450 nm；
- `phone_green.png`：手机镜头 550 nm。

截图由 Playwright 驱动真实 Chromium 生成。自动验收不进行像素完全相同比较。

## 验收结果

- 三个新增入口均只创建一个 Canvas 和一个 Renderer；
- 正式膜层分别为 17、17、3 层，完整加载且可选择；
- WDM 通带 T > 90%，最深阻带 T < 10%；
- 激光镜 1064 nm R > 99%，并提供低反射带外对照；
- 手机镜头可在 450/550/650 nm 间切换；
- 三种相机预设、重置、暂停和 TE/TM 继续有效；
- 四个工程入口是四个独立文档运行时；
- 控制台和页面错误为空。

## 已知限制

1. 独立页面目前由明确 URL 访问，尚未实施 VisualizationRouter 或 WorkspaceShell。
2. 17 层结构的右侧层列表需要滚动，这是为了保留全部正式层而不压缩主视图。
3. 正弦波是 R/T 驱动的教学示意，不是膜内定量电场。
4. 本阶段没有开发光谱页面、热力图、场工作区或智能窗。
