"""Python backend for the teaching-oriented thin-film design report.

This module reproduces the *forward* simulation route in the report:
- single / double / triple anti-reflection coatings
- high-reflection quarter-wave stacks
- single-half-wave / double-half-wave Fabry-Perot filters
- neutral beam splitter stacks

The implementation is based on a standard characteristic-matrix method
rather than COMSOL, which makes it suitable as a lightweight Python
backend for an APP.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

import matplotlib.pyplot as plt
import numpy as np

from .materials import (
    canonical_material_name,
    common_wavelength_window_um,
    material_complex_index,
)
from .paths import OUTPUT_DIR, output_file
from .plot_logic import focused_power_limits, infer_rta_focus, padded_numeric_limits, rta_trace_styles
from .plotting import MUTED, save_publication_figure
from .figure_audit import audit_rta_data, build_figure_audit, write_figure_audit
from ._shared import (
    MAIN_RED,
    TARGET_GREEN,
    TRANS_BLUE,
    ABS_GOLD,
    GRID_COLOR,
    TEXT_DARK,
    PANEL_BG,
    apply_font_defaults,
)

apply_font_defaults()


@dataclass(frozen=True)
class LayerSpec:
    name: str
    n: complex
    thickness_nm: float


from functools import lru_cache


@lru_cache(maxsize=1)
def _get_report_chapter2_cases() -> Dict[str, Dict[str, Any]]:
    return {
    "quarter_wave_single_layer": {
        "title_cn": "1/4波长单层减反射膜",
        "title_en": "Quarter-Wave Single Layer",
        "design_type": "quarter_wave_single_layer",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.5215,
            "n_low": 1.3785,
        },
    },
    "half_wave_single_layer": {
        "title_cn": "1/2波长单层相位膜(虚设层)",
        "title_en": "Half-Wave Single Layer",
        "design_type": "half_wave_single_layer",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.38,
        },
    },
    "single_ar": {
        "title_cn": "单层减反射膜(任意参数)",
        "title_en": "Single-Layer Anti-Reflection",
        "design_type": "single_ar",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.2329,
        },
    },
    "porous_sio2_layer": {
        "title_cn": "多孔二氧化硅减反结构(低折射率多孔介质单层增透膜)",
        "title_en": "Porous Silica Layer",
        "design_type": "single_ar",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.32,
        },
    },
    "porous_double_ar": {
        "title_cn": "多孔双层减反膜(多孔介质双层增透膜)",
        "title_en": "Porous Silica Double-Layer AR",
        "design_type": "porous_double_ar",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.5215,
            "n_porous": 1.18,
            "n_high": 1.45,
        },
    },
    "moth_eye_effective_gradient": {
        "title_cn": "蛾眼等效渐变层减反膜",
        "title_en": "Moth-Eye Effective Gradient",
        "design_type": "moth_eye_effective_gradient",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.5215,
            "n_top": 1.10,
            "n_bottom": 1.50,
            "d_total_nm": 300.0,
            "num_gradient_layers": 5,
            "gradient_type": "linear",
            "layer_indices": [1.10, 1.20, 1.30, 1.40, 1.50],
            "layer_thickness_nm": [60.0, 60.0, 60.0, 60.0, 60.0],
        },
    },
    "double_ar": {
        "title_cn": "双层减反射膜(任意参数)",
        "title_en": "Double-Layer Anti-Reflection",
        "design_type": "double_ar",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.45,
            "n_high": 2.10,
        },
    },
    "quarter_wave_double_layer": {
        "title_cn": "四分之一波长双层减反膜(V形增透膜)",
        "title_en": "Quarter-Wave Double Layer",
        "design_type": "quarter_wave_double_layer",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.38,
            "n_high": 2.0,
        },
    },
    "triple_ar": {
        "title_cn": "三层渐变折射率减反膜",
        "title_en": "Triple-Layer Anti-Reflection",
        "design_type": "triple_ar",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.38,
            "n_mid": 1.60,
            "n_high_2": 1.88,
        },
    },
    "high_reflector": {
        "title_cn": "高反射膜",
        "title_en": "High-Reflection Coating",
        "design_type": "high_reflector",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.5215,
            "n_low": 1.45,
            "n_high_2": 2.10,
            "periods": 6,
        },
    },
    "quarter_wave_stack": {
        "title_cn": "1/4波长QW膜堆",
        "title_en": "Quarter-Wave Stack",
        "design_type": "quarter_wave_stack",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.5215,
            "n_low": 1.45,
            "n_high_2": 2.10,
            "periods": 6,
        },
    },
    "bragg_reflector": {
        "title_cn": "布拉格反射镜",
        "title_en": "Bragg Reflector",
        "design_type": "bragg_reflector",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.5215,
            "n_low": 1.45,
            "n_high_2": 2.10,
            "periods": 6,
        },
    },
    "fp_single_halfwave": {
        "title_cn": "单半波型 F-P 滤光片",
        "title_en": "Single-Half-Wave F-P Filter",
        "design_type": "fp_single_halfwave",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.38,
            "n_high_2": 2.15,
            "periods": 3,
            "fp_spacer_kind": "L",
        },
    },
    "fp_filter": {
        "title_cn": "F-P滤光片",
        "title_en": "Fabry-Perot Filter",
        "design_type": "fp_filter",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.0,
            "n_low": 1.45,
            "n_high_2": 2.10,
            "periods": 4,
            "fp_spacer_kind": "L",
        },
    },
    "fp_double_halfwave": {
        "title_cn": "双半波型 F-P 滤光片",
        "title_en": "Double-Half-Wave F-P Filter",
        "design_type": "fp_double_halfwave",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.38,
            "n_high_2": 2.15,
            "periods": 2,
        },
    },
    "narrowband_filter": {
        "summary_cn": "更高阶的滤波案例，用于展示更窄的透射峰和更强的选择性。",
        "summary_en": "A higher-level filtering case showing narrower transmission peaks and stronger selectivity.",
        "title_cn": "窄带滤光片",
        "title_en": "Narrowband Filter",
        "design_type": "narrowband_filter",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.0,
            "n_low": 1.45,
            "n_high_2": 2.10,
            "periods": 5,
            "fp_spacer_kind": "L",
        },
        "headline_cn": "窄带滤光片",
        "headline_en": "Narrowband Filter",
        "card_tag_cn": "高级滤波",
        "card_tag_en": "Advanced Filter",
        "main_curve": "T",
    },
    "rugate_filter": {
        "summary_cn": "采用连续折射率调制近似的皱褶滤光片，用于展示渐变周期结构的反射带形成。",
        "summary_en": "A rugate filter approximated by continuous index modulation, showing stop-band formation in graded periodic structures.",
        "title_cn": "Rugate(褶皱)渐变折射率滤光片",
        "title_en": "Rugate Filter",
        "design_type": "rugate_filter",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.38,
            "n_high_2": 2.10,
            "periods": 8,
            "total_layers": 80,
        },
        "headline_cn": "Rugate(褶皱)渐变折射率滤光片",
        "headline_en": "Rugate Filter",
        "card_tag_cn": "高级扩展",
        "card_tag_en": "Advanced Extension",
        "main_curve": "R",
    },
    "neutral_beamsplitter": {
        "title_cn": "中性分束薄膜",
        "title_en": "Neutral Beam Splitter",
        "design_type": "neutral_beamsplitter",
        "default_params": {
            "theta_deg": 0.0,
            "pol": "p",
            "lambda0_nm": 550.0,
            "n_incident": 1.0,
            "n_substrate": 1.52,
            "n_low": 1.38,
            "n_high_2": 2.35,
            "beamsplitter_front_halfwave_low": False,
        },
    },
}


REPORT_CHAPTER2_CASES = _get_report_chapter2_cases()


REPORT_COMPARISON_FIGURES: Dict[str, Dict[str, Any]] = {
    "quarter_wave_stack_periods": {
        "title_cn": "QW膜堆不同周期数对比",
        "title_en": "Quarter-Wave Stack | Different Periods",
        "ylabel": "R",
    },
    "high_reflector_periods": {
        "title_cn": "高反膜不同周期数对比",
        "title_en": "High-Reflection Coating | Different Periods",
        "ylabel": "R",
    },
    "fp_single_periods": {
        "title_cn": "单半波 F-P 不同周期数对比",
        "title_en": "Single-Half-Wave F-P | Different Periods",
        "ylabel": "T",
    },
    "narrowband_filter_periods": {
        "title_cn": "窄带滤光片不同周期数对比",
        "title_en": "Narrowband Filter | Different Periods",
        "ylabel": "T",
    },
    "fp_double_angles": {
        "title_cn": "双半波 F-P 不同入射角对比",
        "title_en": "Double-Half-Wave F-P | Different Angles",
        "ylabel": "T",
    },
    "beamsplitter_lambda0": {
        "title_cn": "中性分束膜不同中心波长对比",
        "title_en": "Neutral Beam Splitter | Different Center Wavelengths",
        "ylabel": "R",
    },
    "te_tm_compare": {
        "title_cn": "单层减反膜斜入射 TE/TM 偏振对比",
        "title_en": "Single-Layer AR | TE vs TM at 45 deg",
        "ylabel": "R",
    },
}

REPORT_COMPARISON_UI_META: Dict[str, Dict[str, Any]] = {
    "quarter_wave_stack_periods": {
        "headline_cn": "QW膜堆周期对比",
        "headline_en": "QW Stack Period Sweep",
        "card_tag_cn": "参数对比",
        "card_tag_en": "Parameter Sweep",
        "summary_cn": "比较QW膜堆在不同周期数下的高反射带变化。",
        "summary_en": "Compare the high-reflection band of quarter-wave stacks under different period counts.",
        "series_count": 3,
        "sweep_parameter": "periods",
        "sweep_label_cn": "周期数",
        "sweep_label_en": "Periods",
        "related_case_ids": ["quarter_wave_stack", "bragg_reflector"],
    },
    "high_reflector_periods": {
        "headline_cn": "高反膜周期对比",
        "headline_en": "Reflector Period Sweep",
        "card_tag_cn": "参数对比",
        "card_tag_en": "Parameter Sweep",
        "summary_cn": "比较高反膜周期数变化对反射峰高度与带宽的影响。",
        "summary_en": "Compare how period count changes the reflector peak height and bandwidth.",
        "series_count": 3,
        "sweep_parameter": "periods",
        "sweep_label_cn": "周期数",
        "sweep_label_en": "Periods",
        "related_case_ids": ["high_reflector"],
    },
    "fp_single_periods": {
        "headline_cn": "单半波 F-P 周期对比",
        "headline_en": "Single-Half-Wave F-P Sweep",
        "card_tag_cn": "参数对比",
        "card_tag_en": "Parameter Sweep",
        "summary_cn": "比较单半波 F-P 在不同周期数下的透射峰差异。",
        "summary_en": "Compare single-half-wave F-P transmission peaks under different period counts.",
        "series_count": 3,
        "sweep_parameter": "periods",
        "sweep_label_cn": "周期数",
        "sweep_label_en": "Periods",
        "related_case_ids": ["fp_single_halfwave"],
    },
    "narrowband_filter_periods": {
        "headline_cn": "窄带滤光片周期对比",
        "headline_en": "Narrowband Filter Period Sweep",
        "card_tag_cn": "参数对比",
        "card_tag_en": "Parameter Sweep",
        "summary_cn": "比较窄带滤光片在不同周期数下的通带宽度和选择性变化。",
        "summary_en": "Compare how period count changes the passband width and selectivity of the narrowband filter.",
        "series_count": 3,
        "sweep_parameter": "periods",
        "sweep_label_cn": "周期数",
        "sweep_label_en": "Periods",
        "related_case_ids": ["narrowband_filter"],
    },
    "fp_double_angles": {
        "headline_cn": "双半波 F-P 角度对比",
        "headline_en": "Double-Half-Wave F-P Angle Sweep",
        "card_tag_cn": "角度敏感",
        "card_tag_en": "Angle Sweep",
        "summary_cn": "比较双半波 F-P 在不同入射角下的谱线漂移。",
        "summary_en": "Compare spectral shifts of the double-half-wave F-P under different incident angles.",
        "series_count": 3,
        "sweep_parameter": "theta_deg",
        "sweep_label_cn": "入射角",
        "sweep_label_en": "Incident Angle",
        "related_case_ids": ["fp_double_halfwave"],
    },
    "beamsplitter_lambda0": {
        "headline_cn": "分束膜中心波长对比",
        "headline_en": "Beam-Splitter Center-Wavelength Sweep",
        "card_tag_cn": "设计对比",
        "card_tag_en": "Design Sweep",
        "summary_cn": "比较不同设计中心波长下的中性分束膜反射谱。",
        "summary_en": "Compare beam-splitter reflectance under different design center wavelengths.",
        "series_count": 3,
        "sweep_parameter": "lambda0_nm",
        "sweep_label_cn": "中心波长",
        "sweep_label_en": "Center Wavelength",
        "related_case_ids": ["neutral_beamsplitter"],
    },
    "te_tm_compare": {
        "headline_cn": "单层减反膜偏振对比",
        "headline_en": "Single-Layer AR Polarization Sweep",
        "card_tag_cn": "参数对比",
        "card_tag_en": "Parameter Sweep",
        "summary_cn": "比较单层 MgF2 减反膜在 45° 斜入射下 TE 和 TM 偏振反射率的变化特征。",
        "summary_en": "Compare TE and TM polarizations of a single-layer AR coating at 45 deg incidence.",
        "series_count": 2,
        "sweep_parameter": "pol",
        "sweep_label_cn": "偏振极化",
        "sweep_label_en": "Polarization",
        "related_case_ids": ["single_ar"],
    },
}

REPORT_COMPARISON_DISPLAY_ORDER: List[str] = [
    "quarter_wave_stack_periods",
    "high_reflector_periods",
    "fp_single_periods",
    "narrowband_filter_periods",
    "fp_double_angles",
    "beamsplitter_lambda0",
]

REPORT_COMPARISON_GROUPS: List[Dict[str, Any]] = [
    {
        "group_id": "stack_parameter_sweeps",
        "title_cn": "膜系参数扫描",
        "title_en": "Stack Parameter Sweeps",
        "figure_ids": ["quarter_wave_stack_periods", "high_reflector_periods", "fp_single_periods", "narrowband_filter_periods", "beamsplitter_lambda0"],
    },
    {
        "group_id": "angle_sensitivity",
        "title_cn": "角度敏感性",
        "title_en": "Angle Sensitivity",
        "figure_ids": ["fp_double_angles"],
    },
]

REPORT_MAIN_BRANCH_SECTIONS: List[Dict[str, Any]] = [
    {
        "section_id": "uniform_layers",
        "title_cn": "基础均匀膜层",
        "title_en": "Uniform Layer Basics",
        "summary_cn": "从1/4波长与1/2波长单层出发，逐步建立光学厚度与相位干涉的基础认识。",
        "summary_en": "Start from quarter-wave and half-wave single layers to build intuition for optical thickness and phase interference.",
        "case_ids": ["quarter_wave_single_layer", "half_wave_single_layer", "single_ar", "porous_sio2_layer"],
    },
    {
        "section_id": "ar_coatings",
        "title_cn": "减反射膜",
        "title_en": "Anti-Reflection Coatings",
        "summary_cn": "从单层到三层，逐步展示减反膜带宽与匹配能力的提升。",
        "summary_en": "From single-layer to triple-layer designs, showing how AR bandwidth and matching improve.",
        "case_ids": ["porous_sio2_layer", "porous_double_ar", "moth_eye_effective_gradient", "double_ar", "quarter_wave_double_layer", "triple_ar"],
    },
    {
        "section_id": "periodic_stacks",
        "title_cn": "QW膜堆与布拉格反射镜",
        "title_en": "QW Stacks and Bragg Reflectors",
        "summary_cn": "展示周期QW膜堆与布拉格高反射镜在反射带形成上的物理一致性。",
        "summary_en": "Show the shared physics of periodic quarter-wave stacks and Bragg reflectors in forming high-reflection bands.",
        "case_ids": ["quarter_wave_stack", "bragg_reflector", "high_reflector"],
    },
    {
        "section_id": "reflector_filters",
        "title_cn": "高反膜与 F-P 滤光片",
        "title_en": "Reflectors and F-P Filters",
        "summary_cn": "展示高反堆栈与 F-P 腔结构在反射和透射选择性上的差异。",
        "summary_en": "Show the contrast between reflector stacks and F-P cavities in reflectance and transmittance selectivity.",
        "case_ids": ["quarter_wave_stack", "bragg_reflector", "high_reflector", "fp_single_halfwave", "fp_filter", "fp_double_halfwave", "narrowband_filter", "rugate_filter"],
    },
    {
        "section_id": "beam_splitter",
        "title_cn": "分束膜",
        "title_en": "Beam Splitter",
        "summary_cn": "展示接近均衡分束的膜系设计与谱线变化。",
        "summary_en": "Show near-balanced beam-splitting designs and their spectral behavior.",
        "case_ids": ["neutral_beamsplitter"],
    },
]

REPORT_PARAM_SCHEMA: Dict[str, Dict[str, Any]] = {
    "theta_deg": {
        "label_cn": "入射角",
        "label_en": "Incident Angle",
        "type": "float",
        "unit": "deg",
        "widget": "number",
        "group": "general",
        "min": 0.0,
        "max": 80.0,
        "step": 1.0,
        "recommended": 0.0,
        "required": True,
        "help_cn": "默认用于法向入射或角度扫描案例。",
        "help_en": "Used for normal incidence defaults or angle-sweep cases.",
    },
    "pol": {
        "label_cn": "偏振",
        "label_en": "Polarization",
        "type": "enum",
        "choices": ["s", "p"],
        "widget": "select",
        "group": "general",
        "recommended": "p",
        "required": True,
        "help_cn": "教学案例当前默认使用线偏振中的 p 偏振。",
        "help_en": "Current teaching presets use p polarization by default.",
    },
    "lambda0_nm": {
        "label_cn": "中心波长",
        "label_en": "Center Wavelength",
        "type": "float",
        "unit": "nm",
        "widget": "number",
        "group": "general",
        "min": 400.0,
        "max": 750.0,
        "step": 10.0,
        "recommended": 550.0,
        "required": True,
        "help_cn": "用于定义设计中心波长或标称工作波长。",
        "help_en": "Defines the design center wavelength or nominal working wavelength.",
    },
    "n_incident": {
        "label_cn": "入射介质折射率",
        "label_en": "Incident Index",
        "type": "float",
        "widget": "number",
        "group": "materials",
        "min": 1.0,
        "max": 2.0,
        "step": 0.01,
        "recommended": 1.0,
        "required": True,
        "help_cn": "默认空气入射，可按需要改为其它介质。",
        "help_en": "Defaults to air incidence and can be changed to other media.",
    },
    "n_substrate": {
        "label_cn": "基底折射率",
        "label_en": "Substrate Index",
        "type": "float",
        "widget": "number",
        "group": "materials",
        "min": 1.3,
        "max": 2.2,
        "step": 0.01,
        "recommended": 1.52,
        "required": True,
        "help_cn": "薄膜下方基底介质的折射率。",
        "help_en": "Refractive index of the substrate beneath the coating stack.",
    },
    "n_low": {
        "label_cn": "低折射率",
        "label_en": "Low Index",
        "type": "float",
        "widget": "number",
        "group": "materials",
        "min": 1.2,
        "max": 1.6,
        "step": 0.01,
        "recommended": 1.38,
        "required": True,
        "help_cn": "低折层材料折射率。",
        "help_en": "Refractive index of the low-index layer.",
    },
    "n_porous": {
        "label_cn": "多孔层折射率",
        "label_en": "Porous Layer Index",
        "type": "float",
        "widget": "number",
        "group": "materials",
        "min": 1.05,
        "max": 1.35,
        "step": 0.01,
        "recommended": 1.18,
        "required": True,
        "help_cn": "多孔二氧化硅等效低折射率层的折射率。",
        "help_en": "Effective refractive index of the porous silica layer.",
    },
    "n_mid": {
        "label_cn": "中间折射率",
        "label_en": "Middle Index",
        "type": "float",
        "widget": "number",
        "group": "materials",
        "min": 1.4,
        "max": 1.8,
        "step": 0.01,
        "recommended": 1.60,
        "required": True,
        "help_cn": "三层减反膜中的中间折射率层。",
        "help_en": "Middle-index layer used in the triple-layer AR design.",
    },
    "n_high": {
        "label_cn": "高折射率",
        "label_en": "High Index",
        "type": "float",
        "widget": "number",
        "group": "materials",
        "min": 1.8,
        "max": 2.4,
        "step": 0.01,
        "recommended": 2.0,
        "required": True,
        "help_cn": "双层减反膜中的高折射率层。",
        "help_en": "High-index layer used in the double-layer AR design.",
    },
    "n_high_2": {
        "label_cn": "高折射率",
        "label_en": "High Index",
        "type": "float",
        "widget": "number",
        "group": "materials",
        "min": 1.8,
        "max": 2.5,
        "step": 0.01,
        "recommended": 2.15,
        "required": True,
        "help_cn": "高反膜、F-P 和分束膜中使用的高折射率层。",
        "help_en": "High-index layer used in reflector, F-P, and beam-splitter designs.",
    },
    "periods": {
        "label_cn": "周期数",
        "label_en": "Periods",
        "type": "int",
        "widget": "slider",
        "group": "structure",
        "min": 1,
        "max": 8,
        "step": 1,
        "recommended": 3,
        "required": True,
        "help_cn": "高反堆栈或 F-P 反射镜的重复周期数。",
        "help_en": "Repeat count for reflector stacks or F-P mirrors.",
    },
    "fp_spacer_kind": {
        "label_cn": "腔层类型",
        "label_en": "Spacer Kind",
        "type": "enum",
        "choices": ["L", "H"],
        "widget": "segmented",
        "group": "structure",
        "recommended": "L",
        "required": True,
        "help_cn": "选择腔层使用低折层还是高折层。",
        "help_en": "Choose whether the cavity spacer uses the low- or high-index layer.",
    },
    "beamsplitter_front_halfwave_low": {
        "label_cn": "前置半波低折层",
        "label_en": "Front Half-Wave Low Layer",
        "type": "bool",
        "widget": "switch",
        "group": "structure",
        "recommended": False,
        "required": True,
        "help_cn": "决定分束膜前端是否插入半波低折层。",
        "help_en": "Toggle whether a front half-wave low-index layer is inserted.",
    },
}

REPORT_CONTROL_GROUP_META: Dict[str, Dict[str, str]] = {
    "general": {
        "title_cn": "通用参数",
        "title_en": "General Parameters",
    },
    "materials": {
        "title_cn": "材料参数",
        "title_en": "Material Parameters",
    },
    "structure": {
        "title_cn": "结构参数",
        "title_en": "Structure Parameters",
    },
}

REPORT_CASE_UI_META: Dict[str, Dict[str, str]] = {
    "quarter_wave_single_layer": {
        "summary_cn": "用于展示单层1/4波长光学厚度的相消干涉条件。",
        "summary_en": "Shows the destructive-interference condition of a single quarter-wave layer.",
        "headline_cn": "1/4波长单层",
        "headline_en": "Quarter-Wave Layer",
        "card_tag_cn": "基础相位",
        "card_tag_en": "Phase Basics",
        "main_curve": "R",
    },
    "half_wave_single_layer": {
        "summary_cn": "用于对比单层1/2波长与1/4波长在中心波长处的相位差异。",
        "summary_en": "Contrasts half-wave and quarter-wave single-layer phase behavior at the design wavelength.",
        "headline_cn": "1/2波长单层",
        "headline_en": "Half-Wave Layer",
        "card_tag_cn": "相位对比",
        "card_tag_en": "Phase Contrast",
        "main_curve": "R",
    },
    "single_ar": {
        "summary_cn": "单层四分之一波厚减反膜，用于展示中心波长处反射率压低的基本原理。",
        "summary_en": "Single quarter-wave AR coating showing reflection suppression at the design wavelength.",
        "headline_cn": "单层减反基础",
        "headline_en": "Single-Layer AR Basics",
        "card_tag_cn": "基础案例",
        "card_tag_en": "Core Case",
        "main_curve": "R",
    },
    "porous_sio2_layer": {
        "summary_cn": "采用等效低折射率近似的多孔二氧化硅膜层，用于展示多孔材料作为减反匹配层的基本行为。",
        "summary_en": "A porous silica layer treated as an effective low-index coating, showing its anti-reflection matching behavior.",
        "headline_cn": "多孔二氧化硅减反层",
        "headline_en": "Porous Silica AR Layer",
        "card_tag_cn": "多孔材料",
        "card_tag_en": "Porous Material",
        "main_curve": "R",
    },
    "porous_double_ar": {
        "summary_cn": "由多孔低折层与致密匹配层组成的双层减反结构，用于展示多孔材料在双层匹配中的低反优势。",
        "summary_en": "A double-layer anti-reflection structure combining a porous low-index layer with a dense matching layer.",
        "headline_cn": "多孔双层减反",
        "headline_en": "Porous Double-Layer AR",
        "card_tag_cn": "多孔双层",
        "card_tag_en": "Porous Double",
        "main_curve": "R",
    },
    "moth_eye_effective_gradient": {
        "summary_cn": "采用离散等效渐变折射率层近似的蛾眼减反结构，用于展示渐变界面如何降低反射。",
        "summary_en": "A moth-eye anti-reflection structure approximated by discrete effective gradient-index layers.",
        "headline_cn": "蛾眼等效渐变层",
        "headline_en": "Moth-Eye Gradient Layer",
        "card_tag_cn": "表面结构",
        "card_tag_en": "Surface Structure",
        "main_curve": "R",
    },
    "double_ar": {
        "summary_cn": "双层减反膜，用于展示比单层更宽的低反射工作带。",
        "summary_en": "Double-layer AR coating showing a broader low-reflection band than the single-layer case.",
        "headline_cn": "双层宽带减反",
        "headline_en": "Double-Layer Broadband AR",
        "card_tag_cn": "宽带减反",
        "card_tag_en": "Broadband AR",
        "main_curve": "R",
    },
    "quarter_wave_double_layer": {
        "summary_cn": "展示1/4波长双层匹配结构及其相对于单层的带宽改善。",
        "summary_en": "Shows a quarter-wave double-layer matching stack and its bandwidth gain over the single-layer case.",
        "headline_cn": "1/4波长双层",
        "headline_en": "Quarter-Wave Double Layer",
        "card_tag_cn": "双层匹配",
        "card_tag_en": "Double Match",
        "main_curve": "R",
    },
    "triple_ar": {
        "summary_cn": "三层减反膜，用于展示多层匹配进一步改善带宽与平坦度。",
        "summary_en": "Triple-layer AR coating showing further bandwidth and flatness improvement with multilayer matching.",
        "headline_cn": "三层匹配优化",
        "headline_en": "Triple-Layer Matching",
        "card_tag_cn": "多层优化",
        "card_tag_en": "Multilayer Match",
        "main_curve": "R",
    },
    "high_reflector": {
        "summary_cn": "高低折交替四分之一波堆栈，用于展示中心波长附近的高反射峰。",
        "summary_en": "Alternating quarter-wave high/low index stack showing high reflectance around the design wavelength.",
        "headline_cn": "高反镜堆栈",
        "headline_en": "Reflector Stack",
        "card_tag_cn": "高反镜",
        "card_tag_en": "High Reflector",
        "main_curve": "R",
    },
    "quarter_wave_stack": {
        "summary_cn": "展示周期QW膜堆在中心波长附近形成高反射带的典型行为。",
        "summary_en": "Shows the typical high-reflectance band of a periodic quarter-wave stack.",
        "headline_cn": "QW膜堆",
        "headline_en": "QW Stack",
        "card_tag_cn": "周期堆栈",
        "card_tag_en": "Periodic Stack",
        "main_curve": "R",
    },
    "bragg_reflector": {
        "summary_cn": "作为QW周期膜堆的典型特例，用于突出布拉格高反射机理。",
        "summary_en": "A typical QW-stack special case highlighting Bragg high-reflection behavior.",
        "headline_cn": "布拉格反射镜",
        "headline_en": "Bragg Reflector",
        "card_tag_cn": "高反特例",
        "card_tag_en": "Bragg Case",
        "main_curve": "R",
    },
    "fp_filter": {
        "summary_cn": "标准 F-P 滤光片案例，用于展示腔共振与反射镜协同形成的透射峰。",
        "summary_en": "A standard Fabry-Perot cavity case showing the cooperation between cavity resonance and mirror reflectance.",
        "headline_cn": "标准 F-P 滤光片",
        "headline_en": "Fabry-Perot Filter",
        "card_tag_cn": "腔型滤光",
        "card_tag_en": "Cavity Filter",
        "main_curve": "T",
    },
    "fp_single_halfwave": {
        "summary_cn": "单半波型 F-P 滤光片，用于展示窄带透射峰与腔层共振。",
        "summary_en": "Single-half-wave F-P filter showing narrow transmission peaks from cavity resonance.",
        "headline_cn": "单半波 F-P",
        "headline_en": "Single-Half-Wave F-P",
        "card_tag_cn": "窄带透射",
        "card_tag_en": "Narrowband T",
        "main_curve": "T",
    },
    "fp_double_halfwave": {
        "summary_cn": "双半波型 F-P 滤光片，用于展示更强选择性和角度敏感性。",
        "summary_en": "Double-half-wave F-P filter showing stronger selectivity and angle sensitivity.",
        "headline_cn": "双半波 F-P",
        "headline_en": "Double-Half-Wave F-P",
        "card_tag_cn": "增强选择性",
        "card_tag_en": "Sharper Filter",
        "main_curve": "T",
    },
    "narrowband_filter": {
        "summary_cn": "更高阶的滤波案例，用于展示更窄的透射峰和更强的选择性。",
        "summary_en": "A higher-level filtering case showing narrower transmission peaks and stronger selectivity.",
        "headline_cn": "窄带滤光片",
        "headline_en": "Narrowband Filter",
        "card_tag_cn": "高级滤波",
        "card_tag_en": "Advanced Filter",
        "main_curve": "T",
    },
    "rugate_filter": {
        "summary_cn": "采用连续折射率调制近似的皱褶滤光片，用于展示渐变周期结构形成的反射带。",
        "summary_en": "A rugate filter approximated by continuous index modulation, showing stop-band formation in graded periodic structures.",
        "headline_cn": "皱褶滤光片",
        "headline_en": "Rugate Filter",
        "card_tag_cn": "高级扩展",
        "card_tag_en": "Advanced Extension",
        "main_curve": "R",
    },
    "neutral_beamsplitter": {
        "summary_cn": "中性分束膜，用于展示反射率与透射率接近均衡的分束设计。",
        "summary_en": "Neutral beam splitter showing a near-balanced reflection/transmission design.",
        "headline_cn": "中性分束设计",
        "headline_en": "Neutral Beam Splitter",
        "card_tag_cn": "分束设计",
        "card_tag_en": "Beam Splitter",
        "main_curve": "R",
    },
}

REPORT_CASE_DISPLAY_ORDER: List[str] = [
    "quarter_wave_single_layer",
    "half_wave_single_layer",
    "single_ar",
    "porous_sio2_layer",
    "porous_double_ar",
    "moth_eye_effective_gradient",
    "double_ar",
    "quarter_wave_double_layer",
    "triple_ar",
    "quarter_wave_stack",
    "bragg_reflector",
    "high_reflector",
    "fp_filter",
    "fp_single_halfwave",
    "fp_double_halfwave",
    "narrowband_filter",
    "rugate_filter",
    "neutral_beamsplitter",
]


def _to_complex_index(n_real: float, k_imag: float = 0.0) -> complex:
    return complex(float(n_real), float(k_imag))


def quarter_wave_thickness_nm(lambda0_nm: float, n: complex) -> float:
    return float(lambda0_nm) / (4.0 * max(abs(np.real(n)), 1e-12))


def half_wave_thickness_nm(lambda0_nm: float, n: complex) -> float:
    return float(lambda0_nm) / (2.0 * max(abs(np.real(n)), 1e-12))


def _layer_matrix(delta: complex, q: complex) -> np.ndarray:
    c = np.cos(delta)
    s = np.sin(delta)
    return np.array([[c, 1j * s / q], [1j * q * s, c]], dtype=complex)


def _cos_theta_in_layer(n0: complex, n_layer: complex, theta0_deg: float) -> complex:
    sin_theta0 = np.sin(np.deg2rad(float(theta0_deg)))
    sin_theta_layer = (n0 * sin_theta0) / n_layer
    cos_theta_layer = np.sqrt(1.0 - sin_theta_layer ** 2 + 0j)
    if np.real(cos_theta_layer) < 0:
        cos_theta_layer = -cos_theta_layer
    return cos_theta_layer


def _q_admittance(n_layer: complex, cos_theta_layer: complex, pol: str) -> complex:
    pol_key = str(pol).strip().lower()
    if pol_key == "s":
        return n_layer * cos_theta_layer
    if pol_key == "p":
        return cos_theta_layer / n_layer
    raise ValueError("pol must be 's' or 'p'.")


def _multilayer_rt_spectrum_scalar(
    wavelengths_nm: Sequence[float],
    layers: Sequence[LayerSpec],
    n_incident: complex = 1.0 + 0.0j,
    n_substrate: complex = 1.52 + 0j,
    theta0_deg: float = 0.0,
    pol: str = "p",
) -> Dict[str, np.ndarray]:
    """Scalar (per-wavelength loop) TMM reference implementation."""
    wavelengths_nm = np.asarray(wavelengths_nm, dtype=float).ravel()
    n0 = complex(n_incident)
    ns = complex(n_substrate)
    theta0_deg = float(theta0_deg)

    r_vals: List[complex] = []
    t_vals: List[complex] = []
    r_power: List[float] = []
    t_power: List[float] = []
    a_power: List[float] = []

    cos_theta0 = _cos_theta_in_layer(n0, n0, theta0_deg)
    cos_thetas = _cos_theta_in_layer(n0, ns, theta0_deg)
    q0 = _q_admittance(n0, cos_theta0, pol)
    qs = _q_admittance(ns, cos_thetas, pol)

    for lam_nm in wavelengths_nm:
        lam_m = float(lam_nm) * 1e-9
        m_total = np.eye(2, dtype=complex)

        for layer in layers:
            n_layer = complex(layer.n)
            d_m = float(layer.thickness_nm) * 1e-9
            cos_theta_layer = _cos_theta_in_layer(n0, n_layer, theta0_deg)
            q_layer = _q_admittance(n_layer, cos_theta_layer, pol)
            delta = 2.0 * np.pi * n_layer * d_m * cos_theta_layer / lam_m
            m_total = m_total @ _layer_matrix(delta, q_layer)

        b_val = m_total[0, 0] + m_total[0, 1] * qs
        c_val = m_total[1, 0] + m_total[1, 1] * qs
        y_in = c_val / b_val
        r = (q0 - y_in) / (q0 + y_in)
        t = (2.0 * q0) / (q0 * b_val + c_val)

        r_abs2 = float(np.abs(r) ** 2)
        t_abs2 = float(np.abs(t) ** 2)
        t_scale = np.real(qs / q0)
        t_val = float(max(0.0, t_abs2 * t_scale))
        a_val = float(max(0.0, 1.0 - r_abs2 - t_val))

        r_vals.append(r)
        t_vals.append(t)
        r_power.append(r_abs2)
        t_power.append(t_val)
        a_power.append(a_val)

    return {
        "wavelength_nm": wavelengths_nm.astype(float),
        "r_complex": np.asarray(r_vals, dtype=complex),
        "t_complex": np.asarray(t_vals, dtype=complex),
        "R": np.asarray(r_power, dtype=float),
        "T": np.asarray(t_power, dtype=float),
        "A": np.asarray(a_power, dtype=float),
    }


def multilayer_rt_spectrum(
    wavelengths_nm: Sequence[float],
    layers: Sequence[LayerSpec],
    n_incident: complex = 1.0 + 0.0j,
    n_substrate: complex = 1.52 + 0j,
    theta0_deg: float = 0.0,
    pol: str = "p",
) -> Dict[str, np.ndarray]:
    """Characteristic-matrix solution for a general multilayer stack.

    Vectorized over wavelengths: the layer loop is retained but each layer
    processes all wavelengths simultaneously via NumPy array operations.
    """
    wavelengths_nm = np.asarray(wavelengths_nm, dtype=float).ravel()
    N = len(wavelengths_nm)
    lam_m = wavelengths_nm * 1e-9  # shape (N,)

    n0 = complex(n_incident)
    ns = complex(n_substrate)
    theta0_deg_f = float(theta0_deg)

    # Pre-compute incident/substrate quantities (wavelength-independent)
    cos_theta0 = _cos_theta_in_layer(n0, n0, theta0_deg_f)
    cos_thetas = _cos_theta_in_layer(n0, ns, theta0_deg_f)
    q0 = _q_admittance(n0, cos_theta0, pol)
    qs = _q_admittance(ns, cos_thetas, pol)

    # Accumulated matrix elements — shape (N,) for each
    M00 = np.ones(N, dtype=complex)
    M01 = np.zeros(N, dtype=complex)
    M10 = np.zeros(N, dtype=complex)
    M11 = np.ones(N, dtype=complex)

    # Layer loop (typically 3-21 iterations — cheap compared to wavelength count)
    for layer in layers:
        n_layer = complex(layer.n)
        d_m = float(layer.thickness_nm) * 1e-9
        cos_theta_layer = _cos_theta_in_layer(n0, n_layer, theta0_deg_f)
        q_layer = _q_admittance(n_layer, cos_theta_layer, pol)

        # Phase thickness for all wavelengths at once: shape (N,)
        delta = (2.0 * np.pi * n_layer * d_m * cos_theta_layer) / lam_m

        c = np.cos(delta)
        s = np.sin(delta)

        # Layer matrix elements (scalar for this layer, broadcast over wavelengths)
        A00 = c
        A01 = 1j * s / q_layer
        A10 = 1j * q_layer * s
        A11 = c

        # Matrix multiply: M_new = M @ A  (element-wise over wavelengths)
        new00 = M00 * A00 + M01 * A10
        new01 = M00 * A01 + M01 * A11
        new10 = M10 * A00 + M11 * A10
        new11 = M10 * A01 + M11 * A11

        M00, M01, M10, M11 = new00, new01, new10, new11

    # Reflection and transmission from final matrix
    b_val = M00 + M01 * qs
    c_val = M10 + M11 * qs
    y_in = c_val / b_val
    r_complex = (q0 - y_in) / (q0 + y_in)
    t_complex = (2.0 * q0) / (q0 * b_val + c_val)

    R = np.abs(r_complex) ** 2
    t_scale = float(np.real(qs / q0))
    T = np.maximum(0.0, np.abs(t_complex) ** 2 * t_scale)
    A = np.maximum(0.0, 1.0 - R - T)

    return {
        "wavelength_nm": wavelengths_nm.astype(float),
        "r_complex": r_complex.astype(complex),
        "t_complex": t_complex.astype(complex),
        "R": R.astype(float),
        "T": T.astype(float),
        "A": A.astype(float),
    }


def reflection_phase_radians(result: Dict[str, Any], *, unwrap: bool = True) -> np.ndarray:
    """Extract reflection phase arg(r) from a TMM result dict.

    Parameters
    ----------
    result : dict
        Output of ``multilayer_rt_spectrum`` (must contain ``r_complex``).
    unwrap : bool
        If True, apply ``np.unwrap`` to remove 2π jumps for a continuous
        phase curve.

    Returns
    -------
    np.ndarray
        Phase in radians, same shape as ``result["wavelength_nm"]``.
    """
    r = np.asarray(result["r_complex"], dtype=complex)
    wls = np.asarray(result["wavelength_nm"], dtype=float)
    if len(wls) > 1 and np.any(np.diff(wls) < 0):
        sort_idx = np.argsort(wls)
        r_sorted = r[sort_idx]
        phase_sorted = np.angle(r_sorted)
        if unwrap:
            phase_sorted = np.unwrap(phase_sorted)
        phase = np.zeros_like(phase_sorted)
        phase[sort_idx] = phase_sorted
    else:
        phase = np.angle(r)
        if unwrap:
            phase = np.unwrap(phase)
    return phase


def reflection_phase_degrees(result: Dict[str, Any], *, unwrap: bool = True) -> np.ndarray:
    """Extract reflection phase in degrees."""
    return np.degrees(reflection_phase_radians(result, unwrap=unwrap))


def phase_difference(
    result_left: Dict[str, Any],
    result_right: Dict[str, Any],
    *,
    unwrap: bool = True,
) -> np.ndarray:
    """Compute wrapped phase difference Δφ = arg(r_left) - arg(r_right).

    Parameters
    ----------
    result_left, result_right : dict
        TMM result dicts with matching wavelength grids.
    unwrap : bool
        If True, unwrap each phase before differencing.

    Returns
    -------
    np.ndarray
        Phase difference in radians, range (−π, π] after wrapping.
    """
    phi_left = reflection_phase_radians(result_left, unwrap=unwrap)
    phi_right = reflection_phase_radians(result_right, unwrap=unwrap)
    delta = phi_left - phi_right
    # Wrap to (−π, π]
    return (delta + np.pi) % (2.0 * np.pi) - np.pi


def _material_or_constant_index(
    role: str,
    wavelength_nm: float,
    material_map: Dict[str, Any],
    fallback: complex,
    *,
    allow_extrapolate: bool,
) -> complex:
    value = material_map.get(role)
    if value is None:
        return complex(fallback)
    if isinstance(value, (int, float, complex)):
        return complex(value)
    material = canonical_material_name(str(value))
    if material == "Air":
        return 1.0 + 0.0j
    return complex(
        np.asarray(
            material_complex_index(
                material,
                float(wavelength_nm),
                allow_extrapolate=allow_extrapolate,
            )
        )
    )


def _layer_role_for_material_map(layer_name: str, design_type: str) -> str | None:
    name = str(layer_name).upper()
    key = str(design_type).strip().lower()
    if name.startswith("ME") or name.startswith("RG"):
        return None
    if "POROUS" in name:
        return "n_porous"
    if name == "M":
        return "n_mid"
    if "L" in name:
        return "n_low"
    if "H" in name:
        if key in {
            "high_reflector",
            "high_reflection",
            "quarter_wave_stack",
            "bragg_reflector",
            "fp_single_halfwave",
            "fp_shw",
            "fp_filter",
            "narrowband_filter",
            "fp_double_halfwave",
            "fp_dhw",
            "neutral_beamsplitter",
            "beamsplitter",
        }:
            return "n_high_2"
        return "n_high"
    return None


def _material_or_constant_index_array(
    role: str,
    wavelengths_nm: np.ndarray,
    material_map: Dict[str, Any],
    fallback: complex,
    *,
    allow_extrapolate: bool,
) -> np.ndarray:
    """Return refractive index array of shape (N,) for all wavelengths at once."""
    value = material_map.get(role)
    if value is None:
        return np.full(len(wavelengths_nm), complex(fallback), dtype=complex)
    if isinstance(value, (int, float, complex)):
        return np.full(len(wavelengths_nm), complex(value), dtype=complex)
    material = canonical_material_name(str(value))
    if material == "Air":
        return np.ones(len(wavelengths_nm), dtype=complex)
    return np.asarray(
        material_complex_index(
            material,
            wavelengths_nm,
            allow_extrapolate=allow_extrapolate,
        ),
        dtype=complex,
    )


def multilayer_rt_spectrum_real_materials(
    wavelengths_nm: Sequence[float],
    layers: Sequence[LayerSpec],
    *,
    design_type: str,
    material_map: Dict[str, Any],
    role_fallback_indices: Dict[str, complex],
    theta0_deg: float = 0.0,
    pol: str = "p",
    allow_extrapolate: bool = False,
) -> Dict[str, np.ndarray]:
    """Characteristic-matrix spectrum with wavelength-dependent material n/k.

    Loads all material n(k) arrays once, constructs wavelength-dependent
    layer indices, and calls the vectorized TMM kernel in a single pass.
    """
    wavelengths_nm = np.asarray(wavelengths_nm, dtype=float).ravel()
    N = len(wavelengths_nm)
    lam_m = wavelengths_nm * 1e-9

    n0 = _material_or_constant_index_array(
        "n_incident", wavelengths_nm, material_map,
        role_fallback_indices["n_incident"], allow_extrapolate=allow_extrapolate,
    )
    ns = _material_or_constant_index_array(
        "n_substrate", wavelengths_nm, material_map,
        role_fallback_indices["n_substrate"], allow_extrapolate=allow_extrapolate,
    )

    # Pre-compute incident/substrate quantities per wavelength
    sin_theta0 = np.sin(np.deg2rad(float(theta0_deg)))
    cos_theta0_arr = np.sqrt(1.0 - (n0 * sin_theta0 / n0) ** 2 + 0j)
    cos_thetas_arr = np.sqrt(1.0 - (n0 * sin_theta0 / ns) ** 2 + 0j)
    # Ensure positive real part
    cos_theta0_arr = np.where(np.real(cos_theta0_arr) < 0, -cos_theta0_arr, cos_theta0_arr)
    cos_thetas_arr = np.where(np.real(cos_thetas_arr) < 0, -cos_thetas_arr, cos_thetas_arr)

    pol_key = pol.strip().lower()
    if pol_key == "s":
        q0_arr = n0 * cos_theta0_arr
        qs_arr = ns * cos_thetas_arr
    elif pol_key == "p":
        q0_arr = cos_theta0_arr / n0
        qs_arr = cos_thetas_arr / ns
    else:
        raise ValueError("pol must be 's' or 'p'.")

    # Accumulated matrix elements — shape (N,)
    M00 = np.ones(N, dtype=complex)
    M01 = np.zeros(N, dtype=complex)
    M10 = np.zeros(N, dtype=complex)
    M11 = np.ones(N, dtype=complex)

    for layer in layers:
        role = _layer_role_for_material_map(layer.name, design_type)
        if role is None:
            n_layer = np.full(N, complex(layer.n), dtype=complex)
        else:
            n_layer = _material_or_constant_index_array(
                role, wavelengths_nm, material_map,
                role_fallback_indices.get(role, complex(layer.n)),
                allow_extrapolate=allow_extrapolate,
            )

        d_m = float(layer.thickness_nm) * 1e-9

        # Per-wavelength cos_theta and q for this layer
        cos_theta_layer = np.sqrt(1.0 - (n0 * sin_theta0 / n_layer) ** 2 + 0j)
        cos_theta_layer = np.where(np.real(cos_theta_layer) < 0, -cos_theta_layer, cos_theta_layer)

        if pol_key == "s":
            q_layer = n_layer * cos_theta_layer
        else:
            q_layer = cos_theta_layer / n_layer

        # Phase thickness: shape (N,)
        delta = (2.0 * np.pi * n_layer * d_m * cos_theta_layer) / lam_m

        c = np.cos(delta)
        s = np.sin(delta)

        A00 = c
        A01 = 1j * s / q_layer
        A10 = 1j * q_layer * s
        A11 = c

        new00 = M00 * A00 + M01 * A10
        new01 = M00 * A01 + M01 * A11
        new10 = M10 * A00 + M11 * A10
        new11 = M10 * A01 + M11 * A11

        M00, M01, M10, M11 = new00, new01, new10, new11

    b_val = M00 + M01 * qs_arr
    c_val = M10 + M11 * qs_arr
    y_in = c_val / b_val
    r_complex = (q0_arr - y_in) / (q0_arr + y_in)
    t_complex = (2.0 * q0_arr) / (q0_arr * b_val + c_val)

    R = np.abs(r_complex) ** 2
    t_scale = np.real(qs_arr / q0_arr)
    T = np.maximum(0.0, np.abs(t_complex) ** 2 * t_scale)
    A = np.maximum(0.0, 1.0 - R - T)

    return {
        "wavelength_nm": wavelengths_nm.astype(float),
        "r_complex": r_complex.astype(complex),
        "t_complex": t_complex.astype(complex),
        "R": R.astype(float),
        "T": T.astype(float),
        "A": A.astype(float),
    }


def build_single_ar_layers(lambda0_nm: float, n_low: complex) -> List[LayerSpec]:
    return [
        LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)),
    ]


def build_uniform_single_layer_layers(
    lambda0_nm: float,
    n_layer: complex,
    optical_kind: str = "quarter",
) -> List[LayerSpec]:
    kind = str(optical_kind).strip().lower()
    if kind in {"quarter", "qw", "quarter_wave"}:
        thickness_nm = quarter_wave_thickness_nm(lambda0_nm, n_layer)
        name = "QW"
    elif kind in {"half", "hw", "half_wave"}:
        thickness_nm = half_wave_thickness_nm(lambda0_nm, n_layer)
        name = "HW"
    else:
        raise ValueError("optical_kind must be 'quarter' or 'half'.")
    return [LayerSpec(name, n_layer, thickness_nm)]


def build_double_ar_layers(lambda0_nm: float, n_low: complex, n_high: complex) -> List[LayerSpec]:
    return [
        LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)),
        LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)),
    ]


def build_porous_double_ar_layers(lambda0_nm: float, n_porous: complex, n_high: complex) -> List[LayerSpec]:
    return [
        LayerSpec("Porous", n_porous, quarter_wave_thickness_nm(lambda0_nm, n_porous)),
        LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)),
    ]


def build_triple_ar_layers(
    lambda0_nm: float,
    n_mid: complex,
    n_high: complex,
    n_low: complex,
) -> List[LayerSpec]:
    return [
        LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)),
        LayerSpec("2H", n_high, half_wave_thickness_nm(lambda0_nm, n_high)),
        LayerSpec("M", n_mid, quarter_wave_thickness_nm(lambda0_nm, n_mid)),
    ]


def build_high_reflector_layers(
    lambda0_nm: float,
    n_high: complex,
    n_low: complex,
    periods: int,
) -> List[LayerSpec]:
    layers: List[LayerSpec] = [LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high))]
    for _ in range(int(periods)):
        layers.append(LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)))
        layers.append(LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)))
    return layers


def build_fp_single_halfwave_layers(
    lambda0_nm: float,
    n_high: complex,
    n_low: complex,
    periods: int,
    spacer_kind: str = "L",
) -> List[LayerSpec]:
    periods = int(periods)
    spacer_key = str(spacer_kind).strip().upper()
    if spacer_key not in {"L", "H"}:
        raise ValueError("spacer_kind must be 'L' or 'H'.")

    cavity_index = n_low if spacer_key == "L" else n_high
    cavity_name = "C" if spacer_key == "L" else "C_H"
    d_h = quarter_wave_thickness_nm(lambda0_nm, n_high)
    d_l = quarter_wave_thickness_nm(lambda0_nm, n_low)

    # Symmetric single-half-wave F-P cavity:
    # Air / (H L)^N / C / (L H)^N / Air
    left_mirror: List[LayerSpec] = []
    for _ in range(periods):
        left_mirror.append(LayerSpec("H", n_high, d_h))
        left_mirror.append(LayerSpec("L", n_low, d_l))

    spacer = [LayerSpec(cavity_name, cavity_index, half_wave_thickness_nm(lambda0_nm, cavity_index))]

    right_mirror: List[LayerSpec] = []
    for _ in range(periods):
        right_mirror.append(LayerSpec("L", n_low, d_l))
        right_mirror.append(LayerSpec("H", n_high, d_h))

    return left_mirror + spacer + right_mirror


def build_fp_double_halfwave_layers(
    lambda0_nm: float,
    n_high: complex,
    n_low: complex,
    periods: int,
) -> List[LayerSpec]:
    periods = int(periods)
    left_mirror: List[LayerSpec] = [LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high))]
    for _ in range(periods):
        left_mirror.append(LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)))
        left_mirror.append(LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)))

    right_mirror: List[LayerSpec] = []
    for _ in range(periods):
        right_mirror.append(LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)))
        right_mirror.append(LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)))
    right_mirror.append(LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)))

    center_reflector: List[LayerSpec] = []
    for _ in range(periods):
        center_reflector.append(LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)))
        center_reflector.append(LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)))
    center_reflector.append(LayerSpec("2H", n_high, half_wave_thickness_nm(lambda0_nm, n_high)))
    for _ in range(periods):
        center_reflector.append(LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)))
        center_reflector.append(LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)))

    spacer = [LayerSpec("2L", n_low, half_wave_thickness_nm(lambda0_nm, n_low))]
    return left_mirror + spacer + center_reflector + spacer + right_mirror


def build_neutral_beamsplitter_layers(
    lambda0_nm: float,
    n_high: complex,
    n_low: complex,
    use_front_halfwave_low: bool = False,
) -> List[LayerSpec]:
    layers: List[LayerSpec] = []
    if use_front_halfwave_low:
        layers.append(LayerSpec("2L", n_low, half_wave_thickness_nm(lambda0_nm, n_low)))
    layers.extend(
        [
            LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)),
            LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)),
            LayerSpec("L", n_low, quarter_wave_thickness_nm(lambda0_nm, n_low)),
            LayerSpec("H", n_high, quarter_wave_thickness_nm(lambda0_nm, n_high)),
        ]
    )
    return layers


def build_rugate_filter_layers(
    lambda0_nm: float,
    n_low: complex,
    n_high: complex,
    periods: int,
    slices_per_period: int = 24,
) -> List[LayerSpec]:
    periods = max(int(periods), 1)
    slices_per_period = max(int(slices_per_period), 8)
    n_avg = 0.5 * (n_low + n_high)
    dn = 0.5 * (n_high - n_low)
    spatial_period_nm = float(lambda0_nm) / (2.0 * max(abs(np.real(n_avg)), 1e-12))
    dz_nm = spatial_period_nm / float(slices_per_period)

    layers: List[LayerSpec] = []
    total_slices = periods * slices_per_period
    for idx in range(total_slices):
        phase = 2.0 * np.pi * (idx + 0.5) / float(slices_per_period)
        n_slice = n_avg + dn * np.cos(phase)
        layers.append(LayerSpec(f"RG{idx + 1}", n_slice, dz_nm))
    return layers


def build_moth_eye_effective_gradient_layers(
    n_top: complex,
    n_bottom: complex,
    d_total_nm: float,
    num_gradient_layers: int,
    gradient_type: str = "linear",
    layer_indices: Sequence[float] | None = None,
    layer_thickness_nm: Sequence[float] | None = None,
) -> List[LayerSpec]:
    num_gradient_layers = max(int(num_gradient_layers), 1)

    if layer_indices is not None:
        n_values = [complex(float(v), 0.0) for v in layer_indices]
        num_gradient_layers = len(n_values)
    else:
        if str(gradient_type).strip().lower() != "linear":
            raise ValueError("Only linear gradient_type is currently supported.")
        n_values = [
            n_top + (n_bottom - n_top) * (idx / max(num_gradient_layers - 1, 1))
            for idx in range(num_gradient_layers)
        ]

    if layer_thickness_nm is not None:
        thickness_values = [float(v) for v in layer_thickness_nm]
        if len(thickness_values) != num_gradient_layers:
            raise ValueError("layer_thickness_nm length must match the number of gradient layers.")
    else:
        dz_nm = float(d_total_nm) / float(num_gradient_layers)
        thickness_values = [dz_nm] * num_gradient_layers

    layers: List[LayerSpec] = []
    for idx, (n_value, thickness_nm) in enumerate(zip(n_values, thickness_values), start=1):
        layers.append(LayerSpec(f"ME{idx}", n_value, float(thickness_nm)))
    return layers


def describe_layers(layers: Sequence[LayerSpec]) -> List[Dict[str, Any]]:
    return [
        {
            "name": layer.name,
            "n_real": float(np.real(layer.n)),
            "n_imag": float(np.imag(layer.n)),
            "thickness_nm": float(layer.thickness_nm),
        }
        for layer in layers
    ]


def _pdrc_sio2_index(lambda_um: float) -> complex:
    """First-pass effective SiO2 index for PDRC spectral screening.

    This is a compact teaching/research surrogate, not a replacement for
    measured optical-constant data.  It keeps the solar band nearly lossless
    and adds broad phonon absorption inside the 8-13 um atmospheric window.
    """
    lam = float(lambda_um)
    n_val = 1.46 + 0.012 * np.exp(-((lam - 9.5) / 3.0) ** 2)
    if lam < 2.5:
        k_val = 0.0
    else:
        k_val = (
            0.010
            + 0.090 * np.exp(-((lam - 9.3) / 1.25) ** 2)
            + 0.065 * np.exp(-((lam - 12.2) / 1.15) ** 2)
        )
    # This characteristic-matrix implementation uses n - i*k for passive loss.
    return complex(float(n_val), -float(k_val))


def _pdrc_tio2_index(lambda_um: float) -> complex:
    """Simple low-loss TiO2 dispersion surrogate for first-pass PDRC scans."""
    lam = max(float(lambda_um), 0.25)
    n_val = 2.28 + 0.10 / (lam ** 1.2 + 0.25)
    k_val = 0.002 if lam < 0.38 else 0.0
    return complex(float(n_val), -float(k_val))


def _pdrc_ag_index(lambda_um: float) -> complex:
    """Compact Ag mirror surrogate for wideband screening."""
    lam = float(lambda_um)
    n_real = 0.12 + 0.020 * min(lam, 13.0)
    k_imag = 3.2 + 0.90 * np.sqrt(max(lam, 0.3))
    return complex(float(n_real), -float(k_imag))


def _pdrc_substrate_index(lambda_um: float) -> complex:
    lam = float(lambda_um)
    n_val = 1.52 + 0.015 * np.exp(-((lam - 9.0) / 3.5) ** 2)
    k_val = 0.0 if lam < 7.0 else 0.015
    return complex(float(n_val), -float(k_val))


def _pdrc_material_index(material: str, lambda_um: float) -> complex:
    key = str(material).strip().lower()
    if key in {"sio2", "silica", "二氧化硅"}:
        return _pdrc_sio2_index(lambda_um)
    if key in {"tio2", "titania", "二氧化钛"}:
        return _pdrc_tio2_index(lambda_um)
    if key in {"ag", "silver", "银"}:
        return _pdrc_ag_index(lambda_um)
    if key in {"substrate", "glass", "基底", "玻璃"}:
        return _pdrc_substrate_index(lambda_um)
    if key in {"air", "空气"}:
        return 1.0 + 0.0j
    raise ValueError(f"Unsupported PDRC material: {material}")


def build_pdrc_multilayer_stack(
    *,
    variant: str = "full",
    ag_thickness_nm: float = 500.0,
) -> List[Dict[str, Any]]:
    """Build the first PDRC stack definition used by the wideband TMM model.

    The layer order is from incident air toward the substrate.
    """
    key = str(variant).strip().lower()
    if key in {"simple", "basic", "first"}:
        layers = [
            ("SiO2_1", "SiO2", 1200.0),
            ("TiO2_1", "TiO2", 80.0),
            ("SiO2_3", "SiO2", 1000.0),
            ("Ag", "Ag", ag_thickness_nm),
        ]
    elif key in {"full", "default", "five_dielectric"}:
        layers = [
            ("SiO2_1", "SiO2", 1200.0),
            ("TiO2_1", "TiO2", 80.0),
            ("SiO2_2", "SiO2", 600.0),
            ("TiO2_2", "TiO2", 80.0),
            ("SiO2_3", "SiO2", 1000.0),
            ("Ag", "Ag", ag_thickness_nm),
        ]
    else:
        raise ValueError("variant must be 'full' or 'simple'.")
    return [
        {
            "name": name,
            "material": material,
            "thickness_nm": float(thickness_nm),
        }
        for name, material, thickness_nm in layers
    ]


def _multilayer_rt_single_wavelength(
    *,
    wavelength_nm: float,
    layer_indices: Sequence[complex],
    thicknesses_nm: Sequence[float],
    n_incident: complex,
    n_substrate: complex,
    theta0_deg: float,
    pol: str,
) -> Dict[str, complex | float]:
    n0 = complex(n_incident)
    ns = complex(n_substrate)
    theta0_deg = float(theta0_deg)
    lam_m = float(wavelength_nm) * 1e-9

    cos_theta0 = _cos_theta_in_layer(n0, n0, theta0_deg)
    cos_thetas = _cos_theta_in_layer(n0, ns, theta0_deg)
    q0 = _q_admittance(n0, cos_theta0, pol)
    qs = _q_admittance(ns, cos_thetas, pol)
    m_total = np.eye(2, dtype=complex)

    for n_layer, thickness_nm in zip(layer_indices, thicknesses_nm):
        n_complex = complex(n_layer)
        cos_theta_layer = _cos_theta_in_layer(n0, n_complex, theta0_deg)
        q_layer = _q_admittance(n_complex, cos_theta_layer, pol)
        delta = 2.0 * np.pi * n_complex * float(thickness_nm) * 1e-9 * cos_theta_layer / lam_m
        m_total = m_total @ _layer_matrix(delta, q_layer)

    b_val = m_total[0, 0] + m_total[0, 1] * qs
    c_val = m_total[1, 0] + m_total[1, 1] * qs
    y_in = c_val / b_val
    r = (q0 - y_in) / (q0 + y_in)
    t = (2.0 * q0) / (q0 * b_val + c_val)
    r_power = float(np.abs(r) ** 2)
    t_scale = max(0.0, float(np.real(qs / q0)))
    t_power = float(max(0.0, np.abs(t) ** 2 * t_scale))
    a_power = float(np.clip(1.0 - r_power - t_power, 0.0, 1.0))
    return {
        "r_complex": r,
        "t_complex": t,
        "R": r_power,
        "T": t_power,
        "A": a_power,
    }


def _default_pdrc_wavelength_grid_um() -> np.ndarray:
    solar = np.linspace(0.30, 2.50, 221)
    mid_ir = np.linspace(2.55, 13.00, 420)
    return np.unique(np.concatenate([solar, mid_ir])).astype(float)


def _pdrc_band_label(lambda_um: float) -> str:
    lam = float(lambda_um)
    if 0.3 <= lam <= 2.5:
        return "solar"
    if 8.0 <= lam <= 13.0:
        return "atmospheric_window"
    return "other"


def _band_average(x_values: np.ndarray, y_values: np.ndarray, lower: float, upper: float) -> float:
    mask = (x_values >= float(lower)) & (x_values <= float(upper))
    if int(np.count_nonzero(mask)) < 2:
        return float("nan")
    try:
        integral = np.trapezoid(y_values[mask], x_values[mask])
    except AttributeError:
        integral = np.trapz(y_values[mask], x_values[mask])
    return float(integral / (float(upper) - float(lower)))


def _normalize_pdrc_wavelength_grid(wavelengths_um: Sequence[float] | None) -> np.ndarray:
    """Normalize and validate PDRC wavelength grid."""
    if wavelengths_um is None:
        lambda_um = _default_pdrc_wavelength_grid_um()
    else:
        lambda_um = np.asarray(wavelengths_um, dtype=float).ravel()
        lambda_um = lambda_um[np.isfinite(lambda_um)]
        lambda_um = np.unique(lambda_um)
    if lambda_um.size == 0:
        raise ValueError("wavelengths_um must contain at least one finite value.")
    return lambda_um


def _pdrc_compute_metrics(
    lambda_um: np.ndarray,
    r_arr: np.ndarray,
    t_arr: np.ndarray,
    a_arr: np.ndarray,
    r_complex: np.ndarray,
    t_complex: np.ndarray,
    stack: List[Dict[str, Any]],
    *,
    variant: str,
    theta_deg: float,
    pol: str,
    case_id: str,
    title_cn: str,
    title_en: str,
    optical_note: str,
) -> Dict[str, Any]:
    """Shared post-processing for PDRC simulation results."""
    emissivity = a_arr.copy()
    bands = [_pdrc_band_label(float(lam)) for lam in lambda_um]

    solar_abs = _band_average(lambda_um, a_arr, 0.3, 2.5)
    solar_ref = _band_average(lambda_um, r_arr, 0.3, 2.5)
    epsilon_8_13 = _band_average(lambda_um, emissivity, 8.0, 13.0)
    score = float(epsilon_8_13 - solar_abs)

    representative_wavelengths = np.asarray([0.5, 1.0, 1.5, 8.0, 10.0, 12.0], dtype=float)
    representative_rows: List[Dict[str, Any]] = []
    for target in representative_wavelengths:
        idx = int(np.argmin(np.abs(lambda_um - target)))
        representative_rows.append(
            {
                "lambda_um": float(lambda_um[idx]),
                "target_lambda_um": float(target),
                "R": float(r_arr[idx]),
                "T": float(t_arr[idx]),
                "A": float(a_arr[idx]),
                "emissivity": float(emissivity[idx]),
                "band": bands[idx],
            }
        )

    return {
        "case_id": case_id,
        "title_cn": title_cn,
        "title_en": title_en,
        "variant": str(variant),
        "theta_deg": float(theta_deg),
        "pol": str(pol),
        "lambda_um": lambda_um,
        "wavelength_nm": lambda_um * 1000.0,
        "r_complex": r_complex,
        "t_complex": t_complex,
        "R": r_arr,
        "T": t_arr,
        "A": a_arr,
        "emissivity": emissivity,
        "band": bands,
        "layers": stack,
        "optical_constant_note_cn": optical_note,
        "metrics": {
            "A_solar_avg": solar_abs,
            "R_solar_avg": solar_ref,
            "epsilon_8_13_avg": epsilon_8_13,
            "cooling_score": score,
            "success_basic": bool(solar_abs < 0.15 and epsilon_8_13 > 0.70),
            "success_better": bool(solar_abs < 0.10 and epsilon_8_13 > 0.80),
        },
        "representative_points": representative_rows,
    }


def simulate_pdrc_multilayer_cooling(
    *,
    variant: str = "full",
    wavelengths_um: Sequence[float] | None = None,
    theta_deg: float = 0.0,
    pol: str = "p",
    ag_thickness_nm: float = 500.0,
) -> Dict[str, Any]:
    """Simulate a first-pass PDRC multilayer using wideband TMM.

    This module is intentionally separated from the teaching main tree.  It is
    meant as a fast design-screening entry point before COMSOL representative
    point validation.
    """
    lambda_um = _normalize_pdrc_wavelength_grid(wavelengths_um)

    stack = build_pdrc_multilayer_stack(variant=variant, ag_thickness_nm=ag_thickness_nm)
    thicknesses_nm = [float(layer["thickness_nm"]) for layer in stack]
    wavelengths_nm = lambda_um * 1000.0
    lam_m = wavelengths_nm * 1e-9

    # Vectorized: compute all material indices at once
    n_incident = np.ones(len(lambda_um), dtype=complex)
    n_substrate = np.array([_pdrc_substrate_index(float(lam)) for lam in lambda_um], dtype=complex)

    # Build per-wavelength layer index arrays
    layer_n_arrays: List[np.ndarray] = []
    for layer in stack:
        material = str(layer["material"])
        n_arr = np.array([_pdrc_material_index(material, float(lam)) for lam in lambda_um], dtype=complex)
        layer_n_arrays.append(n_arr)

    # Vectorized TMM
    sin_theta0 = np.sin(np.deg2rad(float(theta_deg)))
    cos_theta0_arr = np.sqrt(1.0 - (n_incident * sin_theta0 / n_incident) ** 2 + 0j)
    cos_thetas_arr = np.sqrt(1.0 - (n_incident * sin_theta0 / n_substrate) ** 2 + 0j)
    cos_theta0_arr = np.where(np.real(cos_theta0_arr) < 0, -cos_theta0_arr, cos_theta0_arr)
    cos_thetas_arr = np.where(np.real(cos_thetas_arr) < 0, -cos_thetas_arr, cos_thetas_arr)

    pol_key = pol.strip().lower()
    if pol_key == "s":
        q0_arr = n_incident * cos_theta0_arr
        qs_arr = n_substrate * cos_thetas_arr
    else:
        q0_arr = cos_theta0_arr / n_incident
        qs_arr = cos_thetas_arr / n_substrate

    N = len(lambda_um)
    M00 = np.ones(N, dtype=complex)
    M01 = np.zeros(N, dtype=complex)
    M10 = np.zeros(N, dtype=complex)
    M11 = np.ones(N, dtype=complex)

    for i, layer in enumerate(stack):
        n_layer = layer_n_arrays[i]
        d_m = float(layer["thickness_nm"]) * 1e-9

        cos_theta_layer = np.sqrt(1.0 - (n_incident * sin_theta0 / n_layer) ** 2 + 0j)
        cos_theta_layer = np.where(np.real(cos_theta_layer) < 0, -cos_theta_layer, cos_theta_layer)

        if pol_key == "s":
            q_layer = n_layer * cos_theta_layer
        else:
            q_layer = cos_theta_layer / n_layer

        delta = (2.0 * np.pi * n_layer * d_m * cos_theta_layer) / lam_m

        c = np.cos(delta)
        s = np.sin(delta)

        A00 = c
        A01 = 1j * s / q_layer
        A10 = 1j * q_layer * s
        A11 = c

        new00 = M00 * A00 + M01 * A10
        new01 = M00 * A01 + M01 * A11
        new10 = M10 * A00 + M11 * A10
        new11 = M10 * A01 + M11 * A11

        M00, M01, M10, M11 = new00, new01, new10, new11

    b_val = M00 + M01 * qs_arr
    c_val = M10 + M11 * qs_arr
    y_in = c_val / b_val
    r_complex = (q0_arr - y_in) / (q0_arr + y_in)
    t_complex = (2.0 * q0_arr) / (q0_arr * b_val + c_val)

    R = np.abs(r_complex) ** 2
    t_scale = np.real(qs_arr / q0_arr)
    T = np.maximum(0.0, np.abs(t_complex) ** 2 * t_scale)
    A = np.maximum(0.0, 1.0 - R - T)

    return _pdrc_compute_metrics(
        lambda_um, R.astype(float), T.astype(float), A.astype(float),
        r_complex, t_complex, stack,
        variant=variant, theta_deg=theta_deg, pol=pol,
        case_id="pdrc_multilayer_cooling",
        title_cn="被动日间辐射冷却薄膜光谱调控模块",
        title_en="Passive Daytime Radiative Cooling Multilayer",
        optical_note="第一版使用内置有效光学常数近似；后续可替换为实测 n,k 数据。",
    )


def simulate_pdrc_multilayer_cooling_real_materials(
    *,
    variant: str = "full",
    wavelengths_um: Sequence[float] | None = None,
    theta_deg: float = 0.0,
    pol: str = "p",
    ag_thickness_nm: float = 500.0,
    allow_extrapolate: bool = False,
) -> Dict[str, Any]:
    """Simulate PDRC multilayer using real-material n(k) data.

    Uses the same stack definition as the surrogate version but loads
    wavelength-dependent optical constants from ``data/real_nk/`` CSV files.
    The vectorized TMM kernel processes all wavelengths in a single pass.
    """
    from .materials import material_complex_index

    lambda_um = _normalize_pdrc_wavelength_grid(wavelengths_um)

    stack = build_pdrc_multilayer_stack(variant=variant, ag_thickness_nm=ag_thickness_nm)
    thicknesses_nm = [float(layer["thickness_nm"]) for layer in stack]

    # Load real n(k) for all materials at all wavelengths (vectorized)
    n_air = np.ones(len(lambda_um), dtype=complex)
    n_substrate = np.full(len(lambda_um), 1.52 + 0j, dtype=complex)

    # Determine valid wavelength intersection from all material data
    from .materials import common_wavelength_window_um
    material_names = list({str(layer["material"]) for layer in stack})
    try:
        valid_names = [m for m in material_names if m not in {"Ag", "Air"}]
        if valid_names:
            lower_um, upper_um = common_wavelength_window_um(valid_names)
            # Clip to valid range with some margin
            lower_um = max(lower_um, 0.3)
            upper_um = min(upper_um, 13.0)
            mask = (lambda_um >= lower_um) & (lambda_um <= upper_um)
            if np.sum(mask) < 10:
                raise ValueError(
                    f"Material data only covers {lower_um:.2f}-{upper_um:.2f} um, "
                    f"too narrow for PDRC analysis."
                )
            lambda_um = lambda_um[mask]
            wavelengths_nm = lambda_um * 1000.0
    except (ValueError, KeyError):
        # If material data is insufficient, use surrogate range
        pass

    # Build layer index arrays
    layer_n_arrays: List[np.ndarray] = []
    for layer in stack:
        material = str(layer["material"])
        n_arr = material_complex_index(
            material, (lambda_um * 1000.0).tolist(),
            allow_extrapolate=allow_extrapolate,
        )
        layer_n_arrays.append(np.asarray(n_arr, dtype=complex))

    # Vectorized TMM: compute per-wavelength n(k) for incident/substrate
    n_incident_arr = np.ones(len(lambda_um), dtype=complex)
    n_substrate_arr = np.full(len(lambda_um), 1.52 + 0j, dtype=complex)

    # Use the scalar TMM for each wavelength with proper dispersive n(k)
    wavelengths_nm = lambda_um * 1000.0
    lam_m = wavelengths_nm * 1e-9

    # Pre-compute incident/substrate quantities
    sin_theta0 = np.sin(np.deg2rad(float(theta_deg)))
    cos_theta0_arr = np.sqrt(1.0 - (n_incident_arr * sin_theta0 / n_incident_arr) ** 2 + 0j)
    cos_thetas_arr = np.sqrt(1.0 - (n_incident_arr * sin_theta0 / n_substrate_arr) ** 2 + 0j)
    cos_theta0_arr = np.where(np.real(cos_theta0_arr) < 0, -cos_theta0_arr, cos_theta0_arr)
    cos_thetas_arr = np.where(np.real(cos_thetas_arr) < 0, -cos_thetas_arr, cos_thetas_arr)

    pol_key = pol.strip().lower()
    if pol_key == "s":
        q0_arr = n_incident_arr * cos_theta0_arr
        qs_arr = n_substrate_arr * cos_thetas_arr
    else:
        q0_arr = cos_theta0_arr / n_incident_arr
        qs_arr = cos_thetas_arr / n_substrate_arr

    # Accumulated matrix elements
    N = len(lambda_um)
    M00 = np.ones(N, dtype=complex)
    M01 = np.zeros(N, dtype=complex)
    M10 = np.zeros(N, dtype=complex)
    M11 = np.ones(N, dtype=complex)

    for i, layer in enumerate(stack):
        n_layer = layer_n_arrays[i]
        d_m = float(layer["thickness_nm"]) * 1e-9

        cos_theta_layer = np.sqrt(1.0 - (n_incident_arr * sin_theta0 / n_layer) ** 2 + 0j)
        cos_theta_layer = np.where(np.real(cos_theta_layer) < 0, -cos_theta_layer, cos_theta_layer)

        if pol_key == "s":
            q_layer = n_layer * cos_theta_layer
        else:
            q_layer = cos_theta_layer / n_layer

        delta = (2.0 * np.pi * n_layer * d_m * cos_theta_layer) / lam_m

        c = np.cos(delta)
        s = np.sin(delta)

        A00 = c
        A01 = 1j * s / q_layer
        A10 = 1j * q_layer * s
        A11 = c

        new00 = M00 * A00 + M01 * A10
        new01 = M00 * A01 + M01 * A11
        new10 = M10 * A00 + M11 * A10
        new11 = M10 * A01 + M11 * A11

        M00, M01, M10, M11 = new00, new01, new10, new11

    b_val = M00 + M01 * qs_arr
    c_val = M10 + M11 * qs_arr
    y_in = c_val / b_val
    r_complex = (q0_arr - y_in) / (q0_arr + y_in)
    t_complex = (2.0 * q0_arr) / (q0_arr * b_val + c_val)

    R = np.abs(r_complex) ** 2
    t_scale = np.real(qs_arr / q0_arr)
    T = np.maximum(0.0, np.abs(t_complex) ** 2 * t_scale)
    A = np.maximum(0.0, 1.0 - R - T)

    r_arr = R.astype(float)
    t_arr = T.astype(float)
    a_arr = A.astype(float)

    return _pdrc_compute_metrics(
        lambda_um, r_arr, t_arr, a_arr,
        r_complex, t_complex, stack,
        variant=variant, theta_deg=theta_deg, pol=pol,
        case_id="pdrc_multilayer_cooling_real_materials",
        title_cn="被动日间辐射冷却薄膜（真实材料色散）",
        title_en="Passive Daytime Radiative Cooling (Real Materials)",
        optical_note="使用 RefractiveIndex.INFO 真实材料 n(k) 数据。",
    )


def export_pdrc_cooling_bundle(
    *,
    prefix: str = "pdrc_multilayer_cooling_v1",
    variant: str = "full",
    wavelengths_um: Sequence[float] | None = None,
    theta_deg: float = 0.0,
    pol: str = "p",
    ag_thickness_nm: float = 500.0,
) -> Dict[str, str]:
    """Export PDRC spectrum, metrics, report text and figure."""
    result = simulate_pdrc_multilayer_cooling(
        variant=variant,
        wavelengths_um=wavelengths_um,
        theta_deg=theta_deg,
        pol=pol,
        ag_thickness_nm=ag_thickness_nm,
    )
    saved: Dict[str, str] = {}

    lambda_um = np.asarray(result["lambda_um"], dtype=float)
    r_vals = np.asarray(result["R"], dtype=float)
    t_vals = np.asarray(result["T"], dtype=float)
    a_vals = np.asarray(result["A"], dtype=float)

    audit = build_figure_audit(
        figure_id=f"{prefix}_spectrum",
        title=str(result.get("title_cn") or result.get("title_en") or prefix),
        evidence_level="real_material_theory" if "real_material" in str(result.get("case_id", "")) else "theory",
        checks=[audit_rta_data(lambda_um, r_vals, t_vals, a_vals, conservation_tolerance=1e-5)],
    )
    audit_path = output_file(f"{prefix}_figure_audit.json")
    saved["audit_json"] = write_figure_audit(audit_path, audit)
    eps_vals = np.asarray(result["emissivity"], dtype=float)
    bands = [str(item) for item in result["band"]]
    metrics = result["metrics"]

    csv_path = output_file(f"{prefix}_spectrum.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("lambda_um,R,T,A,emissivity,band\n")
        for row in zip(lambda_um, r_vals, t_vals, a_vals, eps_vals, bands):
            f.write(f"{row[0]:.12g},{row[1]:.12g},{row[2]:.12g},{row[3]:.12g},{row[4]:.12g},{row[5]}\n")
    saved["csv"] = str(csv_path)

    metrics_path = output_file(f"{prefix}_metrics.csv")
    with open(metrics_path, "w", encoding="utf-8-sig") as f:
        f.write("A_solar_avg,R_solar_avg,epsilon_8_13_avg,cooling_score,success_basic,success_better\n")
        f.write(
            f"{metrics['A_solar_avg']:.12g},{metrics['R_solar_avg']:.12g},"
            f"{metrics['epsilon_8_13_avg']:.12g},{metrics['cooling_score']:.12g},"
            f"{int(bool(metrics['success_basic']))},{int(bool(metrics['success_better']))}\n"
        )
    saved["metrics_csv"] = str(metrics_path)

    json_path = output_file(f"{prefix}_summary.json")
    payload = {
        "case_id": result["case_id"],
        "title_cn": result["title_cn"],
        "title_en": result["title_en"],
        "variant": result["variant"],
        "geometry_type": "2D planar laterally uniform multilayer",
        "comsol_layer_order_top_to_bottom": [
            "Air",
            "SiO2_1",
            "TiO2_1",
            "SiO2_2",
            "TiO2_2",
            "SiO2_3",
            "Ag",
            "substrate",
        ],
        "theta_deg": result["theta_deg"],
        "pol": result["pol"],
        "layers": result["layers"],
        "metrics": metrics,
        "representative_points": result["representative_points"],
        "optical_constant_note_cn": result["optical_constant_note_cn"],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    saved["json"] = str(json_path)

    txt_path = output_file(f"{prefix}_summary.txt")
    lines = [
        "PDRC 被动日间辐射冷却薄膜光谱调控模块",
        "=" * 80,
        f"case_id              = {result['case_id']}",
        f"variant              = {result['variant']}",
        f"theta_deg            = {float(result['theta_deg']):.6f}",
        f"pol                  = {result['pol']}",
        f"A_solar_avg          = {float(metrics['A_solar_avg']):.12e}",
        f"R_solar_avg          = {float(metrics['R_solar_avg']):.12e}",
        f"epsilon_8_13_avg     = {float(metrics['epsilon_8_13_avg']):.12e}",
        f"cooling_score        = {float(metrics['cooling_score']):.12e}",
        f"success_basic        = {bool(metrics['success_basic'])}",
        f"success_better       = {bool(metrics['success_better'])}",
        "",
        "结构：Air / SiO2_1 / TiO2_1 / SiO2_2 / TiO2_2 / SiO2_3 / Ag / substrate",
        "COMSOL 几何：2D 横向均匀矩形层，x 方向宽度 w_cell = 1 um，从下往上画 substrate -> Ag -> SiO2_3 -> TiO2_2 -> SiO2_2 -> TiO2_1 -> SiO2_1 -> Air。",
    ]
    for layer in result["layers"]:
        lines.append(
            f"  {layer['name']}: {layer['material']}, d = {float(layer['thickness_nm']):.6f} nm"
        )
    lines.extend(
        [
            "",
            "代表 COMSOL 验证点：",
        ]
    )
    for row in result["representative_points"]:
        lines.append(
            f"  lambda = {row['lambda_um']:.3f} um | R={row['R']:.6f}, "
            f"T={row['T']:.6f}, A/emissivity={row['emissivity']:.6f}"
        )
    lines.extend(
        [
            "",
            f"说明：{result['optical_constant_note_cn']}",
        ]
    )
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    saved["txt"] = str(txt_path)

    png_path = output_file(f"{prefix}_spectrum.png")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 3.0), gridspec_kw={"width_ratios": [1.9, 1.0]})
    _style_teaching_axis(ax1)
    _style_teaching_axis(ax2)
    ax1.axvspan(0.3, 2.5, color="#dbeafe", alpha=0.45, label="太阳波段 (0.3–2.5 μm)")
    ax1.axvspan(8.0, 13.0, color="#fee2e2", alpha=0.45, label="大气窗口 (8–13 μm)")
    ax1.plot(lambda_um, r_vals, color=MAIN_RED, linewidth=1.8, label="R (反射率)")
    ax1.plot(lambda_um, a_vals, color=ABS_GOLD, linewidth=1.8, label="A (吸收率) ≈ ε")
    ax1.plot(lambda_um, t_vals, color=TRANS_BLUE, linewidth=1.3, alpha=0.8, label="T (透射率)")
    ax1.set_xscale("log")
    ax1.set_xlim(0.3, 13.0)
    ax1.set_ylim(0.0, 1.02)
    ax1.set_xlabel("波长 (μm)", fontsize=7.5)
    ax1.set_ylabel("比值", fontsize=7.5)
    ax1.set_title("PDRC 宽波段光谱", fontsize=8.0, fontweight="semibold")
    ax1.legend(loc="lower left", fontsize=6.2, frameon=True, facecolor="white", edgecolor="#c9d2dc", framealpha=0.9)

    labels = ["太阳吸收", "大气窗口发射", "冷却得分"]
    values = [
        float(metrics["A_solar_avg"]),
        float(metrics["epsilon_8_13_avg"]),
        float(metrics["cooling_score"]),
    ]
    colors = [MAIN_RED, TARGET_GREEN, ABS_GOLD]
    bars = ax2.bar(labels, values, color=colors, alpha=0.86, width=0.55)
    ax2.axhline(0.15, color=MAIN_RED, linestyle=":", linewidth=1.1, label="基本目标 R")
    ax2.axhline(0.70, color=TARGET_GREEN, linestyle=":", linewidth=1.1, label="发射率目标")
    ax2.set_ylim(0.0, 1.02)
    ax2.set_ylabel("指标值", fontsize=7.5)
    ax2.set_title("调控指标", fontsize=8.0, fontweight="semibold")
    ax2.tick_params(axis="x", labelsize=6.8, rotation=12)
    for idx, val in enumerate(values):
        ax2.text(idx, min(1.0, val + 0.035), f"{val:.3f}", ha="center", va="bottom", fontsize=7.2, color=TEXT_DARK)

    fig.suptitle("被动日间辐射冷却薄膜光谱调控", fontsize=9.2, fontweight="semibold", color=TEXT_DARK)
    fig.tight_layout()
    save_publication_figure(fig, png_path)
    plt.close(fig)
    saved["png"] = str(png_path)

    manifest_path = output_file(f"{prefix}_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)
    saved["manifest"] = str(manifest_path)

    return saved


def export_rugate_comsol_layer_table(
    *,
    prefix: str = "rugate_80layer_comsol",
    lambda0_nm: float = 550.0,
    n_low: float = 1.38,
    n_high: float = 2.10,
    periods: int = 8,
    total_layers: int = 80,
) -> Dict[str, str]:
    """Export a COMSOL-friendly layer table for a sliced rugate filter.

    The current default matches the teaching-case rugate branch:
    - 8 spatial periods
    - 80 slices in total
    - therefore 10 slices per spatial period
    """

    periods = max(int(periods), 1)
    total_layers = max(int(total_layers), periods)
    if total_layers % periods != 0:
        raise ValueError("total_layers must be divisible by periods.")
    slices_per_period = total_layers // periods

    layers = build_rugate_filter_layers(
        lambda0_nm=float(lambda0_nm),
        n_low=complex(float(n_low), 0.0),
        n_high=complex(float(n_high), 0.0),
        periods=periods,
        slices_per_period=slices_per_period,
    )

    csv_path = output_file(f"{prefix}_layers.csv")
    json_path = output_file(f"{prefix}_layers.json")
    txt_path = output_file(f"{prefix}_layers.txt")

    rows: List[Dict[str, Any]] = []
    y_start_nm = 0.0
    for idx, layer in enumerate(layers, start=1):
        thickness_nm = float(layer.thickness_nm)
        y_end_nm = y_start_nm + thickness_nm
        n_real = float(np.real(layer.n))
        rows.append(
            {
                "layer_index": idx,
                "layer_name": layer.name,
                "n_real": n_real,
                "n_imag": float(np.imag(layer.n)),
                "eps_r": float(n_real ** 2),
                "thickness_nm": thickness_nm,
                "thickness_m": thickness_nm * 1e-9,
                "y_start_nm": y_start_nm,
                "y_end_nm": y_end_nm,
            }
        )
        y_start_nm = y_end_nm

    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write(
            "layer_index,layer_name,n_real,n_imag,eps_r,thickness_nm,thickness_m,y_start_nm,y_end_nm\n"
        )
        for row in rows:
            f.write(
                ",".join(
                    [
                        str(row["layer_index"]),
                        str(row["layer_name"]),
                        f"{float(row['n_real']):.12g}",
                        f"{float(row['n_imag']):.12g}",
                        f"{float(row['eps_r']):.12g}",
                        f"{float(row['thickness_nm']):.12g}",
                        f"{float(row['thickness_m']):.12g}",
                        f"{float(row['y_start_nm']):.12g}",
                        f"{float(row['y_end_nm']):.12g}",
                    ]
                )
                + "\n"
            )

    payload = {
        "lambda0_nm": float(lambda0_nm),
        "n_low": float(n_low),
        "n_high": float(n_high),
        "periods": periods,
        "total_layers": total_layers,
        "slices_per_period": slices_per_period,
        "rows": rows,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    lines = [
        "Rugate Filter 80-Layer COMSOL Table",
        "=" * 80,
        f"lambda0_nm        = {float(lambda0_nm):.6f}",
        f"n_low             = {float(n_low):.6f}",
        f"n_high            = {float(n_high):.6f}",
        f"periods           = {periods}",
        f"total_layers      = {total_layers}",
        f"slices_per_period = {slices_per_period}",
        "",
        "建议在 COMSOL 中按以下方式使用：",
        "1. 玻璃/空气之外的 rugate 区域拆成 80 个矩形层。",
        "2. 每层厚度使用 thickness_m 列。",
        "3. 每层折射率使用 n_real，或相对介电常数使用 eps_r。",
        "4. 每层的起止位置可直接参考 y_start_nm / y_end_nm。",
        "",
    ]
    for row in rows:
        lines.append(
            f"{int(row['layer_index']):02d} | {row['layer_name']} | n={row['n_real']:.6f} | "
            f"d={row['thickness_nm']:.6f} nm | y=[{row['y_start_nm']:.6f}, {row['y_end_nm']:.6f}] nm"
        )
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "txt": str(txt_path),
    }


@dataclass
class ReportDesignParams:
    """Structured parameters for simulate_report_design."""
    design_type: str = "single_ar"
    wavelengths_nm: Sequence[float] | None = None
    theta_deg: float = 0.0
    pol: str = "p"
    lambda0_nm: float = 550.0
    n_incident: float = 1.0
    n_substrate: float = 1.52
    n_low: float = 1.38
    n_porous: float = 1.18
    n_mid: float = 1.60
    n_high: float = 2.00
    n_high_2: float = 2.15
    k_incident: float = 0.0
    k_substrate: float = 0.0
    k_low: float = 0.0
    k_mid: float = 0.0
    k_high: float = 0.0
    k_high_2: float = 0.0
    periods: int = 3
    slices_per_period: int | None = None
    total_layers: int | None = None
    n_top: float = 1.10
    n_bottom: float = 1.50
    d_total_nm: float = 300.0
    num_gradient_layers: int = 5
    gradient_type: str = "linear"
    layer_indices: Sequence[float] | None = None
    layer_thickness_nm: Sequence[float] | None = None
    fp_spacer_kind: str = "L"
    beamsplitter_front_halfwave_low: bool = False


def simulate_report_design_from_params(params: ReportDesignParams) -> Dict[str, Any]:
    """Run a teaching TMM case from a ReportDesignParams instance."""
    return simulate_report_design(
        design_type=params.design_type,
        wavelengths_nm=params.wavelengths_nm,
        theta_deg=params.theta_deg,
        pol=params.pol,
        lambda0_nm=params.lambda0_nm,
        n_incident=params.n_incident,
        n_substrate=params.n_substrate,
        n_low=params.n_low,
        n_porous=params.n_porous,
        n_mid=params.n_mid,
        n_high=params.n_high,
        n_high_2=params.n_high_2,
        k_incident=params.k_incident,
        k_substrate=params.k_substrate,
        k_low=params.k_low,
        k_mid=params.k_mid,
        k_high=params.k_high,
        k_high_2=params.k_high_2,
        periods=params.periods,
        slices_per_period=params.slices_per_period,
        total_layers=params.total_layers,
        n_top=params.n_top,
        n_bottom=params.n_bottom,
        d_total_nm=params.d_total_nm,
        num_gradient_layers=params.num_gradient_layers,
        gradient_type=params.gradient_type,
        layer_indices=params.layer_indices,
        layer_thickness_nm=params.layer_thickness_nm,
        fp_spacer_kind=params.fp_spacer_kind,
        beamsplitter_front_halfwave_low=params.beamsplitter_front_halfwave_low,
    )


def simulate_report_design(
    design_type: str,
    wavelengths_nm: Sequence[float] | None = None,
    theta_deg: float = 0.0,
    pol: str = "p",
    lambda0_nm: float = 550.0,
    n_incident: float = 1.0,
    n_substrate: float = 1.52,
    n_low: float = 1.38,
    n_porous: float = 1.18,
    n_mid: float = 1.60,
    n_high: float = 2.00,
    n_high_2: float = 2.15,
    k_incident: float = 0.0,
    k_substrate: float = 0.0,
    k_low: float = 0.0,
    k_mid: float = 0.0,
    k_high: float = 0.0,
    k_high_2: float = 0.0,
    periods: int = 3,
    slices_per_period: int | None = None,
    total_layers: int | None = None,
    n_top: float = 1.10,
    n_bottom: float = 1.50,
    d_total_nm: float = 300.0,
    num_gradient_layers: int = 5,
    gradient_type: str = "linear",
    layer_indices: Sequence[float] | None = None,
    layer_thickness_nm: Sequence[float] | None = None,
    fp_spacer_kind: str = "L",
    beamsplitter_front_halfwave_low: bool = False,
) -> Dict[str, Any]:
    """High-level entry matching the report's teaching project."""
    if wavelengths_nm is None:
        wavelengths_nm = _default_wavelength_grid_for_design(design_type, lambda0_nm)
    wavelengths_nm = np.asarray(wavelengths_nm, dtype=float)

    n0 = _to_complex_index(n_incident, k_incident)
    ns = _to_complex_index(n_substrate, k_substrate)
    nl = _to_complex_index(n_low, k_low)
    nporous = _to_complex_index(n_porous, 0.0)
    nm = _to_complex_index(n_mid, k_mid)
    nh = _to_complex_index(n_high, k_high)
    nh2 = _to_complex_index(n_high_2, k_high_2)
    ntop = _to_complex_index(n_top, 0.0)
    nbottom = _to_complex_index(n_bottom, 0.0)

    key = str(design_type).strip().lower()
    if key in {"quarter_wave_single_layer", "qw_single_layer"}:
        layers = build_uniform_single_layer_layers(lambda0_nm, nl, optical_kind="quarter")
    elif key in {"half_wave_single_layer", "hw_single_layer"}:
        layers = build_uniform_single_layer_layers(lambda0_nm, nl, optical_kind="half")
    elif key in {"single_ar", "single_antireflection"}:
        layers = build_single_ar_layers(lambda0_nm, nl)
    elif key in {"porous_double_ar", "porous_double_layer", "porous_double_antireflection"}:
        layers = build_porous_double_ar_layers(lambda0_nm, nporous, nh)
    elif key in {"double_ar", "double_antireflection", "quarter_wave_double_layer"}:
        layers = build_double_ar_layers(lambda0_nm, nl, nh)
    elif key in {"triple_ar", "triple_antireflection"}:
        layers = build_triple_ar_layers(lambda0_nm, nm, nh2, nl)
    elif key in {"high_reflector", "high_reflection", "quarter_wave_stack", "bragg_reflector"}:
        layers = build_high_reflector_layers(lambda0_nm, nh2, nl, periods)
    elif key in {"fp_single_halfwave", "fp_shw", "fp_filter", "narrowband_filter"}:
        layers = build_fp_single_halfwave_layers(lambda0_nm, nh2, nl, periods, spacer_kind=fp_spacer_kind)
    elif key in {"fp_double_halfwave", "fp_dhw"}:
        layers = build_fp_double_halfwave_layers(lambda0_nm, nh2, nl, periods)
    elif key in {"moth_eye_effective_gradient", "moth_eye_gradient", "moth_eye"}:
        layers = build_moth_eye_effective_gradient_layers(
            ntop,
            nbottom,
            d_total_nm=float(d_total_nm),
            num_gradient_layers=int(num_gradient_layers),
            gradient_type=gradient_type,
            layer_indices=layer_indices,
            layer_thickness_nm=layer_thickness_nm,
        )
    elif key in {"rugate_filter", "rugate"}:
        effective_slices_per_period = slices_per_period
        if effective_slices_per_period is None and total_layers is not None:
            total_layers = max(int(total_layers), int(periods))
            if total_layers % max(int(periods), 1) != 0:
                raise ValueError("For rugate_filter, total_layers must be divisible by periods.")
            effective_slices_per_period = total_layers // max(int(periods), 1)
        if effective_slices_per_period is None:
            effective_slices_per_period = 24
        layers = build_rugate_filter_layers(
            lambda0_nm,
            nl,
            nh2,
            periods,
            slices_per_period=int(effective_slices_per_period),
        )
    elif key in {"neutral_beamsplitter", "beamsplitter"}:
        layers = build_neutral_beamsplitter_layers(
            lambda0_nm,
            nh2,
            nl,
            use_front_halfwave_low=beamsplitter_front_halfwave_low,
        )
    else:
        raise ValueError(f"Unsupported design_type: {design_type}")

    spectrum = multilayer_rt_spectrum(
        wavelengths_nm=wavelengths_nm,
        layers=layers,
        n_incident=n0,
        n_substrate=ns,
        theta0_deg=theta_deg,
        pol=pol,
    )

    peak_r_idx = int(np.argmax(spectrum["R"]))
    valley_r_idx = int(np.argmin(spectrum["R"]))
    peak_t_idx = int(np.argmax(spectrum["T"]))
    result: Dict[str, Any] = {
        "design_type": key,
        "theta_deg": float(theta_deg),
        "pol": str(pol),
        "lambda0_nm": float(lambda0_nm),
        "n_incident": n0,
        "n_substrate": ns,
        "layers": describe_layers(layers),
        **spectrum,
        "summary": {
            "R_at_lambda0": float(np.interp(float(lambda0_nm), spectrum["wavelength_nm"], spectrum["R"])),
            "T_at_lambda0": float(np.interp(float(lambda0_nm), spectrum["wavelength_nm"], spectrum["T"])),
            "A_at_lambda0": float(np.interp(float(lambda0_nm), spectrum["wavelength_nm"], spectrum["A"])),
            "R_min": float(np.min(spectrum["R"])),
            "R_min_wavelength_nm": float(spectrum["wavelength_nm"][valley_r_idx]),
            "R_max": float(np.max(spectrum["R"])),
            "R_max_wavelength_nm": float(spectrum["wavelength_nm"][peak_r_idx]),
            "T_max": float(np.max(spectrum["T"])),
            "T_max_wavelength_nm": float(spectrum["wavelength_nm"][peak_t_idx]),
        },
    }
    result["figure_explanations"] = generate_case_figure_explanations(result)
    return result


