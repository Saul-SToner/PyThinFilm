# 截图与证据材料清单 (最终小修版)

本文档列出了《基于 Python 的薄膜光学仿真、设计与教学平台作品说明书》中所需补充的全部截图与证据材料，并明确了它们在文档中的对应插入位置以及自动生成的图片路径。

所有截图均已保存在仓库相对路径 `docs/figures/` 中。

---

## 一、单元测试与冒烟自检验证日志证据

### 1. 冒烟自检测试日志 (docs/evidence/smoke_test_log.txt)
* **执行命令**：`py smoke_test.py`
* **自检状态**：全部校验通过，退出代码为 0，自检输出日志已保存到 `docs/evidence/smoke_test_log.txt`。

### 2. Pytest 单元测试日志 (docs/evidence/pytest_log.txt)
* **执行命令**：`py -m pytest tests/ -v`
* **自检状态**：全部 270 个单元用例执行成功，运行日志已保存到 `docs/evidence/pytest_log.txt`。

---

## 二、作品说明书图示插入计划表

以下是准备插入 Word 排版时，各截图占位符与已生成/整理图片文件的映射表：

| 图号 | 图片文件 | 原始输出来源 | 生成脚本 | 是否代码生成 | 是否需要人工截图 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **图 2-1** | `docs/figures/fig_2_1_tmm_flow.png` | `docs/figures/fig_2_1_tmm_flow.mmd` | N/A (Mermaid 编译生成) | 否 (流程示意图) | 否 |
| **图 2-2** | `docs/figures/fig_2_2_nk_flow.png` | `docs/figures/fig_2_2_nk_flow.mmd` | N/A (Mermaid 编译生成) | 否 (流程示意图) | 否 |
| **图 2-3** | `docs/figures/fig_2_3_physics_mapping.png` | `docs/figures/fig_2_3_physics_mapping.mmd` | N/A (Mermaid 编译生成) | 否 (流程示意图) | 否 |
| **图 3-1** | `docs/figures/fig_3_1_repo_structure.png` | 项目工作区目录树 | N/A (本地仓库目录) | 否 | 是 (手工截图) |
| **图 3-2** | `docs/figures/fig_3_2_dataflow.png` | `docs/figures/fig_3_2_dataflow.mmd` | N/A (Mermaid 编译生成) | 否 (流程示意图) | 否 |
| **图 3-3** | `docs/figures/fig_3_3_pytest_270_passed.png` | pytest 终端运行汇总面板 | `py -m pytest tests/ -v` | 否 | 是 (手工截图) |
| **图 3-4** | `docs/figures/fig_3_4_smoke_test_passed.png` | smoke_test 终端自检通过面板 | `py smoke_test.py` | 否 | 是 (手工截图) |
| **图 3-5** | `docs/figures/fig_3_5_test_flow.png` | `docs/figures/fig_3_5_test_flow.mmd` | N/A (Mermaid 编译生成) | 否 (流程示意图) | 否 |
| **图 3-6** | `docs/figures/fig_3_6_physical_module_overview.png` | `docs/figures/fig_3_6_physical_module_overview.mmd` | N/A (Mermaid 编译生成) | 否 (流程示意图) | 否 |
| **图 4-1** | `docs/figures/fig_4_1_single_ar.png` | `~/thinfilm_outputs/teaching_case_single_ar_main.png` | `run_teaching_demo.py --case single_ar` | 是 | 否 |
| **图 4-2** | `docs/figures/fig_4_2_high_reflector.png` | `~/thinfilm_outputs/teaching_case_high_reflector_main.png` | `run_teaching_demo.py --case high_reflector` | 是 | 否 |
| **图 4-3** | `docs/figures/fig_4_3_fp_filter.png` | `~/thinfilm_outputs/teaching_case_fp_filter_main.png` | `run_teaching_demo.py --case fp_filter` | 是 | 否 |
| **图 4-4** | `docs/figures/fig_4_4_te_tm_compare.png` | `~/thinfilm_outputs/teaching_compare_te_tm_compare.png` | `run_teaching_demo.py --report` | 是 | 否 |
| **图 4-6** | `docs/figures/fig_4_6_material_library.png` | `~/thinfilm_outputs/real_material_library_demo_cn_overview.png` | `run_material_library_demo.py` | 是 | 否 |
| **图 4-7** | `docs/figures/fig_4_7_si_real_nk_compare.png` | `~/thinfilm_outputs/real_material_library_demo_cn_single_ar_real_nk_single_ar_real_nk_main.png` | `run_material_library_demo.py` | 是 | 否 |
| **图 4-8** | `docs/figures/fig_4_8_tio2_real_nk_bragg.png` | `~/thinfilm_outputs/real_material_library_demo_bragg_reflector_real_nk_bragg_reflector_real_nk_main.png` | `run_material_library_demo.py` | 是 | 否 |
| **图 4-9** | `docs/figures/fig_4_9_solar_cell_ar.png` | `outputs/solar_cell_ar/solar_cell_ar_spectrum.html` | `examples/applications/solar_cell_ar.py` | 是 | 否 |
| **图 4-10**| `docs/figures/fig_4_10_wdm_filter.png` | `outputs/wdm_filter/wdm_filter_spectrum.html` | `examples/applications/wdm_filter.py` | 是 | 否 |
| **图 4-11**| `docs/figures/fig_4_11_laser_mirror.png` | `outputs/laser_mirror/laser_mirror_spectrum.html` | `examples/applications/laser_mirror.py` | 是 | 否 |
| **图 4-12**| `docs/figures/fig_4_12_phone_lens_ar.png` | `outputs/phone_lens_ar/phone_lens_ar_comparison.html` | `examples/applications/phone_lens_ar.py` | 是 | 否 |
| **图 4-13**| `docs/figures/fig_4_13_smart_window.png` | `outputs/smart_window/smart_window_spectrum.html` | `examples/applications/smart_window.py` | 是 | 否 |
| **图 4-14**| `docs/figures/fig_4_14_tamm_phase.png` | `~/thinfilm_outputs/tamm_1d_phase_dspacer13_dW40_220_corrected_screen_cn.png` | `run_case.py --group tamm --case reflection_phase_screen` | 是 | 否 |
| **图 4-15**| `docs/figures/fig_4_15_pdrc_spectrum.png` | `~/thinfilm_outputs/pdrc_real_materials_valid_spectrum_cn.png` | `run_case.py --group pdrc --case cooling_bundle` | 是 | 否 |
| **图 4-16**| `docs/figures/fig_4_16_emt_polarization.png` | `~/thinfilm_outputs/guided_grating_demo_minimal_branch_case_RTA.png` | `run_guided_grating_demo.py` | 是 | 否 |
| **图 4-17（已退役，不进入正文）** | `docs/figures/fig_4_17_comsol_csv_compare.png` | 占位近似图，不是可追溯 COMSOL 数据 | 待提供真实外部 CSV 后再生成“同轴光谱 + 残差”图 | 否 | 否 |
| **图 10-1**| `docs/figures/fig_3_3_pytest_270_passed.png` | 对应图 3-3 的完整 pytest 单元测试终端大图 | `py -m pytest tests/ -v` | 否 | 是 (手工截图) |

---

已同步在工作区目录完成归档。相关测试日志、原始输出数据与图示文件分别保存在 `docs/evidence/` 和 `docs/figures/`，可用于后续作品说明书排版与材料核查。
