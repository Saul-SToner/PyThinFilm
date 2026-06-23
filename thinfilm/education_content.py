"""Educational content for the thin-film teaching platform.

Provides parameter explanations, design principles, formulas, and
application scenarios for the frontend to display.

This module contains Chinese-language educational content suitable for
Chinese university physics experiment competitions.
"""

from __future__ import annotations

from typing import Any, Dict


# ---------------------------------------------------------------------------
# Parameter Documentation
# ---------------------------------------------------------------------------

PARAMETER_DOCS: Dict[str, Dict[str, Any]] = {
    # --- Geometry ---
    "n_incident": {
        "name_cn": "入射介质折射率",
        "name_en": "Incident medium refractive index",
        "description": "光从该介质入射到薄膜表面",
        "formula": r"n_0",
        "typical_range": "1.0 (空气/真空)",
        "physical_meaning": "入射介质的光学密度，影响入射角和菲涅尔系数",
        "unit": "无量纲",
        "related_params": ["n_substrate", "theta_deg"],
    },
    "n_substrate": {
        "name_cn": "基底折射率",
        "name_en": "Substrate refractive index",
        "description": "薄膜沉积的基底材料折射率",
        "formula": r"n_s",
        "typical_range": "1.45 ~ 1.9 (玻璃/石英)",
        "physical_meaning": "基底折射率决定了理想的减反膜折射率",
        "unit": "无量纲",
        "related_params": ["n_incident", "n_low"],
    },
    "n_low": {
        "name_cn": "低折射率层",
        "name_en": "Low-index layer",
        "description": "减反膜或高反膜中的低折射率材料",
        "formula": r"n_L",
        "typical_range": "1.38 (MgF2) ~ 1.46 (SiO2)",
        "physical_meaning": "单层减反膜的最优折射率：n_low ≈ √(n0 × ns)",
        "unit": "无量纲",
        "related_params": ["n_high", "n_substrate"],
    },
    "n_high": {
        "name_cn": "高折射率层",
        "name_en": "High-index layer",
        "description": "高反膜或双层减反膜中的高折射率材料",
        "formula": r"n_H",
        "typical_range": "2.0 ~ 2.5 (TiO2, Ta2O5)",
        "physical_meaning": "与低折射率层交替构成布拉格反射镜",
        "unit": "无量纲",
        "related_params": ["n_low", "periods"],
    },
    "n_high_2": {
        "name_cn": "第二高折射率层",
        "name_en": "Second high-index layer",
        "description": "多层膜系中的另一种高折射率材料",
        "formula": r"n_{H2}",
        "typical_range": "1.88 ~ 2.30",
        "physical_meaning": "用于 F-P 滤光片和布拉格反射镜",
        "unit": "无量纲",
        "related_params": ["n_high", "n_low"],
    },
    "n_mid": {
        "name_cn": "中间折射率层",
        "name_en": "Mid-index layer",
        "description": "三层减反膜中的中间折射率材料",
        "formula": r"n_M",
        "typical_range": "1.60 ~ 1.80",
        "physical_meaning": "用于拓宽减反带宽",
        "unit": "无量纲",
        "related_params": ["n_low", "n_high"],
    },
    "n_porous": {
        "name_cn": "多孔层折射率",
        "name_en": "Porous layer refractive index",
        "description": "多孔二氧化硅的等效折射率",
        "formula": r"n_{\text{porous}}",
        "typical_range": "1.10 ~ 1.30",
        "physical_meaning": "通过引入空气孔降低有效折射率",
        "unit": "无量纲",
        "related_params": ["n_low"],
    },
    "n_top": {
        "name_cn": "渐变层顶部折射率",
        "name_en": "Top layer refractive index",
        "description": "蛾眼渐变层的最外层折射率",
        "formula": r"n_{\text{top}}",
        "typical_range": "1.05 ~ 1.15",
        "physical_meaning": "接近空气折射率，减少界面反射",
        "unit": "无量纲",
        "related_params": ["n_bottom"],
    },
    "n_bottom": {
        "name_cn": "渐变层底部折射率",
        "name_en": "Bottom layer refractive index",
        "description": "蛾眼渐变层的最内层折射率",
        "formula": r"n_{\text{bottom}}",
        "typical_range": "1.45 ~ 1.60",
        "physical_meaning": "接近基底折射率，实现平滑过渡",
        "unit": "无量纲",
        "related_params": ["n_top", "n_substrate"],
    },
    "k_incident": {
        "name_cn": "入射介质消光系数",
        "name_en": "Incident medium extinction coefficient",
        "description": "入射介质的虚部折射率（吸收）",
        "formula": r"k_0",
        "typical_range": "0 (无吸收)",
        "physical_meaning": "非零值表示入射介质有吸收",
        "unit": "无量纲",
        "related_params": ["k_substrate"],
    },
    "k_substrate": {
        "name_cn": "基底消光系数",
        "name_en": "Substrate extinction coefficient",
        "description": "基底材料的虚部折射率（吸收）",
        "formula": r"k_s",
        "typical_range": "0 ~ 0.01",
        "physical_meaning": "非零值表示基底有吸收损耗",
        "unit": "无量纲",
        "related_params": ["k_incident"],
    },

    # --- Geometry ---
    "lambda0_nm": {
        "name_cn": "设计波长",
        "name_en": "Design wavelength",
        "description": "膜层光学厚度对应的目标波长",
        "formula": r"\lambda_0",
        "typical_range": "400 ~ 800 nm (可见光)",
        "physical_meaning": "1/4 波长膜层在此波长处反射光相消干涉",
        "unit": "nm",
        "related_params": ["n_low", "n_high"],
    },
    "theta_deg": {
        "name_cn": "入射角",
        "name_en": "Angle of incidence",
        "description": "光束与法线的夹角",
        "formula": r"\theta_0",
        "typical_range": "0° ~ 60°",
        "physical_meaning": "影响有效光学厚度和偏振分裂",
        "unit": "度 (°)",
        "related_params": ["pol"],
    },
    "periods": {
        "name_cn": "周期数",
        "name_en": "Number of periods",
        "description": "布拉格反射镜的 HL 重复次数",
        "formula": r"N",
        "typical_range": "3 ~ 10",
        "physical_meaning": "周期数越多，反射带越宽、峰值越高",
        "unit": "整数",
        "related_params": ["n_high", "n_low"],
    },
    "total_layers": {
        "name_cn": "总层数",
        "name_en": "Total number of layers",
        "description": "皱褶滤光片的总层数",
        "formula": r"N_{\text{total}}",
        "typical_range": "40 ~ 100",
        "physical_meaning": "层数越多，折射率调制越精细",
        "unit": "整数",
        "related_params": ["periods"],
    },

    # --- PDRC specific ---
    "ag_thickness_nm": {
        "name_cn": "银层厚度",
        "name_en": "Silver layer thickness",
        "description": "PDRC 结构中的金属反射层厚度",
        "formula": r"d_{\text{Ag}}",
        "typical_range": "100 ~ 500 nm",
        "physical_meaning": "太薄则红外透射增加，太厚则加工困难",
        "unit": "nm",
        "related_params": [],
    },
    "variant": {
        "name_cn": "结构变体",
        "name_en": "Structure variant",
        "description": "PDRC 多层膜的简化或完整版本",
        "formula": None,
        "typical_range": "simple / full",
        "physical_meaning": "'simple' 减少层数便于理解，'full' 为实际设计",
        "unit": "枚举",
        "related_params": [],
    },

    # --- Grating specific ---
    "period_nm": {
        "name_cn": "光栅周期",
        "name_en": "Grating period",
        "description": "光栅的周期长度",
        "formula": r"\Lambda",
        "typical_range": "500 ~ 2000 nm",
        "physical_meaning": "决定衍射级次的位置和导模共振波长",
        "unit": "nm",
        "related_params": ["fill_factor", "waveguide_thickness_nm"],
    },
    "waveguide_thickness_nm": {
        "name_cn": "波导层厚度",
        "name_en": "Waveguide layer thickness",
        "description": "光栅波导结构中的波导层厚度",
        "formula": r"t_{\text{wg}}",
        "typical_range": "150 ~ 300 nm",
        "physical_meaning": "影响导模的有效折射率和共振条件",
        "unit": "nm",
        "related_params": ["period_nm", "fill_factor"],
    },
    "grating_thickness_nm": {
        "name_cn": "光栅层厚度",
        "name_en": "Grating layer thickness",
        "description": "光栅调制层的物理厚度",
        "formula": r"t_g",
        "typical_range": "50 ~ 300 nm",
        "physical_meaning": "影响光栅的调制强度和共振线宽",
        "unit": "nm",
        "related_params": ["period_nm", "fill_factor"],
    },
    "fill_factor": {
        "name_cn": "占空比",
        "name_en": "Fill factor",
        "description": "光栅高折射率区域占周期的比例",
        "formula": r"f",
        "typical_range": "0.3 ~ 0.7",
        "physical_meaning": "影响等效折射率和衍射效率",
        "unit": "无量纲 (0~1)",
        "related_params": ["period_nm", "n_high"],
    },
    "pol": {
        "name_cn": "偏振态",
        "name_en": "Polarization",
        "description": "入射光的偏振方向",
        "formula": None,
        "typical_range": "TE / TM / s / p",
        "physical_meaning": "TE: E 垂直于入射面; TM: E 平行于入射面",
        "unit": "枚举",
        "related_params": ["theta_deg"],
    },
}


