# 光栅波导研究支线

本目录用于承接如下研究路线：

```text
异构薄膜
-> 周期光栅
-> 波导共振
-> 窄线宽反射镜设计
```

当前目标不是立刻完成完整 RCWA / FEM 求解器，而是先把：

1. 参数结构
2. COMSOL 数据接入口
3. 谱线摘要
4. 图形导出
5. 参数筛选流程

稳定下来。

## 1. 当前模块

```text
guided_grating/models.py
guided_grating/comsol_io.py
guided_grating/solver.py
guided_grating/spectra.py
guided_grating/export.py
guided_grating/examples.py
```

## 2. 当前支持能力

目前支线已经具备三类入口：

1. 占位最小示例
2. COMSOL 单条光谱 CSV 读取
3. COMSOL 波长 + 第二参数联合扫描读取

联合扫描的第二参数当前可直接处理：

- `period`
- `t_wg`
- `fill_factor`

只要 CSV 第二列是某个扫描参数，并在命令行里通过 `--sweep-name` 指定即可。

## 3. 命令行入口

运行最小示例：

```bash
python run_guided_grating_demo.py
```

读取 COMSOL 单条光谱：

```bash
python run_guided_grating_demo.py --csv "path/to/Grant.csv"
```

读取 `lambda + period` 联合扫描：

```bash
python run_guided_grating_demo.py --sweep-csv "path/to/2d.csv" --target-wavelength 1550
```

读取 `lambda + t_wg` 联合扫描：

```bash
python run_guided_grating_demo.py --sweep-csv "path/to/7new.csv" --sweep-name t_wg --target-wavelength 1550
```

读取 `lambda + fill_factor` 联合扫描：

```bash
python run_guided_grating_demo.py --sweep-csv "path/to/8new.csv" --sweep-name fill_factor --target-wavelength 1550
```

## 4. 当前数据读取规则

### 4.1 单条光谱表

典型列结构：

```text
lambda0 (m)
总反射率
总透射率
吸收率
总反射率和透射率
```

即使 COMSOL 导出的是“数值 + 相位”字符串，也会自动提取前面的数值部分。

### 4.2 联合扫描表

典型列结构：

```text
lambda0 (m)
second_param (m 或无量纲)
总反射率
总透射率
吸收率
总反射率和透射率
```

读取后会自动：

1. 按第二参数分组
2. 逐组提取峰位、峰值反射率、FWHM
3. 计算目标波长误差
4. 排序并给出最佳候选

## 5. 当前导出内容

默认输出目录由 `THINFILM_OUTPUT_DIR` 控制；未设置时写入用户主目录下的 `thinfilm_outputs/`：

```text
~/thinfilm_outputs
```

常见输出包括：

```text
*_spectrum.csv
*_summary.json
*_summary.txt
*_RTA.png
*_main.png
*_period_summary.csv
*_error_analysis.png
```

其中联合扫描模式会额外输出：

- 参数扫描摘要表
- 最佳参数对应曲线
- 参数误差分析图

## 6. 当前阶段性结论

截至当前，已得到一个可工作的无损近似设计点：

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
- `t_wg` 可稳定推动峰位漂移
- `fill_factor` 可进一步微调峰位与线宽

## 7. 重要说明

### 7.1 占位求解器说明

`solver.py` 里当前仍保留占位求解器，它只用于：

- 工程骨架验证
- 导出链路验证
- 接口预留

不应用于正式物理论证。

### 7.2 COMSOL 数据说明

如果通过 `--csv` 或 `--sweep-csv` 读取 COMSOL 结果，那么：

- 谱线本身是真实 COMSOL 数据
- Python 负责做摘要、筛选和出图
- 物理求解仍发生在 COMSOL 中

### 7.3 当前未完成部分

目前仍建议后续补充：

1. 吸收与损耗影响
2. `t_grating` 扫描
3. 模态机理解释
4. 工艺容差分析

## 8. 推荐推进顺序

当前建议按下面顺序推进：

1. 先锁 `period`
2. 再扫 `t_wg`
3. 再扫 `fill_factor`
4. 最后补吸收与损耗
