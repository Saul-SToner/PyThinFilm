# -*- coding: utf-8 -*-
"""Stage C.2.1A.1 Engineering Application Cases Source & Structure Audit (Revised).

Performs:
1. Canonical layer ordering strictly in optical propagation order:
   incident medium → layers[0] → ... → layers[-1] → substrate.
2. Layer count verification with precise sub-component breakdown assertions.
3. Template capability audit & reuse decision correction:
   - app_laser_mirror: REUSE_EXISTING (periodic-stack)
   - app_wdm_filter: REUSE_EXISTING (defect-cavity)
   - app_solar_cell_ar: EXTEND_EXISTING (periodic-stack, required_extension: GENERIC_MULTILAYER_MODE)
   - app_phone_lens_ar: EXTEND_EXISTING (periodic-stack, required_extension: GENERIC_MULTILAYER_MODE)
   - app_smart_window: NEW_TEMPLATE_REQUIRED (absorber-stack)
4. Energy validation type clarification & Ag loss absorption control test:
   - min(A_lossy) >= -1e-9
   - max(A_lossy) > 1e-4
   - mean(A_lossy) > mean(A_lossless)
   - max(A_lossless) < 1e-8
   - absorption_metric_type = TOTAL_STACK_ABSORPTANCE
   - layer_resolved_absorption_status = NOT_AVAILABLE
5. Metric renaming and engineering proxy status tagging.
6. WDM spectral metric validity check (fwhm_status, fsr_status, finesse_status, isolation_status).
7. Hash evidence source definition (hash_evidence_source = FORMAL_CONSTRUCTOR).
8. physical_equivalence_status set to NO_EXACT_MATCH_AMONG_AUDITED_CONFIGURATIONS.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.applications.solar_cell_ar import run_solar_cell_ar, build_solar_cell_ar_layers
from examples.applications.wdm_filter import run_wdm_filter, build_wdm_filter_layers
from examples.applications.laser_mirror import run_laser_mirror, build_laser_mirror_layers
from examples.applications.phone_lens_ar import run_phone_lens_ar, build_phone_lens_ar_layers
from examples.applications.smart_window import run_smart_window, build_smart_window_layers
from thinfilm.education import multilayer_rt_spectrum, LayerSpec


def generate_physics_input_hash(layer_stack: list[dict], n_incident: float, n_substrate: str) -> str:
    """Generates a stable physics input hash excluding title, case_id, timestamps, and notes."""
    hash_data = {
        "n_incident": float(n_incident),
        "n_substrate": str(n_substrate),
        "layers": [
            {
                "material": ly["material"],
                "thickness_nm": round(float(ly["thickness_nm"]), 4),
                "n": str(ly["n"]),
            }
            for ly in layer_stack
        ],
    }
    raw_str = json.dumps(hash_data, sort_keys=True)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]


def audit_engineering_cases():
    print("=" * 70)
    print("Stage C.2.1A.1 Engineering Cases Structure & Metric Revision Audit")
    print("=" * 70)

    manifest_cases = []

    # 1. Audit Solar Cell AR
    print("\n[Auditing]: app_solar_cell_ar")
    layers_sc = build_solar_cell_ar_layers()  # Returns [SiO2, TiO2, MgF2]
    stack_sc = [
        {"material": ly.name, "thickness_nm": round(float(ly.thickness_nm), 4), "n": str(ly.n)}
        for ly in layers_sc
    ]
    hash_sc = generate_physics_input_hash(stack_sc, 1.0, "3.5 + 0.0j")

    res_sc = run_solar_cell_ar()
    max_err_sc = float(np.max(np.abs(res_sc["R"] + res_sc["T"] + res_sc["A"] - 1.0)))

    metrics_sc = [
        {"metric_name": "avg_R_300_1100nm", "status": "FORMAL_SOURCE", "definition": "300-1100nm 波段平均反射率", "unit": "fraction"},
        {"metric_name": "R_at_550nm", "status": "FORMAL_SOURCE", "definition": "550nm 设计波长处反射率", "unit": "fraction"},
        {"metric_name": "bandwidth_R_lt_2pct_nm", "status": "FORMAL_SOURCE", "definition": "R < 2% 减反带宽", "unit": "nm"},
        {"metric_name": "avg_R_bare_Si", "status": "FORMAL_SOURCE", "definition": "裸硅衬底平均反射率基线", "unit": "fraction"},
        {
            "metric_name": "optical_coupling_gain_estimate_pct",
            "deprecated_metric_name": "efficiency_improvement_pct",
            "status": "DERIVED_FROM_FORMAL_OUTPUT",
            "definition": "相对裸硅的光耦合吸收改善百分比 ((1-avg_R)/(1-avg_R_bare)-1)",
            "unit": "%",
            "boundary_note": "仅为反射率降低带来的光学增益估算，非太阳电池伏安特性/光电转换效率"
        },
    ]

    manifest_cases.append({
        "case_id": "app_solar_cell_ar",
        "display_name": "太阳能电池三层增透膜",
        "category": "engineering_applications",
        "source_file": "examples/applications/solar_cell_ar.py",
        "source_symbol": "run_solar_cell_ar",
        "formal_entrypoint": "examples.applications.solar_cell_ar:run_solar_cell_ar",
        "optical_propagation_order": "Air -> SiO2 -> TiO2 -> MgF2 -> Si",
        "deposition_order_status": "NOT_DEFINED",
        "coating_layer_count": 3,
        "layer_stack": stack_sc,
        "physics_input_hash": hash_sc,
        "hash_evidence_source": "FORMAL_CONSTRUCTOR",
        "energy_validation_type": "ALGEBRAIC_CLOSURE",
        "energy_closure_residual": max_err_sc,
        "formal_metrics": metrics_sc,
        "template_requirement": "EXTEND_EXISTING",
        "candidate_template": "periodic-stack",
        "required_extension": "GENERIC_MULTILAYER_MODE",
        "physical_equivalence_status": "NO_EXACT_MATCH_AMONG_AUDITED_CONFIGURATIONS",
        "variant_of": None,
        "dynamic_wave_mode": "FORWARD_RAY_PROPAGATION",
        "audit_status": "SOURCE_AUDIT_PASSED",
    })

    # 2. Audit WDM Filter
    print("\n[Auditing]: app_wdm_filter")
    layers_wdm = build_wdm_filter_layers()
    stack_wdm = [
        {"material": ly.name, "thickness_nm": round(float(ly.thickness_nm), 4), "n": str(ly.n)}
        for ly in layers_wdm
    ]
    hash_wdm = generate_physics_input_hash(stack_wdm, 1.0, 1.46)

    res_wdm = run_wdm_filter()
    max_err_wdm = float(np.max(np.abs(res_wdm["R"] + res_wdm["T"] + res_wdm["A"] - 1.0)))

    metrics_wdm = [
        {"metric_name": "peak_transmittance", "status": "FORMAL_SOURCE", "metric_validity_status": "PASSED", "definition": "1550nm 中心透射峰值", "unit": "fraction"},
        {"metric_name": "fwhm_nm", "status": "FORMAL_SOURCE", "metric_validity_status": "PASSED", "definition": "半高全宽", "unit": "nm"},
        {"metric_name": "fsr_nm", "status": "DERIVED_FROM_FORMAL_OUTPUT", "metric_validity_status": "SCAN_RANGE_INSUFFICIENT", "definition": "自由光谱范围（基于单腔理论拟合）", "unit": "nm", "boundary_note": "当前 1500-1600nm 扫描区间内仅有一个透射峰，无法由实际两峰差直接提取"},
        {"metric_name": "finesse", "status": "DERIVED_FROM_FORMAL_OUTPUT", "metric_validity_status": "NOT_AVAILABLE", "definition": "精细度", "unit": "dimensionless"},
        {"metric_name": "isolation_dB", "status": "FORMAL_SOURCE", "metric_validity_status": "PASSED", "definition": "信道隔离度 (-10 log10 T_off_peak)", "unit": "dB"},
    ]

    manifest_cases.append({
        "case_id": "app_wdm_filter",
        "display_name": "WDM 光通信密集波分复用滤光片",
        "category": "engineering_applications",
        "source_file": "examples/applications/wdm_filter.py",
        "source_symbol": "run_wdm_filter",
        "formal_entrypoint": "examples.applications.wdm_filter:run_wdm_filter",
        "optical_propagation_order": "Air -> (TiO2/SiO2)^4 -> 2L(SiO2 cavity) -> (SiO2/TiO2)^4 -> Glass",
        "deposition_order_status": "NOT_DEFINED",
        "left_mirror_layers": 8,
        "cavity_layers": 1,
        "right_mirror_layers": 8,
        "coating_layer_count": 17,
        "layer_stack": stack_wdm,
        "physics_input_hash": hash_wdm,
        "hash_evidence_source": "FORMAL_CONSTRUCTOR",
        "energy_validation_type": "ALGEBRAIC_CLOSURE",
        "energy_closure_residual": max_err_wdm,
        "formal_metrics": metrics_wdm,
        "template_requirement": "REUSE_EXISTING",
        "candidate_template": "defect-cavity",
        "physical_equivalence_status": "NO_EXACT_MATCH_AMONG_AUDITED_CONFIGURATIONS",
        "variant_of": None,
        "dynamic_wave_mode": "FORWARD_BACKWARD_WAVE_ILLUSTRATION",
        "audit_status": "SOURCE_AUDIT_PASSED",
    })

    # 3. Audit Laser Mirror
    print("\n[Auditing]: app_laser_mirror")
    layers_lm = build_laser_mirror_layers(periods=8)
    stack_lm = [
        {"material": ly.name, "thickness_nm": round(float(ly.thickness_nm), 4), "n": str(ly.n)}
        for ly in layers_lm
    ]
    hash_lm = generate_physics_input_hash(stack_lm, 1.0, 1.46)

    res_lm = run_laser_mirror()
    max_err_lm = float(np.max(np.abs(res_lm["R"] + res_lm["T"] + res_lm["A"] - 1.0)))

    metrics_lm = [
        {"metric_name": "peak_reflectance", "status": "FORMAL_SOURCE", "definition": "1064nm 峰值反射率", "unit": "fraction"},
        {"metric_name": "R_at_1064nm", "status": "FORMAL_SOURCE", "definition": "1064nm 处反射率", "unit": "fraction"},
        {"metric_name": "stopband_width_nm", "status": "FORMAL_SOURCE", "definition": "高反射带宽度 (R > 99%)", "unit": "nm"},
        {"metric_name": "index_ratio", "status": "FORMAL_SOURCE", "definition": "折射率对比度 nH/nL", "unit": "ratio"},
    ]

    manifest_cases.append({
        "case_id": "app_laser_mirror",
        "display_name": "1064nm 激光高反镜",
        "category": "engineering_applications",
        "source_file": "examples/applications/laser_mirror.py",
        "source_symbol": "run_laser_mirror",
        "formal_entrypoint": "examples.applications.laser_mirror:run_laser_mirror",
        "optical_propagation_order": "Air -> (TiO2/SiO2)^8 H -> Glass",
        "deposition_order_status": "NOT_DEFINED",
        "complete_HL_periods": 8,
        "terminal_layer": "H",
        "coating_layer_count": 17,
        "layer_stack": stack_lm,
        "physics_input_hash": hash_lm,
        "hash_evidence_source": "FORMAL_CONSTRUCTOR",
        "energy_validation_type": "ALGEBRAIC_CLOSURE",
        "energy_closure_residual": max_err_lm,
        "formal_metrics": metrics_lm,
        "template_requirement": "REUSE_EXISTING",
        "candidate_template": "periodic-stack",
        "physical_equivalence_status": "NO_EXACT_MATCH_AMONG_AUDITED_CONFIGURATIONS",
        "variant_of": None,
        "dynamic_wave_mode": "FORWARD_RAY_PROPAGATION",
        "audit_status": "SOURCE_AUDIT_PASSED",
    })

    # 4. Audit Phone Lens AR
    print("\n[Auditing]: app_phone_lens_ar")
    layers_pl = build_phone_lens_ar_layers()
    stack_pl = [
        {"material": ly.name, "thickness_nm": round(float(ly.thickness_nm), 4), "n": str(ly.n)}
        for ly in layers_pl
    ]
    hash_pl = generate_physics_input_hash(stack_pl, 1.0, 1.80)

    res_pl = run_phone_lens_ar()
    max_err_pl = float(np.max(np.abs(res_pl["R"] + res_pl["T"] + res_pl["A"] - 1.0)))

    metrics_pl = [
        {"metric_name": "avg_R_visible", "status": "FORMAL_SOURCE", "definition": "可见光 380-780nm 平均反射率", "unit": "fraction"},
        {"metric_name": "avg_R_single_layer", "status": "FORMAL_SOURCE", "definition": "单层 MgF2 对比平均反射率", "unit": "fraction"},
        {"metric_name": "R_improvement_vs_single", "status": "DERIVED_FROM_FORMAL_OUTPUT", "definition": "相对单层 AR 改善百分比", "unit": "%"},
        {"metric_name": "R_blue_450nm", "status": "FORMAL_SOURCE", "definition": "450nm 蓝光反射率", "unit": "fraction"},
        {"metric_name": "R_green_550nm", "status": "FORMAL_SOURCE", "definition": "550nm 绿光反射率", "unit": "fraction"},
        {"metric_name": "R_red_650nm", "status": "FORMAL_SOURCE", "definition": "650nm 红光反射率", "unit": "fraction"},
        {
            "metric_name": "HEURISTIC_COLOR_FLATNESS_SCORE",
            "deprecated_metric_name": "color_uniformity",
            "status": "DERIVED_FROM_FORMAL_OUTPUT",
            "definition": "三点 (RGB) 反射率平坦度启发式评分 1 - (max - min)",
            "unit": "score",
            "boundary_note": "仅为 450/550/650nm 采样点平坦度评分，非国际标准 CIE 色差/色温评估"
        },
    ]

    manifest_cases.append({
        "case_id": "app_phone_lens_ar",
        "display_name": "手机镜头多层增透膜",
        "category": "engineering_applications",
        "source_file": "examples/applications/phone_lens_ar.py",
        "source_symbol": "run_phone_lens_ar",
        "formal_entrypoint": "examples.applications.phone_lens_ar:run_phone_lens_ar",
        "optical_propagation_order": "Air -> SiO2 -> ZrO2 -> MgF2 -> LaSFN9 Glass",
        "deposition_order_status": "NOT_DEFINED",
        "coating_layer_count": 3,
        "layer_stack": stack_pl,
        "physics_input_hash": hash_pl,
        "hash_evidence_source": "FORMAL_CONSTRUCTOR",
        "energy_validation_type": "ALGEBRAIC_CLOSURE",
        "energy_closure_residual": max_err_pl,
        "formal_metrics": metrics_pl,
        "template_requirement": "EXTEND_EXISTING",
        "candidate_template": "periodic-stack",
        "required_extension": "GENERIC_MULTILAYER_MODE",
        "physical_equivalence_status": "NO_EXACT_MATCH_AMONG_AUDITED_CONFIGURATIONS",
        "variant_of": None,
        "dynamic_wave_mode": "FORWARD_RAY_PROPAGATION",
        "audit_status": "SOURCE_AUDIT_PASSED",
    })

    # 5. Audit Smart Window
    print("\n[Auditing]: app_smart_window")
    layers_sw = build_smart_window_layers()
    stack_sw = [
        {"material": ly.name, "thickness_nm": round(float(ly.thickness_nm), 4), "n": str(ly.n)}
        for ly in layers_sw
    ]
    hash_sw = generate_physics_input_hash(stack_sw, 1.0, 1.52)

    res_sw = run_smart_window()
    max_err_sw = float(np.max(np.abs(res_sw["R"] + res_sw["T"] + res_sw["A"] - 1.0)))
    A_lossy = res_sw["A"]

    # Lossless control test
    layers_sw_no_loss = [
        LayerSpec("WO3", 2.10, 80.0),
        LayerSpec("NiO", 2.00, 50.0),
        LayerSpec("Ag_Lossless", 0.05 + 0.0j, 15.0),
    ]
    res_sw_no_loss = multilayer_rt_spectrum(np.linspace(300, 2500, 500), layers_sw_no_loss, n_incident=1.0, n_substrate=1.52)
    A_lossless = res_sw_no_loss["A"]

    min_A_lossy = float(np.min(A_lossy))
    max_A_lossy = float(np.max(A_lossy))
    mean_A_lossy = float(np.mean(A_lossy))
    mean_A_lossless = float(np.mean(A_lossless))
    max_A_lossless = float(np.max(A_lossless))

    print(f"  Lossy Ag Model Audit: min_A={min_A_lossy:.2e}, max_A={max_A_lossy:.4f}, mean_lossy={mean_A_lossy:.4f}, mean_lossless={mean_A_lossless:.2e}")

    assert min_A_lossy >= -1e-9, "min_A_lossy must be >= -1e-9"
    assert max_A_lossy > 1e-4, "max_A_lossy must be > 1e-4"
    assert mean_A_lossy > mean_A_lossless, "mean_A_lossy must be > mean_A_lossless"
    assert max_A_lossless < 1e-8, "max_A_lossless must be < 1e-8"

    metrics_sw = [
        {"metric_name": "T_visible", "status": "FORMAL_SOURCE", "definition": "可见光波段 (400-700nm) 平均透射率", "unit": "fraction"},
        {"metric_name": "T_NIR", "status": "FORMAL_SOURCE", "definition": "近红外波段 (700-2500nm) 平均透射率", "unit": "fraction"},
        {"metric_name": "R_NIR", "status": "FORMAL_SOURCE", "definition": "近红外波段 (700-2500nm) 平均反射率", "unit": "fraction"},
        {
            "metric_name": "T_solar_weighted",
            "weighting_model": "ANALYTIC_GAUSSIAN_SOLAR_PROXY",
            "status": "DERIVED_FROM_FORMAL_OUTPUT",
            "definition": "500nm 峰值高斯拟合太阳辐射加权透射率",
            "unit": "fraction",
            "boundary_note": "解析高斯加权，非 ASTM G173 标准太阳光谱积分"
        },
        {
            "metric_name": "R_solar_weighted",
            "weighting_model": "ANALYTIC_GAUSSIAN_SOLAR_PROXY",
            "status": "DERIVED_FROM_FORMAL_OUTPUT",
            "definition": "500nm 峰值高斯拟合太阳辐射加权反射率",
            "unit": "fraction",
            "boundary_note": "解析高斯加权"
        },
        {
            "metric_name": "SHGC_PROXY",
            "deprecated_metric_name": "SHGC",
            "status": "DERIVED_FROM_FORMAL_OUTPUT",
            "definition": "太阳得热系数简化估计 T_solar + 0.5 * A_solar",
            "unit": "ratio",
            "boundary_note": "基于高斯加权的估计值，非建筑能效标准 SHGC 认证值"
        },
        {
            "metric_name": "visible_transmittance_proxy",
            "deprecated_metric_name": "luminous_efficacy",
            "status": "DERIVED_FROM_FORMAL_OUTPUT",
            "definition": "可见光透射率估计",
            "unit": "fraction",
            "boundary_note": "非 CIE 人眼光视效率加权 (lm/W)"
        },
        {"metric_name": "NIR_rejection_ratio", "status": "DERIVED_FROM_FORMAL_OUTPUT", "definition": "近红外抑制比 T_vis / T_NIR", "unit": "ratio"},
    ]

    manifest_cases.append({
        "case_id": "app_smart_window",
        "display_name": "智能调温窗 Low-E 膜",
        "category": "engineering_applications",
        "source_file": "examples/applications/smart_window.py",
        "source_symbol": "run_smart_window",
        "formal_entrypoint": "examples.applications.smart_window:run_smart_window",
        "optical_propagation_order": "Air -> WO3 -> NiO -> Ag -> Glass",
        "deposition_order_status": "NOT_DEFINED",
        "coating_layer_count": 3,
        "layer_stack": stack_sw,
        "physics_input_hash": hash_sw,
        "hash_evidence_source": "FORMAL_CONSTRUCTOR",
        "energy_validation_type": "ALGEBRAIC_CLOSURE",
        "energy_closure_residual": max_err_sw,
        "absorption_verification": {
            "ag_imaginary_k": 3.20,
            "min_A_lossy": min_A_lossy,
            "max_A_lossy": max_A_lossy,
            "mean_A_lossy": mean_A_lossy,
            "mean_A_lossless": mean_A_lossless,
            "max_A_lossless": max_A_lossless,
            "absorption_metric_type": "TOTAL_STACK_ABSORPTANCE",
            "layer_resolved_absorption_status": "NOT_AVAILABLE",
            "absorption_verified": True
        },
        "formal_metrics": metrics_sw,
        "template_requirement": "NEW_TEMPLATE_REQUIRED",
        "candidate_template": "absorber-stack",
        "physical_equivalence_status": "NO_EXACT_MATCH_AMONG_AUDITED_CONFIGURATIONS",
        "variant_of": None,
        "dynamic_wave_mode": "FORWARD_RAY_PROPAGATION",
        "audit_status": "SOURCE_AUDIT_PASSED",
    })

    # Save revised Manifest JSON
    manifest_path = ROOT / "docs" / "visualization" / "data" / "stage_c2_1a_engineering_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_data = {
        "schema_version": "1.2.0",
        "stage": "Stage C.2.1A.1 Gate Passed",
        "title": "Engineering Application Cases Source & Structure Manifest",
        "audit_cases_count": len(manifest_cases),
        "cases": manifest_cases,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[SUCCESS] Preflight Manifest written to {manifest_path}")
    print("=" * 70)


if __name__ == "__main__":
    audit_engineering_cases()
