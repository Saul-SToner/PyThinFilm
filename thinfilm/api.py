from __future__ import annotations

from typing import Any, Dict

from .education import (
    export_pdrc_cooling_bundle,
    export_report_case_outputs,
    export_report_main_branch_catalog,
    export_report_comparison_figures,
    export_report_chapter2_suite_outputs,
    export_report_main_branch_bundle,
    get_report_main_branch_catalog,
    list_report_chapter2_cases,
    simulate_pdrc_multilayer_cooling,
    simulate_report_case,
    simulate_report_chapter2_suite,
    simulate_report_design,
    simulate_report_design_real_materials,
)
from .materials import (
    common_wavelength_window_um,
    export_real_material_library,
    get_material_roles_for_design as _get_material_roles_for_design,
    list_real_materials,
    load_real_material,
    material_complex_index,
    material_display_info,
    material_nk_at,
    sample_real_materials,
)
from .roadmap import (
    export_frontier_research_model_tree,
    export_frontier_research_module_bundle,
    export_teaching_case_expansion_bundle,
    export_teaching_case_expansion_roadmap,
    get_frontier_research_model_tree,
    get_teaching_case_expansion_roadmap,
    list_frontier_research_module_ids,
    list_teaching_case_expansion_ids,
)
from .pdrc import (
    analyze_pdrc_comsol_candidates,
    export_pdrc_comsol_candidate_bundle,
)
from .validation import (
    analyze_tamm_interface_2d_window_csv,
    analyze_tamm_dw_phase_scan,
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
    export_tamm_interface_priority_bundle,
    export_tamm_interface_window_analysis,
    export_tamm_interface_window_collection,
    export_tamm_interface_window_scan_collection,
    export_tamm_phase_candidate_pairs,
    export_tamm_phase_focus_bundle,
    export_tamm_reflection_phase_screen_bundle,
    export_tamm_dw_phase_bundle,
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


def simulate_teaching_design_real_materials(
    design_type: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """APP-facing wrapper for real-dispersion teaching TMM simulations."""
    return simulate_report_design_real_materials(design_type=design_type, **kwargs)


def export_real_material_library_outputs(
    **kwargs: Any,
) -> Dict[str, str]:
    """Export real-material catalog, sampled n/k table, and overview plot."""
    return export_real_material_library(**kwargs)


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


def get_frontier_model_tree() -> Dict[str, Any]:
    """APP-facing frontier research model tree, separated from the teaching main branch."""
    return get_frontier_research_model_tree()


def list_frontier_model_module_ids() -> list[str]:
    """List frontier research module IDs in roadmap order."""
    return list_frontier_research_module_ids()


def export_frontier_model_tree(
    **kwargs: Any,
) -> Dict[str, str]:
    """Export the structured frontier research model tree."""
    return export_frontier_research_model_tree(**kwargs)


def export_frontier_model_bundle(
    **kwargs: Any,
) -> Dict[str, str]:
    """Export the frontier research model tree bundle."""
    return export_frontier_research_module_bundle(**kwargs)


def simulate_pdrc_cooling(
    **kwargs: Any,
) -> Dict[str, Any]:
    """APP-facing wrapper for the PDRC wideband multilayer screening model."""
    return simulate_pdrc_multilayer_cooling(**kwargs)


def export_pdrc_cooling_outputs(
    **kwargs: Any,
) -> Dict[str, str]:
    """Export spectrum, metrics and plot for the PDRC cooling module."""
    return export_pdrc_cooling_bundle(**kwargs)


def analyze_pdrc_comsol_candidate_scan(
    ir_csv_files: list[str],
    **kwargs: Any,
) -> Dict[str, Any]:
    """Analyze merged PDRC COMSOL IR/solar candidate scans."""
    return analyze_pdrc_comsol_candidates(ir_csv_files=ir_csv_files, **kwargs)


def export_pdrc_comsol_candidates(
    ir_csv_files: list[str],
    **kwargs: Any,
) -> Dict[str, str]:
    """Export merged PDRC COMSOL candidate metrics and plots."""
    return export_pdrc_comsol_candidate_bundle(ir_csv_files=ir_csv_files, **kwargs)


def analyze_tamm_interface_window(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Analyze a full-field Tamm interface CSV by cropping a local 2D window in Python."""
    return analyze_tamm_interface_2d_window_csv(reference_csv=reference_csv, **kwargs)


def export_tamm_interface_window_bundle(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Export local-window metrics for one Tamm interface field CSV."""
    return export_tamm_interface_window_analysis(reference_csv=reference_csv, **kwargs)


def export_tamm_interface_window_collection_bundle(
    csv_mapping: Dict[str, str],
    **kwargs: Any,
) -> Dict[str, str]:
    """Export a shared local-window analysis bundle for multiple Tamm interface field CSVs."""
    return export_tamm_interface_window_collection(csv_mapping=csv_mapping, **kwargs)


def export_tamm_interface_window_scan_bundle(
    csv_mapping: Dict[str, str],
    **kwargs: Any,
) -> Dict[str, str]:
    """Export a multi-window scan bundle for multiple Tamm interface field CSVs."""
    return export_tamm_interface_window_scan_collection(csv_mapping=csv_mapping, **kwargs)


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


def analyze_tamm_phase_scan(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Analyze grouped d_W scan data for the Tamm phase/topology stage."""
    return analyze_tamm_dw_phase_scan(reference_csv=reference_csv, **kwargs)


def export_tamm_phase_bundle(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Export grouped d_W phase-stage plots and summaries for the Tamm module."""
    return export_tamm_dw_phase_bundle(reference_csv=reference_csv, **kwargs)


def export_tamm_phase_focus(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Export a focused phase comparison for representative Tamm d_W points."""
    return export_tamm_phase_focus_bundle(reference_csv=reference_csv, **kwargs)


def export_tamm_phase_candidate_ranking(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Export stage-2 candidate-pair ranking for Tamm topology comparison."""
    return export_tamm_phase_candidate_pairs(reference_csv=reference_csv, **kwargs)


def export_tamm_interface_priority(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Export a practical recommendation bundle for Tamm interface-pair selection."""
    return export_tamm_interface_priority_bundle(reference_csv=reference_csv, **kwargs)


def export_tamm_reflection_phase_screen(
    reference_csv: str,
    **kwargs: Any,
) -> Dict[str, str]:
    """Export 1D terminal-pair screening by high reflectance and near-pi phase contrast."""
    return export_tamm_reflection_phase_screen_bundle(reference_csv=reference_csv, **kwargs)


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


# ---------------------------------------------------------------------------
# Material selection module  (APP-facing)
# ---------------------------------------------------------------------------

def list_materials_for_app() -> list[dict]:
    """Return a JSON-serialisable catalog of every real material in the library.

    Each entry contains:
    - ``id``             : canonical material ID used in ``material_selections``
    - ``display_name``   : Chinese display name (for dropdown / list labels)
    - ``display_name_en``: English display name
    - ``category``       : 介质 / 半导体 / 金属 / 气体
    - ``suitable_roles`` : list of layer-role keys this material can fill
    - ``lambda_min_nm``  : lower bound of valid wavelength range (nm)
    - ``lambda_max_nm``  : upper bound of valid wavelength range (nm)
    - ``n_at_550nm``     : real part of refractive index at 550 nm (UI preview)
    - ``k_at_550nm``     : imaginary part (extinction coefficient) at 550 nm

    Example usage (APP frontend)::

        catalog = list_materials_for_app()
        # Show only materials suitable for the low-index role
        low_options = [m for m in catalog if "n_low" in m["suitable_roles"]]
    """
    return material_display_info()


def get_material_roles_for_design(design_type: str) -> dict:
    """Return the material-role picker schema for one design type.

    Tells the APP frontend which layer roles exist in this design, what
    materials are eligible for each role, which roles are user-selectable
    vs. locked, and the recommended default material.

    Parameters
    ----------
    design_type:
        One of the standard teaching design IDs, e.g. ``"single_ar"``,
        ``"high_reflector"``, ``"fp_filter"``.

    Returns
    -------
    dict with keys:

    - ``design_type`` : echoed back (normalised to lowercase)
    - ``roles``       : dict mapping role key → role descriptor, each with

      - ``label``   : Chinese human-readable label
      - ``options`` : list of eligible material IDs
      - ``default`` : recommended default material ID
      - ``locked``  : bool — if True the APP should not expose this to the user

    Example::

        schema = get_material_roles_for_design("single_ar")
        # schema["roles"]["n_low"]["options"] == ["MgF2", "SiO2", "Al2O3"]
    """
    return _get_material_roles_for_design(design_type)


def simulate_with_material_selection(
    design_type: str,
    material_selections: Dict[str, str],
    *,
    lambda0_nm: float = 550.0,
    wavelengths_nm=None,
    warn_range: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Run a TMM simulation using real dispersive materials chosen by the user.

    This is the unified APP entry point that bridges the user-facing material
    picker (names like ``"TiO2"``, ``"MgF2"``) with the internal
    ``simulate_report_design_real_materials`` engine.

    Parameters
    ----------
    design_type:
        Teaching design ID, e.g. ``"single_ar"``, ``"high_reflector"``.
    material_selections:
        Dict mapping layer-role keys to material IDs chosen by the user.
        Only the roles the user actually changed need to be present; unlisted
        roles fall back to the engine defaults.

        Example::

            {"n_low": "MgF2", "n_high": "TiO2"}

    lambda0_nm:
        Design centre wavelength in nm (default 550 nm).
    wavelengths_nm:
        Optional explicit wavelength grid.  When *None* the engine
        automatically restricts the grid to the overlapping valid range of
        the selected materials.
    warn_range:
        When *True* (default), print a warning if any selected material's
        valid wavelength range does not cover ``lambda0_nm``.
    **kwargs:
        Forwarded verbatim to ``simulate_report_design_real_materials``
        (e.g. ``theta_deg``, ``pol``, ``n_periods``).

    Returns
    -------
    dict — same structure as ``simulate_teaching_design``, extended with:

    - ``material_model`` : ``"real_nk"``
    - ``material_map``   : the resolved material mapping that was used
    - ``design_indices_at_lambda0`` : n/k for each role at the design wavelength

    Example::

        result = simulate_with_material_selection(
            "single_ar",
            {"n_low": "MgF2"},
            lambda0_nm=550.0,
        )
        print(result["summary"])
    """
    # Range warning
    if warn_range:
        all_info = {row["id"]: row for row in material_display_info()}
        for role, mat_id in material_selections.items():
            info = all_info.get(mat_id)
            if info is None:
                continue
            lo = info["lambda_min_nm"]
            hi = info["lambda_max_nm"]
            if not (lo <= lambda0_nm <= hi):
                import warnings
                warnings.warn(
                    f"材料 {mat_id} 的有效波长范围为 {lo:.0f}–{hi:.0f} nm，"
                    f"设计波长 {lambda0_nm:.1f} nm 超出范围，"
                    f"结果将使用外推值，物理精度可能下降。",
                    UserWarning,
                    stacklevel=2,
                )

    return simulate_report_design_real_materials(
        design_type=design_type,
        material_map=material_selections,
        wavelengths_nm=wavelengths_nm,
        lambda0_nm=lambda0_nm,
        **kwargs,
    )