def _default_real_material_map_for_design(design_type: str) -> Dict[str, str]:
    key = str(design_type).strip().lower()
    material_map: Dict[str, str] = {
        "n_incident": "Air",
        "n_substrate": "SiO2",
        "n_low": "SiO2",
        "n_mid": "Al2O3",
        "n_high": "TiO2",
        "n_high_2": "TiO2",
    }
    if key in {"quarter_wave_single_layer", "qw_single_layer", "half_wave_single_layer", "hw_single_layer", "single_ar", "single_antireflection"}:
        material_map["n_low"] = "MgF2"
    return material_map


def _used_real_material_names(material_map: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for value in material_map.values():
        if isinstance(value, str):
            material = canonical_material_name(value)
            if material != "Air":
                names.append(material)
    return names


def _reconstruct_layers(layer_rows: Sequence[Dict[str, Any]]) -> List[LayerSpec]:
    layers: List[LayerSpec] = []
    for row in layer_rows:
        n_value = complex(float(row.get("n_real", 0.0)), float(row.get("n_imag", 0.0)))
        layers.append(LayerSpec(str(row["name"]), n_value, float(row["thickness_nm"])))
    return layers


def _summary_from_spectrum(spectrum: Dict[str, np.ndarray], lambda0_nm: float) -> Dict[str, float]:
    peak_r_idx = int(np.argmax(spectrum["R"]))
    valley_r_idx = int(np.argmin(spectrum["R"]))
    peak_t_idx = int(np.argmax(spectrum["T"]))
    
    wls = np.asarray(spectrum["wavelength_nm"], dtype=float)
    r_vals = np.asarray(spectrum["R"], dtype=float)
    t_vals = np.asarray(spectrum["T"], dtype=float)
    a_vals = np.asarray(spectrum["A"], dtype=float)
    
    if len(wls) > 1 and np.any(np.diff(wls) < 0):
        sort_idx = np.argsort(wls)
        wls = wls[sort_idx]
        r_vals = r_vals[sort_idx]
        t_vals = t_vals[sort_idx]
        a_vals = a_vals[sort_idx]
        
    return {
        "R_at_lambda0": float(np.interp(float(lambda0_nm), wls, r_vals)),
        "T_at_lambda0": float(np.interp(float(lambda0_nm), wls, t_vals)),
        "A_at_lambda0": float(np.interp(float(lambda0_nm), wls, a_vals)),
        "R_min": float(np.min(spectrum["R"])),
        "R_min_wavelength_nm": float(spectrum["wavelength_nm"][valley_r_idx]),
        "R_max": float(np.max(spectrum["R"])),
        "R_max_wavelength_nm": float(spectrum["wavelength_nm"][peak_r_idx]),
        "T_max": float(np.max(spectrum["T"])),
        "T_max_wavelength_nm": float(spectrum["wavelength_nm"][peak_t_idx]),
    }


def simulate_report_design_real_materials(
    design_type: str,
    *,
    material_map: Dict[str, Any] | None = None,
    wavelengths_nm: Sequence[float] | None = None,
    allow_extrapolate: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Run a teaching TMM case with wavelength-dependent real n/k data.

    Layer thicknesses are designed at ``lambda0_nm`` using the real material
    index at the design wavelength.  The spectrum is then evaluated with
    interpolated ``n(lambda), k(lambda)`` values for every wavelength point.
    """
    key = str(design_type).strip().lower()
    lambda0_nm = float(kwargs.get("lambda0_nm", 550.0))
    merged_material_map: Dict[str, Any] = _default_real_material_map_for_design(key)
    if material_map:
        merged_material_map.update(material_map)

    if wavelengths_nm is None:
        base_grid = np.asarray(_default_wavelength_grid_for_design(key, lambda0_nm), dtype=float)
        materials = _used_real_material_names(merged_material_map)
        if materials:
            lower_um, upper_um = common_wavelength_window_um(materials)
            mask = (base_grid >= lower_um * 1000.0) & (base_grid <= upper_um * 1000.0)
            wavelengths_nm = base_grid[mask]
            if len(wavelengths_nm) < 5:
                wavelengths_nm = np.linspace(max(lower_um * 1000.0, 400.0), min(upper_um * 1000.0, 750.0), 251)
        else:
            wavelengths_nm = base_grid
    wavelengths_nm = np.asarray(wavelengths_nm, dtype=float)

    role_defaults: Dict[str, complex] = {
        "n_incident": _to_complex_index(float(kwargs.get("n_incident", 1.0)), float(kwargs.get("k_incident", 0.0))),
        "n_substrate": _to_complex_index(float(kwargs.get("n_substrate", 1.52)), float(kwargs.get("k_substrate", 0.0))),
        "n_low": _to_complex_index(float(kwargs.get("n_low", 1.38)), float(kwargs.get("k_low", 0.0))),
        "n_porous": _to_complex_index(float(kwargs.get("n_porous", 1.18)), 0.0),
        "n_mid": _to_complex_index(float(kwargs.get("n_mid", 1.60)), float(kwargs.get("k_mid", 0.0))),
        "n_high": _to_complex_index(float(kwargs.get("n_high", 2.00)), float(kwargs.get("k_high", 0.0))),
        "n_high_2": _to_complex_index(float(kwargs.get("n_high_2", 2.15)), float(kwargs.get("k_high_2", 0.0))),
    }

    design_role_indices = {
        role: _material_or_constant_index(
            role,
            lambda0_nm,
            merged_material_map,
            fallback,
            allow_extrapolate=allow_extrapolate,
        )
        for role, fallback in role_defaults.items()
    }

    design_kwargs = dict(kwargs)
    for role, index in design_role_indices.items():
        if role == "n_incident":
            design_kwargs["n_incident"] = float(np.real(index))
            design_kwargs["k_incident"] = float(np.imag(index))
        elif role == "n_substrate":
            design_kwargs["n_substrate"] = float(np.real(index))
            design_kwargs["k_substrate"] = float(np.imag(index))
        elif role == "n_low":
            design_kwargs["n_low"] = float(np.real(index))
            design_kwargs["k_low"] = float(np.imag(index))
        elif role == "n_mid":
            design_kwargs["n_mid"] = float(np.real(index))
            design_kwargs["k_mid"] = float(np.imag(index))
        elif role == "n_high":
            design_kwargs["n_high"] = float(np.real(index))
            design_kwargs["k_high"] = float(np.imag(index))
        elif role == "n_high_2":
            design_kwargs["n_high_2"] = float(np.real(index))
            design_kwargs["k_high_2"] = float(np.imag(index))
        elif role == "n_porous":
            design_kwargs["n_porous"] = float(np.real(index))

    constant_design = simulate_report_design(
        design_type=key,
        wavelengths_nm=wavelengths_nm,
        **design_kwargs,
    )
    fixed_layers = _reconstruct_layers(constant_design["layers"])
    spectrum = multilayer_rt_spectrum_real_materials(
        wavelengths_nm=wavelengths_nm,
        layers=fixed_layers,
        design_type=key,
        material_map=merged_material_map,
        role_fallback_indices=design_role_indices,
        theta0_deg=float(design_kwargs.get("theta_deg", 0.0)),
        pol=str(design_kwargs.get("pol", "p")),
        allow_extrapolate=allow_extrapolate,
    )

    result = dict(constant_design)
    result.update(spectrum)
    result["summary"] = _summary_from_spectrum(spectrum, lambda0_nm)
    result["layers"] = describe_layers(fixed_layers)
    result["material_model"] = "real_nk"
    result["material_map"] = {
        key_: str(value) if isinstance(value, str) else value
        for key_, value in merged_material_map.items()
    }
    result["design_indices_at_lambda0"] = {
        role: {
            "n": float(np.real(index)),
            "k": float(np.imag(index)),
        }
        for role, index in design_role_indices.items()
    }
    result["figure_explanations"] = generate_case_figure_explanations(result)
    return result


def list_report_chapter2_cases() -> List[Dict[str, Any]]:
    """Return the report chapter-2 menu structure as a Python-friendly catalog."""
    rows: List[Dict[str, Any]] = []
    for case_id, item in REPORT_CHAPTER2_CASES.items():
        rows.append(
            {
                "case_id": case_id,
                "title_cn": item["title_cn"],
                "title_en": item["title_en"],
                "design_type": item["design_type"],
                "default_params": dict(item["default_params"]),
            }
        )
    return rows


def list_report_comparison_figures_catalog() -> List[Dict[str, Any]]:
    """Return the report-style comparison figure catalog for the main branch."""
    rows: List[Dict[str, Any]] = []
    for figure_id, item in REPORT_COMPARISON_FIGURES.items():
        rows.append(
            {
                "figure_id": figure_id,
                "title_cn": item["title_cn"],
                "title_en": item["title_en"],
                "ylabel": item["ylabel"],
            }
        )
    return rows


def get_report_main_branch_catalog() -> Dict[str, Any]:
    """Return a UI-friendly catalog for the whole teaching main branch."""
    cases = list_report_chapter2_cases()
    case_map = {item["case_id"]: item for item in cases}
    preview_results = simulate_report_chapter2_suite()
    cards: List[Dict[str, Any]] = []
    card_map: Dict[str, Dict[str, Any]] = {}
    display_order_map = {case_id: idx for idx, case_id in enumerate(REPORT_CASE_DISPLAY_ORDER, start=1)}
    for item in cases:
        case_id = item["case_id"]
        meta = REPORT_CASE_UI_META.get(case_id, {})
        result = preview_results[case_id]
        summary = result["summary"]
        main_curve = meta.get("main_curve", "R")
        if main_curve == "T":
            hero_metric = {
                "name": "T_at_lambda0",
                "label_cn": "中心透射率",
                "label_en": "Center Transmittance",
                "value": float(summary["T_at_lambda0"]),
                "display": f"{float(summary['T_at_lambda0']) * 100:.2f}%",
            }
        else:
            hero_metric = {
                "name": "R_at_lambda0",
                "label_cn": "中心反射率",
                "label_en": "Center Reflectance",
                "value": float(summary["R_at_lambda0"]),
                "display": f"{float(summary['R_at_lambda0']) * 100:.2f}%",
            }
        card = {
            "case_id": case_id,
            "display_order": display_order_map.get(case_id, 999),
            "title_cn": item["title_cn"],
            "title_en": item["title_en"],
            "headline_cn": meta.get("headline_cn", item["title_cn"]),
            "headline_en": meta.get("headline_en", item["title_en"]),
            "section_id": next(
                (
                    section["section_id"]
                    for section in REPORT_MAIN_BRANCH_SECTIONS
                    if case_id in section["case_ids"]
                ),
                "",
            ),
            "summary_cn": meta.get("summary_cn", ""),
            "summary_en": meta.get("summary_en", ""),
            "card_tag_cn": meta.get("card_tag_cn", ""),
            "card_tag_en": meta.get("card_tag_en", ""),
            "hero_metric": hero_metric,
            "secondary_metrics": [
                {
                    "name": "theta_deg",
                    "label_cn": "入射角",
                    "label_en": "Incident Angle",
                    "value": float(result["theta_deg"]),
                    "display": f"{float(result['theta_deg']):.0f} deg",
                },
                {
                    "name": "lambda0_nm",
                    "label_cn": "中心波长",
                    "label_en": "Center Wavelength",
                    "value": float(result["lambda0_nm"]),
                    "display": f"{float(result['lambda0_nm']):.0f} nm",
                },
            ],
            "preview_main_png": str(output_file(f"teaching_case_{case_id}_main.png")),
            "preview_rta_png": str(output_file(f"teaching_case_{case_id}_RTA.png")),
        }
        cards.append(card)
        card_map[case_id] = card
    cards.sort(key=lambda item: int(item["display_order"]))
    sections: List[Dict[str, Any]] = []
    for section in REPORT_MAIN_BRANCH_SECTIONS:
        section_cases: List[Dict[str, Any]] = []
        for case_id in section["case_ids"]:
            if case_id not in case_map or case_id not in card_map:
                continue
            section_cases.append(
                {
                    **card_map[case_id],
                    "design_type": case_map[case_id]["design_type"],
                    "default_params": dict(case_map[case_id]["default_params"]),
                }
            )
        sections.append(
            {
                "section_id": section["section_id"],
                "title_cn": section["title_cn"],
                "title_en": section["title_en"],
                "summary_cn": section.get("summary_cn", ""),
                "summary_en": section.get("summary_en", ""),
                "case_count": len(section_cases),
                "featured_case_id": section_cases[0]["case_id"] if section_cases else "",
                "cases": section_cases,
            }
        )

    case_controls: Dict[str, List[Dict[str, Any]]] = {}
    case_form_groups: Dict[str, List[Dict[str, Any]]] = {}
    for item in cases:
        controls: List[Dict[str, Any]] = []
        grouped_controls: Dict[str, List[Dict[str, Any]]] = {}
        for key, value in item["default_params"].items():
            meta = REPORT_PARAM_SCHEMA.get(key, {"label_cn": key, "label_en": key, "type": "str"})
            control = {
                "name": key,
                "label_cn": meta["label_cn"],
                "label_en": meta["label_en"],
                "type": meta["type"],
                "default": value,
            }
            for extra_key in (
                "unit",
                "choices",
                "widget",
                "group",
                "min",
                "max",
                "step",
                "recommended",
                "required",
                "help_cn",
                "help_en",
            ):
                if extra_key in meta:
                    control[extra_key] = meta[extra_key]
            if "choices" in control:
                control["choices"] = list(control["choices"])
            controls.append(control)
            group_id = str(control.get("group", "general"))
            grouped_controls.setdefault(group_id, []).append(control)
        case_controls[item["case_id"]] = controls
        form_groups: List[Dict[str, Any]] = []
        for group_id in ("general", "materials", "structure"):
            members = grouped_controls.get(group_id, [])
            if not members:
                continue
            meta = REPORT_CONTROL_GROUP_META.get(
                group_id,
                {"title_cn": group_id, "title_en": group_id},
            )
            form_groups.append(
                {
                    "group_id": group_id,
                    "title_cn": meta["title_cn"],
                    "title_en": meta["title_en"],
                    "controls": members,
                }
            )
        case_form_groups[item["case_id"]] = form_groups

    comparison_order_map = {
        figure_id: idx for idx, figure_id in enumerate(REPORT_COMPARISON_DISPLAY_ORDER, start=1)
    }
    comparison_cards: List[Dict[str, Any]] = []
    for item in list_report_comparison_figures_catalog():
        figure_id = item["figure_id"]
        meta = REPORT_COMPARISON_UI_META.get(figure_id, {})
        ylabel = str(item["ylabel"])
        metric_label_cn = "主显示量"
        metric_label_en = "Primary Axis"
        metric_display = ylabel
        if ylabel == "R":
            metric_label_cn = "主显示量"
            metric_label_en = "Primary Axis"
            metric_display = "R"
        elif ylabel == "T":
            metric_label_cn = "主显示量"
            metric_label_en = "Primary Axis"
            metric_display = "T"
        comparison_cards.append(
            {
                "figure_id": figure_id,
                "display_order": comparison_order_map.get(figure_id, 999),
                "title_cn": item["title_cn"],
                "title_en": item["title_en"],
                "headline_cn": meta.get("headline_cn", item["title_cn"]),
                "headline_en": meta.get("headline_en", item["title_en"]),
                "summary_cn": meta.get("summary_cn", ""),
                "summary_en": meta.get("summary_en", ""),
                "card_tag_cn": meta.get("card_tag_cn", ""),
                "card_tag_en": meta.get("card_tag_en", ""),
                "related_case_ids": list(meta.get("related_case_ids", [])),
                "hero_metric": {
                    "name": "series_count",
                    "label_cn": "对比曲线数",
                    "label_en": "Series Count",
                    "value": int(meta.get("series_count", 0)),
                    "display": str(int(meta.get("series_count", 0))),
                },
                "secondary_metrics": [
                    {
                        "name": "sweep_parameter",
                        "label_cn": "扫描参数",
                        "label_en": "Sweep Parameter",
                        "value": str(meta.get("sweep_parameter", "")),
                        "display": str(meta.get("sweep_label_cn", meta.get("sweep_parameter", ""))),
                    },
                    {
                        "name": "primary_axis",
                        "label_cn": metric_label_cn,
                        "label_en": metric_label_en,
                        "value": ylabel,
                        "display": metric_display,
                    },
                ],
                "ylabel": ylabel,
                "preview_png": str(output_file(f"teaching_compare_{figure_id}.png")),
                "source_csv": str(output_file(f"teaching_compare_{figure_id}.csv")),
            }
        )
    comparison_cards.sort(key=lambda item: int(item["display_order"]))
    comparison_card_map = {item["figure_id"]: item for item in comparison_cards}
    comparison_groups: List[Dict[str, Any]] = []
    for group in REPORT_COMPARISON_GROUPS:
        group_cards = [
            comparison_card_map[figure_id]
            for figure_id in group["figure_ids"]
            if figure_id in comparison_card_map
        ]
        comparison_groups.append(
            {
                "group_id": group["group_id"],
                "title_cn": group["title_cn"],
                "title_en": group["title_en"],
                "comparison_count": len(group_cards),
                "featured_figure_id": group_cards[0]["figure_id"] if group_cards else "",
                "comparisons": group_cards,
            }
        )

    return {
        "branch_id": "main_teaching_branch",
        "title_cn": "设计报告主树",
        "title_en": "Teaching Report Main Branch",
        "chapter": "report_chapter2",
        "platform_scope": {
            "mode": "teaching_forward_only",
            "show_thickness_inversion": False,
            "show_research_branches": False,
            "notes_cn": "教学平台当前只暴露正向仿真、案例导出、对比图和目录配置，不暴露厚度反演入口。",
            "notes_en": "The teaching platform exposes forward simulation, exports, comparison figures, and catalog metadata only; thickness inversion is intentionally hidden.",
        },
        "home_cards": cards,
        "home_summary": {
            "case_count": len(cards),
            "section_count": len(REPORT_MAIN_BRANCH_SECTIONS),
            "comparison_count": len(REPORT_COMPARISON_FIGURES),
            "featured_case_id": cards[0]["case_id"] if cards else "",
        },
        "comparison_summary": {
            "comparison_count": len(comparison_cards),
            "featured_figure_id": comparison_cards[0]["figure_id"] if comparison_cards else "",
        },
        "output_dir": str(OUTPUT_DIR),
        "default_files": {
            "catalog_json": str(output_file("teaching_main_branch_catalog.json")),
            "case_index_csv": str(output_file("teaching_report_case_index.csv")),
            "manifest_json": str(output_file("teaching_report_bundle_manifest.json")),
            "manifest_txt": str(output_file("teaching_report_bundle_manifest.txt")),
        },
        "form_ui_meta": {
            "supported_widgets": ["number", "select", "slider", "segmented", "switch"],
            "render_order": ["general", "materials", "structure"],
            "number_input_note_cn": "数值型参数建议显示单位、步长与推荐值。",
            "number_input_note_en": "Numeric controls should display unit, step, and recommended value.",
        },
        "sections": sections,
        "comparisons": comparison_cards,
        "comparison_groups": comparison_groups,
        "case_controls": case_controls,
        "case_form_groups": case_form_groups,
        "cli_examples": {
            "list_cases": "python run_teaching_demo.py --list",
            "export_catalog": "python run_teaching_demo.py --catalog",
            "export_case": "python run_teaching_demo.py --case single_ar",
            "export_compare": "python run_teaching_demo.py --compare",
            "export_report_bundle": "python run_teaching_demo.py --report",
        },
        "recommended_actions": [
            {
                "action_id": "export_case",
                "title_cn": "导出单个案例",
                "title_en": "Export Single Case",
            },
            {
                "action_id": "export_suite",
                "title_cn": "导出第2章全部案例",
                "title_en": "Export Full Chapter-2 Suite",
            },
            {
                "action_id": "export_compare",
                "title_cn": "导出多曲线对比图",
                "title_en": "Export Comparison Figures",
            },
            {
                "action_id": "export_report_bundle",
                "title_cn": "导出主树报告包",
                "title_en": "Export Main-Branch Report Bundle",
            },
        ],
    }


def export_report_main_branch_catalog(
    filename: str = "teaching_main_branch_catalog.json",
) -> Dict[str, Any]:
    """Export the UI-friendly main-branch catalog to JSON."""
    catalog = get_report_main_branch_catalog()
    json_path = output_file(filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    catalog["catalog_json"] = str(json_path)
    return catalog


def simulate_report_case(
    case_id: str,
    **overrides: Any,
) -> Dict[str, Any]:
    """Run one chapter-2 preset case from the design report."""
    key = str(case_id).strip()
    if key not in REPORT_CHAPTER2_CASES:
        raise ValueError(f"Unsupported report case_id: {case_id}")

    item = REPORT_CHAPTER2_CASES[key]
    params = dict(item["default_params"])
    params.update(overrides)
    result = simulate_report_design(
        design_type=item["design_type"],
        **params,
    )
    result["case_id"] = key
    result["title_cn"] = item["title_cn"]
    result["title_en"] = item["title_en"]
    result["figure_explanations"] = generate_case_figure_explanations(result)
    return result


def simulate_report_chapter2_suite(
    wavelengths_nm: Sequence[float] | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Run the whole chapter-2 menu set with default parameters."""
    results: Dict[str, Dict[str, Any]] = {}
    for case_id in REPORT_CHAPTER2_CASES:
        kwargs: Dict[str, Any] = {}
        if wavelengths_nm is not None:
            kwargs["wavelengths_nm"] = wavelengths_nm
        results[case_id] = simulate_report_case(case_id, **kwargs)
    return results


def _case_output_stem(result: Dict[str, Any], prefix: str = "teaching_case") -> str:
    case_id = str(result.get("case_id") or result.get("design_type") or "case")
    return f"{prefix}_{case_id}"


def _main_curve_kind_for_case(
    result: Dict[str, Any],
    r_vals: Sequence[float] | None = None,
    t_vals: Sequence[float] | None = None,
    a_vals: Sequence[float] | None = None,
) -> str:
    key = str(result.get("case_id") or result.get("design_type") or "").strip().lower()
    return infer_rta_focus(
        [] if r_vals is None else r_vals,
        [] if t_vals is None else t_vals,
        [] if a_vals is None else a_vals,
        context=key,
    )


def _style_teaching_axis(ax: plt.Axes) -> None:
    ax.set_facecolor(PANEL_BG)
    ax.grid(False)
    for side, spine in ax.spines.items():
        spine.set_visible(side in {"left", "bottom"})
        spine.set_color(TEXT_DARK)
        spine.set_linewidth(0.8)
    ax.tick_params(colors=TEXT_DARK)
    ax.xaxis.label.set_color(TEXT_DARK)
    ax.yaxis.label.set_color(TEXT_DARK)
    ax.title.set_color(TEXT_DARK)


def _case_analysis_lines(result: Dict[str, Any]) -> list[str]:
    summary = result["summary"]
    lambda0_nm = float(result["lambda0_nm"])
    key = str(result.get("case_id") or result.get("design_type") or "").strip().lower()

    r_center = float(summary['R_at_lambda0'])
    t_center = float(summary['T_at_lambda0'])
    a_center = float(summary['A_at_lambda0'])

    lines = [
        f"设计中心波长 = {lambda0_nm:.1f} nm",
        f"中心波长反射率 (R) = {r_center*100:.2f}%",
        f"中心波长透射率 (T) = {t_center*100:.2f}%",
    ]
    if "fp_" in key or key in {"fp_filter", "narrowband_filter"}:
        peak_wl = float(summary["T_max_wavelength_nm"])
        t_max = float(summary['T_max'])
        lines.append(f"极大透射率: {t_max*100:.2f}% (于 {peak_wl:.1f} nm)")
        lines.append(f"共振峰波长偏差 = {peak_wl - lambda0_nm:+.2f} nm")
    elif "beamsplitter" in key:
        split_err = float(summary["R_at_lambda0"]) - 0.5
        lines.append(f"中心波长吸收率 (A) = {a_center*100:.2f}%")
        lines.append(f"偏离 50/50 分束值 = {split_err*100:+.2f}%")
    elif any(term in key for term in ("reflector", "mirror", "bragg", "quarter_wave_stack")):
        peak_wl = float(summary["R_max_wavelength_nm"])
        r_max = float(summary['R_max'])
        lines.append(f"极大反射率: {r_max*100:.2f}% (于 {peak_wl:.1f} nm)")
        lines.append(f"反射带中心波长偏差 = {peak_wl - lambda0_nm:+.2f} nm")
    else:
        valley_wl = float(summary["R_min_wavelength_nm"])
        r_min = float(summary['R_min'])
        lines.append(f"极小反射率: {r_min*100:.3f}% (于 {valley_wl:.1f} nm)")
        lines.append(f"反射极小值波长偏差 = {valley_wl - lambda0_nm:+.2f} nm")
    # B: Add A reference + energy conservation check for all cases
    if "beamsplitter" not in key:  # beamsplitter branch already shows A above
        lines.append(f"吸收率 (A) = {a_center*100:.2f}%  [参考]")
    lines.append(f"能量守恒: R+T+A = {(r_center + t_center + a_center)*100:.1f}%")
    return lines


def generate_case_figure_explanations(result: Dict[str, Any]) -> Dict[str, str]:
    """Generate physically rigorous and layperson-friendly figure annotations."""
    key = str(result.get("case_id") or result.get("design_type") or "").strip().lower()
    lambda0_nm = float(result.get("lambda0_nm", 550.0))
    summary = result.get("summary", {})

    # 1. RTA spectrum explanation
    rta_title = "光谱响应曲线图 (RTA Spectrum)"
    if "beamsplitter" in key:
        rta_desc = (
            f"该光谱图展示了中性分束镜在不同波长下的反射率（R，蓝色）、透射率（T，青色）与吸收率（A，紫色）。"
            f"设计目标是在设计波长（{lambda0_nm:.1f} nm）处，使反射率与透射率尽量对半分流（即各占约 50%）。"
            f"曲线整体较为平坦，确保入射的白光或宽带光不会因为分束产生严重的偏色。"
        )
    elif "ar" in key or "antireflection" in key:
        rta_desc = (
            f"该光谱图展示了增透（减反射）膜层在可见光波段内的宏观光学表现。"
            f"反射率（R，蓝色）在设计中心波长 {lambda0_nm:.1f} nm 处降到极低值，"
            f"而透射率（T，青色）相应地提升到极高值，从而将绝大部分入射光能量导向透射方向，起到了高效增透的效果。"
        )
    elif any(term in key for term in ("reflector", "mirror", "bragg", "quarter_wave_stack")):
        rta_desc = (
            f"该光谱图展示了高反射镜（分布式布拉格反射镜 DBR）的宏观反射禁带。"
            f"在设计中心波长 {lambda0_nm:.1f} nm 附近，多层高低折射率反射界面的相长干涉叠加，"
            f"形成了一个宽阔且平坦的高反射区域（反射率 R 接近 100%）。该高反射区域的宽度在物理上被称为反射停带宽度。"
        )
    elif "fp_" in key or "filter" in key:
        rta_desc = (
            f"该光谱图展示了窄带滤光片的光谱特征。"
            f"在设计中心波长 {lambda0_nm:.1f} nm 处，出现了一个极其陡峭且对称的透射共振峰（透射率 T 接近 100%），"
            f"而在共振峰两侧的截止区，透射率迅速降至 0%，从而实现了极窄频带波长的精准选择与过滤。"
        )
    else:
        rta_desc = (
            f"该光谱图展示了薄膜器件在工作波段内反射率（R）、透射率（T）与吸收率（A）的光谱表现。"
            f"设计聚焦于满足中心波长 {lambda0_nm:.1f} nm 处的反射极值或特定能量分流指标。"
        )

    # 2. Analysis plot explanation
    analysis_title = "微观物理分析图 (Physical Analysis)"
    if "fp_" in key or "filter" in key:
        analysis_title = "微观一维电场驻波分布分析图"
        analysis_desc = (
            f"此图展示了在共振透射波长下，入射电磁波在薄膜各层介质内部的空间电场强度局域分布 |E(z)|^2（以入射场强为 1 进行归一化）。"
            f"可以清晰看到，在低折射率的半波长谐振腔（Spacer 层）中心处出现了极陡峭的电场局域化尖峰，场强被放大了数倍甚至数十倍。"
            f"这从微观上揭示了光学共振腔依靠局部驻波极大增强以实现相长干涉完全透射的物理机制。"
        )
    else:
        analysis_title = "设计指标能量分配与谱线对齐评估条形图"
        r_at = float(summary.get("R_at_lambda0", 0.0)) * 100
        t_at = float(summary.get("T_at_lambda0", 0.0)) * 100
        a_at = float(summary.get("A_at_lambda0", 0.0)) * 100
        
        if any(term in key for term in ("reflector", "mirror", "bragg", "quarter_wave_stack")):
            delta_wl = float(summary.get("R_max_wavelength_nm", lambda0_nm)) - lambda0_nm
            feature_name = "反射峰"
        else:
            delta_wl = float(summary.get("R_min_wavelength_nm", lambda0_nm)) - lambda0_nm
            feature_name = "反射谷"
            
        analysis_desc = (
            f"左图（中心波长指标）评估了在目标设计波长 {lambda0_nm:.1f} nm 处的能量精确分配：反射率 R = {r_at:.2f}%，透射率 T = {t_at:.2f}%，吸收率 A = {a_at:.2f}%，体现了能量守恒。"
            f"右图（谱线对齐）对比了设计的中心波长与计算得到的实际{feature_name}位置（两者波长差为 Δλ = {delta_wl:+.2f} nm）。"
            f"该差值越接近 0 nm，表明该器件抗材料色散漂移的性能越优异，镀膜厚度工艺控制精度越高。"
        )

    return {
        "rta_title": rta_title,
        "rta_desc": rta_desc,
        "analysis_title": analysis_title,
        "analysis_desc": analysis_desc
    }


def _default_wavelength_grid_for_design(
    design_type: str,
    lambda0_nm: float,
) -> np.ndarray:
    key = str(design_type).strip().lower()
    if "fp_" in key or key in {"fp_filter", "narrowband_filter"}:
        return np.arange(400.0, 750.0 + 1e-12, 1.0)
    if key in {"single_ar", "double_ar", "triple_ar", "neutral_beamsplitter"}:
        return np.arange(400.0, 750.0 + 1e-12, 2.0)
    return np.arange(400.0, 750.0 + 1e-12, 2.0)


def _main_plot_xlim_for_case(result: Dict[str, Any]) -> tuple[float, float] | None:
    key = str(result.get("case_id") or result.get("design_type") or "").strip().lower()
    lambda0_nm = float(result["lambda0_nm"])
    if "fp_" in key or key in {"fp_filter", "narrowband_filter"}:
        return (max(400.0, lambda0_nm - 70.0), min(750.0, lambda0_nm + 70.0))
    return None


def export_report_case_outputs(
    result: Dict[str, Any],
    prefix: str = "teaching_case",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, str]:
    """Export one chapter-2 case to plot/data/report files."""
    stem = _case_output_stem(result, prefix=prefix)
    saved: Dict[str, str] = {}

    wavelength_nm = np.asarray(result["wavelength_nm"], dtype=float)
    r_vals = np.asarray(result["R"], dtype=float)
    t_vals = np.asarray(result["T"], dtype=float)
    a_vals = np.asarray(result["A"], dtype=float)

    audit_focus = _main_curve_kind_for_case(result, r_vals, t_vals, a_vals)
    audit_key = str(result.get("case_id") or result.get("design_type") or "").lower()
    if audit_focus in {"T", "A"} or any(term in audit_key for term in ("reflector", "mirror", "bragg", "quarter_wave_stack")):
        audit_feature_kind = "peak"
        audit_feature_wavelength = float(wavelength_nm[int(np.argmax({"R": r_vals, "T": t_vals, "A": a_vals}[audit_focus]))])
    else:
        audit_feature_kind = "valley"
        audit_feature_wavelength = float(wavelength_nm[int(np.argmin({"R": r_vals, "T": t_vals, "A": a_vals}[audit_focus]))])
    audit = build_figure_audit(
        figure_id=f"{stem}_main",
        title=str(result.get("title_cn") or result.get("title_en") or stem),
        evidence_level="theory",
        checks=[audit_rta_data(
            wavelength_nm, r_vals, t_vals, a_vals,
            focus=audit_focus,
            feature_kind=audit_feature_kind,
            feature_wavelength=audit_feature_wavelength,
        )],
    )
    audit_path = output_file(f"{stem}_figure_audit.json")
    saved["audit_json"] = write_figure_audit(audit_path, audit)

    if save_csv:
        csv_path = output_file(f"{stem}_spectrum.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write("wavelength_nm,R,T,A\n")
            for wl, rv, tv, av in zip(wavelength_nm, r_vals, t_vals, a_vals):
                f.write(f"{wl:.12g},{rv:.12g},{tv:.12g},{av:.12g}\n")
        saved["csv"] = str(csv_path)

    if save_json:
        json_path = output_file(f"{stem}_summary.json")
        payload = {
            "case_id": result.get("case_id"),
            "title_cn": result.get("title_cn"),
            "title_en": result.get("title_en"),
            "design_type": result.get("design_type"),
            "theta_deg": float(result["theta_deg"]),
            "pol": str(result["pol"]),
            "lambda0_nm": float(result["lambda0_nm"]),
            "layers": result["layers"],
            "summary": result["summary"],
            "figure_explanations": result.get("figure_explanations", {}),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        saved["json"] = str(json_path)

    if save_txt:
        txt_path = output_file(f"{stem}_summary.txt")
        summary = result["summary"]
        lines = [
            f"case_id      = {result.get('case_id', result.get('design_type'))}",
            f"title_cn     = {result.get('title_cn', '')}",
            f"title_en     = {result.get('title_en', '')}",
            f"theta_deg    = {float(result['theta_deg']):.6f}",
            f"pol          = {result['pol']}",
            f"lambda0_nm   = {float(result['lambda0_nm']):.6f}",
            f"R_at_lambda0 = {float(summary['R_at_lambda0']):.12e}",
            f"T_at_lambda0 = {float(summary['T_at_lambda0']):.12e}",
            f"A_at_lambda0 = {float(summary['A_at_lambda0']):.12e}",
            f"R_min        = {float(summary['R_min']):.12e} @ {float(summary['R_min_wavelength_nm']):.6f} nm",
            f"R_max        = {float(summary['R_max']):.12e} @ {float(summary['R_max_wavelength_nm']):.6f} nm",
            f"T_max        = {float(summary['T_max']):.12e} @ {float(summary['T_max_wavelength_nm']):.6f} nm",
            "layers:",
        ]
        for layer in result["layers"]:
            lines.append(
                f"  {layer['name']}: n={layer['n_real']:.6f}+{layer['n_imag']:.6f}j, "
                f"d={layer['thickness_nm']:.6f} nm"
            )
        expl = result.get("figure_explanations", {})
        if expl:
            lines.extend([
                "",
                "figure_explanations:",
                f"  rta_title      = {expl.get('rta_title', '')}",
                f"  rta_desc       = {expl.get('rta_desc', '')}",
                f"  analysis_title = {expl.get('analysis_title', '')}",
                f"  analysis_desc  = {expl.get('analysis_desc', '')}",
            ])
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        saved["txt"] = str(txt_path)

    if save_plot:
        png_path = output_file(f"{stem}_RTA.png")
        fig, ax = plt.subplots(figsize=(8, 5))
        _style_teaching_axis(ax)
        main_kind = _main_curve_kind_for_case(result, r_vals, t_vals, a_vals)
        curves = {"R": r_vals, "T": t_vals, "A": a_vals}
        colors = {"R": MAIN_RED, "T": TRANS_BLUE, "A": ABS_GOLD}
        line_styles = {"solid": "-", "dash": "--", "dot": ":"}
        trace_styles = rta_trace_styles(main_kind, curves)
        legend_labels = {"R": "R (反射率 Reflectance)", "T": "T (透射率 Transmittance)", "A": "A (吸收率 Absorptance)"}
        for kind in ("R", "T", "A"):
            style = trace_styles[kind]
            ax.plot(
                wavelength_nm,
                curves[kind],
                label=legend_labels[kind],
                linewidth=float(style["linewidth"]),
                alpha=float(style["alpha"]),
                linestyle=line_styles[str(style["dash"])],
                color=colors[kind],
                zorder=3 if kind == main_kind else 2,
            )
        ax.axvline(float(result["lambda0_nm"]), linestyle=":", linewidth=1.4, color=TARGET_GREEN, alpha=0.9, label=r"$\lambda_0$ (设计中心波长)")
        title_label = (
            result.get("title_cn")
            or result.get("title_en")
            or result.get("design_type", "case")
        )
        ax.set_title(f"{title_label} | 入射角={float(result['theta_deg']):g}° | 偏振={result['pol']}", fontweight="semibold")
        ax.set_xlabel("波长 (nm)")
        ax.set_ylabel("反射率 / 透射率 / 吸收率")
        ax.set_xlim(float(np.min(wavelength_nm)), float(np.max(wavelength_nm)))
        ax.set_ylim(0.0, max(1.02, float(np.max([np.max(r_vals), np.max(t_vals), np.max(a_vals)])) * 1.05))
        ax.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="#c9d2dc")
        # Textbox overlay removed.
        fig.tight_layout()
        save_publication_figure(fig, png_path)
        plt.close(fig)
        saved["png"] = str(png_path)

        main_vals = {"R": r_vals, "T": t_vals, "A": a_vals}[main_kind]
        main_color = {"R": MAIN_RED, "T": TRANS_BLUE, "A": ABS_GOLD}[main_kind]
        main_label = {"R": "反射率", "T": "透射率", "A": "吸收率"}[main_kind]
        peak_idx = int(np.argmax(main_vals))
        valley_idx = int(np.argmin(main_vals))
        case_key = str(result.get("case_id") or result.get("design_type") or "").lower()
        feature_idx = peak_idx if main_kind in {"T", "A"} or any(
            term in case_key for term in ("reflector", "mirror", "bragg", "quarter_wave_stack")
        ) else valley_idx
        y0, y1 = focused_power_limits(main_vals)

        main_png_path = output_file(f"{stem}_main.png")
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        _style_teaching_axis(ax2)
        legend_labels = {"R": "R (反射率 Reflectance)", "T": "T (透射率 Transmittance)", "A": "A (吸收率 Absorptance)"}
        ax2.plot(wavelength_nm, main_vals, linewidth=2.7, color=main_color, label=legend_labels[main_kind])
        ax2.fill_between(wavelength_nm, main_vals, color=main_color, alpha=0.10)
        ax2.axvline(float(result["lambda0_nm"]), linestyle=":", linewidth=1.4, color=TARGET_GREEN, alpha=0.9)
        ax2.scatter(
            [float(wavelength_nm[feature_idx])],
            [float(main_vals[feature_idx])],
            color=main_color,
            edgecolor="white",
            linewidth=1.0,
            s=36,
            zorder=3,
        )
        ax2.set_title(
            f"{title_label} | {main_label} | 入射角={float(result['theta_deg']):g}° | 偏振={result['pol']}",
            fontweight="semibold",
        )
        ax2.set_xlabel("波长 (nm)")
        ax2.set_ylabel(main_kind)
        xlim = _main_plot_xlim_for_case(result)
        if xlim is None:
            ax2.set_xlim(float(np.min(wavelength_nm)), float(np.max(wavelength_nm)))
        else:
            ax2.set_xlim(*xlim)
        ax2.set_ylim(y0, y1)

        # C: Overlay faint secondary curves on a right twin-axis.
        # twinx is used so secondary curves remain visible even when the
        # primary y-axis is zoomed in tightly around the main curve.
        _sec_colors = {"R": MAIN_RED, "T": TRANS_BLUE, "A": ABS_GOLD}
        _sec_ls     = {"R": "--",     "T": "--",        "A": ":"}
        _sec_labels = {
            "R": "R (反射率) [参考]",
            "T": "T (透射率) [参考]",
            "A": "A (吸收率) [参考]",
        }
        _sec_curves = [(k, {"R": r_vals, "T": t_vals, "A": a_vals}[k])
                       for k in ("R", "T", "A") if k != main_kind]
        _has_visible = any(float(np.max(np.abs(v))) > 0.005 for _, v in _sec_curves)
        if _has_visible:
            ax2_sec = ax2.twinx()
            for _k, _v in _sec_curves:
                _max_v = float(np.max(np.abs(_v)))
                _alpha = 0.16 if _max_v < 0.02 else 0.30
                ax2_sec.plot(
                    wavelength_nm, _v,
                    linewidth=0.85,
                    alpha=_alpha,
                    linestyle=_sec_ls[_k],
                    color=_sec_colors[_k],
                    label=_sec_labels[_k],
                )
            ax2_sec.set_ylim(-0.02, 1.08)
            ax2_sec.set_ylabel("T / A  [参考]", fontsize=6.5, color="#aaaaaa")
            ax2_sec.tick_params(axis="y", labelsize=5.5, colors="#cccccc")
            for _sp, _obj in ax2_sec.spines.items():
                if _sp == "right":
                    _obj.set_linewidth(0.5)
                    _obj.set_color("#dddddd")
                else:
                    _obj.set_visible(False)
            ax2_sec.legend(
                loc="upper left", fontsize=5.8, frameon=True,
                facecolor="white", edgecolor="#eeeeee", framealpha=0.75,
                borderpad=0.4, handlelength=1.4,
            )

        # Textbox overlay removed.
        fig2.tight_layout()
        save_publication_figure(fig2, main_png_path)
        plt.close(fig2)
        saved["main_png"] = str(main_png_path)

        analysis_png_path = output_file(f"{stem}_analysis.png")
        # Note: Analysis plots are disabled to keep outputs clean.
        saved["analysis_png"] = str(analysis_png_path)

    return saved


def export_report_chapter2_suite_outputs(
    wavelengths_nm: Sequence[float] | None = None,
    prefix: str = "teaching_case",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, Dict[str, str]]:
    """Run and export the whole chapter-2 suite."""
    suite = simulate_report_chapter2_suite(wavelengths_nm=wavelengths_nm)
    exported: Dict[str, Dict[str, str]] = {}
    for case_id, result in suite.items():
        exported[case_id] = export_report_case_outputs(
            result=result,
            prefix=prefix,
            save_plot=save_plot,
            save_csv=save_csv,
            save_json=save_json,
            save_txt=save_txt,
        )
    return exported


def _export_comparison_csv(
    path: Path,
    wavelength_nm: np.ndarray,
    series: Dict[str, np.ndarray],
) -> None:
    with open(path, "w", encoding="utf-8-sig") as f:
        headers = ["wavelength_nm"] + list(series.keys())
        f.write(",".join(headers) + "\n")
        for i, wl in enumerate(wavelength_nm):
            row = [f"{float(wl):.12g}"] + [f"{float(series[key][i]):.12g}" for key in series]
            f.write(",".join(row) + "\n")


def _export_comparison_plot(
    filename_stem: str,
    title: str,
    ylabel: str,
    wavelength_nm: np.ndarray,
    series: Dict[str, np.ndarray],
    lambda0_nm: float | None = None,
    xlim: tuple[float, float] | None = None,
) -> Dict[str, str]:
    csv_path = output_file(f"{filename_stem}.csv")
    png_path = output_file(f"{filename_stem}.png")
    analysis_png_path = output_file(f"{filename_stem}_analysis.png")
    _export_comparison_csv(csv_path, wavelength_nm, series)

    fig, ax = plt.subplots(figsize=(8, 5))
    _style_teaching_axis(ax)
    palette = [MAIN_RED, TRANS_BLUE, "#77D7D1", "#7C6CCF", "#B64342", "#A8A8A8"]
    y_all: List[np.ndarray] = []
    center_values: List[float] = []
    peak_positions: List[float] = []
    widths: List[float] = []
    labels: List[str] = []
    for idx, (label, values) in enumerate(series.items()):
        color = palette[idx % len(palette)]
        vals = np.asarray(values, dtype=float)
        y_all.append(vals)
        labels.append(label)
        ax.plot(wavelength_nm, vals, linewidth=2.3, label=label, color=color)
        center_values.append(float(np.interp(float(lambda0_nm or wavelength_nm[len(wavelength_nm) // 2]), wavelength_nm, vals)))
        peak_idx = int(np.argmax(vals))
        peak_positions.append(float(wavelength_nm[peak_idx]))
        half_level = 0.5 * float(np.max(vals))
        above = np.where(vals >= half_level)[0]
        widths.append(float(wavelength_nm[above[-1]] - wavelength_nm[above[0]]) if len(above) >= 2 else 0.0)
    if lambda0_nm is not None:
        ax.axvline(float(lambda0_nm), linestyle=":", linewidth=1.4, color=TARGET_GREEN, alpha=0.9)
    ax.set_title(title, fontweight="semibold")
    ax.set_xlabel("波长 (nm)")
    ax.set_ylabel(ylabel)
    if xlim is None:
        ax.set_xlim(float(np.min(wavelength_nm)), float(np.max(wavelength_nm)))
    else:
        ax.set_xlim(*xlim)
    y_stack = np.concatenate(y_all) if y_all else np.array([0.0, 1.0])
    y_min = float(np.min(y_stack))
    y_max = float(np.max(y_stack))
    span = max(y_max - y_min, 1e-6)
    pad = max(0.015, 0.08 * span)
    ax.set_ylim(max(0.0, y_min - pad), min(1.02, y_max + pad))
    ax.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="#c9d2dc")
    fig.tight_layout()
    save_publication_figure(fig, png_path)
    plt.close(fig)

    # Note: Comparison analysis plots are disabled to keep outputs clean.
    return {"csv": str(csv_path), "png": str(png_path), "analysis_png": str(analysis_png_path)}


def export_report_comparison_figures(
    prefix: str = "teaching_compare",
) -> Dict[str, Dict[str, str]]:
    """Export report-style multi-curve comparison figures."""
    exported: Dict[str, Dict[str, str]] = {}

    # Quarter-wave stack: different periods.
    qw_stack_results = {
        f"周期={periods}": simulate_report_design(
            "quarter_wave_stack",
            lambda0_nm=550.0,
            theta_deg=0.0,
            pol="p",
            n_low=1.45,
            n_high_2=2.10,
            n_substrate=1.5215,
            periods=periods,
        )
        for periods in (4, 6, 8)
    }
    wl = next(iter(qw_stack_results.values()))["wavelength_nm"]
    exported["quarter_wave_stack_periods"] = _export_comparison_plot(
        filename_stem=f"{prefix}_quarter_wave_stack_periods",
        title="QW膜堆 | 不同周期数",
        ylabel="R",
        wavelength_nm=wl,
        series={label: result["R"] for label, result in qw_stack_results.items()},
        lambda0_nm=550.0,
    )

    # High-reflection coating: different periods.
    high_results = {
        f"周期={periods}": simulate_report_design(
            "high_reflector",
            lambda0_nm=550.0,
            theta_deg=0.0,
            pol="p",
            n_low=1.45,
            n_high_2=2.10,
            n_substrate=1.5215,
            periods=periods,
        )
        for periods in (5, 6, 7)
    }
    wl = next(iter(high_results.values()))["wavelength_nm"]
    exported["high_reflector_periods"] = _export_comparison_plot(
        filename_stem=f"{prefix}_high_reflector_periods",
        title="高反膜 | 不同周期数",
        ylabel="R",
        wavelength_nm=wl,
        series={label: result["R"] for label, result in high_results.items()},
        lambda0_nm=550.0,
    )

    # Single-half-wave FP: different periods.
    fp_single_results = {
        f"周期={periods}": simulate_report_design(
            "fp_single_halfwave",
            lambda0_nm=550.0,
            theta_deg=0.0,
            pol="p",
            n_low=1.45,
            n_high_2=2.10,
            n_substrate=1.0,
            periods=periods,
        )
        for periods in (3, 4, 5)
    }
    wl = next(iter(fp_single_results.values()))["wavelength_nm"]
    exported["fp_single_periods"] = _export_comparison_plot(
        filename_stem=f"{prefix}_fp_single_periods",
        title="单半波 F-P | 不同周期数",
        ylabel="T",
        wavelength_nm=wl,
        series={label: result["T"] for label, result in fp_single_results.items()},
        lambda0_nm=550.0,
        xlim=(480.0, 620.0),
    )

    narrowband_results = {
        f"周期={periods}": simulate_report_design(
            "narrowband_filter",
            lambda0_nm=550.0,
            theta_deg=0.0,
            pol="p",
            n_low=1.45,
            n_high_2=2.10,
            n_substrate=1.0,
            periods=periods,
        )
        for periods in (4, 5, 6)
    }
    wl = next(iter(narrowband_results.values()))["wavelength_nm"]
    exported["narrowband_filter_periods"] = _export_comparison_plot(
        filename_stem=f"{prefix}_narrowband_filter_periods",
        title="窄带滤光片 | 不同周期数",
        ylabel="T",
        wavelength_nm=wl,
        series={label: result["T"] for label, result in narrowband_results.items()},
        lambda0_nm=550.0,
        xlim=(500.0, 600.0),
    )

    # Double-half-wave FP: different angles.
    fp_double_angle_results = {
        f"入射角={int(theta)}°": simulate_report_design(
            "fp_double_halfwave",
            lambda0_nm=550.0,
            theta_deg=theta,
            pol="p",
            n_low=1.38,
            n_high_2=2.15,
            n_substrate=1.52,
            periods=2,
        )
        for theta in (0.0, 30.0, 45.0)
    }
    wl = next(iter(fp_double_angle_results.values()))["wavelength_nm"]
    exported["fp_double_angles"] = _export_comparison_plot(
        filename_stem=f"{prefix}_fp_double_angles",
        title="双半波 F-P | 不同入射角",
        ylabel="T",
        wavelength_nm=wl,
        series={label: result["T"] for label, result in fp_double_angle_results.items()},
        lambda0_nm=550.0,
        xlim=(430.0, 620.0),
    )

    # Neutral beam splitter: different central wavelengths.
    beamsplitter_results = {
        f"中心波长={int(lambda0)}nm": simulate_report_design(
            "neutral_beamsplitter",
            lambda0_nm=lambda0,
            theta_deg=0.0,
            pol="p",
            n_low=1.38,
            n_high_2=2.35,
            n_substrate=1.52,
        )
        for lambda0 in (500.0, 550.0, 600.0)
    }
    wl = next(iter(beamsplitter_results.values()))["wavelength_nm"]
    exported["beamsplitter_lambda0"] = _export_comparison_plot(
        filename_stem=f"{prefix}_beamsplitter_lambda0",
        title="中性分束膜 | 不同中心波长",
        ylabel="R",
        wavelength_nm=wl,
        series={label: result["R"] for label, result in beamsplitter_results.items()},
        lambda0_nm=550.0,
    )

    # TE vs TM comparison at 45 degrees for single_ar.
    te_results = simulate_report_design(
        "single_ar",
        lambda0_nm=550.0,
        theta_deg=45.0,
        pol="s",
        n_low=1.38,
        n_substrate=1.52,
    )
    tm_results = simulate_report_design(
        "single_ar",
        lambda0_nm=550.0,
        theta_deg=45.0,
        pol="p",
        n_low=1.38,
        n_substrate=1.52,
    )
    wl_te = te_results["wavelength_nm"]
    exported["te_tm_compare"] = _export_comparison_plot(
        filename_stem=f"{prefix}_te_tm_compare",
        title="单层减反膜 @ 45°斜入射 | TE vs TM 偏振对比",
        ylabel="R",
        wavelength_nm=wl_te,
        series={
            "TE 偏振 (s-pol)": te_results["R"],
            "TM 偏振 (p-pol)": tm_results["R"],
        },
        lambda0_nm=550.0,
    )

    return exported


def export_report_main_branch_bundle(
    case_prefix: str = "teaching_case",
    compare_prefix: str = "teaching_compare",
    save_plot: bool = True,
    save_csv: bool = True,
    save_json: bool = True,
    save_txt: bool = True,
) -> Dict[str, Any]:
    """Export the main teaching branch as one report-style bundle."""
    catalog = export_report_main_branch_catalog()
    suite_files = export_report_chapter2_suite_outputs(
        prefix=case_prefix,
        save_plot=save_plot,
        save_csv=save_csv,
        save_json=save_json,
        save_txt=save_txt,
    )
    compare_files = export_report_comparison_figures(prefix=compare_prefix)

    suite_results = simulate_report_chapter2_suite()
    case_summaries: List[Dict[str, Any]] = []
    for case_id, result in suite_results.items():
        summary = result["summary"]
        case_summaries.append(
            {
                "case_id": case_id,
                "title_cn": result.get("title_cn"),
                "title_en": result.get("title_en"),
                "theta_deg": float(result["theta_deg"]),
                "pol": str(result["pol"]),
                "lambda0_nm": float(result["lambda0_nm"]),
                "R_at_lambda0": float(summary["R_at_lambda0"]),
                "T_at_lambda0": float(summary["T_at_lambda0"]),
                "A_at_lambda0": float(summary["A_at_lambda0"]),
                "R_min": float(summary["R_min"]),
                "R_min_wavelength_nm": float(summary["R_min_wavelength_nm"]),
                "R_max": float(summary["R_max"]),
                "R_max_wavelength_nm": float(summary["R_max_wavelength_nm"]),
                "T_max": float(summary["T_max"]),
                "T_max_wavelength_nm": float(summary["T_max_wavelength_nm"]),
                "files": suite_files.get(case_id, {}),
            }
        )

    manifest: Dict[str, Any] = {
        "bundle_name": "main_teaching_branch",
        "chapter": "report_chapter2",
        "case_prefix": case_prefix,
        "compare_prefix": compare_prefix,
        "catalog_json": catalog.get("catalog_json"),
        "cases": case_summaries,
        "comparison_figures": compare_files,
    }

    case_index_csv = output_file("teaching_report_case_index.csv")
    with open(case_index_csv, "w", encoding="utf-8-sig") as f:
        headers = [
            "case_id",
            "title_cn",
            "title_en",
            "theta_deg",
            "pol",
            "lambda0_nm",
            "R_at_lambda0",
            "T_at_lambda0",
            "A_at_lambda0",
            "R_min",
            "R_min_wavelength_nm",
            "R_max",
            "R_max_wavelength_nm",
            "T_max",
            "T_max_wavelength_nm",
        ]
        f.write(",".join(headers) + "\n")
        for item in case_summaries:
            row = [
                str(item["case_id"]),
                str(item["title_cn"] or ""),
                str(item["title_en"] or ""),
                f"{float(item['theta_deg']):.12g}",
                str(item["pol"]),
                f"{float(item['lambda0_nm']):.12g}",
                f"{float(item['R_at_lambda0']):.12g}",
                f"{float(item['T_at_lambda0']):.12g}",
                f"{float(item['A_at_lambda0']):.12g}",
                f"{float(item['R_min']):.12g}",
                f"{float(item['R_min_wavelength_nm']):.12g}",
                f"{float(item['R_max']):.12g}",
                f"{float(item['R_max_wavelength_nm']):.12g}",
                f"{float(item['T_max']):.12g}",
                f"{float(item['T_max_wavelength_nm']):.12g}",
            ]
            f.write(",".join(row) + "\n")

    manifest["case_index_csv"] = str(case_index_csv)

    manifest_json = output_file("teaching_report_bundle_manifest.json")
    with open(manifest_json, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    lines = [
        "Teaching Report Bundle",
        "=" * 88,
        "Case exports:",
    ]
    for item in case_summaries:
        lines.append(
            f"{item['case_id']}: R(lambda0)={item['R_at_lambda0']:.6f}, "
            f"T(lambda0)={item['T_at_lambda0']:.6f}, "
            f"theta={item['theta_deg']:.2f} deg, pol={item['pol']}"
        )
        files = item["files"]
        for key in ("csv", "json", "txt", "png", "main_png"):
            if key in files:
                lines.append(f"  {key}: {files[key]}")
    lines.append("-" * 88)
    lines.append("Comparison figures:")
    for fig_id, files in compare_files.items():
        lines.append(f"{fig_id}:")
        for key in ("csv", "png"):
            if key in files:
                lines.append(f"  {key}: {files[key]}")
    lines.append("-" * 88)
    lines.append(f"catalog_json: {catalog.get('catalog_json')}")
    lines.append(f"case_index_csv: {case_index_csv}")
    lines.append(f"manifest_json: {manifest_json}")

    manifest_txt = output_file("teaching_report_bundle_manifest.txt")
    with open(manifest_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    manifest["manifest_json"] = str(manifest_json)
    manifest["manifest_txt"] = str(manifest_txt)
    return manifest
