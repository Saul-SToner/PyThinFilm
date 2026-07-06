from __future__ import annotations

import json
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from .paths import output_file
from .plotting import BLUE, GREEN, INK, MUTED, PAPER, PANEL, RED, save_publication_figure, style_axis


TEACHING_CASE_EXPANSION_ROADMAP: List[Dict[str, Any]] = [
    {
        "group_id": "foundation_layers",
        "title_cn": "基础均匀膜层",
        "title_en": "Foundation Uniform Layers",
        "goal_cn": "建立光学厚度、相位补偿与单层干涉的基础认知。",
        "priority": 1,
        "cases": [
            {
                "case_id": "quarter_wave_single_layer",
                "title_cn": "1/4波长单层膜",
                "title_en": "Quarter-Wave Single Layer",
                "recommended_mode": "parameter_mode",
                "host_case_id": "single_ar",
                "why_cn": "最适合作为光学厚度与相消干涉的入门案例。",
                "outputs_cn": ["R(λ)", "中心波长处反射率", "谷位偏移"],
            },
            {
                "case_id": "half_wave_single_layer",
                "title_cn": "1/2波长单层膜",
                "title_en": "Half-Wave Single Layer",
                "recommended_mode": "parameter_mode",
                "host_case_id": "single_ar",
                "why_cn": "用于对比 1/4 波长与 1/2 波长在相位条件上的差异。",
                "outputs_cn": ["R(λ)", "T(λ)", "中心波长相位作用对比"],
            },
            {
                "case_id": "quarter_wave_double_layer",
                "title_cn": "1/4波长双层膜系",
                "title_en": "Quarter-Wave Double Layer",
                "recommended_mode": "independent_case",
                "host_case_id": "double_ar",
                "why_cn": "从单层过渡到双层，适合展示多层匹配与带宽改善。",
                "outputs_cn": ["R(λ)", "中心波长反射率", "带宽变化"],
            },
        ],
    },
    {
        "group_id": "periodic_qw_stacks",
        "title_cn": "周期QW膜堆",
        "title_en": "Periodic QW Stacks",
        "goal_cn": "展示周期多层结构的高反射机理与禁带形成。",
        "priority": 2,
        "cases": [
            {
                "case_id": "quarter_wave_stack",
                "title_cn": "1/4波长QW膜堆",
                "title_en": "Quarter-Wave Stack",
                "recommended_mode": "parameter_mode",
                "host_case_id": "high_reflector",
                "why_cn": "适合作为周期膜堆的总入口，再扩展到不同周期数。",
                "outputs_cn": ["R(λ)", "禁带宽度", "周期数影响"],
            },
            {
                "case_id": "bragg_reflector",
                "title_cn": "布拉格反射镜",
                "title_en": "Bragg Reflector",
                "recommended_mode": "thematic_alias",
                "host_case_id": "high_reflector",
                "why_cn": "物理上属于QW周期膜堆的典型高反特例，建议作为主题名展示。",
                "outputs_cn": ["R(λ)", "中心反射率", "反射带宽"],
            },
        ],
    },
    {
        "group_id": "filter_family",
        "title_cn": "滤光片家族",
        "title_en": "Filter Family",
        "goal_cn": "从腔型透射结构过渡到功能型窄带滤光设计。",
        "priority": 3,
        "cases": [
            {
                "case_id": "fp_filter",
                "title_cn": "F-P滤光片",
                "title_en": "Fabry-Perot Filter",
                "recommended_mode": "independent_case",
                "host_case_id": "fp_single_halfwave",
                "why_cn": "已经有稳定基础，可作为滤光器支线核心案例。",
                "outputs_cn": ["T(λ)", "峰位", "半高全宽"],
            },
            {
                "case_id": "narrowband_filter",
                "title_cn": "窄带滤光片",
                "title_en": "Narrowband Filter",
                "recommended_mode": "advanced_case",
                "host_case_id": "fp_single_halfwave",
                "why_cn": "更适合作为F-P或缺陷层设计的高阶目标，而非最基础结构分类。",
                "outputs_cn": ["T(λ)", "峰宽", "旁瓣抑制"],
            },
            {
                "case_id": "rugate_filter",
                "title_cn": "皱褶滤光片",
                "title_en": "Rugate Filter",
                "recommended_mode": "advanced_extension",
                "host_case_id": None,
                "why_cn": "需要引入连续折射率调制，建议放在高级扩展区。",
                "outputs_cn": ["R(λ)", "T(λ)", "折射率渐变影响"],
            },
        ],
    },
]


