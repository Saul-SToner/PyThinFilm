from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .api import fit_two_angle
from . import config as cfg
from .fitting import multiscale_dual_search
from .io import load_spectrum_csv
from .optics import unify_two_reflectance_curves
from .paths import DEG_P_DIR, output_file


def summarize_n1b_theta_sweep(
    csv_path: Path | None = None,
    reflectance_scale: float = 1.0,
    output_name: str = "n1b_theta_sweep_summary.csv",
) -> pd.DataFrame:
    """Summarize a COMSOL full-combination sweep table grouped by theta and n1_B."""
    path = DEG_P_DIR / "p.csv" if csv_path is None else Path(csv_path)
    spec = load_spectrum_csv(path, y_selector=5)
    df = spec.data_table.copy()

    wavelength_nm = df.iloc[:, 0].to_numpy(dtype=float) * 1e9
    theta_deg = df.iloc[:, 1].to_numpy(dtype=float)
    n1_b = df.iloc[:, 2].to_numpy(dtype=float)
    reflectance = df.iloc[:, 5].to_numpy(dtype=float) * float(reflectance_scale)

    rows: List[Dict[str, float]] = []
    for theta_value in sorted(np.unique(theta_deg)):
        theta_mask = np.isclose(theta_deg, theta_value)
        base_curve = None

        for b_value in sorted(np.unique(n1_b[theta_mask])):
            mask = theta_mask & np.isclose(n1_b, b_value)
            order = np.argsort(wavelength_nm[mask])
            curve = reflectance[mask][order]
            wl = wavelength_nm[mask][order]

            if base_curve is None:
                rmse_vs_b0 = 0.0
                maxabs_vs_b0 = 0.0
                base_curve = curve
            else:
                diff = curve - base_curve
                rmse_vs_b0 = float(np.sqrt(np.mean(diff ** 2)))
                maxabs_vs_b0 = float(np.max(np.abs(diff)))

            rows.append(
                {
                    "theta_deg": float(theta_value),
                    "n1_B": float(b_value),
                    "n_points": int(len(curve)),
                    "lambda_min_nm": float(np.min(wl)),
                    "lambda_max_nm": float(np.max(wl)),
                    "reflectance_mean": float(np.mean(curve)),
                    "reflectance_min": float(np.min(curve)),
                    "reflectance_max": float(np.max(curve)),
                    "reflectance_scale": float(reflectance_scale),
                    "rmse_vs_n1_B_0": rmse_vs_b0,
                    "maxabs_vs_n1_B_0": maxabs_vs_b0,
                }
            )

    summary = pd.DataFrame(rows)
    summary.to_csv(output_file(output_name), index=False, encoding="utf-8-sig")
    return summary


