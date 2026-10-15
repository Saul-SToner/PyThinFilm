# 动画仿真资料 V2

《论文.md》建议将介绍视频与动态仿真资料分开。这里先制作可复算的无配音原片，不把 PPT 翻页或软件操作录屏冒充物理过程动画。

| 原片 | 变量 | 动态证据 | 建议解说重点 |
| --- | --- | --- | --- |
| `00_interference_mechanism.mp4` | 固定 MgF₂ 99.6 nm，波长 440–740 nm | 前两束反射的复振幅示意与完整 TMM 反射率同步 | 上、下界面返回波的相位关系随波长变化；金色箭头只代表前两束和，不是精确反射率或几何光线追踪。 |
| `01_mgf2_thickness.mp4` | MgF₂ 膜厚 80–135 nm | 完整 TMM 的 R(λ)、550 nm 反射率和反射谷；前两束反射的相位箭头仅作示意 | 膜厚改变往返传播相位，反射谷并非固定在 550 nm；相位箭头不是完整多光束求解。 |
| `02_bragg_periods.mp4` | TiO₂/SiO₂ 从 1 到 10 周期 | 各周期完整 TMM 反射光谱与 90% 阈值 | 随周期堆叠，550 nm 附近高反射增强；固定厚度不是优化设计。 |
| `04_fp_cavity.mp4` | 固定 (HL)₃ 与 (LH)₃ 镜堆，SiO₂ 腔层 300–400 nm | 完整 TMM 的 T(λ)、透射峰位置与峰值 | 腔层变厚时选通波长移向长波；峰值取当前 500–650 nm 范围的最大透射点，不暗示全波段单峰。 |
| `03_field_vs_wavelength.mp4` | 固定 MgF₂ 99.6 nm，探针 440–740 nm | R(λ) 上的探针位置、同波长的层内相对电场强度 | 空间场强分布随探针波长变化；这不是时间演化或几何光线追踪。 |

每段 1280×720、20 fps、10 秒，无音轨，可循环、减速或配音剪辑。`video_materials/simulation_v1/simulation_manifest.json` 保存参数与端点数值；片源由 `tools/video/render_simulation_clips.py` 在本地重建。素材采用当前 PyThinFilm 实测材料库，在正入射、一维平面分层模型边界内解释。

`PyThinFilm_simulation_preview_50s.mp4` 按机制、减反、高反、选频、场强顺序串接五段，仅供检查结构与节奏，不是最终的 3–5 分钟参赛视频。正式版还需配音、必要的停顿和解释。旧版 30 秒预览仍保留作对照。

介绍视频另行录制软件操作、模型选择与验收，不应把这些数值原片包装为 Optiland 镜头光线追踪或 COMSOL 全波场。成片宜用“问题 → 控制变量 → 动态结果 → 物理解释 → 模型边界”的顺序；前两束反射动画是相位示意，完整结果始终由旁边的 TMM 曲线承担。

生成：

```powershell
& "Frontend/V3/.venv/Scripts/python.exe" tools/video/render_simulation_clips.py --ffmpeg "C:\path\to\ffmpeg.exe"
```
