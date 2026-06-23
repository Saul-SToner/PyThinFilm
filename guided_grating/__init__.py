"""Guided grating branch.

This package is intentionally kept separate from ``thinfilm/`` so the
existing teaching main branch and inversion pipeline stay stable.
"""

from .comsol_io import load_comsol_grating_csv, load_comsol_two_param_sweep
from .examples import (
    build_minimal_demo_spec,
    run_comsol_csv_demo,
    run_comsol_two_param_sweep_demo,
    run_minimal_demo,
    run_rcwa_demo,
)
from .export import export_guided_grating_result, export_guided_grating_sweep_summary
from .models import GuidedGratingSpec, GratingSweepConfig
from .rcwa import GratingLayer, rcwa_1d, rcwa_convergence_test
from .solver import simulate_guided_grating_placeholder
from .spectra import summarize_guided_grating_spectrum, summarize_lambda_period_sweep

__all__ = [
    "GuidedGratingSpec",
    "GratingLayer",
    "GratingSweepConfig",
    "build_minimal_demo_spec",
    "load_comsol_grating_csv",
    "load_comsol_two_param_sweep",
    "rcwa_1d",
    "rcwa_convergence_test",
    "run_comsol_csv_demo",
    "run_comsol_two_param_sweep_demo",
    "run_minimal_demo",
    "run_rcwa_demo",
    "simulate_guided_grating_placeholder",
    "summarize_guided_grating_spectrum",
    "summarize_lambda_period_sweep",
    "export_guided_grating_result",
    "export_guided_grating_sweep_summary",
]
