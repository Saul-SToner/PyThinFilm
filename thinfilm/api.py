from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from . import config as cfg
from .fitting import fit_dual_csv_with_theta2_search_from_files
from .paths import DEG_S_DIR


def fit_two_angle(
    csv_angle1: Path,
    csv_angle2: Path,
    theta1_deg: float,
    theta2_deg: float,
    pol: str = "s",
    use_dispersion: bool = False,
    n1_b: float = 0.0,
    n1_c: float = 0.0,
    n2_b: float = 0.0,
    n2_c: float = 0.0,
    y_selector_angle1: int | str | None = None,
    y_selector_angle2: int | str | None = None,
    save_plots: bool = False,
    sample_id: str = "api_case",
) -> Dict[str, Any]:
    """Run the current two-angle thickness inversion engine."""
    original = {
        "CSV_FILE_ANGLE1": cfg.CSV_FILE_ANGLE1,
        "CSV_FILE_ANGLE2": cfg.CSV_FILE_ANGLE2,
        "THETA1": cfg.THETA1,
        "THETA2": cfg.THETA2,
        "POL": cfg.POL,
        "USE_DISPERSION": cfg.USE_DISPERSION,
        "N1_DISPERSION_B": cfg.N1_DISPERSION_B,
        "N1_DISPERSION_C": cfg.N1_DISPERSION_C,
        "N2_DISPERSION_B": cfg.N2_DISPERSION_B,
        "N2_DISPERSION_C": cfg.N2_DISPERSION_C,
        "FIT_Y_SELECTOR_ANGLE1": cfg.FIT_Y_SELECTOR_ANGLE1,
        "FIT_Y_SELECTOR_ANGLE2": cfg.FIT_Y_SELECTOR_ANGLE2,
    }

    try:
        cfg.CSV_FILE_ANGLE1 = Path(csv_angle1)
        cfg.CSV_FILE_ANGLE2 = Path(csv_angle2)
        cfg.THETA1 = float(theta1_deg)
        cfg.THETA2 = float(theta2_deg)
        cfg.POL = str(pol)
        cfg.USE_DISPERSION = bool(use_dispersion)
        cfg.N1_DISPERSION_B = float(n1_b)
        cfg.N1_DISPERSION_C = float(n1_c)
        cfg.N2_DISPERSION_B = float(n2_b)
        cfg.N2_DISPERSION_C = float(n2_c)
        if y_selector_angle1 is not None:
            cfg.FIT_Y_SELECTOR_ANGLE1 = y_selector_angle1
        if y_selector_angle2 is not None:
            cfg.FIT_Y_SELECTOR_ANGLE2 = y_selector_angle2
        cfg.sync_angle_config_aliases()

        return fit_dual_csv_with_theta2_search_from_files(
            Path(csv_angle1),
            Path(csv_angle2),
            sample_id=sample_id,
            save_plots=save_plots,
        )
    finally:
        for name, value in original.items():
            setattr(cfg, name, value)
        cfg.sync_angle_config_aliases()


def fit_current_main_case(save_plots: bool = False) -> Dict[str, Any]:
    """Run the current recommended 60 nm, 10deg + 80deg, s-polarized case."""
    return fit_two_angle(
        csv_angle1=DEG_S_DIR / "60nm_10deg_s.csv",
        csv_angle2=DEG_S_DIR / "60nm_80deg_s.csv",
        theta1_deg=10.0,
        theta2_deg=80.0,
        pol="s",
        use_dispersion=False,
        save_plots=save_plots,
        sample_id="current_main_case",
    )
