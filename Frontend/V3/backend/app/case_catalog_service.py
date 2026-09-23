from __future__ import annotations

import json
import os
import sys
import csv
from pathlib import Path
from typing import Any
from .case_review import review_metadata, review_cards


CATEGORY_LABELS = {
    "teaching_thinfilm": "薄膜物理教学",
    "teaching_emt": "虚拟实验（EMT）",
    "engineering_applications": "工程应用",
    "research_extension": "研究拓展",
}


# Teaching cases are kept as physics models, but each one now exposes a clear
# application bridge so the UI can teach: law -> coating function -> system use
# -> design task.  The bridge is descriptive metadata only; it does not alter
# the underlying TMM or evidence result.
APPLICATION_ROUTES: dict[str, dict[str, str]] = {
    "quarter_wave_single_layer": {"learning_goal": "理解四分之一波相消干涉", "coating_function": "窄带单点减反", "application_scene": "单色镜头或探测器窗口", "design_task": "为 550 nm 选择低折射率材料并确定厚度"},
    "half_wave_single_layer": {"learning_goal": "理解半波光学厚度的相位作用", "coating_function": "相位延迟与光程调节", "application_scene": "成像系统相位校准", "design_task": "比较半波层与四分之一波层对反射相位的影响"},
    "single_ar": {"learning_goal": "理解界面反射相消", "coating_function": "降低镜片表面 Fresnel 反射", "application_scene": "相机镜头单层减反", "design_task": "用真实 MgF2 优化中心波长反射率"},
    "porous_sio2_layer": {"learning_goal": "理解低折射率介质的阻抗匹配", "coating_function": "低折射率单层增透", "application_scene": "镜头保护窗与盖板玻璃", "design_task": "改变孔隙率，平衡折射率、强度与透过率"},
    "porous_double_ar": {"learning_goal": "理解渐进阻抗匹配", "coating_function": "双层宽带减反", "application_scene": "可见光镜头宽带增透", "design_task": "选择多孔层与高折射率层的顺序和厚度"},
    "moth_eye_effective_gradient": {"learning_goal": "理解连续折射率过渡", "coating_function": "宽角度、宽带减反", "application_scene": "手机镜头与户外光学窗口", "design_task": "增加切片层数，比较蛾眼结构的角度容差"},
    "double_ar": {"learning_goal": "理解双层干涉协同", "coating_function": "可见光双层减反", "application_scene": "摄影镜头表面镀膜", "design_task": "在材料可用范围内压低 450–700 nm 平均反射率"},
    "quarter_wave_double_layer": {"learning_goal": "理解 V 形膜系的光谱整形", "coating_function": "双波段或宽带增透", "application_scene": "镜头与成像窗口", "design_task": "调整高低折射率层，控制反射谷的位置和宽度"},
    "triple_ar": {"learning_goal": "理解多层渐变折射率匹配", "coating_function": "宽带多层减反", "application_scene": "多片镜头组的宽带透过", "design_task": "在层数、材料和总厚度约束下优化可见光带宽"},
    "high_reflector": {"learning_goal": "理解周期膜堆的高反停带", "coating_function": "窄带高反射", "application_scene": "激光镜与镜头内部折返镜", "design_task": "用周期数控制反射率和停带宽度"},
    "quarter_wave_stack": {"learning_goal": "理解四分之一波膜堆的递迭增强", "coating_function": "设计可控高反镜面", "application_scene": "激光器和精密成像折返光路", "design_task": "比较不同周期数对高反带宽的影响"},
    "bragg_reflector": {"learning_goal": "理解一维光子带隙", "coating_function": "布拉格高反与阻带控制", "application_scene": "激光镜和杂散光抑制", "design_task": "改变折射率对比度，设计目标波段反射镜"},
    "fp_single_halfwave": {"learning_goal": "理解缺陷层引入的共振透射", "coating_function": "窄带光谱选择", "application_scene": "相机传感器前置滤光片", "design_task": "控制腔体厚度与周期数，得到目标中心波长"},
    "fp_filter": {"learning_goal": "理解 Fabry–Perot 多光束干涉", "coating_function": "高选择性窄带滤光", "application_scene": "光谱相机与检测镜头", "design_task": "以 FWHM 和 Q 因子为约束设计滤光片"},
    "fp_double_halfwave": {"learning_goal": "理解耦合腔共振", "coating_function": "双腔谱线整形", "application_scene": "多通道成像滤光组件", "design_task": "比较双腔耦合对峰形和带宽的影响"},
    "narrowband_filter": {"learning_goal": "理解窄带透射峰与带外抑制", "coating_function": "目标谱线提取", "application_scene": "窄带光谱成像镜头", "design_task": "用中心波长、FWHM 和带外抑制定义验收标准"},
    "rugate_filter": {"learning_goal": "理解连续渐变折射率的光谱调控", "coating_function": "平滑宽带阻带/通带", "application_scene": "光谱仪与多波段成像系统", "design_task": "切片逼近连续膜，并检查切片数对结果的影响"},
    "neutral_beamsplitter": {"learning_goal": "理解反射与透射能量分配", "coating_function": "中性分光", "application_scene": "取景、测距和双通道成像", "design_task": "在波段和入射角范围内保持目标分光比"},
    "app_solar_cell_ar": {"learning_goal": "理解宽带减反的工程权衡", "coating_function": "降低窗口反射损耗", "application_scene": "光伏盖板与光电探测窗口", "design_task": "以太阳光谱加权反射率为目标选材和定厚"},
    "app_wdm_filter": {"learning_goal": "理解多腔滤光器的通带整形", "coating_function": "多波长选择与隔离", "application_scene": "光谱相机和 WDM 接收镜头", "design_task": "同时满足中心波长、通带平坦度和串扰约束"},
    "app_laser_mirror": {"learning_goal": "理解高反膜的窄带工程设计", "coating_function": "激光波长高反", "application_scene": "激光器腔镜与折返镜", "design_task": "在 1064 nm 附近最大化反射并控制吸收"},
    "app_phone_lens_ar": {"learning_goal": "理解多层减反的宽带收益", "coating_function": "可见光宽带增透", "application_scene": "手机镜头模组", "design_task": "对比单层、多层和真实材料在 400–700 nm 的表现"},
    "app_smart_window": {"learning_goal": "理解选择性反射与透射", "coating_function": "可见光透过、红外阻隔", "application_scene": "建筑 Low-E 窗与观察窗", "design_task": "在可见光透过率和红外反射率之间优化"},
    "guided_grating_emt": {"learning_goal": "理解周期结构中的衍射级耦合", "coating_function": "光栅耦光与波长选择", "application_scene": "光栅波导入耦器与衍射光学元件", "design_task": "比较周期、占空比和厚度对共振波长的影响"},
    "mat_library_demo": {"learning_goal": "理解真实材料色散与吸收", "coating_function": "按工作波段选择薄膜材料", "application_scene": "宽带镜头与多光谱窗口", "design_task": "比较候选材料在目标波段的 n、k 与适用范围"},
    "tamm_interface_priority": {"learning_goal": "理解 Tamm 界面态的偏振反射特征", "coating_function": "界面共振与窄带选择", "application_scene": "相位传感和窄带探测镀膜", "design_task": "用 p/s 反射曲线定位优先研究的界面态"},
    "tamm_phase_bundle": {"learning_goal": "理解界面态附近的反射相位跃迁", "coating_function": "相位敏感共振筛选", "application_scene": "干涉传感与相位调控镀膜", "design_task": "联合反射率与反射相位确认共振位置"},
    "tamm_phase_candidates": {"learning_goal": "理解功率谱对界面态的候选筛选", "coating_function": "共振吸收与谱线选择", "application_scene": "窄带吸收器和折射率传感器", "design_task": "从反射降低和吸收增强区域筛选候选波长"},
    "tamm_phase_focus": {"learning_goal": "理解界面共振引起的能量局域与耗散", "coating_function": "共振吸收增强", "application_scene": "光热探测和界面敏感器件", "design_task": "比较吸收峰位置、峰值与线宽，避免将其误作场强"},
    "tamm_reflection_phase_screen": {"learning_goal": "理解复反射系数的幅相信息", "coating_function": "偏振相位筛选", "application_scene": "相位补偿和偏振敏感镀膜", "design_task": "识别相位快速变化区并排除主值换支假象"},
    "tamm_interface_window_bundle": {"learning_goal": "理解界面态的光谱工作窗口", "coating_function": "窄带窗口限定", "application_scene": "滤光、传感与探测器前置膜", "design_task": "确定窗口中心、宽度与偏振一致性"},
    "tamm_interface_window_scan": {"learning_goal": "理解切向波矢对界面态的调谐", "coating_function": "角度容差评估", "application_scene": "不同视场角下工作的镀膜器件", "design_task": "扫描归一化切向波矢并估计稳定工作范围"},
    "pdrc_cooling_bundle": {"learning_goal": "理解太阳波段反射与红外发射的协同", "coating_function": "选择性热辐射调控", "application_scene": "被动日间辐射制冷表面", "design_task": "同时检查太阳波段吸收和大气窗口发射能力"},
    "absorbing_baseline_template": {"learning_goal": "建立吸收表面的光谱基线", "coating_function": "宽带光热吸收", "application_scene": "光热接收器和红外吸收表面", "design_task": "用正式基线比较后续结构的吸收增益"},
    "absorbing_surface_bundle": {"learning_goal": "理解吸收、反射和透射的能量分配", "coating_function": "光热能量捕获", "application_scene": "太阳能吸收器与热探测表面", "design_task": "评估目标波段平均吸收率和带外损失"},
    "absorbing_surface_gain": {"learning_goal": "理解结构改动带来的吸收增益", "coating_function": "吸收增强", "application_scene": "高效光热转换涂层", "design_task": "待正式外部数据接入后量化相对基线增益"},
    "absorbing_surface_gain_trend": {"learning_goal": "理解吸收增益随结构参数的趋势", "coating_function": "光热参数优化", "application_scene": "可制造吸收表面设计", "design_task": "待正式参数扫描数据接入后寻找稳健设计区间"},
    "rugate_80layer_table": {"learning_goal": "理解连续折射率的离散切片逼近", "coating_function": "平滑阻带与旁瓣抑制", "application_scene": "高性能光谱滤光器", "design_task": "检查 80 层离散结构对连续 Rugate 响应的逼近误差"},
    "advanced_ar_bundle": {"learning_goal": "理解复杂宽带增透的系统权衡", "coating_function": "多表面宽带减反", "application_scene": "复杂摄影镜头和多光谱镜头", "design_task": "待正式材料与膜厚输入接入后验证系统级收益"},
    "porous_double_ar_topic_bundle": {"learning_goal": "理解多孔双层膜的宽角度增透机制", "coating_function": "低折射率宽角度匹配", "application_scene": "大视场镜头与户外窗口", "design_task": "待正式孔隙率和角度扫描数据接入后评估制造容差"},
}

