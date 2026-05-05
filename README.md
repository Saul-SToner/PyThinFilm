# 薄膜光学 Python 平台

本仓库当前服务于三条并行工作线：

1. 反演主线  
   从 COMSOL 或实验导出的光谱中，反推单层薄膜厚度与相关参数。
2. 教学仿真主树  
   用 Python 复现设计报告中的平面多层膜正向仿真，并为 APP 提供稳定后端。
3. 光栅波导研究支线  
   从异构薄膜扩展到周期光栅、波导共振与窄线宽反射镜设计。

## 1. 当前边界

当前统一约定：

```text
教学平台只展示教学主树
不暴露厚度反演入口
反演代码继续保留在仓库中
```

这意味着：

- 教学平台面向“正向仿真、演示、导出、APP 对接”
- 反演代码用于研究模式、内部验证和后续扩展
- 光栅波导支线目前属于研究模块，不直接进入教学首页

## 2. 目录概览

```text
thinfilm_core.py             早期集中式脚本，仍保留反演相关旧入口
thinfilm/                    当前推荐使用的教学主树与反演函数包
guided_grating/              光栅波导研究支线
run_teaching_demo.py         教学主树命令行入口
run_guided_grating_demo.py   光栅波导支线命令行入口
archive/inversion_examples/  归档后的反演样本
data/                        主路径说明目录，不再存放反演样本
```

`thinfilm/` 当前重点模块：

```text
thinfilm/api.py
thinfilm/education.py
thinfilm/sweep.py
thinfilm/joint.py
thinfilm/validation.py
thinfilm/uncertainty.py
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

### 3.3 常用 API

```python
from thinfilm import (
    list_teaching_cases,
    simulate_teaching_case,
    export_teaching_case_outputs,
    export_teaching_comparison_figures,
    export_teaching_main_branch_catalog,
    export_teaching_report_bundle,
)
```

### 3.4 当前可导出的内容

当前已具备：

1. 单案例导出
2. 第 2 章整套案例导出
3. 多曲线对比图导出
4. 主树总包导出
5. 主树目录配置导出
6. 首页卡片、分区卡片、对比图卡片统一 JSON 结构
7. 参数面板自动渲染所需表单配置
8. 单案例分析图 `analysis_png`
9. 对比图分析图 `analysis_png`

单案例典型输出：

```text
teaching_case_*_spectrum.csv
teaching_case_*_summary.json
teaching_case_*_summary.txt
teaching_case_*_RTA.png
teaching_case_*_main.png
teaching_case_*_analysis.png
```

对比图典型输出：

```text
teaching_compare_*.csv
teaching_compare_*.png
teaching_compare_*_analysis.png
```

### 3.5 前端对接约定

优先对接：

```text
thinfilm/api.py
thinfilm/education.py
C:\Users\L2791\thinfilm_outputs\teaching_main_branch_catalog.json
```

`teaching_main_branch_catalog.json` 当前已包含：

- `home_cards`
- `home_summary`
- `sections`
- `comparisons`
- `comparison_groups`
- `case_controls`
- `case_form_groups`
- `form_ui_meta`
- `default_files`
- `platform_scope`

其中平台边界已写入：

```text
show_thickness_inversion = false
show_research_branches = false
```

前端不要硬编码案例名、参数名、图路径。

## 4. 反演主线

### 4.1 模型定位

当前反演不是神经网络，而是物理模型反演：

1. 使用单层薄膜 Fresnel 反射模型
2. 输入两个入射角下的反射率曲线
3. 联合搜索厚度 `d`
4. 可选修正第二角 `theta2`

### 4.2 当前最稳工程路线

```text
10° + 80°
s 偏振
双角联合反演厚度
```

推荐配置：

```python
RUN_MODE = "fit_csv_with_theta2_search"
THETA1 = 10.0
THETA2 = 80.0
POL = "s"
```

推荐输入：

```python
CSV_FILE_ANGLE1 = Path(r"...10deg_s.csv")
CSV_FILE_ANGLE2 = Path(r"...80deg_s.csv")
```

### 4.3 常用 API

```python
from thinfilm import fit_two_angle, fit_current_main_case

