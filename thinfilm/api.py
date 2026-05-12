from __future__ import annotations

from typing import Any, Dict

from .education import (
    export_report_case_outputs,
    export_report_main_branch_catalog,
    export_report_comparison_figures,
    export_report_chapter2_suite_outputs,
    export_report_main_branch_bundle,
    get_report_main_branch_catalog,
    list_report_chapter2_cases,
    simulate_report_case,
    simulate_report_chapter2_suite,
    simulate_report_design,
)
from .roadmap import (
    export_teaching_case_expansion_bundle,
    export_teaching_case_expansion_roadmap,
    get_teaching_case_expansion_roadmap,
    list_teaching_case_expansion_ids,
)
from .validation import (
    analyze_quasi_random_absorbing_surface,
    analyze_absorbing_surface_gain_against_baseline,
    export_absorbing_surface_roughness_bundle,
    export_absorbing_surface_baseline_template,
    export_absorbing_surface_gain_bundle,
    export_absorbing_surface_gain_trend_bundle,
    export_absorbing_surface_topic_bundle,
    build_advanced_ar_validation_cases,
    build_teaching_expansion_validation_cases_from_mapping,
    build_teaching_expansion_validation_templates,
    export_advanced_ar_bundle,
    export_porous_double_ar_sensitivity_bundle,
    export_quasi_random_absorbing_surface_bundle,
    summarize_absorbing_surface_roughness,
    export_teaching_expansion_validation_bundle_from_file,
    export_teaching_expansion_validation_bundle_from_mapping,
    export_teaching_expansion_validation_template_bundle,
    load_teaching_expansion_validation_mapping,
)


