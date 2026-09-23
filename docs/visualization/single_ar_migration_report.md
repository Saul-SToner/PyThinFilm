# PyThinFilm 全案例 3D 动态可视化 — Stage B.1A 单案例 (single_ar) 迁移报告

本报告记录对 **`single_ar`（单层增透膜）** 的单案例受限迁移过程。我们严格遵循“禁止前端二次计算覆盖 Python 数据”原则，建立了基于 Python TMM 引擎点对点算效导出的 `web3d/public/results/single_ar.json` 物理数据链，并在统一 3D 引擎中完成了渲染对接与状态升级。

---

## 一、 物理结构与计算参数

1. **结构参数**：
   * **环境介质**：Air ($n_0 = 1.0$)
   * **薄膜层**：$\text{MgF}_2$ ($n_1 = 1.38$, 厚度 $d_1 = 111.5\text{ nm}$，满足 $550\text{ nm}$ 四分之一波长增透)
   * **基底介质**：Glass ($n_s = 1.52$)
2. **计算条件**：
   * **设计中心波长**：$\lambda_0 = 550.0\text{ nm}$
   * **入射角**：$\theta_0 = 45.0^\circ$
   * **偏振模式**：TE ($s$-polarization) 与 TM ($p$-polarization)
3. **物理数据导出路径**：
   * `web3d/public/results/single_ar.json`（由 `tools/export_visualization_cases.py` 自动导出，包含当前 Git Commit Hash 溯源）

---

## 二、 Python 与前端数据显示点对点核查

| 偏振模式 (45°) | Python 计算反射率 $R$ | Python 计算透射率 $T$ | 吸收率 $A$ | 能量守恒关系 $R + T + A$ | 前端 JSON 读取值 | 绝对误差 | 对照判定 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **TE 偏振 ($s$)** | `0.040048` | `0.959952` | `0.000000` | **`1.000000`** | `0.040048` | $< 10^{-6}$ | **PASSED** |
| **TM 偏振 ($p$)** | `0.001356` | `0.998644` | `0.000000` | **`1.000000`** | `0.001356` | $< 10^{-6}$ | **PASSED** |

### 说明与动画语义标注
* **能量守恒**：在无吸收介质（$\text{MgF}_2, \text{Glass}$ 均为纯实数折射率）条件下，$R + T + A = 1.000000$ 严格成立。
* **动画说明**：3D 光路电场矢量波动的振幅在 3D 场景中已作适度放大显示以保证教学直观性，标注为 `animation_semantics = "TEACHING_ILLUSTRATION"`；核心光强曲线、R/T 数值与能谱分布 100% 绑定 Python 导出 JSON 数据。

---

## 三、 注册表状态升级

在 `web3d/data/case_registry.json` 中对 `single_ar` 完成如下状态提升：

```json
{
  "id": "single_ar",
  "geometry_status": "GEOMETRY_VERIFIED",
  "physics_data_status": "PHYSICS_DATA_AVAILABLE",
  "migration_status": "READY_FOR_MIGRATION",
  "python_reference_comparison": "PASSED",
  "calculation_source": "python_export"
}
```

其余 39 项物理案例保持受限暂缓状态，不进行提前迁移。

---

## 四、 测试与验证

1. **`npm run test`**：Vitest 场景切换 50 次生命周期回归与数据 Loader 校验测试 $\to$ **`2 passed in 3.91s`**
2. **`npm run build`**：执行 `prebuild` 自动同步注册表并构建生产包 $\to$ **`built in 1.15s`**
3. **`py -m pytest tests/ -q`**：Python 全量回归 $\to$ **`334 passed in 11.81s`**

---

## 五、 Git 提交信息

* **Git Branch**：`national/v1.1-dev`
* **Commit Message**：`feat(web3d): migrate single AR case with Python-backed results`