FRONTIER_RESEARCH_MODEL_TREE: List[Dict[str, Any]] = [
    {
        "module_id": "topological_tamm_thermal_radiation",
        "title_cn": "拓扑 Tamm 边界态与热辐射空间调控",
        "title_en": "Topological Tamm Boundary States for Spatial Thermal Radiation Control",
        "module_type": "frontier_research",
        "goal_cn": "从普通 Tamm/TPP 吸收器出发，逐步走向反射相位拓扑分类、界面边界态与热辐射空间调控。",
        "why_cn": "该模块仍建立在一维多层膜与金属薄膜结构之上，能够与现有薄膜平台平滑衔接，同时又具备明显的前沿研究属性。",
        "status": "optimized_absorber_found",
        "stages": [
            {
                "stage_id": "tamm_absorber_basic",
                "title_cn": "普通 Tamm / TPP 吸收器",
                "title_en": "Conventional Tamm Absorber",
                "priority": 1,
                "status": "optimized_absorber_found",
                "goal_cn": "建立 Air / 金属薄膜 / 间隔层 / DBR / 基底 结构，并锁定主要高吸收工作波段与近完美吸收候选。",
                "suitable_backend_cn": ["平面多层膜理论模型", "COMSOL 单谱与参数扫描"],
                "core_outputs_cn": ["R(λ)", "A(λ)", "峰值吸收率", "峰位", "平均吸收率"],
                "current_progress_cn": [
                    "已修正“结构参数随扫描波长变化”的错误，当前光谱已可按固定结构解释。",
                    "已完成 d_W = 10~120 nm 的主扫描，普通 Tamm 吸收器的主要高吸收工作区已锁定。",
                    "参考 TPP 文献结构重建 Air / W / Si spacer / (Si / SiO2)^4 / Si substrate 反射型吸收器。",
                    "在 W 厚度固定为 8.42 nm 时，已通过 spacer 粗扫与精扫获得自主优化近完美吸收点。",
                ],
                "current_best_params_cn": [
                    "TPP 当前最佳点：d_spacer = 320 nm，d_W = 8.42 nm",
                    "峰值吸收率 A = 1 - R ≈ 0.9994",
                    "反射率 R ≈ 0.00059",
                    "峰位 λ ≈ 3.34 μm",
                ],
                "current_findings_cn": [
                    "d_W 从 10 nm 增加到 120 nm 时，峰值吸收率由约 0.241 持续提升到约 0.998。",
                    "峰位随 d_W 增厚呈轻微短波漂移，由约 4.80 μm 移动到约 4.50 μm。",
                    "到 110~120 nm 区间时已进入近完美吸收区，继续增厚的边际收益开始明显减小。",
                    "TPP 反射型结构在 d_spacer = 320 nm、λ = 3.34 μm 处达到 A≈0.9994，证明前沿吸收器模块已具备正结果。",
                    "该 TPP 结果不包装为严格复现论文 4.14 μm，而定义为参考文献结构后的自主参数优化结果。",
                ],
                "transition_ready_cn": "普通 Tamm/TPP 吸收器已形成可展示正结果，可支撑第 2 阶段的反射相位与拓扑分类。",
                "next_actions_cn": [
                    "补充 d_spacer = 320 nm、λ = 3.34 μm 的 |E|² 电场分布图，用于解释吸收能量局域位置。",
                    "保留论文 4.14 μm 对齐问题作为后续复现差异讨论，不再阻塞当前前沿模块展示。",
                    "后续可在当前 TPP 正结果基础上提取反射相位曲线，进入拓扑分类。"
                ],
            },
            {
                "stage_id": "reflection_phase_topology",
                "title_cn": "反射相位与拓扑分类",
                "title_en": "Reflection Phase and Topological Classification",
                "priority": 2,
                "status": "in_progress",
                "goal_cn": "在普通 Tamm 吸收器参数基础上，引入反射相位、卷绕数或平庸/非平庸反射表面分类。",
                "suitable_backend_cn": ["平面多层膜理论模型优先", "必要时用 COMSOL 做交叉验证"],
                "core_outputs_cn": ["反射相位", "相位跨越", "卷绕数分类", "平庸/非平庸标记"],
                "current_progress_cn": [
                    "已建立 d_W 联合扫描的相位分析入口，并已导出第一版相位分析总包。",
                    "已新增 1D 反射相位端结构筛选入口 run_tamm_reflection_phase_screen.py，用于筛选同一波长下高反射且相位差接近 π 的端结构对。",
                    "当前最适合以 d_W = 100, 110, 120 nm 三个代表点作为第 2 阶段核心样本做相位比较。",
                ],
                "current_findings_cn": [
                    "现阶段已能够同步追踪 A_max、峰位、峰处相位和展开相位跨度。",
                    "随着 d_W 增大，吸收峰位轻微向短波移动，相位信息已具备进入拓扑分类的最小分析条件。",
                    "当前整体相位对比最强的候选对为 90 nm 与 120 nm。",
                    "当前峰处相位差最大的高吸收候选对为 110 nm 与 120 nm。",
                    "已建立 cutline 界面态候选判据：interface/background、peak/background、hotspot_peak_x 与 FWHM。",
                    "119/120 nm @ 4.55 μm 三条 y 位置 cutline 均显示 interface/background≈0.965、FWHM≈11.6 μm，不支持强界面局域态。",
                    "100~130 nm 左右厚度 49 组筛选与 130/130 nm 波长扫描均未发现满足界面局域判据的正候选。",
                    "对当前 tamm_spectrum_dW_scan(4).csv 按 min(R)>=0.70、|π-Δφ|<=0.35 rad 筛选后，通过候选数为 0；最佳对为 90/120 nm，但 min(R) 仅约 0.024，仍不适合进入正界面态拼接。",
                ],
                "next_actions_cn": [
                    "暂停直接拼接相近厚度的 2D 猜测式扫描。",
                    "回到 1D 反射相位筛选，扩大 d_W、金属层厚度或 DBR 端层厚度范围，寻找同一波长下 R 较高且 arg(S11) 相差接近 π 的两种端结构。",
                    "只有找到相位差明确的左右端结构后，再做 2D 拼接 cutline 或场图验证。",
                ],
            },
            {
                "stage_id": "topological_tamm_boundary_state",
                "title_cn": "拓扑 Tamm 边界态与空间调控",
                "title_en": "Topological Tamm Boundary State and Spatial Control",
                "priority": 3,
                "status": "screening_negative",
                "goal_cn": "构造两类不同拓扑反射表面的界面，验证边界态局域化与热辐射空间调控潜力。",
                "suitable_backend_cn": ["二维或更高维 COMSOL 模型", "界面场分布与局域增强分析"],
                "core_outputs_cn": ["界面场分布", "局域化强度", "界面热辐射空间分布", "边界态存在性证据"],
                "current_progress_cn": [
                    "已完成 119/120 nm @ 4.55 μm 三条 cutline 验证。",
                    "已完成 d_W,L/d_W,R = 100~130 nm 的 49 组 cutline 筛选。",
                    "已完成 130/130 nm 在 4.45~4.75 μm 的波长 cutline 扫描。",
                    "当前所有已测候选均未满足 interface/background > 1.5、|peak_x| < 0.5 μm、FWHM < 5 μm 的正候选判据。",
                ],
                "next_actions_cn": [
                    "将当前阶段定位为界面态量化判据建立与反例排除，不作为正界面态结果。",
                    "下一轮若继续追正结果，应先做 1D phase scan：d_W=80~160 nm、λ=4.3~4.9 μm，筛选反射相位差接近 π 的左右端结构。",
                    "找到相位端结构后，再进入 2D 拼接验证，而不是继续围绕 119/120 或 130/130 做局部微调。",
                ],
            },
        ],
    },
    {
        "module_id": "pdrc_multilayer_cooling",
        "title_cn": "被动日间辐射冷却薄膜光谱调控",
        "title_en": "Passive Daytime Radiative Cooling Multilayer Spectral Control",
        "module_type": "frontier_application",
        "goal_cn": "构建兼具太阳波段高反射与 8-13 μm 大气窗口高发射的薄膜结构，形成由 COMSOL 宽波段扫描与 Python 指标筛选共同支撑的 PDRC 模块。",
        "why_cn": "该模块以平面多层膜为第一入口，复用现有薄膜理论平台，同时把应用目标从可见光减反/滤光扩展到热辐射冷却。",
        "status": "real_material_validated",
        "selected_candidate_cn": {
            "structure_cn": "Air / SiO2_1 / TiO2_1 / SiO2_2 / TiO2_2 / SiO2_3 / Ag / substrate",
            "thicknesses_nm": {
                "d_SiO2_1": 200.0,
                "d_TiO2_1": 440.0,
                "d_SiO2_2": 500.0,
                "d_TiO2_2": 440.0,
                "d_SiO2_3": 1000.0,
                "d_Ag": 500.0,
            },
            "metrics": {
                "A_solar_avg": 0.0466,
                "A_solar_weighted_astm_g173_am15_global": 0.0435,
                "R_solar_weighted_astm_g173_am15_global": 0.9565,
                "epsilon_8_13_avg": 0.8044,
                "cooling_score_weighted_astm_g173": 0.7609,
            },
            "note_cn": "该候选已完成太阳波段与 8-13 μm 红外窗口真实材料验证，适合作为 PDRC 平面膜第一版主结果。",
        },
        "stages": [
            {
                "stage_id": "pdrc_tmm_wideband_screening",
                "title_cn": "宽波段 TMM 光谱筛选",
                "title_en": "Wideband TMM Spectral Screening",
                "priority": 1,
                "status": "implemented",
                "goal_cn": "先用 Air / SiO2_1 / TiO2_1 / SiO2_2 / TiO2_2 / SiO2_3 / Ag / substrate 平面膜跑通 0.3-13 μm 光谱。",
                "suitable_backend_cn": ["Python TMM 宽波段扫描"],
                "core_outputs_cn": ["R(λ)", "T(λ)", "A(λ)", "emissivity(λ)≈A(λ)", "A_solar_avg", "epsilon_8_13_avg", "cooling_score"],
                "current_progress_cn": [
                    "已接入 pdrc_multilayer_cooling 独立模块，不放入教学主树首页。",
                    "第一版结构已对齐 COMSOL 2D 平面层模型，并完成真实材料宽波段 R/T/A 导出。",
                    "已支持导出 spectrum.csv、metrics.csv、summary.json、summary.txt 和宽波段图。",
                    "TMM 快速筛选保留为辅助入口，展示主结果以 COMSOL 真实材料扫描和 Python 指标筛选为准。",
                ],
                "next_actions_cn": [
                    "已接入 ASTM G173-03 AM1.5 global tilt 标准太阳光谱权重；blackbody_5778K 仅保留为无外部数据时的快速近似。",
                    "保留当前 TMM 版本作为快速教学演示，不再把它作为最终 PDRC 性能结论。",
                ],
            },
            {
                "stage_id": "pdrc_comsol_representative_validation",
                "title_cn": "COMSOL 宽波段参数扫描与候选筛选",
                "title_en": "COMSOL Wideband Parameter Scan and Candidate Selection",
                "priority": 2,
                "status": "real_material_validated",
                "goal_cn": "通过 COMSOL 导出太阳波段与 8-13 μm 红外窗口 R/T/A，再由 Python 合并多段扫描、计算太阳加权吸收和窗口平均发射率。",
                "suitable_backend_cn": ["COMSOL 2D 平面多层膜", "Python COMSOL CSV 合并、去重、指标筛选与出图"],
                "core_outputs_cn": ["A_solar_avg", "A_solar_weighted", "epsilon_8_13_avg", "cooling_score_weighted", "候选参数表", "二维参数散点图"],
                "current_progress_cn": [
                    "已完成 d_TiO2 等厚扫描，并锁定 d_TiO2_1=d_TiO2_2=440 nm 作为后续 SiO2 微调基准。",
                    "已完成 d_SiO2_1 / d_SiO2_2 粗扫与候选太阳波段复核。",
                    "最终主候选为 d_SiO2_1=200 nm、d_SiO2_2=500 nm、d_TiO2_1=d_TiO2_2=440 nm、d_SiO2_3=1000 nm、Ag=500 nm。",
                    "真实材料验证指标：A_solar_avg=0.0466、A_solar_weighted(ASTM G173)=0.0435、R_solar_weighted=0.9565、epsilon_8_13_avg=0.8044、cooling_score_weighted(ASTM G173)=0.7609。",
                    "太阳波段 0.3-2.5 μm 使用真实材料有效波段导出，ASTM G173 加权吸收为 0.0435。",
                    "红外窗口 8-13 μm 使用 COMSOL 中红外 n,k，平均发射率为 0.8044。",
                    "历史红外最高对照候选为 d_SiO2_1=240 nm、d_SiO2_2=600 nm，epsilon_8_13_avg=0.8011，仅作为早期筛选参考。",
                ],
                "next_actions_cn": [
                    "停止继续大规模扫参，转入结果整理、冷却功率模型或汇报图表输出。",
                    "在文档中明确当前标准太阳加权使用 ASTM G173-03 AM1.5 global tilt。",
                    "保留 240/600 nm 作为红外最高对照，不作为主候选。",
                ],
            },
            {
                "stage_id": "pdrc_advanced_structures",
                "title_cn": "多孔/粗糙/微结构增强版本",
                "title_en": "Porous, Rough and Textured PDRC Extensions",
                "priority": 3,
                "status": "planned",
                "goal_cn": "在平面膜跑通之后，引入多孔 SiO2、粗糙发射表面或等效渐变层，提高太阳反射与红外发射的综合表现。",
                "suitable_backend_cn": ["Python 等效介质模型", "COMSOL 二维或三维结构验证"],
                "core_outputs_cn": ["参数敏感性", "结构增强因子", "PDRC 指标提升量"],
                "next_actions_cn": [
                    "优先从多孔 SiO2 有效折射率和厚度扫描开始。",
                    "再接入蛾眼/粗糙结构作为高级版本，不和第一版平面膜混在一起。",
                ],
            },
        ],
    }
]


