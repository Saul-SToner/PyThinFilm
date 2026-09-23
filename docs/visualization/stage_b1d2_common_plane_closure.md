# PyThinFilm 全案例 3D 动态可视化 — Stage B.1D.2 Tamm 公共参考面最终闭合报告

本报告记录对 **`tamm_phase_bundle`（Tamm 反射极小值/泄漏相位相干候选）** 在 $\text{Ag}/H_1$ 真正公共界面参考面 ($z = 30\text{ nm}$) 上的复反射匹配闭合结果。

---

## 一、 修正后的 DBR 侧公共参考面 (Method A 与 Method B 交叉验证)

1. **结构定义**：
   正式 8 层异质结构：$\text{Air} / \text{Ag (30nm)} / H_1(d_H) / L_1(d_L) / H_2 / L_2 / H_3 / L_3 / H_4 / \text{Glass}$。
   公共参考面位于 $z = 30\text{ nm}$ 处的 $\text{Ag}/H_1$ 物理界面，参考介质为 $n_H = 2.15$ ($\text{TiO}_2$)。

2. **反射系数求解方式与等价性验证**：
   - **Method A (包含 $H_1$ 传播)**：直接计算介质 $n_H \mid H_1(d_H) / L_1 / H_2 / L_2 / H_3 / L_3 / H_4 \mid \text{Glass}$ 的复反射系数 $r_{\text{dbr\_method\_A}}$。
   - **Method B (从 $H_1/L_1$ 界面按时间因子平移)**：计算 $r_{\text{HL\_boundary}}$ ($n_H \mid L_1 / H_2 / L_2 / H_3 / L_3 / H_4 \mid \text{Glass}$)，平移回到 $z = 30\text{ nm}$：
     $$r_{\text{dbr\_method\_B}} = r_{\text{HL\_boundary}} \cdot e^{i 2 k_H d_H}$$
   - **等价性校验**：Pytest 自动化断言 $\max|r_{\text{dbr\_method\_A}} - r_{\text{dbr\_method\_B}}| = 1.14 \times 10^{-15} < 10^{-10}$，证明两种方式高度收敛一致。

---

## 二、 细网格 (0.05nm 采样) 界面相位与复残差数据

| 物理指标项 (采样步长 $0.05\text{nm}$) | 数值结果 | 物理含义与判据状态 |
| :--- | :---: | :--- |
| **反射极小值波长 $\lambda_{\text{dip}}$** | **`634.00 nm`** ($R_{\min} = 0.193289$) | DBR 阻带内吸收/反射耦合极小值 |
| **金属侧复反射 $r_{\text{metal\_interface}}$** | $-0.814227 + 0.007626i$ ($|r|=0.8143$) | 从 $z=30\text{nm}$ 向左看 $\text{Ag }(30\text{nm})/\text{Air}$ 的反射 |
| **DBR 侧复反射 $r_{\text{dbr\_interface}}$** | $-0.917631 - 0.014282i$ ($|r|=0.9177$) | 从 $z=30\text{nm}$ 向右看 $H_1 \dots H_4/\text{Glass}$ 的反射 |
| **界面相位残差 $\Delta\phi = \text{wrap\_to\_pi}(\phi_m + \phi_d)$** | **`-0.006138 rad` ($\mathbf{-0.35^\circ}$)** | **Ag/H1 界面反射相位在 $634.0\text{nm}$ 几乎完全抵消零残差** |
| **振幅乘积 $A_{\text{product}} = |r_m| \cdot |r_d|$** | `0.747271` | 由于 30nm 银层透射吸收，乘积未达 1 |
| **复匹配残差 $|1 - r_m \cdot r_d|$** | `0.252733` | 损耗边界下的有限反射低谷残差 |
| **最小复残差波长** | `630.00 nm` ($\mathcal{E}_{\min} = 0.247938$) | 距反射低谷 $634\text{nm}$ 仅 $4.0\text{nm}$ 差距 |

---

## 三、 修正后的 Tamm 验证等级

根据规范，在有损金属与开放边界下，相位残差 $\Delta\phi = -0.35^\circ \approx 0^\circ$ 成立，且复残差存在局部极小：
$$\text{tamm\_validation\_status} = \mathbf{\text{PHASE\_MATCHED\_LEAKY\_CANDIDATE}}$$
$$\text{phase\_validation\_status} = \mathbf{\text{REFERENCE\_PLANE\_AUDIT\_COMPLETED}}$$
