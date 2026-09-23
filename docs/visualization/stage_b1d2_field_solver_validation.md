# PyThinFilm 全案例 3D 动态可视化 — Stage B.1D.2 一维 TMM 场求解器交叉验证与包络包落报告

本报告记录对 **📄 [thinfilm/field_profile.py](file:///C:/Users/L2791/Downloads/PyThinFilm/thinfilm/field_profile.py) 一维 TMM 复电场求解器** 的严密交叉验证以及一维界面场包络与局域性指标。

---

## 一、 一维 TMM 场求解器 5 项严密验证 (`tests/test_tmm_field_profile.py`)

1. **反射与透射光谱交叉验证**：
   与 `thinfilm/education.py:multilayer_rt_spectrum` 交叉校验，能量指标 $R, T, A$ 误差 $\max < 10^{-10}$，通过 Pytest。
2. **界面切向 $E$ 与 $H$ 连续性**：
   在所有 8 层异质界面左右两侧，切向复电场与复磁场连续残差 $\max(|E_{\text{left}} - E_{\text{right}}|, |H_{\text{left}} - H_{\text{right}}|) < 10^{-10}$。
3. **边界条件规范性**：
   - 入射端前向振幅归一 $E_0^+ = 1.0$；
   - 基底端无反向入射波 $E_{\text{sub}}^- = 0.0$；
   - 有损金属 Ag 内部 Poynting 通量梯度严格对应局域吸收 $A$。
4. **网格收敛性**：
   对比 $dz = 1.0\text{ nm}, 0.5\text{ nm}, 0.25\text{ nm}$，极大值场强收敛误差 $< 10^{-6}$。
5. **解析基准验证**：
   Air/Glass 菲涅耳单界面与无损/有损单层膜解与解析公式一致。

求解器状态标记为：`field_solver_status = "FIELD_SOLVER_VERIFIED"`。

---

## 二、 一维场包络衰减与多波长对照 ($634.0\text{ nm}$ vs $500.0\text{ nm}$ / $750.0\text{ nm}$)

| 局域场与包络指标 | $634.0\text{ nm}$ 候选态 | $500.0\text{ nm}$ 阻带对照 1 | $750.0\text{ nm}$ 阻带对照 2 | 物理结论 |
| :--- | :---: | :---: | :---: | :--- |
| **电场极大值 $|E|_{\max}^2$** | **`3.4813`** | `0.5536` | `1.2678` | 候选态获得显著场响应 |
| **极大值位置 $z_{\text{peak}}$** | **`77.0 nm`** | `-50.0 nm` (空气侧) | `-50.0 nm` (空气侧) | 极大值位于首层 H1 内 (距 Ag/H1 界面 47nm) |
| **场强增强倍数 Ratio** | N/A | **`6.29×`** | **`2.75×`** | 候选态显著高于同阻带两侧非共振波长 |
| **金属侧衰减比 $|E|_{z=0}^2 / |E|_{z=30}^2$** | **`0.8123`** | N/A | N/A | 金属内部呈现由吸收引起的衰减包络 |
| **界面窗口 $[0, 93.95\text{nm}]$ 能量占比** | **`42.15%`** | N/A | N/A | 电场能量高度集中于界面与首层 H1 |

---

## 三、 DBR 4 周期包络衰减轨迹 ($634.0\text{ nm}$)

```text
Period 1 (H1 + L1,  30.0nm ~ 193.6nm): |E|^2 max = 3.4813  (Integrated |E|^2 = 368.5)
Period 2 (H2 + L2, 193.6nm ~ 357.2nm): |E|^2 max = 1.3410  (Integrated |E|^2 = 141.2)
Period 3 (H3 + L3, 357.2nm ~ 520.8nm): |E|^2 max = 0.5165  (Integrated |E|^2 =  54.3)
Period 4 (H4,       520.8nm ~ 584.7nm): |E|^2 max = 0.1989  (Integrated |E|^2 =  10.9)
```

**物理结论**：电场极大值从 Period 1 ($3.4813$) 到 Period 4 ($0.1989$) 呈**单调指数衰减**。
根据规范，因极大值位于首层 H1 内 (距 Ag/H1 界面 47nm)，标记为：
$$\text{field\_localization\_status} = \mathbf{\text{FIELD\_ENHANCEMENT\_CANDIDATE}}$$
