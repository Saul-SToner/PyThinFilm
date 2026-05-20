# Tamm 前沿模块

这里放 Tamm 吸收器、反射相位、候选参数对和界面窗口分析脚本。

常用根目录入口：

```bash
python run_tamm_phase_bundle.py --csv "path/to/tamm_phase_scan.csv"
python run_tamm_reflection_phase_screen.py --csv "path/to/tamm_phase_scan.csv"
python run_tamm_interface_window_bundle.py
python run_tamm_interface_window_scan.py
```

本目录内的具体脚本：

```text
run_tamm_phase_bundle.py
run_tamm_phase_focus.py
run_tamm_phase_candidates.py
run_tamm_reflection_phase_screen.py
run_tamm_interface_priority.py
run_tamm_interface_window_bundle.py
run_tamm_interface_window_scan.py
```

专题说明页：

```text
// 技术分析页
phase_scan/
interface_window/

// 展示叙事页
tamm_absorber_baseline/
tamm_phase_transition/
tamm_interface_state/
```

推荐展示顺序：

1. `tamm_absorber_baseline/`：先说明普通 Tamm 吸收器和候选吸收峰。
2. `tamm_phase_transition/`：再说明反射相位、相位跃迁和参数分类。
3. `tamm_interface_state/`：最后说明左右参数拼接后，如何判断界面局域态。

当前深化路线：

```text
1D 固定端结构扫描
  -> 筛选同一波长下 min(R_left,R_right) 高、相位差接近 pi 的参数对
  -> 只把通过筛选的参数对拿去做 2D 界面拼接
  -> 用 Grid 2D / Cut Line 2D 量化界面场增强
```

推荐先运行：

```bash
python run_tamm_reflection_phase_screen.py ^
  --csv "path/to/tamm_phase_scan.csv" ^
  --lambda-min-um 4.3 ^
  --lambda-max-um 4.8 ^
  --min-reflectance 0.70 ^
  --max-phase-error-rad 0.35
```