def get_teaching_case_expansion_roadmap() -> Dict[str, Any]:
    return {
        "summary_cn": "教学主树扩展建议应按物理层级推进，而不是按名词平铺。",
        "principles_cn": [
            "优先把同一物理族的案例组织成参数模式或主题别名，避免重复模块。",
            "先扩基础均匀膜层，再扩周期QW膜堆，最后扩展到高级滤光结构。",
            "高级滤光片与皱褶结构建议放入扩展区，不建议直接挤入核心首页。",
        ],
        "recommended_sequence_cn": [
            "1/4波长单层膜",
            "1/2波长单层膜",
            "1/4波长双层膜系",
            "QW膜堆 / 布拉格反射镜",
            "窄带滤光片",
            "皱褶滤光片",
        ],
        "groups": TEACHING_CASE_EXPANSION_ROADMAP,
    }


def list_teaching_case_expansion_ids() -> List[str]:
    seen: List[str] = []
    for group in TEACHING_CASE_EXPANSION_ROADMAP:
        for case in group["cases"]:
            case_id = str(case["case_id"])
            if case_id not in seen:
                seen.append(case_id)
    return seen


def get_frontier_research_model_tree() -> Dict[str, Any]:
    return {
        "summary_cn": "前沿研究模块建议与教学主树分离管理；当前保留 PDRC 被动日间辐射冷却、TPP 反射型近完美吸收与 Tamm 界面态筛选三条前沿支线。",
        "principles_cn": [
            "不把前沿研究模块直接塞进教学主树首页，避免打乱教学案例层级。",
            "优先做一维或准一维可验证结构，先锁定光谱和参数趋势，再进入二维场分布或微结构增强。",
            "先保证“固定结构光谱”解释正确，再开展相位、界面结构或 PDRC 参数优化。",
        ],
        "recommended_sequence_cn": [
            "普通 Tamm / TPP 吸收器",
            "反射相位与拓扑分类",
            "拓扑 Tamm 边界态与热辐射空间调控",
            "PDRC 平面多层膜宽波段筛选",
            "PDRC COMSOL 代表点验证",
        ],
        "modules": FRONTIER_RESEARCH_MODEL_TREE,
    }


