# PyThinFilm AR 镀膜的 Optiland 原生系统级验证

## 案例定位

本案例是 PyThinFilm 与 Optiland 的第一个系统级联合实验。当前阶段保持 Optiland 原生状态：

- 2D 使用 Matplotlib；
- 3D 使用 VTK 离屏渲染；
- Spot、PSF、MTF 使用 Optiland 原生分析；
- 不迁移 Three.js；
- 不继续 Zemax 导入导出工作；
- 不定义通用 Backend 或前端 JSON Contract。

实验脚本：`experiments/optiland_ar_comparison.py`。

## 实验结构

两套系统采用完全相同的镜片曲率、厚度、材料、孔径、视场、波长和采样：

```text
Object -> front surface -> singlet -> rear Fresnel surface -> Image Plane
```

唯一变量是镜片前表面：

- 基线：Air → Glass 的空膜堆，即裸玻璃 Fresnel 界面；
- AR：Air → PyThinFilm 单层四分之一波 AR → Glass。

后表面在两套系统中均使用相同的 Glass → Air Fresnel 界面，避免把“无镀膜”错误处理为 `R=0, T=1`。

## PyThinFilm 设计

设计由 `thinfilm.education.build_single_ar_layers()` 生成：

| 参数 | 数值 |
| --- | ---: |
| 设计波长 | 550 nm |
| 入射介质 | n = 1.0 |
| 玻璃 | n = 1.52 |
| 理想 AR 折射率 | n = 1.2328828006 |
| AR 物理厚度 | 111.5272270 nm |

折射率满足 `n_AR = sqrt(n_air * n_glass)`，厚度满足四分之一波光学厚度。

## 运行

```powershell
C:\Users\L2791\Downloads\optiland\.venv\Scripts\python.exe `
  experiments\optiland_ar_comparison.py
```

默认输出到：

```text
C:\Users\L2791\thinfilm_outputs\optiland_ar_comparison\
├── comparison_result.json
├── coating_spectrum.png
├── coating_aoi_scan.png
├── layout_uncoated.png
├── layout_coated.png
├── system3d_uncoated.png
├── system3d_coated.png
├── spot_comparison.png
├── psf_normalized_comparison.png
├── psf_absolute_comparison.png
└── mtf_comparison.png
```

## 主要结果

### 1. 膜系响应

550 nm、法向入射：

| 指标 | 裸玻璃 | AR |
| --- | ---: | ---: |
| 前表面 R | 0.0425799950 | 约 `1.45e-32` |
| 前表面 T | 0.9574200050 | 1.0000000000 |

AR 将设计波长处的理想单界面反射降至数值零。该结论只针对当前理想、无吸收、精确折射率匹配模型，不代表真实制造一定达到零反射。

### 2. 交叉计算一致性

PyThinFilm TMM 和 Optiland `ThinFilmStack` 在裸界面与 AR 膜层的 s/p、R/T/A 光谱上最大差异：

```text
9.99e-16
```

能量守恒最大误差：

```text
1.11e-16
```

### 3. 光线几何

对应光线的最大坐标差和方向余弦差均为零：

```text
max Δposition = 0.0 mm
max Δdirection = 0.0
```

这说明 AR 镀膜没有改变由镜片曲率和折射率决定的几何光路。

### 4. 能量

包含相同后表面 Fresnel 损耗后的平均出口光线权重：

| 系统 | 平均出口权重 |
| --- | ---: |
| 裸玻璃 | 0.91664043 |
| AR | 0.95741000 |

相对绝对能量 PSF 的积分值由约 `1.11135e7` 增加至 `1.16078e7`。该值是相同采样、相同 FFT 约定下的相对单位，可用于两系统比较，不应标为绝对瓦特。

### 5. Spot、PSF 与 MTF

- Spot 坐标保持一致，颜色权重发生变化；
- 峰值归一化 PSF 的最大形状差约 `1.69e-4`；
- 归一化 MTF 的最大差约 `1.49e-4`；
- AR 的主要收益体现在反射损耗和绝对能量，而不是几何像差或归一化分辨率显著改善。

因此，“MTF 几乎重合”是当前物理设置下的合理结果，不是计算失败。

## 自动验收

脚本在写出结果后检查：

- `R + T + A` 能量守恒；
- PyThinFilm 与 Optiland TMM 一致；
- `R_AR < R_bare`；
- `T_AR > T_bare`；
- 对应光线坐标和方向一致；
- Spot、PSF、MTF 数组有限；
- 两套 2D 原生图存在；
- 两套 3D 原生图存在。

任一检查失败时脚本以非零状态退出。

## 教学结论

> AR 镀膜基本不改变由镜片几何和折射决定的光线路径及几何像差，但显著降低界面反射损耗、提高出射光场能量。只有当镀膜响应随入射角、偏振和瞳面位置产生明显不均匀加权时，归一化 PSF 与 MTF 才会进一步出现可见变化。

## 当前边界

本案例使用理想常数折射率材料，目的是建立清晰、可复验的系统级物理基线。
真实材料扩展已经完成，见 `docs/OPTILAND_REAL_MATERIAL_AR_COMPARISON.md` 和
`experiments/optiland_real_material_ar_comparison.py`。该扩展直接使用 PyThinFilm
的 MgF2/N-BK7 `n(λ), k(λ)` 数据，并保留相同对照和验收口径；当前阶段仍不进入
Three.js 或 Zemax 工作。
