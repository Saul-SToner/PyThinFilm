# 薄膜反射谱拟合项目协作说明

## 项目目标

本项目用于从 COMSOL 或实验导出的反射率光谱中反演薄膜厚度。

当前方法是**物理模型反演**，不是神经网络：

1. 用单层薄膜 Fresnel 反射模型生成理论反射谱。
2. 输入两个入射角下的反射率曲线。
3. 联合拟合薄膜厚度 `d`。
4. 可选地修正第二入射角 `theta2`。

当前最稳定的工程主线是：

```text
10° + 80°
s 偏振
双角联合反演厚度
```

## 主文件

主要使用：

```text
thinfilm_core.py
```

其他文件主要是早期探索或辅助分析：

```text
comsol_only_analysis.py
theta_scan_fit_from_comsol.py
Untitled-1.py
```

## 当前推荐主线

推荐配置：

```python
RUN_MODE = "fit_csv_with_theta2_search"
THETA1 = 10.0
THETA2 = 80.0
POL = "s"
```

输入文件：

```python
CSV_FILE_ANGLE1 = Path(r"...10deg_s.csv")
CSV_FILE_ANGLE2 = Path(r"...80deg_s.csv")
```

当前 `60 nm` 样品在 `10° + 80°`、`s` 偏振下的验证结果约为：

```text
d_fit_corrected ≈ 59.97 nm
theta2_fit      ≈ 80.04°
best_objective  ≈ 3.02e-02
```

这说明当前主线已经比较稳定。

## COMSOL 导出建议

工程主线优先导出纯 `s` 偏振反射率：

```text
10deg_s.csv
80deg_s.csv
```

如果后续要比较偏振影响，可以额外导出：

```text
10deg_p.csv
80deg_p.csv
```

当前不建议直接依赖 COMSOL 的 `mixed` 或 `avg(0.6p)` 导出作为主拟合输入。

之前已经观察到：

```text
COMSOL 直接导出的 mixed 曲线不等于 eta * R_p + (1 - eta) * R_s
```

因此如果要做混合偏振，更稳的方式是：

```text
分别导出纯 s 和纯 p 端点，然后在 Python 后处理中线性合成。
```

混合偏振模型为：

```text
R_mix = eta * R_p + (1 - eta) * R_s
```

其中：

```text
0 <= eta <= 1
```

## 主要运行模式

在 `thinfilm_core.py` 顶部设置 `RUN_MODE`。

常用模式：

```text
fit_csv_with_theta2_search      单样品双角拟合，并搜索第二角修正
fit_csv_compare_pols            比较 s / p / avg / mix 模型
single_sample_error_analysis    单样品误差来源分析
batch_error_analysis            批量厚度误差分析
single_angle_0deg_scan          单角厚度扫描，虽然名字含 0deg，但现在已随 THETA1 变化
objective_heatmap_d_theta2      输出 d-theta2 目标函数热图
```

当前主线使用：

```text
fit_csv_with_theta2_search
```

## 关键配置项

双角输入：

```python
CSV_FILE_ANGLE1 = Path(...)
CSV_FILE_ANGLE2 = Path(...)
THETA1 = 10.0
THETA2 = 80.0
```

偏振设置：

```python
POL = "s"      # 当前推荐主线
POL = "p"      # p 偏振对照
POL = "avg"    # 固定 50% s + 50% p
POL = "mix"    # eta * p + (1 - eta) * s
```

混合偏振端点合成：

```python
MIX_USE_ENDPOINT_TARGET_BLEND = True
MIX_SOURCE_P_WEIGHT = 0.6
MIX_SOURCE_ANGLE1_MODE = "blend"
MIX_SOURCE_ANGLE2_MODE = "blend"
```

端点文件：

```python
MIX_SOURCE_CSV_ANGLE1_S = Path(...)
MIX_SOURCE_CSV_ANGLE1_P = Path(...)
MIX_SOURCE_CSV_ANGLE2_S = Path(...)
MIX_SOURCE_CSV_ANGLE2_P = Path(...)
```

## 色散模型

代码支持可选 Cauchy 色散模型：

```text
n(lambda) = A + B / lambda_um^2 + C / lambda_um^4
```

开关：

```python
USE_DISPERSION = True
```

参数：

```python
N1 = 1.38
N1_DISPERSION_B = ...
N1_DISPERSION_C = ...

N2 = 1.52
N2_DISPERSION_B = ...
N2_DISPERSION_C = ...
```

在 COMSOL 中，建议先定义无量纲波长：

```text
lambda_um = lambda0/1[um]
```

然后材料折射率写成：

```text
n1 = n1_A + n1_B/(lambda_um^2) + n1_C/(lambda_um^4)
```

不要直接使用无单位的 `lambda0`。

当前观察：

```text
n1_B = 0.005 这组色散参数在 60 nm、10° + 80°、s 偏振数据上没有改善拟合，反而使 objective 变大。
```

这不代表色散模型错误，只说明这组色散参数不适合当前数据。

后续如果寻找色散参数，建议先小范围扫描：

```text
n1_A: 1.36 ~ 1.40
n1_B: 0 ~ 0.005
n1_C: 0
n2 暂时固定
```

不要只用一个厚度点确定色散参数，至少应使用多个厚度点共同判断。

## 输出目录

所有结果默认输出到：

```text
C:\Users\L2791\thinfilm_outputs
```

常见输出包括：

```text
fit_csv_with_theta2_search_summary.txt
fit_csv_with_theta2_search_summary.json
fit_csv_with_theta2_search_result.csv
拟合曲线图
残差图
目标函数热图
```

## APP / 可视化封装建议

当前代码已经可以交给队友做 APP 原型。

APP 不要写死样品、角度或偏振，应该做成参数驱动。

建议输入：

```text
csv_angle1
csv_angle2
theta1
theta2
pol
n0
n1
n2
use_dispersion
n1_dispersion_b
n1_dispersion_c
n2_dispersion_b
n2_dispersion_c
```

建议输出：

```text
d_fit_corrected_nm
theta2_fit_deg
best_objective
拟合曲线
残差曲线
输入文件信息
模型参数信息
```

服务器需求不高：

```text
原型：4 核 CPU，8 GB 内存
多人使用：8 核 CPU，16 GB 内存
GPU：不需要
```

这是 CPU 数值计算，不是神经网络推理。

## 当前已知限制

1. 当前模型是单层薄膜模型。
2. 尚未加入粗糙度、过渡层、多层膜。
3. COMSOL 直接导出的 mixed / avg 曲线目前不可靠。
4. 色散支持已经接入，但材料参数还需要系统寻找。
5. 部分旧函数名仍带有 `0deg`，但新配置已经改为 `ANGLE1 / ANGLE2` 别名。

## 推荐后续推进顺序

1. 固定主线：`10° + 80°`，`s` 偏振。
2. 用 `60 / 70 / 80 / 100 / 120 nm` 做多厚度验证表。
3. 记录每组：
   - `d_fit_corrected`
   - 厚度误差
   - `theta2_fit`
   - `best_objective`
4. 主线稳定后，再小范围扫描 `n1_A / n1_B`。
5. mixed 偏振作为诊断支线，不作为当前生产主线。
6. APP 可以并行开发，但必须保持参数驱动，不要硬编码当前样品。