# System-level teaching scaffold.  These are descriptive bindings for the
# future Optiland templates; they do not change the existing TMM results.
SYSTEM_EXPERIMENTS: dict[str, dict[str, Any]] = {
    "quarter_wave_single_layer": {"system_template": "single_lens_imaging", "complexity": "基础", "default_views": ["layout_2d", "system_3d", "spot", "mtf"], "primary_question": "单层减反膜能否改善单色成像？"},
    "half_wave_single_layer": {"system_template": "phase_interferometer", "complexity": "进阶", "default_views": ["layout_2d", "system_3d", "phase"], "primary_question": "半波层如何改变反射相位和光程？"},
    "single_ar": {"system_template": "camera_lens_coverglass", "complexity": "基础", "default_views": ["layout_2d", "system_3d", "spot", "mtf"], "primary_question": "单层膜如何减少镜片表面反射？"},
    "porous_sio2_layer": {"system_template": "wide_angle_window", "complexity": "进阶", "default_views": ["layout_2d", "spot", "mtf"], "primary_question": "低折射率多孔层能否改善斜入射增透？"},
    "porous_double_ar": {"system_template": "multi_element_imaging", "complexity": "进阶", "default_views": ["layout_2d", "system_3d", "spot", "mtf"], "primary_question": "双层多孔膜如何降低多表面反射？"},
    "moth_eye_effective_gradient": {"system_template": "wide_field_camera", "complexity": "复杂", "default_views": ["layout_2d", "system_3d", "spot", "psf", "mtf"], "primary_question": "渐变折射率结构能否扩大减反角度范围？"},
    "double_ar": {"system_template": "photographic_lens", "complexity": "进阶", "default_views": ["layout_2d", "spot", "psf", "mtf"], "primary_question": "双层减反膜如何改善宽带成像？"},
    "quarter_wave_double_layer": {"system_template": "dual_band_imager", "complexity": "进阶", "default_views": ["layout_2d", "system_3d", "mtf"], "primary_question": "双层膜能否同时控制两个工作波段？"},
    "triple_ar": {"system_template": "multi_element_imaging", "complexity": "复杂", "default_views": ["layout_2d", "system_3d", "spot", "psf", "mtf"], "primary_question": "多层宽带膜如何影响镜头组的综合性能？"},
    "high_reflector": {"system_template": "folded_reflector", "complexity": "进阶", "default_views": ["layout_2d", "system_3d", "spot"], "primary_question": "高反膜如何减少折返光路中的能量损失？"},
    "quarter_wave_stack": {"system_template": "laser_expander", "complexity": "进阶", "default_views": ["layout_2d", "system_3d", "spot"], "primary_question": "周期数如何改变激光反射镜的性能？"},
    "bragg_reflector": {"system_template": "dbr_laser_cavity", "complexity": "复杂", "default_views": ["layout_2d", "system_3d", "spectrum"], "primary_question": "DBR 停带如何为激光腔提供反馈？"},
    "fp_single_halfwave": {"system_template": "sensor_prefilter", "complexity": "进阶", "default_views": ["layout_2d", "system_3d", "psf", "mtf"], "primary_question": "缺陷层如何形成目标波长透射峰？"},
    "fp_filter": {"system_template": "spectral_camera", "complexity": "复杂", "default_views": ["layout_2d", "system_3d", "spectrum", "mtf"], "primary_question": "F-P 腔如何实现高选择性窄带滤光？"},
    "narrowband_filter": {"system_template": "multispectral_imager", "complexity": "复杂", "default_views": ["layout_2d", "system_3d", "spectrum", "mtf"], "primary_question": "窄带滤光片如何提取目标谱线？"},
    "fp_double_halfwave": {"system_template": "dual_channel_spectral_imager", "complexity": "复杂", "default_views": ["layout_2d", "system_3d", "spectrum", "mtf"], "primary_question": "耦合腔如何整形多个通道的谱线？"},
    "rugate_filter": {"system_template": "spectrometer", "complexity": "复杂", "default_views": ["layout_2d", "system_3d", "spectrum"], "primary_question": "连续渐变膜如何形成平滑阻带？"},
    "neutral_beamsplitter": {"system_template": "dual_path_beamsplitter", "complexity": "复杂", "default_views": ["layout_2d", "system_3d", "spot", "mtf"], "primary_question": "分光膜如何同时服务两个成像通道？"},
    "guided_grating_emt": {"system_template": "grating_waveguide_coupler", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "angle_scan"], "primary_question": "有效介质近似如何预测光栅波导耦合？"},
    "app_solar_cell_ar": {"system_template": "solar_cell_receiver", "complexity": "工程", "default_views": ["layout_2d", "system_3d", "spectrum", "angle_scan"], "primary_question": "宽带减反膜能否提高入射光功率？"},
    "app_wdm_filter": {"system_template": "wdm_receiver", "complexity": "工程", "default_views": ["layout_2d", "system_3d", "spectrum", "mtf"], "primary_question": "多腔滤光膜如何降低 WDM 通道串扰？"},
    "app_laser_mirror": {"system_template": "dbr_laser_cavity", "complexity": "工程", "default_views": ["layout_2d", "system_3d", "spectrum"], "primary_question": "1064 nm 高反膜如何提高激光腔反馈？"},
    "app_phone_lens_ar": {"system_template": "phone_camera_module", "complexity": "工程", "default_views": ["layout_2d", "system_3d", "spot", "psf", "mtf"], "primary_question": "多层减反膜如何改善手机镜头的综合色差和鬼像？"},
    "app_smart_window": {"system_template": "low_e_window", "complexity": "工程", "default_views": ["layout_2d", "system_3d", "spectrum", "angle_scan"], "primary_question": "Low-E 膜如何平衡可见光透过和红外阻隔？"},
    "mat_library_demo": {"system_template": "dispersive_lens", "complexity": "进阶", "default_views": ["layout_2d", "system_3d", "psf", "mtf"], "primary_question": "材料色散如何改变焦点和成像清晰度？"},
    "tamm_interface_priority": {"system_template": "prism_coupled_tamm", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "angle_scan"], "primary_question": "Tamm 界面态如何通过偏振反射被识别？"},
    "tamm_phase_bundle": {"system_template": "prism_coupled_tamm", "complexity": "研究", "default_views": ["layout_2d", "phase", "angle_scan"], "primary_question": "反射相位匹配如何定位 Tamm 共振？"},
    "tamm_phase_candidates": {"system_template": "prism_coupled_tamm_scan", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "angle_scan"], "primary_question": "如何从角度—波长扫描中寻找相位匹配点？"},
    "tamm_phase_focus": {"system_template": "tamm_absorption_probe", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "spectrum"], "primary_question": "界面共振如何增强局部场和吸收？"},
    "tamm_reflection_phase_screen": {"system_template": "polarized_phase_screen", "complexity": "研究", "default_views": ["layout_2d", "phase", "angle_scan"], "primary_question": "不同偏振和波长下反射相位如何变化？"},
    "tamm_interface_window_bundle": {"system_template": "prism_coupled_tamm_window", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "angle_scan"], "primary_question": "Tamm 界面态在哪个参数窗口内稳定存在？"},
    "tamm_interface_window_scan": {"system_template": "prism_coupled_tamm_scan", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "angle_scan"], "primary_question": "参数扫描如何评估界面态的容差？"},
    "pdrc_cooling_bundle": {"system_template": "radiative_cooling_emitter", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "spectrum"], "primary_question": "多层膜如何抑制太阳吸收并增强大气窗口辐射？"},
    "absorbing_baseline_template": {"system_template": "photothermal_receiver", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "spectrum"], "primary_question": "吸收表面的基线光热响应是什么？"},
    "absorbing_surface_bundle": {"system_template": "photothermal_receiver", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "spectrum"], "primary_question": "吸收、反射和热转换如何共同变化？"},
    "absorbing_surface_gain": {"system_template": "photothermal_receiver", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "spectrum"], "primary_question": "吸收增强能带来多大的热增益？"},
    "absorbing_surface_gain_trend": {"system_template": "photothermal_parameter_scan", "complexity": "研究", "default_views": ["layout_2d", "angle_scan", "spectrum"], "primary_question": "厚度、材料和角度如何影响光热增益？"},
    "rugate_80layer_table": {"system_template": "high_resolution_spectrometer", "complexity": "研究", "default_views": ["layout_2d", "system_3d", "spectrum"], "primary_question": "80 层离散切片能否逼近连续 Rugate 响应？"},
    "advanced_ar_bundle": {"system_template": "complex_camera_lens", "complexity": "工程", "default_views": ["layout_2d", "system_3d", "spot", "psf", "mtf"], "primary_question": "复杂增透膜如何改善真实镜头的综合成像？"},
    "porous_double_ar_topic_bundle": {"system_template": "wide_angle_multi_element", "complexity": "工程", "default_views": ["layout_2d", "system_3d", "spot", "mtf", "angle_scan"], "primary_question": "多孔双层膜如何在宽角度下保持增透？"},
}

