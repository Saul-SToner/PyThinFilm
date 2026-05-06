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