result = fit_current_main_case(save_plots=False)
```

### 4.4 数据与样本位置

反演样本已从主路径移出，当前归档在：

```text
archive/inversion_examples/deg.s
archive/inversion_examples/deg.p
archive/inversion_examples/deg.avg
```

教学平台主路径 `data/` 只保留说明，不再混放反演样本。

### 4.5 当前建议

当前不建议把 COMSOL 直接导出的 `mixed` 或 `avg(0.6p)` 作为主拟合输入。更稳的方式是：

```text
分别导出纯 s 和纯 p
在 Python 后处理中按比例线性合成
```

混合模型：

```text
R_mix = eta * R_p + (1 - eta) * R_s
```

## 5. 光栅波导研究支线

### 5.1 路线定位

该支线用于承接：

```text
异构薄膜
-> 周期光栅
-> 波导共振
-> 窄线宽反射镜设计
```

当前状态：

1. 已建立独立包结构
2. 已定义最小参数模型
3. 已接入 COMSOL 单谱与联合扫描 CSV
4. 已支持自动筛选最接近目标波长的参数点
5. 已支持误差分析图导出

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

### 5.3 当前分析能力

当前联合扫描模式会自动：

1. 按第二参数分组
2. 提取各组峰位、峰值反射率、FWHM
3. 按目标波长误差排序
4. 给出最佳候选参数
5. 导出最佳曲线图与误差分析图

### 5.4 当前阶段性设计点

截至当前，已锁定一个可工作的无损近似设计点：

```text
period = 980 nm
t_wg = 220 nm
fill_factor = 0.55
peak_wavelength ≈ 1550.0 nm
R_peak ≈ 0.99999985
FWHM ≈ 9.6 nm
```

这说明：

- `period` 是强主控参数
- `t_wg` 会稳定推动峰位沿波长漂移
- `fill_factor` 可进一步微调峰位与线宽

### 5.5 当前保留项

当前结果基于无损或近似无损条件获得，后续仍可继续补：

1. 吸收与损耗影响
2. `t_grating` 的系统影响
3. 模态机理解释
4. 工艺容差分析

## 6. 实验验证、对照与误差分析

这一部分是后续竞赛文档和验收阶段必须补强的重点，建议按下面方式组织。

### 6.1 至少保留三组对照对象

建议至少做以下三类：

1. 单层减反膜
2. F-P 滤光片
3. 高反膜

每一类都尽量给出三条曲线：

```text
理论曲线
COMSOL 曲线
实验曲线（若暂时没有，可先用 COMSOL 对照占位）
```

### 6.2 当前平台已支持的展示方式

现在曲线展示可以直接带分析信息：

- 主曲线图 `main.png`
- 总览图 `RTA.png`
- 分析图 `analysis.png`
- 光栅扫描误差图 `error_analysis.png`

适合直接展示：

- 峰位与目标波长偏差
- 峰值反射率
- 近似 FWHM
- `R / T / A @ lambda0`

### 6.3 建议补写的性能指标

对于反演主线，建议明确写出：

1. 厚度反演误差
2. 入射角误差影响
3. 谱仪分辨率影响
4. 噪声敏感性
5. 反演稳定区间

对于教学主树与光栅支线，建议明确写出：

1. 中心波长偏差
2. 峰值反射率或透射率
3. FWHM
4. 参数变化灵敏度
5. 模型与 COMSOL / 实验的均方误差或最大误差

### 6.4 建议补写的系统误差来源

建议在文档中单列说明：

1. 材料折射率设置误差
2. 入射角设置误差
3. COMSOL 网格与求解器收敛误差
4. 采样步长与光谱分辨率误差
5. 曲线读取、归一化与噪声引入误差

### 6.5 当前已新增的后端工具

现在仓库里已经新增两类后端工具：

1. `thinfilm/validation.py`  
   用于生成“理论曲线 vs COMSOL/实验曲线”的对比结果、误差指标和分析图。
2. `thinfilm/uncertainty.py`  
   用于生成厚度反演对角度偏差、噪声和分辨率变化的敏感性分析。

可直接从包入口导入：

```python
from thinfilm import (
    compare_teaching_case_to_reference,
    export_teaching_validation_result,
    run_inversion_uncertainty_analysis,
    export_inversion_uncertainty_analysis,
)
```

## 7. 输出目录

所有默认输出写入：

```text
C:\Users\L2791\thinfilm_outputs
```

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
teaching_report_case_index.csv
teaching_report_bundle_manifest.json
teaching_report_bundle_manifest.txt
guided_grating_*_summary.json
guided_grating_*_summary.txt
guided_grating_*_main.png
guided_grating_*_RTA.png
guided_grating_*_error_analysis.png
guided_grating_*_period_summary.csv
```

## 8. 协作说明

### 8.1 给前端 / APP 同学

优先接教学主树，不接厚度反演入口。

推荐使用：

```text
thinfilm/api.py
C:\Users\L2791\thinfilm_outputs\teaching_main_branch_catalog.json
```

### 8.2 给算法 / 建模同学

若继续反演主线，优先保持：

```text
10° + 80°
s 偏振
双角反演
```

### 8.3 给光栅波导支线同学

当前建议推进顺序：

1. 先锁 `period`
2. 再看 `t_wg`
3. 再看 `fill_factor`
4. 最后补吸收与损耗影响

## 9. 已知限制

1. 反演主线目前仍以单层膜模型为主
2. 尚未系统加入粗糙度、过渡层、多层反演
3. 教学主树是 Python 正向等价实现，不是 COMSOL 场分布逐点复刻
4. `thinfilm_core.py` 中仍保留部分旧入口
5. 光栅支线当前仍保留占位求解器，仅用于工程骨架，不作为正式物理论证依据
6. 光栅支线的吸收、损耗和容差影响尚未系统展开
7. 实验对照、系统误差和不确定度分析仍需继续补齐
8. PowerShell 里若中文显示乱码，通常是终端编码问题，不代表文件损坏

## 10. 环境依赖

安装依赖：

```powershell
pip install -r requirements.txt
```

当前依赖见：

```text
requirements.txt
```

缓存与输出忽略规则见：

```text
.gitignore
```
