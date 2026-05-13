from __future__ import annotations

import json
from typing import Any, Dict, List

from .paths import output_file


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
        "goal_cn": "从普通 Tamm 吸收器出发，逐步走向反射相位拓扑分类、界面边界态与热辐射空间调控。",
        "why_cn": "该模块仍建立在一维多层膜与金属薄膜结构之上，能够与现有薄膜平台平滑衔接，同时又具备明显的前沿研究属性。",
        "status": "in_progress",
        "stages": [
            {
                "stage_id": "tamm_absorber_basic",
                "title_cn": "普通 Tamm 吸收器",
                "title_en": "Conventional Tamm Absorber",
                "priority": 1,
                "status": "phase_complete",
                "goal_cn": "建立 Air / 金属薄膜 / 间隔层 / DBR / 基底 结构，并锁定主要高吸收工作波段。",
                "suitable_backend_cn": ["平面多层膜理论模型", "COMSOL 单谱与参数扫描"],
                "core_outputs_cn": ["R(λ)", "A(λ)", "峰值吸收率", "峰位", "平均吸收率"],
                "current_progress_cn": [
                    "已修正“结构参数随扫描波长变化”的错误，当前光谱已可按固定结构解释。",
                    "已完成 d_W = 10~120 nm 的主扫描，普通 Tamm 吸收器的主要高吸收工作区已锁定。",
                    "当前峰位稳定在约 4.50~4.80 μm，高吸收工作区已基本成形。",
                ],
                "current_best_params_cn": [
                    "当前阶段性最佳点：d_W = 120 nm",
                    "峰值吸收率 A_max ≈ 0.9979",
                    "峰位约为 4.50 μm",
                    "平均吸收率 A_mean ≈ 0.9272",
                ],
                "current_findings_cn": [
                    "d_W 从 10 nm 增加到 120 nm 时，峰值吸收率由约 0.241 持续提升到约 0.998。",
                    "峰位随 d_W 增厚呈轻微短波漂移，由约 4.80 μm 移动到约 4.50 μm。",
                    "到 110~120 nm 区间时已进入近完美吸收区，继续增厚的边际收益开始明显减小。",
                ],
                "transition_ready_cn": "普通 Tamm 吸收器的主摸底阶段已经足够支撑第 2 阶段的反射相位与拓扑分类。",
                "next_actions_cn": [
                    "优先转入反射相位与拓扑分类，不再把主精力放在继续大范围增厚 d_W 上。",
                    "如需做数值收尾，可只在 110, 115, 120, 125, 130 nm 附近做小范围细扫。",
                    "后续将以 d_W = 120 nm 及其邻域代表点为基础提取反射相位曲线。",
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
                    "当前最适合以 d_W = 100, 110, 120 nm 三个代表点作为第 2 阶段核心样本做相位比较。",
                ],
                "current_findings_cn": [
                    "现阶段已能够同步追踪 A_max、峰位、峰处相位和展开相位跨度。",
                    "随着 d_W 增大，吸收峰位轻微向短波移动，相位信息已具备进入拓扑分类的最小分析条件。",
                    "当前整体相位对比最强的候选对为 90 nm 与 120 nm。",
                    "当前峰处相位差最大的高吸收候选对为 110 nm 与 120 nm。",
                    "若以“后续界面边界态验证”为默认目标，当前更推荐先采用 110 nm 与 120 nm 作为界面拼接默认组。",
                ],
                "next_actions_cn": [
                    "固定 d_W 代表点，提取 4.2~5.0 μm 区间的反射相位曲线。",
                    "默认先围绕 (110, 120) nm 做界面拼接，保留 (90, 120) nm 作为探索对照组。",
                    "在相位证据足够后，再设计平庸/非平庸反射表面的界面拼接方案。",
                ],
            },
            {
                "stage_id": "topological_tamm_boundary_state",
                "title_cn": "拓扑 Tamm 边界态与空间调控",
                "title_en": "Topological Tamm Boundary State and Spatial Control",
                "priority": 3,
                "status": "planned",
                "goal_cn": "构造两类不同拓扑反射表面的界面，验证边界态局域化与热辐射空间调控潜力。",
                "suitable_backend_cn": ["二维或更高维 COMSOL 模型", "界面场分布与局域增强分析"],
                "core_outputs_cn": ["界面场分布", "局域化强度", "界面热辐射空间分布", "边界态存在性证据"],
                "current_progress_cn": [
                    "当前尚未进入界面拼接与场局域分析阶段。",
                ],
                "next_actions_cn": [
                    "在获得平庸/非平庸反射表面分类后，设计界面拼接结构。",
                    "优先验证界面附近场增强，再考虑更完整的热辐射空间分布分析。",
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
        "summary_cn": "前沿研究模块建议与教学主树分离管理；当前普通 Tamm 吸收器的工作波段与关键参数已基本锁定，下一步应转入反射相位与拓扑分类。",
        "principles_cn": [
            "不把前沿研究模块直接塞进教学主树首页，避免打乱教学案例层级。",
            "优先做一维或准一维可验证结构，先锁定光谱和参数趋势，再进入拓扑边界态。",
            "先保证“固定结构光谱”解释正确，再开展 d_W、相位与界面结构的高阶分析。",
        ],
        "recommended_sequence_cn": [
            "普通 Tamm 吸收器",
            "反射相位与拓扑分类",
            "拓扑 Tamm 边界态与热辐射空间调控",
        ],
        "modules": FRONTIER_RESEARCH_MODEL_TREE,
    }


def list_frontier_research_module_ids() -> List[str]:
    return [str(module["module_id"]) for module in FRONTIER_RESEARCH_MODEL_TREE]


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

    return {
        "json": str(json_path),
        "txt": str(txt_path),
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

    return {
        "json": str(json_path),
        "txt": str(txt_path),
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