# Case-driven Optiland routing.  The catalog remains the single source of
# truth for whether a teaching case should open a system-level analysis panel.
# Cases not listed in the two enabled groups intentionally stay pure thin-film
# cases; this prevents empty Optiland cards for phase/field-only experiments.
_OPTILAND_DEEP_CASES = {
    "single_ar", "porous_double_ar", "moth_eye_effective_gradient", "double_ar",
    "quarter_wave_double_layer", "triple_ar", "high_reflector", "quarter_wave_stack",
    "bragg_reflector", "fp_filter", "fp_double_halfwave", "narrowband_filter",
    "neutral_beamsplitter", "app_solar_cell_ar", "app_wdm_filter", "app_laser_mirror",
    "app_phone_lens_ar", "app_smart_window", "advanced_ar_bundle",
    "porous_double_ar_topic_bundle",
}
_OPTILAND_LIGHT_CASES = {
    "quarter_wave_single_layer", "porous_sio2_layer", "fp_single_halfwave",
    "rugate_filter", "mat_library_demo", "pdrc_cooling_bundle", "rugate_80layer_table",
}
_OPTILAND_OBSERVABLES = {
    "deep": [
        "throughput", "detector_irradiance", "ghost", "stray_light",
        "spectral_response", "color_response", "ray_intensity",
    ],
    "light": ["throughput", "detector_irradiance", "spectral_response"],
}