def list_frontier_research_module_ids() -> List[str]:
    return [str(module["module_id"]) for module in FRONTIER_RESEARCH_MODEL_TREE]


def _status_color(status: str) -> str:
    key = str(status).lower()
    if key in {"implemented", "phase_complete", "first_version_locked", "real_material_validated", "optimized_absorber_found"}:
        return GREEN
    if key in {"screening_negative"}:
        return RED
    if key in {"in_progress", "ready_to_start"}:
        return BLUE
    return MUTED


def _status_label_cn(status: str) -> str:
    labels = {
        "implemented": "已实现",
        "phase_complete": "相位扫描完成",
        "first_version_locked": "第一版已锁定",
        "real_material_validated": "真实材料验证完成",
        "optimized_absorber_found": "已获得优化吸收正结果",
        "screening_negative": "反例筛选",
        "in_progress": "进行中",
        "ready_to_start": "待启动",
        "planned": "计划中",
    }
    return labels.get(str(status), str(status))


def _draw_box(
    ax: plt.Axes,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    subtitle: str = "",
    color: str = BLUE,
    fontsize: float = 9.2,
) -> None:
    from matplotlib.patches import FancyBboxPatch

    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        linewidth=1.35,
        edgecolor=color,
        facecolor=PANEL,
        alpha=0.98,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center", fontsize=fontsize, fontweight="semibold", color=INK)
    if subtitle:
        ax.text(x + w / 2, y + h * 0.28, subtitle, ha="center", va="center", fontsize=fontsize - 1.2, color=MUTED)