# ---------------------------------------------------------------------------
# Design Type Documentation
# ---------------------------------------------------------------------------

DESIGN_DOCS: Dict[str, Dict[str, Any]] = {
    "single_ar": {
        "title_cn": "单层减反射膜",
        "title_en": "Single-Layer Anti-Reflection Coating",
        "principle": "利用 1/4 波长膜层的相消干涉，使膜层前后表面的反射光振幅相等、相位相反，从而抵消反射。",
        "formula": r"R_{\min} = \left(\frac{n_0 n_s - n_L^2}{n_0 n_s + n_L^2}\right)^2",
        "key_condition": r"n_L = \sqrt{n_0 \cdot n_s}",
        "key_condition_cn": "最优膜层折射率 = √(入射介质 × 基底)",
        "design_rule": "膜层光学厚度 = λ₀/4",
        "applications": ["手机镜头", "太阳能电池", "显示器面板", "LED 封装"],
        "typical_materials": {"n_low": "MgF2 (1.38)", "n_substrate": "玻璃 (1.52)"},
        "limitations": ["减反带宽有限", "只能在单一波长处达到最优"],
    },
    "double_ar": {
        "title_cn": "双层减反射膜",
        "title_en": "Double-Layer Anti-Reflection Coating",
        "principle": "使用两种不同折射率的 1/4 波长膜层，通过两个界面的反射光干涉，实现更宽的减反带宽。",
        "formula": r"R = \left|\frac{r_1 + r_2 e^{-2i\delta_1} + r_3 e^{-2i(\delta_1+\delta_2)}}{1 + ...}\right|^2",
        "key_condition": r"n_L^2 / n_H = n_s \text{ (满足 V 型条件)}",
        "key_condition_cn": "低/高折射率之比应匹配基底折射率",
        "design_rule": "两层均为 λ₀/4 光学厚度",
        "applications": ["宽光谱减反", "摄影镜头", "光学仪器"],
        "typical_materials": {"n_low": "MgF2 (1.38)", "n_high": "Al2O3 (1.63)"},
        "limitations": ["需要两种材料精确匹配"],
    },
    "triple_ar": {
        "title_cn": "三层减反射膜",
        "title_en": "Triple-Layer Anti-Reflection Coating",
        "principle": "三层结构提供更宽带宽和更低的残余反射率，但设计复杂度更高。",
        "formula": None,
        "key_condition": None,
        "key_condition_cn": "低-中-高三层折射率梯度递增",
        "design_rule": "外层 λ₀/4，中间层 λ₀/2",
        "applications": ["高精度光学系统", "激光窗口"],
        "typical_materials": {"n_low": "MgF2", "n_mid": "Al2O3", "n_high": "TiO2"},
        "limitations": ["工艺控制要求高"],
    },
    "high_reflector": {
        "title_cn": "高反射膜（布拉格反射镜）",
        "title_en": "High-Reflection Coating (Bragg Reflector)",
        "principle": "高低折射率材料交替排列，每层 λ₀/4 光学厚度，利用多层反射光的相长干涉实现高反射。",
        "formula": r"R_{\max} = \left(\frac{1 - (n_H/n_L)^{2N} \cdot (n_s/n_0)}{1 + (n_H/n_L)^{2N} \cdot (n_s/n_0)}\right)^2",
        "key_condition": r"n_H > n_L, \text{ 每层 } d = \lambda_0 / (4n)",
        "key_condition_cn": "高/低折射率交替，每层 λ₀/4 光学厚度",
        "design_rule": "H-L-H-L-... 共 2N+1 层",
        "applications": ["激光反射镜", "VCSEL", "光学滤波器", "太阳能聚光器"],
        "typical_materials": {"n_high": "TiO2 (2.30)", "n_low": "SiO2 (1.46)"},
        "limitations": ["反射带宽由折射率比决定", "角度偏转会移动反射带"],
    },
    "fp_filter": {
        "title_cn": "法布里-珀罗滤光片",
        "title_en": "Fabry-Perot Filter",
        "principle": "两个高反射镜之间夹一个半波长腔层，形成谐振腔，只有满足共振条件的波长能透射。",
        "formula": r"FSR = \frac{\lambda_0^2}{2 n_c d_c \cos\theta_c}",
        "key_condition": r"d_{\text{cavity}} = \lambda_0 / (2 n_c)",
        "key_condition_cn": "腔层光学厚度 = λ₀/2",
        "design_rule": "DBR-HW-DBR 或 DBR-LW-DBR 结构",
        "applications": ["光纤通信 WDM", "光谱分析", "激光线宽压窄"],
        "typical_materials": {"cavity": "λ₀/2 层", "mirrors": "H/L 交替"},
        "limitations": ["线宽与腔层精细度成反比", "角度敏感"],
    },
    "narrowband_filter": {
        "title_cn": "窄带滤光片",
        "title_en": "Narrowband Filter",
        "principle": "多腔 F-P 结构，通过增加腔层数量实现更窄的透射带宽。",
        "formula": None,
        "key_condition": None,
        "key_condition_cn": "多个 F-P 腔串联",
        "design_rule": "DBR-C-DBR-C-DBR 多腔结构",
        "applications": ["高精度光谱分析", "荧光检测", "激光净化"],
        "typical_materials": {"cavity": "λ₀/2 层", "mirrors": "H/L 交替"},
        "limitations": ["腔间耦合需要精确控制"],
    },
    "rugate_filter": {
        "title_cn": "皱褶滤光片",
        "title_en": "Rugate Filter",
        "principle": "折射率沿深度方向连续周期性变化（正弦调制），形成光子带隙。",
        "formula": r"n(z) = n_0 + \Delta n \cdot \sin(2\pi z / \Lambda)",
        "key_condition": r"\Delta n \neq 0, \Lambda = \lambda_0 / (2 n_0)",
        "key_condition_cn": "折射率正弦调制，周期 = λ₀/(2n₀)",
        "design_rule": "连续折射率剖面，离散化为多层",
        "applications": ["窄带反射镜", "激光防护", "光谱合束"],
        "typical_materials": {"连续调制": "SiO2/TiO2 混合"},
        "limitations": ["制造工艺复杂", "需要精确控制折射率分布"],
    },
    "neutral_beamsplitter": {
        "title_cn": "中性分束膜",
        "title_en": "Neutral Beam Splitter",
        "principle": "在宽光谱范围内实现接近 50:50 的分束比，且分束比随波长变化小。",
        "formula": None,
        "key_condition": r"R \approx T \approx 0.5",
        "key_condition_cn": "反射率 ≈ 透射率 ≈ 50%",
        "design_rule": "特殊膜层组合实现宽带 50:50",
        "applications": ["光学干涉仪", "分束器", "光学测量"],
        "typical_materials": {},
        "limitations": ["宽带中性难以完美实现"],
    },
    "moth_eye_effective_gradient": {
        "title_cn": "蛾眼等效渐变层",
        "title_en": "Moth-Eye Effective Gradient",
        "principle": "模拟蛾眼微结构的等效折射率渐变层，从空气到基底实现平滑过渡，消除界面反射。",
        "formula": r"n(z) = n_{\text{air}} + (n_{\text{sub}} - n_{\text{air}}) \cdot (z/d)^p",
        "key_condition": r"n_{\text{top}} \approx n_{\text{air}}, n_{\text{bottom}} \approx n_{\text{sub}}",
        "key_condition_cn": "顶部接近空气，底部接近基底",
        "design_rule": "渐变层数越多，效果越好",
        "applications": ["太阳能电池", "LED 抽取效率", "显示器"],
        "typical_materials": {"渐变": "SiO2 多孔/致密混合"},
        "limitations": ["需要纳米加工技术"],
    },
    "quarter_wave_single_layer": {
        "title_cn": "1/4 波长单层膜",
        "title_en": "Quarter-Wave Single Layer",
        "principle": "最基本的膜层结构，展示 1/4 波长膜层的相位特性。",
        "formula": r"d = \frac{\lambda_0}{4n}",
        "key_condition": None,
        "key_condition_cn": "光学厚度 = λ₀/4",
        "design_rule": "单层 λ₀/4 膜层",
        "applications": ["教学演示", "基础减反"],
        "typical_materials": {},
        "limitations": [],
    },
    "half_wave_single_layer": {
        "title_cn": "1/2 波长单层膜",
        "title_en": "Half-Wave Single Layer",
        "principle": "1/2 波长膜层对反射率无影响（'缺失层'），演示相位特性。",
        "formula": r"d = \frac{\lambda_0}{2n}",
        "key_condition": None,
        "key_condition_cn": "光学厚度 = λ₀/2",
        "design_rule": "单层 λ₀/2 膜层",
        "applications": ["教学演示", "相位调控"],
        "typical_materials": {},
        "limitations": ["不改变反射率"],
    },
}


