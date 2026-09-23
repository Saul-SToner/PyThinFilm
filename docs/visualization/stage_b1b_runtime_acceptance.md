# PyThinFilm 全案例 3D 动态可视化 — Stage B.1B.1 真实浏览器运行态验收报告

本文档记录对 **Stage B.1B.1（`single_ar` 与 `bragg_reflector` 真实浏览器运行态与偏振指标收口）** 的验收结果。

---

## 一、 开发服务器启动日志 (`npm run dev`)

```text
> pythinfilm-web3d@1.0.0 predev
> npm run sync-registry

[sync-registry] Successfully synced C:\Users\L2791\Downloads\PyThinFilm\web3d\data\case_registry.json -> C:\Users\L2791\Downloads\PyThinFilm\web3d\public\data\case_registry.json

> pythinfilm-web3d@1.0.0 dev
> vite

  VITE v5.4.21  ready in 248 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

---

## 二、 模板路由映射表

| 注册表 `visualization_template` 字段 | 对应 3D 模板组件文件 | 当前接入状态 | 加载处理机制 |
| :--- | :--- | :---: | :--- |
| **`single-interface`** | `web3d/src/templates/single-interface.js` | **MIGRATION_VERIFIED** | 读取 `single_ar.json` 导出数据渲染 3 层结构 |
| **`periodic-stack`** | `web3d/src/templates/periodic-stack.js` | **MIGRATION_VERIFIED** | 读取 `bragg_reflector.json` 导出数据渲染 7 层 $\text{Air}/(HL)^3H/\text{Glass}$ |
| **`defect-cavity`** | `web3d/src/templates/defect-cavity.js` | *PENDING (Stage B.1C)* | 捕获并提示“未接入 3D 模板”，不显示伪造数值 |

---

## 三、 Bragg 反射镜设计口径与 TE/TM 分离指标

### 1. 设计口径与膜厚定义
* **设计中心波长**：$\lambda_0 = 550.0\text{ nm}$
* **正入射四分之一波厚度 (0° QWOT)**：
  - 高折射率层 ($H = \text{TiO}_2, n_H = 2.15$)：$d_H = \frac{550}{4 \times 2.15} = 63.9535\text{ nm}$
  - 低折射率层 ($L = \text{SiO}_2, n_L = 1.38$)：$d_L = \frac{550}{4 \times 1.38} = 99.6377\text{ nm}$
* **设计口径说明**：膜层厚度按 **$550\text{ nm}$ 正入射四分之一波条件** 设计，随后评估其在 $45^\circ$ 斜入射下的 TE/TM 光谱响应；未针对 $45^\circ$ 进行角度厚度补偿，因此中心高反带存在正常的斜入射蓝移现象（中心波长蓝移至 $498\text{ nm}$）。

### 2. $45^\circ$ 斜入射下的 TE/TM 分离指标 (阈值 $R \ge 0.70$)

| 偏振模式 ($45^\circ$) | 峰值反射率 $R_{\max}$ | 峰值波长 $\lambda_{\text{peak}}$ | 高反带起止波长 ($R \ge 0.70$) | 高反带带宽 $\Delta\lambda$ | 550nm 反射率 $R$ | 550nm 透射率 $T$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **TE 偏振 ($s$)** | `0.963766` (96.38%) | `498.0 nm` | `410.0 nm` $\sim$ `630.0 nm` | **`220.0 nm`** | `0.785231` | `0.214769` |
| **TM 偏振 ($p$)** | `0.791552` (79.16%) | `498.0 nm` | `450.0 nm` $\sim$ `546.0 nm` | **`96.0 nm`** | `0.589871` | `0.410129` |

* **相位相位数据状态**：正式计算入口当前未返回复数反射相位，JSON 中明确标记 `phase_data_status = "NOT_AVAILABLE"`，杜绝伪造数组。

---

## 四、 真实浏览器运行态检查结果

1. **`single_ar` 场景**：Air / MgF2 / Glass 结构、45° 入射光路、TE/TM 切换数值同步刷新、展开/叠合正常、悬停 Tooltip 准确。
2. **`bragg_reflector` 场景**：`periodic-stack` 模板顺利加载，Air / (HL)^3 H / Glass 7 层排列清晰，悬停正确显示层序号 (1-7)、H/L 类型、折射率与厚度。
3. **控制台检查**：无未捕获异常，无 WebGL 报错。

---

## 五、 Git 提交日志

* **Commit Message**：`fix(web3d): close Bragg runtime and polarization metrics`