def _draw_arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], *, color: str = MUTED) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={"arrowstyle": "->", "linewidth": 1.25, "color": color, "shrinkA": 4, "shrinkB": 4},
    )


def _export_frontier_model_tree_png(roadmap: Dict[str, Any], *, prefix: str) -> str:
    png_path = output_file(f"{prefix}.png")
    fig, ax = plt.subplots(figsize=(14.5, 8.2))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.955, "前沿研究模型树", ha="center", va="center", fontsize=18, fontweight="semibold", color=INK)
    ax.text(
        0.5,
        0.91,
        "PDRC 已形成真实材料验证正结果；TPP 已获得近完美吸收正结果；Tamm 界面态继续作为前沿筛选分支。",
        ha="center",
        va="center",
        fontsize=10.5,
        color=MUTED,
    )

    modules = roadmap["modules"]
    y_positions = np.linspace(0.67, 0.23, max(len(modules), 1))
    for module, y in zip(modules, y_positions):
        module_color = _status_color(str(module["status"]))
        _draw_box(
            ax,
            x=0.035,
            y=y,
            w=0.23,
            h=0.19,
            title=str(module["title_cn"]),
            subtitle=f"状态：{_status_label_cn(str(module['status']))}",
            color=module_color,
            fontsize=9.4,
        )
        stages = list(module["stages"])
        stage_xs = np.linspace(0.33, 0.79, max(len(stages), 1))
        for idx, (stage, sx) in enumerate(zip(stages, stage_xs)):
            stage_color = _status_color(str(stage["status"]))
            _draw_box(
                ax,
                x=sx,
                y=y + 0.02,
                w=0.17,
                h=0.15,
                title=str(stage["title_cn"]),
                subtitle=_status_label_cn(str(stage["status"])),
                color=stage_color,
                fontsize=8.5,
            )
            if idx == 0:
                _draw_arrow(ax, (0.265, y + 0.095), (sx, y + 0.095))
            else:
                _draw_arrow(ax, (stage_xs[idx - 1] + 0.17, y + 0.095), (sx, y + 0.095))

    legend_items = [
        ("已锁定 / 已完成", GREEN),
        ("进行中", BLUE),
        ("反例筛选", RED),
        ("计划中", MUTED),
    ]
    lx = 0.06
    for label, color in legend_items:
        ax.scatter([lx], [0.085], s=90, color=color)
        ax.text(lx + 0.022, 0.085, label, va="center", ha="left", fontsize=9, color=INK)
        lx += 0.21

    save_publication_figure(fig, png_path)
    plt.close(fig)
    return str(png_path)


