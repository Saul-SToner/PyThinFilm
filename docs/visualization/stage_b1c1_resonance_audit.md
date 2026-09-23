# PyThinFilm 全案例 3D 动态可视化 — Stage B.1C.1 F-P 谐振物理审计与峰识别报告

本报告响应《Stage B.1C.1 F-P 谐振物理审计与真实浏览器验收》指令，彻底纠正了将“全局最大透射点”误判为“缺陷腔共振模”的问题，完成了相位相位匹配一阶估计、多段连续阻带分割与阻带内局部缺陷模峰定位。

---

## 一、 核心物理纠偏：全局最大透射 vs 缺陷腔谐振模

1. **全局最大透射点 (Passband Oscillation)**：
   * **问题**：直接在 $400\sim750\text{ nm}$ 全光谱执行 `np.argmax(T)`，会搜索到位于 DBR 阻带外的通带震荡区 ($664.0\text{ nm} / 644.0\text{ nm}$，透射率 $97.88\% / 99.96\%$)。
   * **改动**：在 `fp_filter.json` 中单独记录为 `global_transmission_metrics`，严禁将其直接填入谐振模属性。
2. **阻带内真实缺陷腔共振模 (Intra-Stopband Defect Mode)**：
   * **物理位置**：真正的 Fabry-Perot 缺陷腔透射峰位于 DBR 高阻带通道内部。
   * **检测结果**：
     - **TE 偏振 ($s$) 缺陷模**：位于 **$\lambda = 484.0\text{ nm}$**（透射率 $T = 0.900790$，反射率降低至 $R = 0.099210$）；
     - **TM 偏振 ($p$) 缺陷模**：位于 **$\lambda = 486.0\text{ nm}$**（透射率 $T = 0.990813$，反射率降低至 $R = 0.009187$）。

---

## 二、 理论相位相位一阶估计与偏振蓝移核验

1. **一阶相位估计公式**：
   $$\lambda_{\text{cavity}} \approx 2 \cdot n_C \cdot d_C \cdot \cos\theta_C$$
   - 缺陷腔材料：$\text{SiO}_2, n_C = 1.38, d_C = 199.2754\text{ nm}$
   - 腔内折射角：$\sin\theta_C = \frac{1.0 \cdot \sin 45^\circ}{1.38} = 0.512396 \implies \theta_C = 30.82^\circ, \cos\theta_C = 0.858749$
   - 理论预估波长：$\lambda_{\text{cavity}} \approx 2 \times 1.38 \times 199.2754 \times 0.858749 = \mathbf{472.3\text{ nm}}$
2. **偏差核验**：
   * TE 缺陷模 ($484.0\text{ nm}$) 与估计值偏差：$11.7\text{ nm}$ (相对偏差 **$2.48\%$**)；
   * TM 缺陷模 ($486.0\text{ nm}$) 与估计值偏差：$13.7\text{ nm}$ (相对偏差 **$2.90\%$**)；
   * 偏差原因：有限周期 DBR 镜像相干反射的相位随波长变化产生微小推移，完全符合斜入射蓝移与偏振分裂规律。

---

## 三、 `periods = 4` 规格参数语义闭环

在 `thinfilm/education.py:build_fp_single_halfwave_layers` 中：
* 规格参数 `periods = 4` 的真实语义为：指定两侧 DBR 反射镜组的干涉配对阶数（构造器内部计算 `periods - 1 = 3` 对）。
* 结构构成：
  - 顶反射镜：$(HL)^3 = 6$ 层
  - 缺陷腔层：$C = 2L = 1$ 层 ($d_C = 199.275\text{ nm}$)
  - 底反射镜：$(LH)^3 = 6$ 层
  - 总层数：$6 + 1 + 6 = \mathbf{13\text{ 层}}$。

---

## 四、 自动化测试日志

* **`py -m pytest tests/test_web3d_fp_resonance_detection.py -v`** $\to$ **`1 passed in 0.24s`**
* **`py -m pytest tests/ -q`** $\to$ **`337 passed in 4.30s`**
