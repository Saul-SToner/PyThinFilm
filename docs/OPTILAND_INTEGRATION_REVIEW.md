# Optiland 作为 PyThinFilm 系统级下游引擎的集成审阅

## 结论摘要

审阅对象：

- PyThinFilm：`C:\Users\L2791\Downloads\PyThinFilm`
- Optiland：`C:\Users\L2791\Downloads\optiland`
- Optiland 审阅提交：`17610805`（`master`）
- Optiland 版本：`0.6.2.post89+g17610805`

结论：**Optiland 适合作为 PyThinFilm 的可选系统级光学下游引擎，且最小闭环已经跑通。** 它不应替代 PyThinFilm 的膜系编辑、材料管理和 TMM 主计算，而应接收已经明确单位和材料映射的膜系数据，负责顺序光线追迹和系统级分析，再把数值数组交回 PyThinFilm 前端。

本轮没有修改 PyThinFilm 现有计算逻辑，没有复制 Optiland 源码，也没有改动 Optiland 源码。新增内容只有：

- `experiments/optiland_poc.py`：独立 PoC；
- 本报告；
- 仓库外输出目录 `C:\Users\L2791\thinfilm_outputs\optiland_poc`；
- Optiland 自身的隔离环境 `C:\Users\L2791\Downloads\optiland\.venv`。

需要特别注意：Optiland 可直接给出膜系功率透射率 `T`，但顺序追迹返回的 `rays.i` 是最终 Jones 场强范数。在不同折射率介质之间，它不等于已经完成光学导纳归一化的功率透射率。前端必须分别标注，不能把二者混称为“系统透过率”。

## A. Optiland 项目架构

与本项目有关的主要层次如下：

```text
Optic
├── SurfaceGroup / Surface / geometry / aperture
├── Material / IdealMaterial / dispersion database
├── RealRayTracer -> RealRays / PolarizedRays
├── ThinFilmStack -> ThinFilmCoating -> JonesThinFilm
├── SpotDiagram / RayFan
├── Wavefront / OPD
├── PSF / MTF
├── OpticViewer (Matplotlib 2D)
├── OpticViewer3D (VTK 3D)
└── fileio (Optiland JSON / Zemax / CODE V / OSLO)
```

核心系统对象是 `optiland.optic.Optic`。它组合 `surfaces`、`fields`、`wavelengths`、系统孔径、偏振状态和 `RealRayTracer`。追迹时，`SurfaceGroup.trace()` 逐面调用几何求交、折射/反射、镀膜 Jones 变换，并在每个面保存数值快照。

Optiland 要求 Python 3.11 及以上，并依赖 NumPy、SciPy、Pandas、Numba、Matplotlib 和 VTK。为了不改变 PyThinFilm 现有依赖，本轮使用 Optiland 自己的 `.venv`。正式集成也建议保留可选依赖或进程隔离边界。

## B. 与 PyThinFilm 相关的核心 API