def _extract_curve_from_sweep_table(
    df: pd.DataFrame,
    theta_deg: float,
    n1_b: float,
    reflectance_scale: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    wavelength_nm = df.iloc[:, 0].to_numpy(dtype=float) * 1e9
    theta_values = df.iloc[:, 1].to_numpy(dtype=float)
    n1_b_values = df.iloc[:, 2].to_numpy(dtype=float)
    reflectance = df.iloc[:, 5].to_numpy(dtype=float) * float(reflectance_scale)

    mask = np.isclose(theta_values, theta_deg) & np.isclose(n1_b_values, n1_b)
    if not np.any(mask):
        raise ValueError(f"No curve found for theta={theta_deg}, n1_B={n1_b}.")

    order = np.argsort(wavelength_nm[mask])
    return wavelength_nm[mask][order], reflectance[mask][order]


def _write_curve_csv(path: Path, wavelength_nm: np.ndarray, reflectance: np.ndarray, theta_deg: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(
        {
            "wavelength_nm": wavelength_nm,
            "reflectance": reflectance,
            "theta_deg": np.full_like(wavelength_nm, float(theta_deg), dtype=float),
        }
    )
    out.to_csv(path, index=False, encoding="utf-8-sig")


def fit_n1b_theta_sweep(
    csv_path: Path | None = None,
    theta1_deg: float = 10.0,
    theta2_deg: float = 80.0,
    pol: str = "p",
    reflectance_scale: float = 1.0,
    output_name: str = "n1b_theta_sweep_fit_results.csv",
) -> pd.DataFrame:
    """Fit each n1_B group in a COMSOL theta+n1_B+lambda sweep table."""
    path = DEG_P_DIR / "p.csv" if csv_path is None else Path(csv_path)
    spec = load_spectrum_csv(path, y_selector=5)
    df = spec.data_table.copy()
    n1_b_values = sorted(np.unique(df.iloc[:, 2].to_numpy(dtype=float)))

    temp_dir = output_file("_sweep_temp").parent / "_sweep_temp"
    rows: List[Dict[str, float]] = []

    for n1_b in n1_b_values:
        w1_nm, r1 = _extract_curve_from_sweep_table(df, theta1_deg, float(n1_b), reflectance_scale)
        w2_nm, r2 = _extract_curve_from_sweep_table(df, theta2_deg, float(n1_b), reflectance_scale)

        file1 = temp_dir / f"theta{theta1_deg:g}_n1B_{n1_b:.6f}.csv"
        file2 = temp_dir / f"theta{theta2_deg:g}_n1B_{n1_b:.6f}.csv"
        _write_curve_csv(file1, w1_nm, r1, theta1_deg)
        _write_curve_csv(file2, w2_nm, r2, theta2_deg)

        result = fit_two_angle(
            csv_angle1=file1,
            csv_angle2=file2,
            theta1_deg=theta1_deg,
            theta2_deg=theta2_deg,
            pol=pol,
            use_dispersion=True,
            n1_b=float(n1_b),
            n1_c=0.0,
            n2_b=0.0,
            n2_c=0.0,
            y_selector_angle1="reflectance",
            y_selector_angle2="reflectance",
            save_plots=False,
            sample_id=f"sweep_n1B_{n1_b:.6f}",
        )

        rows.append(
            {
                "n1_B": float(n1_b),
                "reflectance_scale": float(reflectance_scale),
                "theta1_deg": float(theta1_deg),
                "theta2_fit_deg": float(result["theta2_fit_deg"]),
                "d_fit_nominal_nm": float(result["d_fit_nominal_nm"]),
                "d_fit_corrected_nm": float(result["d_fit_corrected_nm"]),
                "delta_d_nm": float(result["delta_d_nm"]),
                "best_objective": float(result["best_objective"]),
                "nominal_objective": float(result["nominal_objective"]),
            }
        )

    fit_df = pd.DataFrame(rows).sort_values("best_objective").reset_index(drop=True)
    fit_df.to_csv(output_file(output_name), index=False, encoding="utf-8-sig")
    return fit_df


def score_n1b_theta_sweep(
    csv_path: Path | None = None,
    theta1_deg: float = 10.0,
    theta2_deg: float = 80.0,
    pol: str = "p",
    reflectance_scale: float = 1.0,
    output_name: str = "n1b_theta_sweep_model_scores.csv",
) -> pd.DataFrame:
    """Score each n1_B sweep group against the physical model without CSV range checks."""
    path = DEG_P_DIR / "p.csv" if csv_path is None else Path(csv_path)
    spec = load_spectrum_csv(path, y_selector=5)
    df = spec.data_table.copy()
    n1_b_values = sorted(np.unique(df.iloc[:, 2].to_numpy(dtype=float)))

    rows: List[Dict[str, float]] = []
    for n1_b in n1_b_values:
        w1_nm, r1 = _extract_curve_from_sweep_table(df, theta1_deg, float(n1_b), reflectance_scale)
        w2_nm, r2 = _extract_curve_from_sweep_table(df, theta2_deg, float(n1_b), reflectance_scale)
        lam_nm, r1_i, r2_i = unify_two_reflectance_curves(
            w1_nm,
            r1,
            w2_nm,
            r2,
            wmin_nm=cfg.LAMBDA_MIN_NM,
            wmax_nm=cfg.LAMBDA_MAX_NM,
            n_lambda=cfg.N_LAMBDA,
        )
        lam = lam_nm * 1e-9

        result = multiscale_dual_search(
            lam=lam,
            R1=r1_i,
            theta1_fixed=theta1_deg,
            R2=r2_i,
            theta2_nominal=theta2_deg,
            n0=cfg.N0,
            n1=cfg.N1,
            n2=cfg.N2,
            pol=pol,
            mix_p_weight=cfg.MIX_P_WEIGHT,
            d_min=cfg.D_MIN,
            d_max=cfg.D_MAX,
            lambda_a=cfg.LAMBDA_A,
            lambda_b=cfg.LAMBDA_B,
            theta2_min=theta2_deg + cfg.THETA2_SEARCH_MIN,
            theta2_max=theta2_deg + cfg.THETA2_SEARCH_MAX,
        )

        rows.append(
            {
                "n1_B": float(n1_b),
                "reflectance_scale": float(reflectance_scale),
                "theta1_deg": float(theta1_deg),
                "theta2_fit_deg": float(result["theta2_fit_deg"]),
                "d_fit_nm": float(result["d_fit_nm"]),
                "best_objective": float(result["best_objective"]),
                "r1_mean": float(np.mean(r1_i)),
                "r2_mean": float(np.mean(r2_i)),
                "r1_min": float(np.min(r1_i)),
                "r1_max": float(np.max(r1_i)),
                "r2_min": float(np.min(r2_i)),
                "r2_max": float(np.max(r2_i)),
            }
        )

    score_df = pd.DataFrame(rows).sort_values("best_objective").reset_index(drop=True)
    score_df.to_csv(output_file(output_name), index=False, encoding="utf-8-sig")
    return score_df
