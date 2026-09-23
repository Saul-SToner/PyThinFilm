# PyThinFilm 全案例 3D 动态可视化 — Tamm 界面态正式案例来源与物理判据审计

本报告记录对 **`tamm_phase_bundle`（Tamm 反射相位匹配界面态）** 的正式案例代码来源、结构参数、金属衰减与相位匹配判据审计结果。

---

## 一、 权威代码来源与结构参数

1. **代码入口与文件路径**：
   * **运行入口**：📄 [cases/tamm/run_tamm_phase_bundle.py](file:///C:/Users/L2791/Downloads/PyThinFilm/cases/tamm/run_tamm_phase_bundle.py)
   * **核心分析模块**：📄 [thinfilm/validation.py](file:///C:/Users/L2791/Downloads/PyThinFilm/thinfilm/validation.py): `analyze_tamm_dw_phase_scan` & `analyze_tamm_reflection_phase_screen`
   * **相位计算函数**：📄 [thinfilm/education.py](file:///C:/Users/L2791/Downloads/PyThinFilm/thinfilm/education.py): `reflection_phase_radians`, `phase_difference`
2. **正式结构与材料明细**：
   $$\text{Air} / \text{Ag (30nm)} / (HL)^3 H \text{ DBR} / \text{Glass}$$
   - **入射介质**：Air ($n_0 = 1.0$)
   - **金属层**：Ag 银薄层 ($d_{\text{Ag}} = 30.0\text{ nm}$, 复折射率 $n_{\text{Ag}} = 0.13 + 3.98i$ at $550\text{nm}$)
   - **DBR 反射镜层**：7 层 $\text{TiO}_2 (H, n_H = 2.15, d_H = 63.95\text{nm}) / \text{SiO}_2 (L, n_L = 1.38, d_L = 99.64\text{nm})$
   - **基底介质**：Glass Substrate ($n_s = 1.52$)
   - **设计入射角**：$0.0^\circ$ (正入射)

---

## 二、 Tamm 界面态物理判据与数值验证

根据规范，Tamm 界面态判定需同时评估 DBR 阻带、反射低谷与相位匹配条件：

1. **DBR 主阻带范围**：
   - 阻带阈值 $R \ge 0.50$：$400.0\text{ nm} \sim 730.0\text{ nm}$ 连续区间。
2. **反射光谱极小值 (Reflectance Dip)**：
   - 在阻带内部，反射率在 **$\lambda = 634.0\text{ nm}$** 出现极小值 **$R_{\min} = 0.193289$** ($19.33\%$)。
3. **反射相位匹配残差 (Phase Matching Residual)**：
   - 金属侧反射相位 $\phi_{\text{metal}}$ 与 DBR 侧反射相位 $\phi_{\text{DBR}}$ 满足相干残差：
     $$\Delta\phi = \text{wrap\_to\_pi}(\phi_{\text{metal}} + \phi_{\text{DBR}} - 2\pi m)$$
   - 在 **$\lambda = 633.0\text{ nm}$** 处，相位残差达到 **$\Delta\phi = 0.000796\text{ rad} \approx 0.045^\circ$**（极接近 0）。
4. **金属吸收与能量守恒**：
   - 在候选点 $\lambda = 633.0\text{ nm}$ 处：$R = 0.193895$, $T = 0.639343$, $A = 0.166762$ ($16.68\%$ 银层吸收)；
   - 能量残差 $\max|R + T + A - 1.0| = 1.11 \times 10^{-16} < 10^{-6}$，严密满足有损介质能量守恒。
5. **局域场状态与验证等级**：
   * 当前 TMM 矩阵导出接口未提供 2D 空间网格电场分布数据，`field_data_status` 标记为 `"NOT_AVAILABLE"`。
   * 根据规范，无真实场数据时，`tamm_validation_status` 最高标记为 **`"PHASE_MATCHED_CANDIDATE"`**，**严禁标记为 `TAMM_STATE_VERIFIED`**；前端 3D 动画标注为 `animation_semantics = "TEACHING_ILLUSTRATION"`。
