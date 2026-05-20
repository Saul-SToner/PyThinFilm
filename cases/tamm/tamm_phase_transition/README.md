# Tamm 反射相位与参数分类

## 1. 物理对象

通过反射复振幅 `S11` 的相位变化，为不同厚度参数建立候选分类，服务于后续界面拼接结构。

## 2. 结构参数

推荐最小扫描：

```text
d_W = 110 nm, 119 nm, 120 nm, 130 nm
lambda = range(4.2[um], 0.02[um], 5.0[um])
```

## 3. 推荐比较量

- `real(S11)`
- `imag(S11)`
- `abs(S11)^2`
- `arg(S11)`
- 相位快速变化位置

## 4. COMSOL 导出要求

推荐导出：

- `lambda`
- `d_W`
- `real(ewfd.S11)`
- `imag(ewfd.S11)`
- `abs(ewfd.S11)^2`

## 5. Python 运行方式

```bash
python run_tamm_phase_bundle.py --csv "path/to/tamm_phase_scan.csv"
python run_tamm_phase_candidates.py --csv "path/to/tamm_phase_scan.csv"
python run_tamm_reflection_phase_screen.py --csv "path/to/tamm_phase_scan.csv"
```

## 6. 结果判断

重点不是只找最大吸收，而是判断候选参数之间是否存在可解释的相位差异。若相位变化与吸收峰位置同时稳定，才适合进入界面拼接阶段。

进入 2D 拼接前，优先使用更严格的端结构判据：

```text
min(R_left, R_right) >= 0.70
abs(pi - abs(arg(r_left)-arg(r_right))) <= 0.35 rad
同一波长下同时满足上述两个条件
```

如果没有参数对满足该条件，不建议继续做大规模 2D 拼接；应先回到 1D 扫描，扩大 `d_W`、金属层厚度或 DBR 端层厚度范围。
