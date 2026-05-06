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
    build_teaching_expansion_validation_cases_from_mapping,
    build_teaching_expansion_validation_templates,
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