def _optiland_system_family(template: str) -> str:
    if template == "dual_path_beamsplitter":
        return "beamsplitter"
    families = {
        "imaging": {"single_lens_imaging", "multi_element_imaging", "complex_camera_lens", "phone_camera_module", "wide_angle_multi_element", "wide_field_camera", "photographic_lens", "camera_lens_coverglass", "dual_band_imager", "dispersive_lens", "wide_angle_window", "dual_path_beamsplitter"},
        "spectral": {"spectral_camera", "multispectral_imager", "dual_channel_spectral_imager", "spectrometer", "high_resolution_spectrometer", "sensor_prefilter", "wdm_receiver", "solar_cell_receiver", "low_e_window"},
        "reflector": {"folded_reflector", "laser_expander", "dbr_laser_cavity"},
        "interface": {"prism_coupled_tamm", "prism_coupled_tamm_scan", "tamm_absorption_probe", "polarized_phase_screen", "prism_coupled_tamm_window", "phase_interferometer"},
        "thermal": {"radiative_cooling_emitter", "photothermal_receiver", "photothermal_parameter_scan"},
        "grating": {"grating_waveguide_coupler"},
    }
    return next((family for family, templates in families.items() if template in templates), "baseline")


def _optiland_route(case_id: str) -> dict[str, Any]:
    if case_id in _OPTILAND_DEEP_CASES:
        level = "deep"
    elif case_id in _OPTILAND_LIGHT_CASES:
        level = "light"
    else:
        return {"enabled": False, "level": "none", "observables": []}
    template = str((SYSTEM_EXPERIMENTS.get(case_id) or {}).get("system_template", "single_lens_imaging"))
    return {
        "enabled": True,
        "level": level,
        "system_template": template,
        "system_family": _optiland_system_family(template),
        "observables": list(_OPTILAND_OBSERVABLES[level]),
    }