| 功能 | Optiland API | 源码位置 | 可直接调用 | 可获得原始数组 |
| --- | --- | --- | --- | --- |
| 光学系统构建 | `Optic`; `optic.surfaces.add()` | `optiland/optic/optic.py`; `optiland/surfaces/surface_group.py` | 是 | 是，系统/表面可 `to_dict()` |
| Surface | `Surface`; `SurfaceGroup` | `optiland/surfaces/standard_surface.py`; `surface_group.py` | 是 | 是，几何、顶点、逐面记录 |
| 材料 | `Material`; `IdealMaterial`; `BaseMaterial` | `optiland/materials/` | 是 | 是，`n(λ)`、`k(λ)` |
| 色散 | `BaseMaterial.n()` / `k()` | `optiland/materials/base.py` | 是 | 是，标量或数组 |
| 顺序追迹 | `Optic.trace()`; `RealRayTracer.trace()` | `optiland/optic/optic.py`; `optiland/raytrace/real_ray_tracer.py` | 是 | 是，返回 `RealRays`/`PolarizedRays` |
| 逐面坐标 | `optic.surfaces.x/y/z` | `optiland/surfaces/surface_group.py` | 是 | 是，形状约为 `[surface, ray]` |
| 方向余弦 | `optic.surfaces.L/M/N` | `optiland/surfaces/surface_group.py` | 是 | 是 |
| 强度和 OPD | `optic.surfaces.intensity/opd` | `optiland/surfaces/surface_group.py` | 是 | 是 |
| 膜系 | `ThinFilmStack` | `optiland/thin_film/stack.py` | 是 | 是，`r/t/R/T/A` |
| 表面镀膜 | `ThinFilmCoating`; `JonesThinFilm` | `optiland/coatings.py` | 是 | 是，复振幅/Jones 变换 |
| 偏振 | `PolarizationState`; `PolarizedRays` | `optiland/rays/polarization_state.py`; `polarized_rays.py` | 是 | 最终 `p` 与出口场可取 |
| Spot Diagram | `SpotDiagram.data` / `SpotData` | `optiland/analysis/spot_diagram/core.py` | 是 | 是，`x/y/intensity` |
| Ray Fan | `RayFan.data` | `optiland/analysis/ray_fan.py` | 是 | 是，瞳坐标和像面偏差 |
| Wavefront / OPD | `OPD.get_data()`; `generate_opd_map()` | `optiland/wavefront/opd.py` | 是 | 是，散点及插值二维数组 |
| PSF | `FFTPSF.psf` 等 | `optiland/psf/` | 是 | 是，二维数组 |
| MTF | `FFTMTF.mtf`; `freq_tang/freq_sag` | `optiland/mtf/fft.py` | 是 | 是，频率与切向/弧矢值数组 |
| 2D 布局 | `Optic.draw(show=False)` | `optiland/visualization/system/optic_viewer.py` | 是 | 绘图前数据来自逐面快照 |
| 3D 布局 | `OpticViewer3D`; `Rays3D`; `OpticalSystem` | `optiland/visualization/system/` | 是 | 绘图前数据来自同一追迹/表面对象 |
| Zemax 导入 | `load_zemax_file()` | `optiland/fileio/__init__.py` | 是 | 转为 `Optic` 后可取 |
| Zemax 导出 | `save_zemax_file()` | `optiland/fileio/zemax/writer/exporter.py` | 是 | 写出 `.zmx` |

官方示例位置：

- 最小系统、2D、3D：`docs/examples/Tutorial_1a_Optiland_for_Beginners.ipynb`
- 光线追迹与像面坐标：`Tutorial_2a_Tracing_and_Analyzing_Rays.ipynb`
- OPD、PSF、MTF：`Tutorial_2d_OPD_PSF_and_MTF_Calculations.ipynb`
- 镀膜和膜堆：`Tutorial_5a_Coatings_and_Multilayer_Stacks.ipynb`
- 偏振：`Tutorial_5b_Introduction_to_Polarization.ipynb`
- Zemax：`docs/gallery/miscellaneous/zemax_circular_aperture_demo.ipynb` 和 `tests/test_fileio/test_zemax_*.py`

## C. 2D 能力

`Optic.draw()` 使用 Matplotlib，返回 `Figure` 和 `Axes`。传入 `show=False` 后不需要 GUI，可在 CI 或服务进程中直接保存 PNG、SVG 等 Matplotlib 支持的格式。

本轮已实际生成：

- `minimal_system_2d.png`
- `minimal_system_2d.svg`

2D 绘图并不是封闭黑箱。光线折线可以直接从 `SurfaceGroup.x/y/z` 取得，表面顶点可由 `vertices_gcs` 取得，曲率、厚度、孔径和坐标系均在 `Surface`/`geometry` 对象中。因此前端不必嵌入 Matplotlib，可以自行使用 Canvas/SVG/Three.js 绘制。

## D. 3D 能力

3D 使用 VTK。公共 `draw3D()` 默认创建交互窗口并进入 `vtkRenderWindowInteractor.Start()`，因此不适合直接放进无界面 Web 后端。

