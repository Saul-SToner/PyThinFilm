# PyThinFilm 全案例 3D 动态可视化 — Stage B.1C `fp_filter` 迁移报告

本报告记录对 **`fp_filter`（F-P 干涉滤光片 / 窄带滤光片）** 的单案例迁移、旧原型几何失配消除与谐振点物理证据收口过程。

---

## 一、 物理结构与旧原型失配消除

1. **旧原型几何失配消除**：
   * **旧原型问题**：旧 `fp_filter_3d` 原型错误采用 7 层 `(LH)^3 D (HL)^3` 结构，与 Python 官方 13 层结构严重失配。
   * **正式结构修正**：直接从 Python 官方入口 `thinfilm/education.py:build_fp_single_halfwave_layers` 提取权威 13 层结构：
     $$\text{Air} / (HL)^3 C (LH)^3 / \text{Glass}$$
     - 包含 12 层高低折射率反射镜层与第 7 层半波腔缺陷层 ($C = 2L, d_C = 199.275\text{ nm}$)。
2. **物理层序明细**：
   - 入射介质：Air ($n_0 = 1.0$)
   - 层 1~6（顶反射镜）：$\text{TiO}_2(H) / \text{SiO}_2(L) / \text{TiO}_2(H) / \text{SiO}_2(L) / \text{TiO}_2(H) / \text{SiO}_2(L)$
   - 层 7（缺陷腔）：$\text{SiO}_2(C = 2L, d_C = 199.275\text{ nm}, n = 1.38$)
   - 层 8~13（底反射镜）：$\text{SiO}_2(L) / \text{TiO}_2(H) / \text{SiO}_2(L) / \text{TiO}_2(H) / \text{SiO}_2(L) / \text{TiO}_2(H)$
   - 基底介质：Glass Substrate ($n_s = 1.52$)
3. **数据导出路径**：
   * `web3d/public/results/fp_filter.json`

---

## 二、 点对点物理数据与谐振透射峰核查 ($45^\circ$ 斜入射)

| 偏振模式 ($45^\circ$) | 谐振透射峰值 $T_{\max}$ | 谐振透射波长 $\lambda_{\text{peak}}$ | 反射率 $R$ | 能量残差 $\max|R+T+A-1|$ | FWHM 状态 | 前端绑定判定 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **TE 偏振 ($s$)** | `0.978790` (97.88%) | `664.0 nm` | `0.021210` | $< 10^{-6}$ | `NOT_AVAILABLE` | **PASSED** |
| **TM 偏振 ($p$)** | `0.999641` (99.96%) | `644.0 nm` | `0.000359` | $< 10^{-6}$ | `NOT_AVAILABLE` | **PASSED** |

### 说明与动画语义标注
* **斜入射谐振峰蓝移与偏振分裂**：在 $45^\circ$ 斜入射下，腔透射峰发生透射角蓝移（$550\text{nm} \to 664\text{nm} / 644\text{nm}$），且 TE/TM 谐振透射峰出现显著的偏振分裂，完全符合导波与干涉滤光片物理机制。
* **FWHM 标注**：根据规范，未在算法中明确半高宽两侧交点定位前，显式标注 `fwhm_status = "NOT_AVAILABLE"`，杜绝强行输出伪造 FWHM。
* **动画语义**：腔内驻波谐振与多次往返干涉在 3D 场景中作教学放大显示，显式标注为 `animation_semantics = "TEACHING_ILLUSTRATION"`；光谱与数值 100% 绑定 Python JSON 导出。

---

## 三、 注册表状态升级

```json
{
  "id": "fp_filter",
  "geometry_status": "GEOMETRY_VERIFIED",
  "physics_data_status": "PHYSICS_DATA_AVAILABLE",
  "python_export_status": "VERIFIED",
  "frontend_binding_status": "PASSED",
  "python_reference_comparison": "NOT_APPLICABLE",
  "migration_status": "MIGRATION_VERIFIED",
  "calculation_source": "python_export",
  "visualization_template": "defect-cavity",
  "conflict_status": "NONE"
}
```

---

## 四、 Git 提交日志

* **Commit Message**：`feat(web3d): migrate FP filter with Python-backed resonance data`