def _public_root_candidates(project_root: Path, app_root: Path) -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("THINFILM_CASE_LIBRARY_ROOT")
    if configured:
        candidates.append(Path(configured))
    pyinstaller_root = getattr(sys, "_MEIPASS", None)
    if pyinstaller_root:
        candidates.append(Path(pyinstaller_root) / "web3d_public")
    candidates.extend(
        [
            project_root / "web3d" / "public",
            app_root / "web3d_public",
            Path(sys.executable).resolve().parent / "web3d_public",
        ]
    )
    return candidates


def resolve_public_root(project_root: Path, app_root: Path) -> Path:
    candidates = _public_root_candidates(project_root, app_root)
    for candidate in candidates:
        if (candidate / "data" / "case_registry.json").exists():
            return candidate
    searched = "; ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Case registry not found. Searched: {searched}")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _case_data_path(public_root: Path, case_id: str) -> tuple[Path, str]:
    for folder, kind in (("results", "result"), ("evidence", "evidence")):
        path = public_root / folder / f"{case_id}.json"
        if path.exists():
            return path, kind
    raise FileNotFoundError(f"No result or evidence JSON for case_id: {case_id}")


def build_case_catalog(project_root: Path, app_root: Path, dynamic_cases: list[dict[str, Any]]) -> dict[str, Any]:
    public_root = resolve_public_root(project_root, app_root)
    registry = _read_json(public_root / "data" / "case_registry.json")
    dynamic_by_id = {str(case["case_id"]): case for case in dynamic_cases}
    cases: list[dict[str, Any]] = []

    for index, item in enumerate(registry.get("cases", []), start=1):
        if item.get("entry_kind") != "case":
            continue
        case_id = str(item["id"])
        data_path, data_kind = _case_data_path(public_root, case_id)
        dynamic = dynamic_by_id.get(case_id)
        cases.append(
            {
                "order": index,
                "case_id": case_id,
                "title_cn": item.get("display_name", case_id),
                "title_en": dynamic.get("title_en", "") if dynamic else "",
                "category": item.get("category", "research_extension"),
                "category_label": CATEGORY_LABELS.get(item.get("category", ""), item.get("category", "")),
                "access_mode": "interactive" if dynamic else data_kind,
                "has_live_simulation": dynamic is not None,
                "design_type": dynamic.get("design_type", "") if dynamic else "",
                "default_params": dynamic.get("default_params", {}) if dynamic else {},
                "physics_model": item.get("physics_model", ""),
                "structure": item.get("structure", ""),
                "materials": item.get("materials", []),
                "incidence_angle": item.get("incidence_angle", ""),
                "polarization_support": item.get("polarization_support", ""),
                "physics_data_status": item.get("physics_data_status", ""),
                "migration_status": item.get("migration_status", ""),
                "calculation_source": item.get("calculation_source", ""),
                "data_dependencies": item.get("data_dependencies", "NONE"),
                "notes": item.get("notes", ""),
                "data_kind": data_kind,
                "data_file": data_path.name,
                "system_experiment": SYSTEM_EXPERIMENTS.get(case_id),
                "optiland": _optiland_route(case_id),
                **APPLICATION_ROUTES.get(case_id, {}),
                **review_metadata(case_id),
            }
        )

    return {
        "version": registry.get("version"),
        "physical_case_count": len(cases),
        "interactive_case_count": sum(case["has_live_simulation"] for case in cases),
        "static_case_count": sum(not case["has_live_simulation"] for case in cases),
        "category_breakdown": {
            key: sum(case["category"] == key for case in cases) for key in CATEGORY_LABELS
        },
        "categories": CATEGORY_LABELS,
        "cases": cases,
    }