def _export_teaching_expansion_tree_png(roadmap: Dict[str, Any], *, prefix: str) -> str:
    png_path = output_file(f"{prefix}.png")
    fig, ax = plt.subplots(figsize=(14.5, 7.6))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.94, "教学主树扩展路线图", ha="center", va="center", fontsize=18, fontweight="semibold", color=INK)
    ax.text(0.5, 0.895, str(roadmap["summary_cn"]), ha="center", va="center", fontsize=10.5, color=MUTED)

    groups = roadmap["groups"]
    y_positions = np.linspace(0.70, 0.18, max(len(groups), 1))
    for group, y in zip(groups, y_positions):
        _draw_box(
            ax,
            x=0.035,
            y=y,
            w=0.19,
            h=0.15,
            title=str(group["title_cn"]),
            subtitle=f"优先级 {group['priority']}",
            color=BLUE,
            fontsize=9.3,
        )
        all_cases = list(group["cases"])
        cases = all_cases[:4]
        if not cases:
            continue
        x0 = 0.29
        gap = 0.16
        for idx, case in enumerate(cases):
            x = x0 + idx * gap
            _draw_box(
                ax,
                x=x,
                y=y + 0.015,
                w=0.13,
                h=0.12,
                title=str(case["title_cn"]),
                subtitle=str(case["recommended_mode"]),
                color=GREEN if idx == 0 else MUTED,
                fontsize=7.8,
            )
            if idx == 0:
                _draw_arrow(ax, (0.225, y + 0.075), (x, y + 0.075))
            else:
                _draw_arrow(ax, (x0 + (idx - 1) * gap + 0.13, y + 0.075), (x, y + 0.075))
        if len(all_cases) > len(cases):
            ax.text(0.95, y + 0.075, f"+{len(all_cases) - len(cases)} 项", ha="right", va="center", fontsize=8.5, color=MUTED)

    save_publication_figure(fig, png_path)
    plt.close(fig)
    return str(png_path)