但底层 `OpticViewer3D.rays` 与 `OpticViewer3D.system` 可以对离屏 `vtkRenderWindow` 绘制。本轮 PoC 已通过 `SetOffScreenRendering(1)` 实际生成 `minimal_system_3d.png`，未启动 GUI 事件循环。

更推荐的正式路线仍是：

```text
Surface.vertices/geometry + SurfaceGroup.x/y/z
                     ↓ JSON
              PyThinFilm Three.js
```

原因是 Three.js 已经属于 PyThinFilm 的前端体系，交互、选层、相机控制和视觉样式都可统一；VTK 只保留为验证或离线图像输出工具。

## E. Thin film / coating 能力

`ThinFilmStack` 支持：

- 层序和厚度（内部波长、厚度单位为 µm，另有 nm/deg 便利接口）；
- `s`、`p`、非偏振；
- 复振幅 `r/t`；
- 功率 `R/T/A`；
- 波长和 AOI 数组；
- 理想材料与材料库色散；
- `ThinFilmCoating` 挂载到系统表面；
- 通过 `JonesThinFilm` 进入偏振光线追迹。

本轮用 PyThinFilm 风格 JSON 字典建立了 `Air/(H/L)^2/BK7`，再转换为 `ThinFilmCoating` 并挂载到单透镜第一面。550 nm、0° 时得到：

| 偏振 | R | T | A |
| --- | ---: | ---: | ---: |
| s | 0.65121184 | 0.34878816 | 约 0 |
| p | 0.65121184 | 0.34878816 | 0 |

这组 `(H/L)^2` 是高反倾向的闭环验证膜系，不是推荐的 AR 设计。下一阶段“增透膜 → 成像系统验证”应改用 PyThinFilm 实际 AR 结果，并做有/无镀膜的同系统对照。

### 功率与追迹强度的口径

同一 PoC 中，`ThinFilmStack` 的功率透射率为 `0.34878816`，而最终 `PolarizedRays.i` 的平均值约为 `0.22948223`。后者主要是 Jones 振幅范数；前者还包含介质光学导纳比。正式适配层应输出不同字段：

```json
{
  "coating_power_T": 0.34878816,
  "exit_ray_field_intensity_mean": 0.22948223
}
```

不得只保留一个含义模糊的 `transmission` 字段。

## F. 系统级分析能力

本轮除 Spot 和 Ray Fan 外，还对 PoC 系统做了小采样探测：

- OPD：成功获得 `32 × 32` 数值图；
- FFT PSF：成功获得 `32 × 32` 数值数组；
- FFT MTF：成功获得频率数组以及每个视场的 tangential/sagittal 数组；
- Spot：91 个有效像面点；
- Ray Fan：每个方向 33 个采样点。

这些分析类在构造时通常立即计算数据，图形只是对已有数组的显示。因此可以采用“Optiland 计算，PyThinFilm 显示”的架构。

需要控制计算规模：PSF/MTF/波前的默认采样明显重于 Spot 和少量光线追迹，正式 API 应显式接收采样参数、超时和缓存键，不应在前端每次拖动时用默认高采样同步重算。

## G. 数据能否传给 Three.js

答案是可以。以下数据可直接变成 JSON：

- 表面顶点：`vertices_gcs -> [[x,y,z], ...]`；
- 表面参数：曲率、厚度、圆锥常数、孔径、坐标变换；
- 光路：`x/y/z -> ray_paths[].points_mm`；
- 方向：`L/M/N -> ray_paths[].directions`；
- 强度、OPD：数值数组；
- Spot、Ray Fan、MTF：一维数组；
- PSF、OPD map：二维数组。

复数不能直接用标准 JSON 表示，应统一编码为：

```json
{"real": 0.12, "imag": -0.03}
```

建议的 Three.js 最小载荷：