def _standard_series(data: dict[str, Any]) -> list[dict[str, Any]]:
    wavelengths = data.get("wavelength_nm")
    if isinstance(wavelengths, list):
        output: list[dict[str, Any]] = []
        for polarization in ("TE", "TM"):
            channel = data.get(polarization)
            if not isinstance(channel, dict):
                continue
            for quantity in ("R", "T", "A"):
                values = channel.get(quantity)
                if isinstance(values, list) and len(values) == len(wavelengths):
                    output.append(
                        {
                            "label": f"{polarization} {quantity}",
                            "x": wavelengths,
                            "y": values,
                            "x_label": "波长",
                            "x_unit": "nm",
                        }
                    )
        return output

    output = []
    for item in data.get("series", []):
        if not isinstance(item, dict):
            continue
        x_values = item.get("x")
        y_values = item.get("y")
        if isinstance(x_values, list) and isinstance(y_values, list) and len(x_values) == len(y_values):
            output.append(
                {
                    "label": item.get("label", f"曲线 {len(output) + 1}"),
                    "x": x_values,
                    "y": y_values,
                    "x_label": item.get("x_label", "横坐标"),
                    "x_unit": item.get("x_unit", ""),
                }
            )
    if output:
        return output

    # Evidence bundles often contain a compact numeric scan table instead of
    # a pre-rendered series.  Promote numeric table columns to chart traces so
    # the UI can visualize real evidence without inventing a spectrum.
    table = data.get("table")
    columns = table.get("columns") if isinstance(table, dict) else None
    rows = table.get("rows") if isinstance(table, dict) else None
    if not isinstance(columns, list) or not isinstance(rows, list) or len(columns) < 2:
        return output
    numeric_columns: list[int] = []
    for column in range(len(columns)):
        values = [row[column] for row in rows if isinstance(row, list) and len(row) > column]
        if values and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            numeric_columns.append(column)
    if len(numeric_columns) < 2:
        return output
    x_column = numeric_columns[0]
    x_values = [float(row[x_column]) for row in rows if isinstance(row, list) and len(row) > x_column]
    for column in numeric_columns[1:]:
        y_values = [float(row[column]) for row in rows if isinstance(row, list) and len(row) > column]
        if len(y_values) == len(x_values) and len(x_values) >= 2:
            output.append({
                "label": str(columns[column]),
                "x": x_values,
                "y": y_values,
                "x_label": str(columns[x_column]),
                "x_unit": "",
            })
    return output


