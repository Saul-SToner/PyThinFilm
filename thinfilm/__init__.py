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

from .api import fit_two_angle, fit_current_main_case
from .sweep import fit_n1b_theta_sweep, score_n1b_theta_sweep, summarize_n1b_theta_sweep

__all__ = [
    "fit_two_angle",
    "fit_current_main_case",
    "fit_n1b_theta_sweep",
    "score_n1b_theta_sweep",
    "summarize_n1b_theta_sweep",
]