# ---------------------------------------------------------------------------
# Formula Library
# ---------------------------------------------------------------------------

FORMULA_LIBRARY: Dict[str, Dict[str, str]] = {
    "fresnel_reflection": {
        "title": "菲涅尔反射系数",
        "formula": r"r = \frac{n_0 \cos\theta_0 - n_s \cos\theta_s}{n_0 \cos\theta_0 + n_s \cos\theta_s}",
        "te_polarization": r"r_s = \frac{n_0 \cos\theta_0 - n_s \cos\theta_s}{n_0 \cos\theta_0 + n_s \cos\theta_s}",
        "tm_polarization": r"r_p = \frac{n_s \cos\theta_0 - n_0 \cos\theta_s}{n_s \cos\theta_0 + n_0 \cos\theta_s}",
        "note": "反射率 R = |r|²",
    },
    "quarter_wave_condition": {
        "title": "1/4 波长条件",
        "formula": r"d = \frac{\lambda_0}{4n}",
        "note": "此时相位厚度 δ = π/2，反射光相消干涉",
    },
    "half_wave_condition": {
        "title": "1/2 波长条件",
        "formula": r"d = \frac{\lambda_0}{2n}",
        "note": "此时相位厚度 δ = π，膜层'消失'（缺失层效应）",
    },
    "bragg_reflector_max_R": {
        "title": "布拉格反射镜最大反射率",
        "formula": r"R_{\max} = \left(\frac{1 - (n_H/n_L)^{2N} \cdot (n_s/n_0)}{1 + (n_H/n_L)^{2N} \cdot (n_s/n_0)}\right)^2",
        "note": "N 为周期数，n_H/n_L 越大，反射带越宽",
    },
    "fp_fsr": {
        "title": "F-P 腔自由光谱范围",
        "formula": r"FSR = \frac{\lambda_0^2}{2 n_c d_c \cos\theta_c}",
        "note": "FSR 是相邻透射峰的波长间隔",
    },
    "fp_finesse": {
        "title": "F-P 腔精细度",
        "formula": r"\mathcal{F} = \frac{\pi \sqrt{R}}{1 - R}",
        "note": "R 为镜面反射率，精细度越高透射峰越窄",
    },
    "snell_law": {
        "title": "斯涅尔定律",
        "formula": r"n_0 \sin\theta_0 = n_s \sin\theta_s",
        "note": "光在不同介质界面的折射关系",
    },
    "effective_medium_TE": {
        "title": "有效介质理论 (TE)",
        "formula": r"n_{\text{eff}}^2 = f \cdot n_H^2 + (1-f) \cdot n_L^2",
        "note": "亚波长光栅的等效折射率（E 垂直于光栅槽）",
    },
    "effective_medium_TM": {
        "title": "有效介质理论 (TM)",
        "formula": r"\frac{1}{n_{\text{eff}}^2} = \frac{f}{n_H^2} + \frac{1-f}{n_L^2}",
        "note": "亚波长光栅的等效折射率（E 平行于光栅槽）",
    },
}