def _summary_cards(data: dict[str, Any]) -> list[dict[str, Any]]:
    cards = data.get("summary_cards")
    if isinstance(cards, list):
        return [card for card in cards if isinstance(card, dict)]

    preferred = (
        "metrics",
        "design_point_550nm",
        "case_specific_metrics",
        "global_transmission_metrics",
        "stopband_metrics",
        "resonance_metrics",
        "emt_applicability",
        "energy_conservation",
    )
    output: list[dict[str, Any]] = []
    for group_name in preferred:
        group = data.get(group_name)
        if not isinstance(group, dict):
            continue
        for key, value in group.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                output.append({"label": key, "value": value, "unit": "", "note": group_name})
            if len(output) >= 12:
                return output
    return output


def _bound_baseline_series(project_root: Path, case_id: str) -> list[dict[str, Any]]:
    """Load an explicitly approved external baseline for template cases."""
    if case_id != "absorbing_baseline_template":
        return []
    candidates = [
        project_root / "docs" / "evidence" / "rough_absorbing_surface_topic_v1_baseline_spectrum.csv",
        project_root / "web3d" / "public" / "evidence" / "rough_absorbing_surface_topic_v1_baseline_spectrum.csv",
    ]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        return []
    rows: list[dict[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                rows.append({key: float(row[key]) for key in ("wavelength_nm", "R", "T", "A")})
            except (KeyError, TypeError, ValueError):
                continue
    if len(rows) < 2:
        return []
    wavelengths = [row["wavelength_nm"] for row in rows]
    return [
        {"label": quantity, "x": wavelengths, "y": [row[quantity] for row in rows], "x_label": "波长", "x_unit": "nm"}
        for quantity in ("R", "T", "A")
    ]


def load_case_detail(
    project_root: Path,
    app_root: Path,
    dynamic_cases: list[dict[str, Any]],
    case_id: str,
) -> dict[str, Any]:
    catalog = build_case_catalog(project_root, app_root, dynamic_cases)
    metadata = next((case for case in catalog["cases"] if case["case_id"] == case_id), None)
    if metadata is None:
        raise KeyError(case_id)
    public_root = resolve_public_root(project_root, app_root)
    data_path, data_kind = _case_data_path(public_root, case_id)
    data = _read_json(data_path)
    table = data.get("table") if isinstance(data.get("table"), dict) else {"columns": [], "rows": []}
    series = _standard_series(data)
    bound_series = _bound_baseline_series(project_root, case_id)
    return {
        **metadata,
        "data_kind": data_kind,
        "title": data.get("title", metadata["title_cn"]),
        "generated_at": data.get("generated_at", data.get("export_time", "")),
        "evidence_status": "READY_EXTERNAL_BOUND" if bound_series else data.get("evidence_status", ""),
        "model_scope": data.get("model_scope", data.get("physics", "")),
        "semantic_limit": data.get("semantic_limit", ""),
        "layers": data.get("layers", []),
        "series": series or bound_series,
        "summary_cards": review_cards(case_id, _summary_cards(data), bool(bound_series)),
        "table": table,
        "limitations": (["曲线来自已绑定的外部基线，仅适用于对应输入。"] if bound_series else data.get("limitations", [])),
        "external_data_provenance": data.get("external_data_provenance", []),
        "result_hash": data.get("result_hash", ""),
    }