def export_teaching_case_expansion_roadmap(
    *,
    prefix: str = "teaching_case_expansion_roadmap",
) -> Dict[str, str]:
    roadmap = get_teaching_case_expansion_roadmap()

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(roadmap, f, ensure_ascii=False, indent=2)

    txt_path = output_file(f"{prefix}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("教学主树案例扩展路线图\n")
        f.write("=" * 72 + "\n")
        f.write(f"{roadmap['summary_cn']}\n\n")
        f.write("推荐扩展顺序：\n")
        for item in roadmap["recommended_sequence_cn"]:
            f.write(f"- {item}\n")
        f.write("\n")
        for group in roadmap["groups"]:
            f.write(f"{group['title_cn']}\n")
            f.write(f"目标：{group['goal_cn']}\n")
            for case in group["cases"]:
                f.write(f"  - {case['title_cn']} | 模式：{case['recommended_mode']}\n")
                if case["host_case_id"]:
                    f.write(f"    依托案例：{case['host_case_id']}\n")
                f.write(f"    说明：{case['why_cn']}\n")
            f.write("\n")

    png_path = _export_teaching_expansion_tree_png(roadmap, prefix=prefix)

    return {
        "json": str(json_path),
        "txt": str(txt_path),
        "png": str(png_path),
    }


def export_frontier_research_model_tree(
    *,
    prefix: str = "frontier_research_model_tree",
) -> Dict[str, str]:
    roadmap = get_frontier_research_model_tree()

    json_path = output_file(f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(roadmap, f, ensure_ascii=False, indent=2)

    txt_path = output_file(f"{prefix}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("前沿研究模型树\n")
        f.write("=" * 72 + "\n")
        f.write(f"{roadmap['summary_cn']}\n\n")
        f.write("推荐推进顺序：\n")
        for item in roadmap["recommended_sequence_cn"]:
            f.write(f"- {item}\n")
        f.write("\n")
        for module in roadmap["modules"]:
            f.write(f"{module['title_cn']}\n")
            f.write(f"模块类型：{module['module_type']}\n")
            f.write(f"状态：{module['status']}\n")
            f.write(f"目标：{module['goal_cn']}\n")
            f.write(f"说明：{module['why_cn']}\n")
            for stage in module["stages"]:
                f.write(f"  - {stage['title_cn']} | 优先级：{stage['priority']} | 状态：{stage['status']}\n")
                f.write(f"    目标：{stage['goal_cn']}\n")
                if stage.get("current_progress_cn"):
                    f.write("    当前进展：\n")
                    for item in stage["current_progress_cn"]:
                        f.write(f"      * {item}\n")
                if stage.get("current_best_params_cn"):
                    f.write("    当前代表参数：\n")
                    for item in stage["current_best_params_cn"]:
                        f.write(f"      * {item}\n")
                if stage.get("current_findings_cn"):
                    f.write("    当前结论：\n")
                    for item in stage["current_findings_cn"]:
                        f.write(f"      * {item}\n")
                if stage.get("transition_ready_cn"):
                    f.write(f"    阶段切换判断：{stage['transition_ready_cn']}\n")
                if stage.get("next_actions_cn"):
                    f.write("    下一步：\n")
                    for item in stage["next_actions_cn"]:
                        f.write(f"      * {item}\n")
            f.write("\n")

    png_path = _export_frontier_model_tree_png(roadmap, prefix=prefix)

    return {
        "json": str(json_path),
        "txt": str(txt_path),
        "png": str(png_path),
    }


def export_frontier_research_module_bundle(
    *,
    prefix: str = "frontier_research_module_bundle",
) -> Dict[str, str]:
    roadmap_files = export_frontier_research_model_tree(prefix=f"{prefix}_roadmap")
    manifest = {
        "module_ids": list_frontier_research_module_ids(),
        "roadmap_files": roadmap_files,
    }
    manifest_path = output_file(f"{prefix}_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    index_path = output_file(f"{prefix}_index.txt")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("前沿研究模型树总包索引\n")
        f.write("=" * 72 + "\n")
        f.write("模块列表：\n")
        for module_id in manifest["module_ids"]:
            f.write(f"- {module_id}\n")
        f.write("\n路线图文件：\n")
        f.write(f"- JSON: {roadmap_files['json']}\n")
        f.write(f"- TXT: {roadmap_files['txt']}\n")

    return {
        "manifest": str(manifest_path),
        "index": str(index_path),
        "roadmap_json": roadmap_files["json"],
        "roadmap_txt": roadmap_files["txt"],
    }


def export_teaching_case_expansion_bundle(
    *,
    prefix: str = "teaching_case_expansion_bundle",
) -> Dict[str, Any]:
    from .education import REPORT_CHAPTER2_CASES, export_report_case_outputs, export_report_comparison_figures, simulate_report_case
    from .validation import export_teaching_expansion_validation_template_bundle

    requested_case_ids = list_teaching_case_expansion_ids()
    supported_case_ids = [case_id for case_id in requested_case_ids if case_id in REPORT_CHAPTER2_CASES]
    pending_case_ids = [case_id for case_id in requested_case_ids if case_id not in REPORT_CHAPTER2_CASES]
    case_files: Dict[str, Dict[str, str]] = {}
    for case_id in supported_case_ids:
        result = simulate_report_case(case_id)
        case_files[case_id] = export_report_case_outputs(
            result=result,
            prefix=prefix,
            save_plot=True,
            save_csv=True,
            save_json=True,
            save_txt=True,
        )

    roadmap_files = export_teaching_case_expansion_roadmap(prefix=f"{prefix}_roadmap")
    comparison_files = export_report_comparison_figures(prefix=f"{prefix}_compare")
    validation_template_files = export_teaching_expansion_validation_template_bundle(
        prefix=f"{prefix}_validation_templates"
    )

    manifest = {
        "requested_case_ids": requested_case_ids,
        "supported_case_ids": supported_case_ids,
        "pending_case_ids": pending_case_ids,
        "roadmap_files": roadmap_files,
        "case_files": case_files,
        "comparison_files": comparison_files,
        "validation_template_files": validation_template_files,
    }
    manifest_path = output_file(f"{prefix}_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    index_path = output_file(f"{prefix}_index.txt")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("教学扩展案例总包索引\n")
        f.write("=" * 72 + "\n")
        f.write("案例列表：\n")
        for case_id in supported_case_ids:
            f.write(f"- {case_id}\n")
        if pending_case_ids:
            f.write("\n待实现规划项：\n")
            for case_id in pending_case_ids:
                f.write(f"- {case_id}\n")
        f.write("\n路线图文件：\n")
        f.write(f"- JSON: {roadmap_files['json']}\n")
        f.write(f"- TXT: {roadmap_files['txt']}\n")
        f.write("\n案例导出文件：\n")
        for case_id, files in case_files.items():
            f.write(f"{case_id}\n")
            for key, path in files.items():
                f.write(f"  - {key}: {path}\n")
        f.write("\n对比图文件：\n")
        for figure_id, files in comparison_files.items():
            f.write(f"{figure_id}\n")
            for key, path in files.items():
                f.write(f"  - {key}: {path}\n")
        f.write("\n验证模板文件：\n")
        for key, path in validation_template_files.items():
            f.write(f"  - {key}: {path}\n")

    return {
        "manifest": str(manifest_path),
        "index": str(index_path),
        "roadmap_files": roadmap_files,
        "case_files": case_files,
        "comparison_files": comparison_files,
        "validation_template_files": validation_template_files,
    }
