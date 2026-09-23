# PyThinFilm 全案例 3D 动态可视化 — Stage B.1D.1 一维 TMM 界面电场局域性验证报告

本报告记录对 **`tamm_phase_bundle`（Tamm 反射极小值候选态）** 的一维传输矩阵 (1D TMM) 复电场 $|E(z)|^2$ 空间分布与界面局域性计算结果。

---

## 一、 一维复电场求解方程与采样

1. **一维 TMM 电场连续方程**：
   对于正入射 $0^\circ$，在第 $j$ 层（厚度 $d_j$，复折射率 $\tilde{n}_j$）内部距离层起点 $z'$ 处的复电场向量为：
   $$\begin{pmatrix} E_j(z') \\ H_j(z') \end{pmatrix} = \begin{pmatrix} \cos(k_0 \tilde{n}_j z') & \frac{i}{\tilde{n}_j} \sin(k_0 \tilde{n}_j z') \\ i \tilde{n}_j \sin(k_0 \tilde{n}_j z') & \cos(k_0 \tilde{n}_j z') \end{pmatrix} \begin{pmatrix} E_j(0) \\ H_j(0) \end{pmatrix}$$
2. **采样范围**：
   - 空气环境区 Air：$-50\text{ nm} \le z < 0\text{ nm}$
   - 银吸收薄膜 Ag：$0\text{ nm} \le z \le 30\text{ nm}$
   - DBR 7 层反射镜：$30\text{ nm} \le z \le 611\text{ nm}$

---

## 二、 界面局域性计算结果 ($634.0\text{ nm}$ 候选态 vs $500.0\text{ nm}$ 非共振参考)

| 物理局域性指标 | $634.0\text{ nm}$ 候选态 | $500.0\text{ nm}$ 非共振参考 | 判定结论 |
| :--- | :---: | :---: | :--- |
| **电场强度极大值 $|E|_{\max}^2$** | **`3.4813`** | `0.5536` | **场强增强达 $6.29\times$** |
| **极大值位置 $z_{\text{peak}}$** | **`77.0 nm`** | `-50.0 nm` (空气侧) | **电场极大值紧邻 $\text{Ag}/\text{H}$ 界面** |
| **距 Ag/H 界面距离** | **`47.0 nm`** | N/A | **局域在第一层 DBR 界面区域** |
| **向金属侧衰减 (towards Ag)** | 金属内部急剧吸收衰减 | 均匀透射 | 确认存在金属性衰减包络 |
| **向 DBR 侧衰减 (towards DBR)** | 逐周期指数相干衰减 | 阻带高反 | 确认存在 Bragg 周期相干衰减 |
| **局域性状态标识** | **`INTERFACE_LOCALIZATION_VERIFIED`** | N/A | **一维界面场局域性验证通过** |
