from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .comsol_io import (
    load_comsol_grating_csv,
    load_comsol_two_param_sweep,
)
from .export import export_guided_grating_result, export_guided_grating_sweep_summary
from .models import GuidedGratingSpec, GratingSweepConfig
from .solver import simulate_guided_grating_placeholder
from .spectra import summarize_guided_grating_spectrum, summarize_lambda_period_sweep


def build_minimal_demo_spec() -> GuidedGratingSpec:
    """Minimal starter case for the guided grating branch."""

    return GuidedGratingSpec(
        sample_id="minimal_branch_case",
        period_nm=780.0,
        waveguide_thickness_nm=180.0,
        grating_thickness_nm=85.0,
        fill_factor=0.52,
        n_incident=1.0,
        n_waveguide=2.0,
        n_grating=2.0,
        n_substrate=1.45,
        theta_deg=0.0,
        pol="TE",
        lambda0_nm=1550.0,
        notes="Branch scaffold only. Replace placeholder solver with COMSOL/RCWA later.",
    )


def run_minimal_demo(prefix: str = "guided_grating_demo") -> Dict[str, Any]:
    spec = build_minimal_demo_spec()
    sweep = GratingSweepConfig(
        wavelength_start_nm=1450.0,
        wavelength_stop_nm=1650.0,
        wavelength_step_nm=0.5,
    )
    result = simulate_guided_grating_placeholder(spec=spec, sweep=sweep)
    summary = summarize_guided_grating_spectrum(result)
    files = export_guided_grating_result(
        result,
        prefix=prefix,
        target_wavelength_nm=spec.lambda0_nm,
    )
    return {
        "spec": spec.to_dict(),
        "summary": summary,
        "files": files,
        "warning": result.get("warning"),
    }


def run_comsol_csv_demo(
    csv_path: Path | str,
    prefix: str = "guided_grating_comsol",
    target_wavelength_nm: float | None = None,
) -> Dict[str, Any]:
    result = load_comsol_grating_csv(csv_path)
    summary = summarize_guided_grating_spectrum(result)
    files = export_guided_grating_result(
        result,
        prefix=prefix,
        target_wavelength_nm=target_wavelength_nm,
    )
    return {
        "spec": result.get("spec", {}),
        "summary": summary,
        "files": files,
        "warning": result.get("warning"),
        "source_csv": result.get("source_csv"),
        "meta": result.get("meta", {}),
    }


def run_comsol_two_param_sweep_demo(
    csv_path: Path | str,
    prefix: str = "guided_grating_sweep",
    target_wavelength_nm: float = 1550.0,
    sweep_name: str | None = None,
) -> Dict[str, Any]:
    bundle = load_comsol_two_param_sweep(csv_path, sweep_name=sweep_name)
    bundle_summary = summarize_lambda_period_sweep(
        bundle,
        target_wavelength_nm=target_wavelength_nm,
    )
    summary_files = export_guided_grating_sweep_summary(bundle_summary, prefix=prefix)

    best_period_key = str(bundle_summary["best_candidate"]["period_key"])
    best_result = bundle["sweep_groups"][best_period_key]
    best_files = export_guided_grating_result(
        best_result,
        prefix=f"{prefix}_best",
        target_wavelength_nm=target_wavelength_nm,
    )
    files = {
        **{f"bundle_{key}": value for key, value in summary_files.items()},
        **{f"best_{key}": value for key, value in best_files.items()},
    }

    return {
        "summary": bundle_summary,
        "best_result": best_result.get("spec", {}),
        "files": files,
        "source_csv": bundle.get("source_csv"),
    }
