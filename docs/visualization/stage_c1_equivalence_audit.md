# PyThinFilm 全案例 3D 动态可视化 — Stage C.1.1 案例物理等价关系与去重审计报告

本报告记录对 **Stage C.1 首批 6 个教学案例中物理等价重复案例** 的数值对比与注册表归类审计结果。

---

## 一、 物理等价组数值比对 (Max Abs Diff $R, T, A = 0.0$)

经过对 $400\sim750\text{nm}$ 全光谱 TE/TM 光谱数组与膜层结构的点对点比对：

1. **第一组等价关系 (`dbr_7layer_hlh`)**：
   - 主案例：`bragg_reflector` (Air / (HL)^3 H 7层 / Glass)
   - 变体/教学别名：`high_reflector` (Air / (HL)^3 H 7层 / Glass)
   - 光谱最大绝对残差：$\max|R_{\text{bragg}} - R_{\text{high}}| = \mathbf{0.0}$
   - 策略：`SHARED_PHYSICS_DISTINCT_PEDAGOGY` (共享物理数据，保留独立教学入口)

2. **第二组等价关系 (`fp_13layer_defect_cavity`)**：
   - 主案例：`fp_filter` (Air / (HL)^3 C (LH)^3 13层 / Glass)
   - 变体/教学别名：`fp_single_halfwave` (Air / (HL)^3 C (LH)^3 13层 / Glass)
   - 光谱最大绝对残差：$\max|R_{\text{fp}} - R_{\text{halfwave}}| = \mathbf{0.0}$
   - 策略：`SHARED_PHYSICS_DISTINCT_PEDAGOGY` (共享物理数据，保留独立教学入口)

---

## 二、 修正后的注册表统计口径

```text
- registry_entry_count:                   41 (注册表条目总数)
- visualization_entry_count:              40 (3D 可视化入口数)
- runner_entry_count:                     1  (guided_grating_demo)
- unique_physical_configuration_count:    38 (独立物理模型配置数 = 40 - 2 重复变体)
- migrated_verified_entry_count:          7  (single_ar, bragg_reflector, fp_filter,
                                              quarter_wave_single_layer, half_wave_single_layer,
                                              quarter_wave_stack, narrowband_filter)
- migrated_candidate_entry_count:         1  (tamm_phase_bundle - PHASE_MATCHED_LEAKY_CANDIDATE)
- result_reuse_entry_count:               2  (high_reflector, fp_single_halfwave)
- total_active_visualization_entries:     10 (已迁移可加载 3D 页面入口)
- remaining_unique_physical_configurations: 30 (待迁移独立物理模型数)
```
