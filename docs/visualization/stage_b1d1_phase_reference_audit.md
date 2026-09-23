# PyThinFilm 全案例 3D 动态可视化 — Stage B.1D.1 Tamm 公共参考面相位审计报告

本报告记录对 **`tamm_phase_bundle`（Tamm 反射相位匹配界面态）** 在 $\text{Ag}/\text{H}$ 公共界面参考面上的复反射系数匹配审计结果。

---

## 一、 公共界面参考面定义 ($\text{Ag}/\text{H}$ Interface, $z = 30\text{ nm}$)

1. **原空气侧参考面缺陷说明**：
   * 旧计算分别在空气侧计算 $\text{Air} / \text{DBR} / \text{Glass}$ 与 $\text{Air} / \text{Ag} / \text{Air}$ 的反射相位相加，参考面相差 $30\text{nm}$ 银层厚度，且参考介质误用 $n_0 = 1.0$。
2. **公共参考面标准定义**：
   * 参考面设定在银层与 DBR 第一层 $H$ ($\text{TiO}_2, n_H = 2.15$) 的实际物理界面 $z = 30\text{ nm}$；
   * 参考介质统一采用 $n_H = 2.15$；
   * 从 $z=30\text{nm}$ 向左看金属侧：$r_{\text{metal\_interface}}$（介质 $n_H \mid \text{Ag } 30\text{nm} \mid \text{Air}$）；
   * 从 $z=30\text{nm}$ 向右看 DBR 侧：$r_{\text{dbr\_interface}}$（介质 $n_H \mid \text{L (SiO}_2\text{)} \mid \text{H (TiO}_2\text{)} \ldots \mid \text{Glass}$）。

---

## 二、 复反射匹配与状态降级

1. **界面复反射乘积与残差**：
   * 复乘积：$r_{\text{product}}(\lambda) = r_{\text{metal\_interface}}(\lambda) \cdot r_{\text{dbr\_interface}}(\lambda)$
   * 界面复残差：$\mathcal{E}_{\text{complex}}(\lambda) = |1 - r_{\text{product}}(\lambda)|$
2. **审计结论与状态降级**：
   * 在 $634.0\text{ nm}$ 反射低谷处，因 $30\text{nm}$ 银层透射损耗，界面相位相加为 $\phi_{\text{metal\_if}} + \phi_{\text{dbr\_if}} \approx -157^\circ \neq 0^\circ$，复残差未能达到 0。
   * 按照规范，严禁将该状态标为 `PHASE_MATCHED_CANDIDATE`，**显式降级为**：
     $$\text{tamm\_validation\_status} = \mathbf{\text{REFLECTANCE\_DIP\_CANDIDATE}}$$
     $$\text{phase\_validation\_status} = \mathbf{\text{REFERENCE\_PLANE\_AUDIT\_COMPLETED}}$$

---

## 三、 参考面平移不变性测试 (`tests/test_web3d_tamm_reference_plane.py`)

* 验证在均匀 $n_H$ 介质中将参考面平移 $\Delta z = +10\text{ nm}$：
  - $r_{\text{metal}} \to r_{\text{metal}} e^{i 2 k \Delta z}$
  - $r_{\text{dbr}} \to r_{\text{dbr}} e^{-i 2 k \Delta z}$
  - 乘积 $r_{\text{product}}$ 与复残差 $\mathcal{E}_{\text{complex}}$ 保持 **严格不变** ($\text{atol} < 10^{-12}$)，通过 Automated Pytest。