```json
{
  "schema_version": "1.0",
  "units": {"length": "mm", "wavelength": "um"},
  "surfaces": [{"index": 1, "vertex": [0, 0, 0], "radius": 40}],
  "ray_paths": [{"ray_index": 0, "points": [[0, 0, -10], [0, 0, 0]]}],
  "image_plane": {"spot_x": [], "spot_y": [], "intensity": []}
}
```

本轮生成的完整 PoC JSON 约 295 KB，91 条光线可直接使用。正式接口需要对大量光线和二维数组支持降采样或二进制传输，避免高采样 PSF 进入普通布局接口。

## H. PyThinFilm → Optiland 数据转换设计

建议定义中立数据合同，不让 PyThinFilm 前端直接依赖 Optiland 类：

```python
class OpticalSystemBackend:
    def load_system(self, system_spec): ...
    def set_material(self, surface_id, material_spec): ...
    def set_coating(self, surface_id, layer_stack_spec): ...
    def trace(self, trace_request): ...
    def get_layout(self, layout_request): ...
    def get_spot(self, analysis_request): ...
    def get_psf(self, analysis_request): ...
    def get_mtf(self, analysis_request): ...
    def get_wavefront(self, analysis_request): ...


class OptilandBackend(OpticalSystemBackend):
    """Optional downstream backend; converts neutral specs to Optiland objects."""


class ZemaxBackend(OpticalSystemBackend):
    """Future placeholder only; not implemented in this phase."""
```

膜系转换规则：

1. PyThinFilm 输出明确的 incident、substrate、层序、厚度和材料色散标识；
2. 适配层把 nm 转为 `ThinFilmCoating` 所需的层厚输入；
3. 材料优先按 PyThinFilm 的实测 `n(λ)+ik(λ)` 建立可验证映射，不能仅按相似名称模糊匹配；
4. `ThinFilmCoating` 绑定到指定 `Surface`；
5. trace/analysis 返回中立 JSON，不把 Optiland Python 对象暴露给前端。

当前 PoC 已实现前 2、4、5 步的最小版本，材料仅使用理想常数折射率，尚未宣称完成真实材料色散映射。

## I. 推荐集成架构

推荐采用可选的进程边界：

```text
PyThinFilm 主进程 / Web API
  ├── 现有 TMM、材料、教学和前端（保持不变）
  └── OpticalSystemBackend client
          ↓ versioned JSON request
      Optiland worker（Python >= 3.11，独立 venv）
          ↓ versioned JSON result
      PyThinFilm charts / Three.js
```

优点：

- 不把 VTK、Numba 等大型依赖强行加入 PyThinFilm 基础安装；
- 避免两个项目的 Python 版本和依赖冲突；
- 可以固定 Optiland commit；
- 未来可增加 ZemaxBackend，而不改变前端合同；
- Optiland 失败或未安装时，PyThinFilm 教学主树仍正常工作。

正式实施前先定义四个版本化对象：`LayerStackSpec`、`OpticalSystemSpec`、`TraceRequest`、`OpticalResult`。本轮不建议直接把 Optiland 包导入 `thinfilm/api.py`。

## J. 当前技术风险

1. **单位风险**：Optiland 系统长度通常为 mm，波长和膜层内部量常用 µm，同时提供 nm 便利函数；PyThinFilm 前端必须随字段传单位。
2. **功率口径风险**：`rays.i` 与经过导纳归一化的膜系功率 `T` 不等价，必须分字段。
3. **逐面 AOI 缺口**：`Surface` 有 `aoi` 缓冲字段，但当前顺序追迹没有写入。可从入射方向和局部法向重建，但不应假装是现成输出。
4. **逐面 Jones 缺口**：`PolarizedRays.p` 给出最终累计变换，当前表面快照没有保存每一面的 Jones 矩阵。
5. **反射分支边界**：顺序模式沿一个既定透射或反射路径传播，不会因一个部分反射膜同时生成两条系统光路。膜系 `R/T` 可算，但鬼像/多路径需另行评估非顺序模式。
6. **材料映射风险**：Optiland 材料库按 name/reference/catalog 查找，PyThinFilm 的材料数据来源和复折射率约定必须逐材料核验。
7. **复数 JSON**：`r/t` 和 Jones 数据必须拆分实部/虚部。
8. **3D headless**：公共 `draw3D()` 是交互式阻塞 API；服务端要使用离屏 VTK，或更直接地只发数值给 Three.js。
9. **计算成本**：PSF/MTF/OPD 的高采样不适合跟随每次 UI 拖动同步执行。
10. **API 演进**：仓库同时保留部分 deprecated facade；适配层应锁定 commit 并优先使用 `surfaces.add`、`fields.add`、`wavelengths.add`、`updater` 等当前接口。
11. **模型责任边界**：PyThinFilm 的 TMM 仍是教学、验证和膜系设计真值入口。Optiland 下游结果必须明确标注引擎和版本，不能静默替换。

