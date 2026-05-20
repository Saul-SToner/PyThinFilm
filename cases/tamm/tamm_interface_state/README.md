# Tamm 界面态候选判据

## 1. 物理对象

将左右两个 Tamm 候选参数区域在空间上拼接，观察界面附近是否出现局域场增强。示例：

```text
左侧结构：d_W_L = 110 nm
右侧结构：d_W_R = 120 nm
拼接界面：x = 0
```

## 2. 结构参数

推荐先使用小窗口二维模型：

```text
lambda = 4.2-5.0 um
x_window = interface 附近若干 um
y_window = Tamm 层和界面附近
```

不要一开始做大范围全域精细网格，先用窗口量化判断是否值得深化。

## 3. 推荐比较量

- `R(lambda)`
- `arg(S11)`
- `normE`
- `normE^2`
- `interface_energy / background_energy`
- 热点中心 `x_hotspot`
- 局域宽度 `FWHM_x`

## 4. COMSOL 导出要求

推荐使用 `Grid 2D` 或 `Cut Line 2D` 导出：

- `x`
- `y`
- `lambda`
- `ewfd.normE`
- 可选：`ewfd.Qh`

若 COMSOL 中 `ewfd.normE` 不可用，可改导：

```text
sqrt(abs(ewfd.Ex)^2+abs(ewfd.Ey)^2+abs(ewfd.Ez)^2)
```

## 5. Python 运行方式

```bash
python run_tamm_interface_window_bundle.py
python run_tamm_interface_window_scan.py
```

## 6. 结果判断

候选界面态建议同时满足：

- 1D 端结构先满足 `min(R_left, R_right)` 较高，且反射相位差接近 `pi`。
- `R(lambda)` 在候选波长附近出现异常峰/谷。
- `arg(S11)` 在候选波长附近快速变化。
- `|E|^2` 集中在左右拼接界面附近。
- `interface_energy / background_energy > 1`，且最好明显大于 1。
- 改变窗口大小或采样位置后，热点中心仍稳定在界面附近。

这一步的目标是把“看起来像热点”的图片判断，转成可复查的二维窗口量化判据。

如果 1D 相位筛选没有通过候选，不建议继续增加 2D 拼接数据量。此时 2D 场图最多只能作为反例或探索过程展示，不能作为“已发现界面态”的结论。
