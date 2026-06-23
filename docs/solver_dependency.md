# 求解器依赖说明

本文档明确说明教学平台各模块的依赖关系，特别是 COMSOL 的角色。

## 核心原则

**教学平台不依赖 COMSOL 作为运行依赖。**

所有核心计算功能均由 Python 自主求解器实现。

## 模块依赖矩阵

| 模块 | TMM | RCWA | COMSOL | Python | 材料数据库 |
|------|-----|------|--------|--------|-----------|
| TMM 核心计算 | ✅ | - | - | ✅ | - |
| 工程应用案例 | ✅ | - | - | ✅ | - |
| 真实材料仿真 | ✅ | - | - | ✅ | ✅ (nk CSV) |
| RCWA 求解器 | - | ✅ | - | ✅ | - |
| 光栅波导分析 | - | ✅ | 可选 | ✅ | - |
| COMSOL CSV 读取 | - | - | 可选 | ✅ | - |

## 详细说明

### 1. TMM 模块（独立求解）

- **文件**: `thinfilm/education.py`
- **依赖**: 仅 Python + NumPy
- **功能**: 传输矩阵法计算多层膜 R/T/A
- **精度**: 精确解析解（非近似）
- **不依赖 COMSOL**: ✅

```python
from thinfilm.education import multilayer_rt_spectrum, LayerSpec

layers = [LayerSpec("MgF2", 1.38, 100.0)]
result = multilayer_rt_spectrum([550.0], layers, n_incident=1.0, n_substrate=1.52)
```

### 2. 工程应用案例（TMM-only）

- **文件**: `examples/applications/`
- **依赖**: 仅 TMM 模块
- **功能**: 5 个完整工程设计案例
- **不依赖 COMSOL**: ✅

```python
from examples.applications import run_solar_cell_ar
result = run_solar_cell_ar()
```

### 3. 真实材料模块

- **文件**: `thinfilm/materials.py`
- **依赖**: Python + nk CSV 文件
- **数据**: `data/real_nk/` 目录下的材料光学常数
- **不依赖 COMSOL**: ✅

```python
from thinfilm import list_real_materials, material_nk_at
materials = list_real_materials()
n, k = material_nk_at("SiO2", 0.55)
```

### 4. RCWA 模块（独立求解器）

- **文件**: `guided_grating/rcwa.py`
- **依赖**: 仅 Python + NumPy
- **功能**: 1D 光栅严格耦合波分析
- **精度**: 有效介质理论近似（亚波长光栅）
- **不依赖 COMSOL**: ✅

```python
from guided_grating.rcwa import GratingLayer, rcwa_1d
grating = GratingLayer(980, 200, 1.45, 3.4, 0.55)
result = rcwa_1d([1550.0], grating, pol="TE")
```

### 5. COMSOL CSV 读取（可选）

- **文件**: `guided_grating/comsol_io.py`, `thinfilm/io.py`
- **依赖**: Python + pandas
- **功能**: 读取 COMSOL 导出的 CSV 数据
- **用途**: 导入外部参考数据，非必需

```python
from guided_grating.comsol_io import load_comsol_grating_csv
result = load_comsol_grating_csv("path/to/comsol_export.csv")
```

## COMSOL 的角色

COMSOL 仅作为：

1. **高级验证源** — 论文发表时交叉验证
2. **外部参考数据** — 导入已有的 COMSOL 导出文件
3. **非必需的高级功能** — 教学演示不需要

COMSOL **不是**：

- ❌ 教学平台的运行依赖
- ❌ TMM 计算的必需组件
- ❌ 工程应用案例的必需组件
- ❌ RCWA 求解器的必需组件

## 安装要求

### 最小安装（教学平台）

```bash
pip install numpy pandas matplotlib
```

### 完整安装（含 Plotly 交互图表）

```bash
pip install numpy pandas matplotlib plotly
```

### 不需要安装

- ❌ COMSOL Multiphysics
- ❌ COMSOL LiveLink
- ❌ 任何 COMSOL 相关组件