# ---------------------------------------------------------------------------
# Common Mistakes / Warnings
# ---------------------------------------------------------------------------

COMMON_MISTAKES: Dict[str, Dict[str, str]] = {
    "wrong_order": {
        "title": "膜层顺序错误",
        "description": "减反膜应从低折射率到高折射率排列（从入射侧）",
        "consequence": "反射率反而增加",
        "fix": "检查 LayerSpec 中的折射率顺序",
    },
    "too_thick": {
        "title": "膜层过厚",
        "description": "实际厚度远大于设计值",
        "consequence": "干涉极值位置偏移",
        "fix": "调整厚度使光学厚度接近 λ₀/4",
    },
    "wrong_polarization": {
        "title": "偏振态混淆",
        "description": "TE 和 TM 的折射率匹配条件不同",
        "consequence": "斜入射时结果偏差大",
        "fix": "明确指定 pol='TE' 或 pol='TM'",
    },
    "periods_too_few": {
        "title": "布拉格反射镜周期数不足",
        "description": "少于 3 个周期时反射率较低",
        "consequence": "R < 0.9",
        "fix": "增加 periods 到 5~10",
    },
}


# ---------------------------------------------------------------------------
# API Functions
# ---------------------------------------------------------------------------

def get_parameter_info(param_name: str) -> Dict[str, Any] | None:
    """Get documentation for a parameter.

    Parameters
    ----------
    param_name : str
        Parameter name (e.g., 'n_low', 'lambda0_nm').

    Returns
    -------
    dict or None
        Parameter documentation, or None if not found.
    """
    return PARAMETER_DOCS.get(param_name)