def simulate_teaching_design(
    design_type: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """APP-facing wrapper for the report-style forward thin-film simulator."""
    return simulate_report_design(design_type=design_type, **kwargs)


def list_teaching_cases() -> list[dict[str, Any]]:
    """APP-facing chapter-2 case catalog."""
    return list_report_chapter2_cases()


def get_teaching_main_branch_catalog() -> Dict[str, Any]:
    """APP-facing UI catalog for the whole teaching main branch."""
    return get_report_main_branch_catalog()


def simulate_teaching_case(
    case_id: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """APP-facing wrapper for one chapter-2 preset case."""
    return simulate_report_case(case_id=case_id, **kwargs)


def simulate_teaching_suite(
    **kwargs: Any,
) -> Dict[str, Dict[str, Any]]:
    """APP-facing wrapper for the full chapter-2 preset suite."""
    return simulate_report_chapter2_suite(**kwargs)


def export_teaching_case_outputs(
    case_id: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Run one teaching case and export plot/data/report files."""
    export_keys = {"prefix", "save_plot", "save_csv", "save_json", "save_txt"}
    export_kwargs = {key: kwargs.pop(key) for key in list(kwargs.keys()) if key in export_keys}
    result = simulate_report_case(case_id=case_id, **kwargs)
    return export_report_case_outputs(result=result, **export_kwargs)


def export_teaching_suite_outputs(
    **kwargs: Any,
) -> Dict[str, Dict[str, str]]:
    """Run and export the whole chapter-2 teaching suite."""
    return export_report_chapter2_suite_outputs(**kwargs)


def export_teaching_comparison_figures(
    **kwargs: Any,
) -> Dict[str, Dict[str, str]]:
    """Export report-style multi-curve comparison figures for the main teaching branch."""
    return export_report_comparison_figures(**kwargs)


def export_teaching_main_branch_catalog(
    **kwargs: Any,
) -> Dict[str, Any]:
    """Export the UI-friendly main-branch catalog to JSON."""
    return export_report_main_branch_catalog(**kwargs)


def export_teaching_report_bundle(
    **kwargs: Any,
) -> Dict[str, Any]:
    """Export the whole main teaching branch as a report-style bundle."""
    return export_report_main_branch_bundle(**kwargs)


def get_teaching_expansion_roadmap() -> Dict[str, Any]:
    """APP-facing roadmap for the next wave of teaching-case expansion."""
    return get_teaching_case_expansion_roadmap()


def export_teaching_expansion_roadmap(
    **kwargs: Any,
) -> Dict[str, str]:
    """Export the structured roadmap for extending teaching cases."""
    return export_teaching_case_expansion_roadmap(**kwargs)


def list_teaching_expansion_case_ids() -> list[str]:
    """List the current teaching-case expansion IDs in roadmap order."""
    return list_teaching_case_expansion_ids()


def export_teaching_expansion_bundle(
    **kwargs: Any,
) -> Dict[str, Any]:
    """Export roadmap, case outputs, and comparison figures for the expansion set."""
    return export_teaching_case_expansion_bundle(**kwargs)


def list_teaching_expansion_validation_templates() -> list[dict[str, Any]]:
    """List validation templates for expansion cases before CSV references are available."""
    return build_teaching_expansion_validation_templates()


def build_teaching_expansion_validation_cases(
    reference_mapping: Dict[str, Dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build runnable validation cases from a filled expansion reference mapping."""
    return build_teaching_expansion_validation_cases_from_mapping(reference_mapping)


def build_advanced_ar_cases(
    single_ar_csv: str,
    porous_csv: str,
    porous_double_csv: str,
    moth_eye_effective_csv: str,
    moth_eye_2d_csv: str,
    *,
    reference_label: str = "COMSOL",
) -> list[dict[str, Any]]:
    """Build the advanced anti-reflection validation suite."""
    return build_advanced_ar_validation_cases(
        single_ar_csv=single_ar_csv,
        porous_csv=porous_csv,
        porous_double_csv=porous_double_csv,
        moth_eye_effective_csv=moth_eye_effective_csv,
        moth_eye_2d_csv=moth_eye_2d_csv,
        reference_label=reference_label,
    )


def export_advanced_ar_topic_bundle(
    single_ar_csv: str,
    porous_csv: str,
    porous_double_csv: str,
    moth_eye_effective_csv: str,
    moth_eye_2d_csv: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Export the advanced anti-reflection topic bundle."""
    return export_advanced_ar_bundle(
        single_ar_csv=single_ar_csv,
        porous_csv=porous_csv,
        porous_double_csv=porous_double_csv,
        moth_eye_effective_csv=moth_eye_effective_csv,
        moth_eye_2d_csv=moth_eye_2d_csv,
        **kwargs,
    )


def export_porous_double_ar_sensitivity_topic(
    n_porous_csv: str,
    d_porous_csv: str,
    d_high_csv: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Export the porous double-layer AR sensitivity bundle."""
    return export_porous_double_ar_sensitivity_bundle(
        n_porous_csv=n_porous_csv,
        d_porous_csv=d_porous_csv,
        d_high_csv=d_high_csv,
        **kwargs,
    )


def analyze_absorbing_surface(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Analyze a quasi-random rough absorbing surface COMSOL result."""
    return analyze_quasi_random_absorbing_surface(reference_csv=reference_csv, **kwargs)


def export_absorbing_surface_bundle(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Export plots and summaries for a quasi-random rough absorbing surface."""
    return export_quasi_random_absorbing_surface_bundle(reference_csv=reference_csv, **kwargs)


def export_absorbing_surface_baseline_reference_template(
    **kwargs: Any,
) -> Dict[str, str]:
    """Export a template describing the planar baseline CSV needed for gain analysis."""
    return export_absorbing_surface_baseline_template(**kwargs)


def analyze_absorbing_surface_gain(
    rough_csv: str,
    baseline_csv: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Analyze the absorption gain of a rough surface against a planar baseline."""
    return analyze_absorbing_surface_gain_against_baseline(
        rough_csv=rough_csv,
        baseline_csv=baseline_csv,
        **kwargs,
    )


def export_absorbing_surface_gain_analysis(
    rough_csv: str,
    baseline_csv: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Export gain analysis files for rough surface versus planar baseline."""
    return export_absorbing_surface_gain_bundle(
        rough_csv=rough_csv,
        baseline_csv=baseline_csv,
        **kwargs,
    )


def export_absorbing_surface_gain_trend(
    roughness_files: Dict[float, str],
    baseline_csv: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Export roughness-factor gain trend against planar baseline."""
    return export_absorbing_surface_gain_trend_bundle(
        roughness_files=roughness_files,
        baseline_csv=baseline_csv,
        **kwargs,
    )


def export_absorbing_surface_topic(
    baseline_csv: str,
    best_rough_csv: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Export a final topic bundle for the rough absorbing surface branch."""
    return export_absorbing_surface_topic_bundle(
        baseline_csv=baseline_csv,
        best_rough_csv=best_rough_csv,
        **kwargs,
    )


def summarize_absorbing_surface_roughness_trend(
    roughness_files: Dict[float, str],
    **kwargs: Any,
) -> Dict[str, Any]:
    """Summarize the roughness trend of a rough absorbing surface sweep."""
    return summarize_absorbing_surface_roughness(roughness_files=roughness_files, **kwargs)


def export_absorbing_surface_roughness_trend(
    roughness_files: Dict[float, str],
    **kwargs: Any,
) -> Dict[str, str]:
    """Export roughness sweep plots and automatic conclusion files."""
    return export_absorbing_surface_roughness_bundle(roughness_files=roughness_files, **kwargs)


def export_teaching_expansion_validation_templates(
    **kwargs: Any,
) -> Dict[str, str]:
    """Export CSV/JSON/TXT templates for future expansion-case validation."""
    return export_teaching_expansion_validation_template_bundle(**kwargs)


def load_teaching_expansion_validation_template(
    template_file: str,
) -> Dict[str, Dict[str, Any]]:
    """Load a filled expansion validation template file."""
    return load_teaching_expansion_validation_mapping(template_file)


def export_teaching_expansion_validation_bundle(
    reference_mapping: Dict[str, Dict[str, Any]],
    **kwargs: Any,
) -> Dict[str, Any]:
    """Run expansion-case validation from an in-memory mapping."""
    return export_teaching_expansion_validation_bundle_from_mapping(reference_mapping, **kwargs)


def export_teaching_expansion_validation_bundle_from_template(
    template_file: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Run expansion-case validation directly from a filled JSON/CSV template file."""
    return export_teaching_expansion_validation_bundle_from_file(template_file, **kwargs)
