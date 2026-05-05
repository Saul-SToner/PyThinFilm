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
