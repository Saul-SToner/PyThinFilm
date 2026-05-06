# 薄膜光学 Python 平台

当前仓库聚焦两条工作线：

1. 教学仿真主树  
   用 Python 复现设计报告中的平面多层膜正向仿真，并为展示或 APP 提供后端。
2. 光栅波导研究支线  
   从异构薄膜扩展到周期光栅、波导共振与窄线宽反射镜设计。

原有反演主线和样本数据已从仓库主工作流中移出，不再作为当前仓库内的主要维护对象。

## 1. 当前边界

当前统一约定：

```text
教学平台只展示教学主树
不暴露厚度反演入口
仓库内不再保留反演样本 CSV
```

这意味着：

- 教学平台面向“正向仿真、演示、导出、验证”
- 光栅波导支线继续作为研究模块保留
- 旧反演样本已备份到本机仓库外目录，不再留在项目目录中

## 2. 目录概览

```text
thinfilm/                    教学主树、通用 CSV 读取、验证模块
guided_grating/              光栅波导研究支线
run_teaching_demo.py         教学主树命令行入口
run_guided_grating_demo.py   光栅波导支线命令行入口
data/                        主路径说明目录
```

`thinfilm/` 当前重点模块：

```text
thinfilm/api.py
thinfilm/education.py
thinfilm/io.py
thinfilm/validation.py
thinfilm/paths.py
```

`guided_grating/` 当前重点模块：

```text
guided_grating/comsol_io.py
guided_grating/models.py
guided_grating/spectra.py
guided_grating/export.py
guided_grating/examples.py
```

## 3. 教学仿真主树

### 3.1 目标

教学主树用于复现设计报告中的平面多层膜正向仿真，当前覆盖：

1. 单层减反射膜
2. 双层减反射膜
3. 三层减反射膜
4. 高反射膜
5. 单半波型 F-P 滤光片
6. 双半波型 F-P 滤光片
7. 中性分束膜

底层方法为传输矩阵法 / 特征矩阵法，不依赖 COMSOL 即可快速生成 `R / T / A` 曲线。

### 3.1.1 ??????

????????????????????????

1. `quarter_wave_single_layer`?1/4?????
2. `half_wave_single_layer`?1/2?????
3. `quarter_wave_double_layer`?1/4??????
4. `quarter_wave_stack`?1/4?? QW ??
5. `bragg_reflector`???????
6. `fp_filter`??? F-P ???
7. `narrowband_filter`??????
8. `rugate_filter`??????

??????????

- `quarter_wave_stack_periods`
- `narrowband_filter_periods`

### 3.2 命令行入口

列出案例：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_teaching_demo.py --list
```

导出单个案例：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_teaching_demo.py --case single_ar
```

导出对比图：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_teaching_demo.py --compare
```

导出目录配置：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_teaching_demo.py --catalog
```

导出完整主树报告包：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_teaching_demo.py --report
```

### 3.3 当前可导出的内容

当前已具备：

1. 单案例导出
2. 第 2 章整套案例导出
3. 多曲线对比图导出
4. 主树总包导出
5. 主树目录配置导出
6. 参数面板自动渲染所需 JSON 配置
7. 单案例分析图 `analysis_png`
8. 对比图分析图 `analysis_png`

常见输出包括：

```text
teaching_case_*_spectrum.csv
teaching_case_*_summary.json
teaching_case_*_summary.txt
teaching_case_*_RTA.png
teaching_case_*_main.png
teaching_case_*_analysis.png
teaching_compare_*.csv
teaching_compare_*.png
teaching_compare_*_analysis.png
teaching_main_branch_catalog.json
```

### 3.4 ????????

### 3.4.1 ???????????

??????

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .un_teaching_expansion_validation.py --template-out --prefix teaching_expansion_validation_cli
```

????? `reference_csv` ???????????

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .un_teaching_expansion_validation.py --template-file "C:\path	oilled_template.json" --prefix teaching_expansion_validation_run
```

???? `.json` ? `.csv` ?????


??????????????? COMSOL ?????????????????????????????

??????

```python
from thinfilm import (
    build_teaching_expansion_validation_templates,
    export_teaching_expansion_validation_template_bundle,
)
```

???????????????

- ????? `R / T`
- ?? CSV ??????? `R (1)` ? `T (1)`
- ?????????
- ???? COMSOL / ??????????

?????

- `quarter_wave_single_layer`
- `half_wave_single_layer`
- `quarter_wave_double_layer`
- `quarter_wave_stack`
- `bragg_reflector`
- `fp_filter`
- `narrowband_filter`
- `rugate_filter`

????????

```python
from thinfilm import export_teaching_expansion_validation_template_bundle

