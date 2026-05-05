"""Thin-film fitting package.

Module layout:
- thinfilm.io: CSV and COMSOL data loading.
- thinfilm.optics: thin-film forward model and interpolation.
- thinfilm.fitting: objective functions and inverse fitting.
- thinfilm.diagnostics: error analysis, heatmaps, and batch utilities.
- thinfilm.reports: report helpers.
- thinfilm.api: APP-facing high-level API.
- thinfilm.sweep: COMSOL parameter-sweep table analysis.
"""

from .api import (
    export_teaching_case_outputs,
    export_teaching_main_branch_catalog,
    export_teaching_comparison_figures,
    export_teaching_report_bundle,
    export_teaching_suite_outputs,
    fit_two_angle,
    fit_current_main_case,
    get_teaching_main_branch_catalog,
    list_teaching_cases,
    simulate_teaching_case,
    simulate_teaching_design,
    simulate_teaching_suite,
)
from .education import (
    LayerSpec,
    REPORT_CHAPTER2_CASES,
    REPORT_COMPARISON_FIGURES,
    build_double_ar_layers,
    build_fp_double_halfwave_layers,
    build_fp_single_halfwave_layers,
    build_high_reflector_layers,
    build_neutral_beamsplitter_layers,
    build_single_ar_layers,
    build_triple_ar_layers,
    describe_layers,
    export_report_case_outputs,
    export_report_main_branch_catalog,
    export_report_comparison_figures,
    export_report_chapter2_suite_outputs,
    export_report_main_branch_bundle,
    get_report_main_branch_catalog,
    list_report_chapter2_cases,
    list_report_comparison_figures_catalog,
    multilayer_rt_spectrum,
    simulate_report_case,
    simulate_report_chapter2_suite,
    simulate_report_design,
)
from .joint import fit_joint_p_80_100_case, fit_joint_shared_material_two_angle_samples
from .sweep import (
    fit_d_n1b_theta_sweep,
    fit_n1b_theta_sweep,
    quick_screen_d_n1b_theta_sweep,
    score_n1b_theta_sweep,
    screen_d_n1b_sweep_quality,
    summarize_n1b_theta_sweep,
)
from .uncertainty import (
    export_inversion_uncertainty_analysis,
    run_inversion_uncertainty_analysis,
)
from .validation import (
    compare_teaching_case_to_reference,
    export_teaching_validation_result,
    export_teaching_validation_suite_summary,
    run_teaching_validation_suite,
)

__all__ = [
    "export_teaching_case_outputs",
    "export_teaching_main_branch_catalog",
    "export_teaching_comparison_figures",
    "export_teaching_report_bundle",
    "export_teaching_suite_outputs",
    "fit_two_angle",
    "fit_current_main_case",
    "get_teaching_main_branch_catalog",
    "list_teaching_cases",
    "simulate_teaching_case",
    "simulate_teaching_design",
    "simulate_teaching_suite",
    "LayerSpec",
    "REPORT_CHAPTER2_CASES",
    "REPORT_COMPARISON_FIGURES",
    "multilayer_rt_spectrum",
    "describe_layers",
    "simulate_report_design",
    "simulate_report_case",
    "simulate_report_chapter2_suite",
    "export_report_case_outputs",
    "export_report_main_branch_catalog",
    "export_report_comparison_figures",
    "export_report_chapter2_suite_outputs",
    "export_report_main_branch_bundle",
    "get_report_main_branch_catalog",
    "list_report_chapter2_cases",
    "list_report_comparison_figures_catalog",
    "build_single_ar_layers",
    "build_double_ar_layers",
    "build_triple_ar_layers",
    "build_high_reflector_layers",
    "build_fp_single_halfwave_layers",
    "build_fp_double_halfwave_layers",
    "build_neutral_beamsplitter_layers",
    "fit_joint_shared_material_two_angle_samples",
    "fit_joint_p_80_100_case",
    "fit_d_n1b_theta_sweep",
    "fit_n1b_theta_sweep",
    "quick_screen_d_n1b_theta_sweep",
    "score_n1b_theta_sweep",
    "screen_d_n1b_sweep_quality",
    "summarize_n1b_theta_sweep",
    "compare_teaching_case_to_reference",
    "run_teaching_validation_suite",
    "export_teaching_validation_result",
    "export_teaching_validation_suite_summary",
    "run_inversion_uncertainty_analysis",
    "export_inversion_uncertainty_analysis",
]
