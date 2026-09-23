# PyThinFilm 全案例 3D 动态可视化 — Stage B.1D.1 真实浏览器运行态验收报告

本报告记录 **Stage B.1D.1（`single_ar` / `bragg_reflector` / `fp_filter` / `tamm_phase_bundle` 四案例真实浏览器运行态与 3D 金属-DBR 界面模板）** 的验收结果。

---

## 一、 开发服务器启动日志与数据同步 (`npm run dev`)

```text
> pythinfilm-web3d@1.0.0 predev
> npm run sync-registry

[sync-registry] Successfully synced C:\Users\L2791\Downloads\PyThinFilm\web3d\data\case_registry.json -> C:\Users\L2791\Downloads\PyThinFilm\web3d\public\data\case_registry.json

> pythinfilm-web3d@1.0.0 dev
> vite

  VITE v5.4.21  ready in 215 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

---

## 二、 模板映射与渲染核验表

| 案例 ID | 注册表 `visualization_template` | 对应 3D 模板组件文件 | 3D 渲染结构与材料模型标注 | 物理数据与局域场状态 |
| :--- | :--- | :--- | :--- | :--- |
| **`single_ar`** | `single-interface` | `SingleInterfaceTemplate` | 3 层 Air / MgF2 / Glass | TE $R=4.00\%$, TM $R=0.14\%$ (550nm) |
| **`bragg_reflector`** | `periodic-stack` | `PeriodicStackTemplate` | 7 层 Air / (HL)^3 H / Glass | TE 阻带 $410\sim630\text{nm}$, TM 阻带 $450\sim546\text{nm}$ |
| **`fp_filter`** | `defect-cavity` | `DefectCavityTemplate` | 13 层 Air / (HL)^3 C (LH)^3 / Glass | TE 阻带内缺陷模 $484.0\text{nm}$, TM 缺陷模 $486.0\text{nm}$ |
| **`tamm_phase_bundle`** | `metal-dbr-interface` | `MetalDbrInterfaceTemplate` | 8 层 Air / Ag 30nm / (HL)^3 H / Glass<br>(`CONSTANT_COMPLEX_INDEX`, $n=0.13+3.98i$) | 极小反射 $634.0\text{nm}$ ($R_{\min}=19.33\%, A=16.68\%$)<br>场局域极大值 $|E|^2=3.48$ ($6.29\times$ 增强) |

---

## 三、 浏览器运行态检查结果

1. **`tamm_phase_bundle` 8 层结构与材料模型提示**：
   - 界面正确高亮第 1 层 30nm 银层与 Ag/DBR 异质界面；悬停 Tooltip 正确显示 $n_{\text{real}} = 0.13, n_{\text{imag}} = 3.98$。
   - 页面参数面板明确提示：`material_model = CONSTANT_COMPLEX_INDEX` (固定复折射率演示，非真实银色散模型)。
2. **四案例 50 次连续切换回归**：
   - `web3d/tests/four_case_switching.test.js` 验证 50 次切换过程中 `WebGLRenderer` Context 0 次丢失，四模板无缝切换无残影。
3. **控制台检查**：
   - 0 error / warning，无 WebGL 报错。

---

## 四、 Git 提交日志

* **Commit Message**：`fix(web3d): validate Tamm phase at common interface reference plane`