def get_design_info(design_type: str) -> Dict[str, Any] | None:
    """Get documentation for a design type.

    Parameters
    ----------
    design_type : str
        Design type (e.g., 'single_ar', 'high_reflector').

    Returns
    -------
    dict or None
        Design documentation, or None if not found.
    """
    return DESIGN_DOCS.get(design_type)


def get_formula_info(formula_name: str) -> Dict[str, Any] | None:
    """Get a formula from the library.

    Parameters
    ----------
    formula_name : str
        Formula name (e.g., 'fresnel_reflection').

    Returns
    -------
    dict or None
        Formula documentation, or None if not found.
    """
    return FORMULA_LIBRARY.get(formula_name)


def list_parameters() -> List[str]:
    """List all available parameter names."""
    return list(PARAMETER_DOCS.keys())


def list_designs() -> List[str]:
    """List all available design types."""
    return list(DESIGN_DOCS.keys())


def list_formulas() -> List[str]:
    """List all available formula names."""
    return list(FORMULA_LIBRARY.keys())


def get_parameter_help(param_name: str) -> str:
    """Get a formatted help string for a parameter.

    Returns
    -------
    str
        Formatted help text suitable for display.
    """
    info = get_parameter_info(param_name)
    if info is None:
        return f"未知参数: {param_name}"

    lines = [
        f"**{info['name_cn']}** ({info.get('name_en', '')})",
        "",
        info["description"],
        "",
    ]
    if info.get("formula"):
        lines.append(f"公式: {info['formula']}")
        lines.append("")
    lines.append(f"典型范围: {info['typical_range']}")
    lines.append(f"物理意义: {info['physical_meaning']}")
    if info.get("related_params"):
        lines.append(f"相关参数: {', '.join(info['related_params'])}")

    return "\n".join(lines)


def get_design_help(design_type: str) -> str:
    """Get a formatted help string for a design type.

    Returns
    -------
    str
        Formatted help text suitable for display.
    """
    info = get_design_info(design_type)
    if info is None:
        return f"未知设计类型: {design_type}"

    lines = [
        f"**{info['title_cn']}** ({info.get('title_en', '')})",
        "",
        "## 原理",
        info["principle"],
        "",
    ]
    if info.get("formula"):
        lines.append(f"## 关键公式")
        lines.append(info["formula"])
        lines.append("")
    if info.get("key_condition_cn"):
        lines.append(f"**关键条件**: {info['key_condition_cn']}")
        lines.append("")
    if info.get("design_rule"):
        lines.append(f"**设计规则**: {info['design_rule']}")
        lines.append("")
    if info.get("applications"):
        lines.append(f"**应用场景**: {', '.join(info['applications'])}")
    if info.get("limitations"):
        lines.append(f"**局限性**: {', '.join(info['limitations'])}")

    return "\n".join(lines)