files = export_teaching_expansion_validation_template_bundle(
    prefix="teaching_expansion_validation_templates_v1"
)
print(files)
```

## 4. 理论-参考曲线验证

当前仓库已保留验证模块，用于把理论曲线与 COMSOL / 实验曲线做直接对照。

可直接导入：

```python
from thinfilm import (
    compare_teaching_case_to_reference,
    export_teaching_validation_result,
    run_teaching_validation_suite,
    export_teaching_validation_suite_summary,
)
```

适合当前优先做的三类验证对象：

1. 单层减反膜
2. F-P 滤光片
3. 高反膜

输出重点：

- 理论曲线
- 参考曲线
- 误差曲线
- `MAE / RMSE / 最大绝对误差 / lambda0 处误差`

## 5. 光栅波导研究支线

### 5.1 路线定位

该支线用于承接：

```text
异构薄膜
-> 周期光栅
-> 波导共振
-> 窄线宽反射镜设计
```

### 5.2 命令行入口

运行最小占位示例：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_guided_grating_demo.py
```

读取 COMSOL 单条光谱：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_guided_grating_demo.py --csv "C:\path\to\Grant.csv"
```

读取 `lambda + period` 联合扫描：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_guided_grating_demo.py --sweep-csv "C:\path\to\2d.csv" --target-wavelength 1550
```

读取 `lambda + t_wg` 联合扫描：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_guided_grating_demo.py --sweep-csv "C:\path\to\7new.csv" --sweep-name t_wg --target-wavelength 1550
```

读取 `lambda + fill_factor` 联合扫描：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_guided_grating_demo.py --sweep-csv "C:\path\to\8new.csv" --sweep-name fill_factor --target-wavelength 1550
```

### 5.3 当前阶段性设计点

截至当前，已锁定一个可工作的无损近似设计点：

```text
period = 980 nm
t_wg = 220 nm
fill_factor = 0.55
peak_wavelength ≈ 1550.0 nm
R_peak ≈ 0.99999985
FWHM ≈ 9.6 nm
```

后续仍建议继续补：

1. 吸收与损耗影响
2. `t_grating` 的系统影响
3. 模态机理解释
4. 工艺容差分析

## 6. 输出目录

所有默认输出写入：

```text
C:\Users\L2791\thinfilm_outputs
```

光栅支线常见输出包括：

```text
guided_grating_*_summary.json
guided_grating_*_summary.txt
guided_grating_*_main.png
guided_grating_*_RTA.png
guided_grating_*_error_analysis.png
guided_grating_*_period_summary.csv
```

## 7. 已移出的反演样本

仓库内原反演样本 CSV 已备份到本机目录：

```text
C:\Users\L2791\thinfilm_backups\inversion_examples_20260505
```

项目目录内不再保留这批反演样本。

## 8. 环境依赖

安装依赖：

```powershell
pip install -r requirements.txt
```

缓存与输出忽略规则见：

```text
.gitignore
```

## 9. 一键生成验证与性能总包

如果已经准备好三类 COMSOL CSV：

1. 单层减反膜
2. F-P 滤光片
3. 高反膜

可以直接运行：

```powershell
C:/Users/L2791/AppData/Local/Programs/Python/Python313/python.exe .\run_teaching_metrics_bundle.py `
  --single-ar-csv "C:\Users\L2791\OneDrive\Desktop\deg.p\AR_MgF2_BK7G18_550nm_theta0.csv" `
  --fp-csv "C:\Users\L2791\OneDrive\Desktop\deg.p\FP_HL4_C_LH4_air_air_550nm_theta0_comsol.csv" `
  --high-reflector-csv "C:\Users\L2791\OneDrive\Desktop\deg.p\highreflect.csv" `
  --prefix teaching_pipeline_v1
```

该脚本会自动生成：

- 理论 vs COMSOL 验证总包
- 分辨率与噪声敏感性结果
- 系统误差结果
- 分层厚度敏感性结果
- 精细厚度容差结果
- 精细角度容差结果
- 综合性能总表
- 竞赛口径中文总结

如果希望在 Python 中直接调用，也可以使用：

```python
from pathlib import Path
from thinfilm import export_final_delivery_bundle

result = export_final_delivery_bundle(
    single_ar_csv=Path(r"C:\Users\L2791\OneDrive\Desktop\deg.p\AR_MgF2_BK7G18_550nm_theta0.csv"),
    fp_single_csv=Path(r"C:\Users\L2791\OneDrive\Desktop\deg.p\FP_HL4_C_LH4_air_air_550nm_theta0_comsol.csv"),
    high_reflector_csv=Path(r"C:\Users\L2791\OneDrive\Desktop\deg.p\highreflect.csv"),
    prefix="teaching_final_delivery_v1",
    reference_label="COMSOL",
)
```