## K. 第一版最值得实现的案例

优先案例仍应是“增透膜 → 成像系统验证”：

```text
同一个简单成像镜头
  ├── 无镀膜基线
  └── PyThinFilm 设计的 AR coating
          ↓ Optiland ThinFilmCoating
          ↓ 同视场、同波长、同采样追迹
          ↓ 比较 coating R/T、出口能量口径、Spot、PSF、MTF
```

第一版验收指标建议：

- 设计中心波长与宽带平均 `R/T`；
- s/p 和 AOI 扫描；
- 有/无镀膜的相同 ray path 几何一致性；
- 像面有效光线权重变化；
- Spot 坐标与权重；
- 仅增加一个系统分析：优先 MTF，PSF 作为其数值来源；
- 所有输出包含 engine、commit、单位、材料来源和采样参数。

第二案例再做“1550 nm 高反膜 → 系统级验证”。高反膜更适合验证反射型既定路径；如果目标是同时展示透射和反射两条真实光路，需要先确定使用顺序多配置还是 Optiland 非顺序场景，不能只靠一个顺序 `Optic.trace()`。

## 本轮 PoC 运行记录

运行命令：

```powershell
C:\Users\L2791\Downloads\optiland\.venv\Scripts\python.exe `
  experiments\optiland_poc.py
```

输出：

```text
C:\Users\L2791\thinfilm_outputs\optiland_poc\
├── optiland_poc_result.json
├── minimal_system_2d.png
├── minimal_system_2d.svg
├── minimal_system_3d.png
├── spot_diagram.png
└── lens1_roundtrip.zmx
```

已验证：

- 4 个系统面；
- 91 条逐面光线路径；
- 91 个 Spot 点；
- 33 点 Ray Fan；
- 101 点 s/p 膜系光谱；
- Matplotlib 2D 无 GUI 输出；
- VTK 3D 离屏输出；
- OPD、PSF、MTF 数值数组；
- Zemax `lens1.zmx` 导入、导出、再次导入，前后均为 9 个面。

## 阶段结论

本阶段目标“确定 Optiland 是否适合作为 PyThinFilm 系统级下游，并跑通最小闭环”已经达成。后续优先完成严格的 AR 镀膜前后对照案例，不大规模接入全部分析，也暂不把 backend 接到正式 API。材料映射、功率口径和 AOI/Jones 数据策略仍需在更多真实案例中继续验证。

## 后续阶段状态（原生 AR 对照已完成）

根据当前短期边界，Three.js 迁移和 Zemax 后续工作均已暂缓。仓库新增
`experiments/optiland_ar_comparison.py`，完成裸玻璃 Fresnel 与 PyThinFilm
四分之一波 AR 的原生 Optiland 对照。结果与物理解读见
`docs/OPTILAND_AR_COMPARISON.md`。

该案例验证了：AR 显著改善界面 R/T 和绝对光场能量，但不改变对应光线几何；
归一化 Spot/PSF/MTF 只比较而不设“必须改善”的验收条件。当前不再推进通用
Backend、Three.js 数据合同或 Zemax 集成。
