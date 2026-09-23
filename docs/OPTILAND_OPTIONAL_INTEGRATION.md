# PyThinFilm → Optiland 可选集成层

## 定位

`thinfilm/optiland_integration.py` 是 PyThinFilm 的可选系统光学桥接层。它不改变
现有 TMM、材料选择或教学案例接口，也不把 Optiland 加入 PyThinFilm 的强制依赖。

职责边界如下：

```text
PyThinFilm                         Optiland
材料 n(λ), k(λ) ────────────────→ 色散材料对象
膜层材料与厚度 ─────────────────→ ThinFilmCoating
带单位的顺序系统输入 ───────────→ Optic
                                    ↓
                              光线 / Spot / PSF / MTF
```

## 公共输入模型

- `CoatingLayerInput`：材料 ID、物理厚度 `thickness_nm`、显示标签；
- `CoatingStackInput`：入射介质、衬底介质和膜层；
- `SequentialSurfaceInput`：曲率半径、面后间隔、面后材料、光阑和镀膜；
- `SequentialSystemInput`：表面序列、波长、主波长、孔径和视场；
- `OptilandBridge`：惰性加载 Optiland 并完成对象转换。

单位固定为：

| 字段 | 单位 |
| --- | --- |
| `wavelengths_um` | μm |
| `radius_mm`、`thickness_mm`、`aperture_epd_mm` | mm |
| `CoatingLayerInput.thickness_nm` | nm |

平面使用 `radius_mm=None`；无限物距使用标准 JSON 字符串
`thickness_mm="infinity"`，避免输出非标准数值 `Infinity`。

## 自动检查

构建 Optiland 系统前会检查：

- 膜层厚度有限且大于零；
- 波长、孔径和表面参数有效；
- 镀膜入射介质等于上一面的面后介质；
- 镀膜衬底介质等于当前面的面后介质；
- 所有系统波长均落在每种 PyThinFilm 材料的数据范围内；
- 指定的 Optiland 源码目录真实存在；
- 同一进程没有混用不同 Optiland 运行时。

材料名称在输入阶段通过 PyThinFilm 别名表规范化，例如 `bk7` 会转为
`N-BK7`。Optiland 中的材料对象按规范化 ID 缓存，但 n/k 数值始终由
`thinfilm.materials.material_complex_index()` 提供。

## 最小示例

```python
from thinfilm import (
    CoatingLayerInput,
    CoatingStackInput,
    OptilandBridge,
    make_singlet_system_input,
)

front = CoatingStackInput(
    incident_material_id="Air",
    substrate_material_id="N-BK7",
    layers=(
        CoatingLayerInput("MgF2", thickness_nm=99.74568767),
    ),
)

system_input = make_singlet_system_input(
    name="MgF2 AR singlet",
    glass_material_id="N-BK7",
    front_coating=front,
    wavelength_um=0.55,
)

bridge = OptilandBridge(r"C:\Users\L2791\Downloads\optiland")
optic = bridge.build_system(system_input)
rays = optic.trace(Hx=0.0, Hy=0.0, wavelength=0.55)
```

若 Optiland 已安装到当前环境，`OptilandBridge()` 可以不传源码目录。可先调用：

```python
from thinfilm import optiland_runtime_status

print(optiland_runtime_status(r"C:\Users\L2791\Downloads\optiland"))
```

## 已完成验证

真实 MgF2/N-BK7 实验已经改用该集成层：

```powershell
C:\Users\L2791\Downloads\optiland\.venv\Scripts\python.exe `
  experiments\optiland_real_material_ar_comparison.py
```

实验仍满足：

- PyThinFilm 与 Optiland R/T/A 最大差异 `9.99e-16`；
- 能量守恒最大误差 `1.11e-16`；
- Optiland 原生 2D、3D、Spot、PSF 和 MTF 均能生成。

这说明代码已从单次实验内的临时材料类，迁移为可复用、可校验且不污染默认依赖
的可选集成层。
