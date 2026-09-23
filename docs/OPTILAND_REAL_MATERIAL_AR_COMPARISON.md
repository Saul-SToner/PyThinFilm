# PyThinFilm 真实材料 AR 的 Optiland 原生验证

## 结论

真实材料链路已经跑通。PyThinFilm 的 `MgF2_Dodge_o.csv` 与
`N-BK7_Schott.csv` 通过一个只读材料适配器直接提供给 Optiland，膜系
R/T/A 在 400–700 nm 范围内与 PyThinFilm TMM 的最大差异为
`9.99e-16`。这说明当前适配没有引入第二份材料数据或近似色散公式。

本实验仍保持 Optiland 原生工作方式：

- 2D 使用 Matplotlib；
- 3D 使用 VTK 离屏渲染；
- Spot、PSF、MTF 使用 Optiland 原生分析；
- 不引入 Three.js；
- 不处理 Zemax 导入导出。

实验脚本：`experiments/optiland_real_material_ar_comparison.py`。

## 物理模型

比较对象为同一片 N-BK7 单透镜，唯一变量是前表面：

- 基线：Air/N-BK7 裸界面；
- 镀膜：Air/MgF2/N-BK7 单层四分之一波减反膜。

设计波长为 550 nm。PyThinFilm 真实材料库给出的设计点参数为：

| 参数 | 数值 |
| --- | ---: |
| N-BK7 折射率 | 1.51852200 |
| MgF2 折射率 | 1.37850571 |
| 零反射所需理想折射率 | 1.23228325 |
| MgF2 与理想值的差 | 0.14622246 |
| MgF2 物理厚度 | 99.74568767 nm |

因此真实 MgF2 并不满足 `n_layer = sqrt(n_air * n_substrate)`。四分之一波
厚度仍能降低反射，但不会像理想材料基线那样在 550 nm 达到数值零反射。

材料来源：

- MgF2：Dodge 1984 ordinary ray，数据有效范围 200–7000 nm；
- N-BK7：Schott 2015 catalog，数据有效范围 300–2500 nm。

本实验仅计算两者共同有效区间内的 400–700 nm，没有外推或截断。

## 主要结果

550 nm、法向入射：

| 指标 | 裸 N-BK7 | MgF2 AR |
| --- | ---: | ---: |
| 前表面 R | 4.2387995% | 1.2468791% |
| 前表面 T | 95.7612005% | 98.7531209% |
| 平均出口光线权重 | 0.91700819 | 0.94566080 |
| 相对积分 PSF 能量 | `1.11180e7` | `1.14653e7` |

设计波长处的前表面反射相对降低约 **70.58%**。对应光线坐标和方向余弦
的最大差均为零；峰值归一化 PSF 的最大差约 `2.93e-4`，归一化 MTF
最大差约 `1.21e-4`。结果再次表明减反膜首先改善系统能量，而不是改变
透镜几何光路或归一化成像形状。

## 数值验收

脚本自动通过以下检查：

- `R + T + A` 最大能量守恒误差 `1.11e-16`；
- PyThinFilm 与 Optiland 最大 R/T/A 差异 `9.99e-16`；
- AR 的中心反射低于裸界面，透射高于裸界面；
- 真实 MgF2 结果不被误判为理想零反射；
- 两系统对应光线的几何位置和方向一致；
- Spot、PSF、MTF 均为有限数值；
- 两套 Optiland 原生 2D 与 3D 图均成功输出。

## 运行

```powershell
C:\Users\L2791\Downloads\optiland\.venv\Scripts\python.exe `
  experiments\optiland_real_material_ar_comparison.py
```

默认输出目录：

```text
C:\Users\L2791\thinfilm_outputs\optiland_real_material_ar_comparison\
├── comparison_result.json
├── material_dispersion.png
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

`comparison_result.json` 保存完整光谱、角度扫描、逐面光线、Spot、PSF、MTF、
材料来源、指标与验收结果，可作为后续工作区界面接入前的可追溯基准。

## 当前架构判断

真实材料验证进一步支持以下分工：

```text
PyThinFilm
  材料库 + 膜系设计 + TMM 主结果
             ↓ 相同 n(λ), k(λ) 与层厚
Optiland
  曲面系统 + 镀膜表面 + 光线追迹 + Spot/PSF/MTF
```

不需要用 Optiland 材料库替换 PyThinFilm 材料库，也不需要改写现有 TMM。
当前实验已经改用 `thinfilm/optiland_integration.py` 中的稳定可选集成层和最小
系统输入模型，详见 `docs/OPTILAND_OPTIONAL_INTEGRATION.md`。下一阶段可在此边界
上增加系统级结果导出接口；在此之前不必扩大到 Three.js 或 Zemax。
