"""Diagnostics, error analysis, heatmaps, and batch helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from .config import *
from .fitting import (
    fit_dual_csv_from_files,
    fit_dual_csv_with_theta2_search_from_files,
    invert_thickness_single_only,
)
from .io import (
    export_clean_csv,
    load_reflectance_spec,
    preview_csv,
    read_reflectance_csv,
    validate_dual_fit_inputs,
)
from .objectives import evaluate_dual_fit_objective
from .optics import thinfilm_reflectance_angle, unify_two_reflectance_curves
from .reports import save_json_report, save_rows_csv, save_text_report


SCAN_D_MIN_NM = 5.0
SCAN_D_MAX_NM = 200.0
SCAN_D_STEP_NM = 0.2

HEATMAP_D_MIN_NM = 5.0
HEATMAP_D_MAX_NM = 200.0
HEATMAP_D_STEP_NM = 1.0

HEATMAP_THETA2_MIN_DEG = 70.0
HEATMAP_THETA2_MAX_DEG = 90.0
HEATMAP_THETA2_STEP_DEG = 0.25


def compute_single_angle_objective_curve(
    lam: np.ndarray,
    R_target: np.ndarray,
    theta_deg: float,
    n0: float,
    n1: float,
    n2: float,
    pol: str,
    d_grid_nm: np.ndarray,
) -> np.ndarray:
    obj = []

    for d_nm in d_grid_nm:
        d = d_nm * 1e-9
        R_model = thinfilm_reflectance_angle(lam, n0, n1, n2, d, theta_deg, pol=pol)
        err = np.mean((R_model - R_target) ** 2)
        obj.append(float(err))

    return np.array(obj, dtype=float)

def plot_single_angle_scan_0deg(
    lam_nm: np.ndarray,
    R0_raw: np.ndarray,
    d_grid_nm: np.ndarray,
    obj_curve: np.ndarray,
    best_d_nm: float,
    out_prefix: str = "single_angle_0deg_scan",
) -> None:
    angle_label = format_angle_label(THETA1)
    plt.figure(figsize=(8, 5))
    plt.plot(d_grid_nm, obj_curve, linewidth=1.8)
    plt.axvline(best_d_nm, linestyle="--", label=f"best d = {best_d_nm:.3f} nm")
    plt.xlabel("Thickness (nm)")
    plt.ylabel("Objective (MSE)")
    plt.title(f"{angle_label} single-angle objective scan")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{out_prefix}_objective.png", dpi=200)
    plt.show()

    lam = lam_nm * 1e-9
    R_best = thinfilm_reflectance_angle(
        lam, N0, N1, N2, best_d_nm * 1e-9, THETA1, pol=POL
    )

    plt.figure(figsize=(8, 5))
    plt.plot(lam_nm, R0_raw, label=f"COMSOL {angle_label}", linewidth=1.5)
    plt.plot(lam_nm, R_best, "--", label=f"Model best d={best_d_nm:.3f} nm", linewidth=2)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Reflectance")
    plt.title(f"{angle_label} single-angle fit check")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{out_prefix}_fit.png", dpi=200)
    plt.show()

    plt.figure(figsize=(8, 5))
    plt.plot(lam_nm, R0_raw - R_best, linewidth=1.5)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Residual")
    plt.title(f"{angle_label} single-angle residual")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{out_prefix}_residual.png", dpi=200)
    plt.show()

def run_single_angle_0deg_scan() -> None:
    sync_angle_config_aliases()
    angle_label = format_angle_label(THETA1)
    w0_nm, R0 = read_reflectance_csv(CSV_FILE_0DEG, y_selector=FIT_Y_SELECTOR_0DEG)

    mask = (w0_nm >= LAMBDA_MIN_NM) & (w0_nm <= LAMBDA_MAX_NM)
    w0_nm = w0_nm[mask]
    R0 = R0[mask]

    if len(w0_nm) < 5:
        raise ValueError(f"{angle_label} 数据点太少，无法进行单角扫描。")

    lam_nm = np.linspace(np.min(w0_nm), np.max(w0_nm), N_LAMBDA)
    R0_i = np.interp(lam_nm, w0_nm, R0)
    lam = lam_nm * 1e-9

    d_grid_nm = np.arange(
        SCAN_D_MIN_NM,
        SCAN_D_MAX_NM + 1e-12,
        SCAN_D_STEP_NM
    )

    obj_curve = compute_single_angle_objective_curve(
        lam=lam,
        R_target=R0_i,
        theta_deg=THETA1,
        n0=N0,
        n1=N1,
        n2=N2,
        pol=POL,
        d_grid_nm=d_grid_nm,
    )

    best_idx = int(np.argmin(obj_curve))
    best_d_nm = float(d_grid_nm[best_idx])
    best_obj = float(obj_curve[best_idx])

    plot_single_angle_scan_0deg(
        lam_nm=lam_nm,
        R0_raw=R0_i,
        d_grid_nm=d_grid_nm,
        obj_curve=obj_curve,
        best_d_nm=best_d_nm,
        out_prefix=f"single_angle_{angle_label}_scan",
    )

    sort_idx = np.argsort(obj_curve)
    top_rows = []
    used_d = []

    for idx in sort_idx:
        d_nm = float(d_grid_nm[idx])

        if any(abs(d_nm - x) < max(1.0, 3 * SCAN_D_STEP_NM) for x in used_d):
            continue

        used_d.append(d_nm)
        top_rows.append([d_nm, float(obj_curve[idx])])

        if len(top_rows) >= 5:
            break

    save_rows_csv(
        f"single_angle_{angle_label}_scan_top_candidates.csv",
        ["thickness_nm", "objective"],
        top_rows
    )

    lines = [
        f"{angle_label} single-angle scan summary",
        f"csv_file_angle1 = {CSV_FILE_0DEG}",
        f"POL = {POL}",
        f"scan_range_nm = [{SCAN_D_MIN_NM}, {SCAN_D_MAX_NM}]",
        f"scan_step_nm = {SCAN_D_STEP_NM}",
        f"best_d_nm = {best_d_nm:.6f}",
        f"best_objective = {best_obj:.12e}",
        "",
        "Top candidate minima:",
    ]
    for row in top_rows:
        lines.append(f"d_nm = {row[0]:.6f}, objective = {row[1]:.12e}")

    save_text_report(f"single_angle_{angle_label}_scan_summary.txt", lines)

    print("=" * 90)
    print(f"{angle_label} single-angle scan")
    print("=" * 90)
    print(f"best_d_nm      = {best_d_nm:.6f}")
    print(f"best_objective = {best_obj:.12e}")
    print("Top candidate minima:")
    for row in top_rows:
        print(f"  d_nm = {row[0]:.6f}, objective = {row[1]:.12e}")

def compute_dual_objective_heatmap(
    lam: np.ndarray,
    R1: np.ndarray,
    R2: np.ndarray,
    theta1_fixed: float,
    d_grid_nm: np.ndarray,
    theta2_grid_deg: np.ndarray,
    n0: float,
    n1: float,
    n2: float,
    pol: str,
) -> np.ndarray:
    heatmap = np.zeros((len(theta2_grid_deg), len(d_grid_nm)), dtype=float)

    for i, theta2_test in enumerate(theta2_grid_deg):
        for j, d_nm in enumerate(d_grid_nm):
            err, _, _ = evaluate_dual_fit_objective(
                lam=lam,
                R1=R1,
                theta1=theta1_fixed,
                R2=R2,
                theta2=float(theta2_test),
                d=float(d_nm * 1e-9),
            n0=n0,
            n1=n1,
            n2=n2,
            pol=pol,
            mix_p_weight=MIX_P_WEIGHT,
            lambda_a=LAMBDA_A,
                lambda_b=LAMBDA_B,
                smooth_window=OBJECTIVE_SMOOTH_WINDOW,
                weight_level=OBJECTIVE_WEIGHT_LEVEL,
                weight_shape=OBJECTIVE_WEIGHT_SHAPE,
                weight_slope=OBJECTIVE_WEIGHT_SLOPE,
            )
            heatmap[i, j] = float(err)

    return heatmap

def plot_objective_heatmap_d_theta2(
    d_grid_nm: np.ndarray,
    theta2_grid_deg: np.ndarray,
    heatmap: np.ndarray,
    out_prefix: str = "objective_heatmap_d_theta2",
) -> None:
    min_idx = np.unravel_index(np.argmin(heatmap), heatmap.shape)
    best_theta2 = float(theta2_grid_deg[min_idx[0]])
    best_d_nm = float(d_grid_nm[min_idx[1]])
    best_obj = float(heatmap[min_idx])

    plt.figure(figsize=(9, 6))
    plt.imshow(
        heatmap,
        aspect="auto",
        origin="lower",
        extent=[
            float(np.min(d_grid_nm)),
            float(np.max(d_grid_nm)),
            float(np.min(theta2_grid_deg)),
            float(np.max(theta2_grid_deg)),
        ],
    )
    plt.colorbar(label="Objective")
    plt.scatter([best_d_nm], [best_theta2], marker="x", s=80, label="Global min")
    plt.xlabel("Thickness (nm)")
    plt.ylabel("Theta2 (deg)")
    plt.title("Objective heatmap: thickness vs theta2")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{out_prefix}.png", dpi=200)
    plt.show()

    plt.figure(figsize=(8, 5))
    plt.plot(d_grid_nm, heatmap[min_idx[0], :], linewidth=1.8)
    plt.axvline(best_d_nm, linestyle="--", label=f"best d = {best_d_nm:.3f} nm")
    plt.xlabel("Thickness (nm)")
    plt.ylabel("Objective")
    plt.title(f"Heatmap slice at theta2 = {best_theta2:.3f} deg")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{out_prefix}_slice_d.png", dpi=200)
    plt.show()

    plt.figure(figsize=(8, 5))
    plt.plot(theta2_grid_deg, heatmap[:, min_idx[1]], linewidth=1.8)
    plt.axvline(best_theta2, linestyle="--", label=f"best theta2 = {best_theta2:.3f} deg")
    plt.xlabel("Theta2 (deg)")
    plt.ylabel("Objective")
    plt.title(f"Heatmap slice at d = {best_d_nm:.3f} nm")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{out_prefix}_slice_theta2.png", dpi=200)
    plt.show()

    lines = [
        "Objective heatmap summary",
        f"best_d_nm = {best_d_nm:.6f}",
        f"best_theta2_deg = {best_theta2:.6f}",
        f"best_objective = {best_obj:.12e}",
        f"d_range_nm = [{np.min(d_grid_nm):.6f}, {np.max(d_grid_nm):.6f}]",
        f"theta2_range_deg = [{np.min(theta2_grid_deg):.6f}, {np.max(theta2_grid_deg):.6f}]",
    ]
    save_text_report("objective_heatmap_d_theta2_summary.txt", lines)

    print("=" * 90)
    print("Objective heatmap: thickness vs theta2")
    print("=" * 90)
    print(f"best_d_nm         = {best_d_nm:.6f}")
    print(f"best_theta2_deg   = {best_theta2:.6f}")
    print(f"best_objective    = {best_obj:.12e}")

def run_objective_heatmap_d_theta2() -> None:
    w1_nm, R1 = read_reflectance_csv(CSV_FILE_0DEG, y_selector=FIT_Y_SELECTOR_0DEG)
    w2_nm, R2 = read_reflectance_csv(CSV_FILE_2DEG, y_selector=FIT_Y_SELECTOR_2DEG)

    lam_nm, R1_i, R2_i = unify_two_reflectance_curves(
        w1_nm, R1, w2_nm, R2,
        wmin_nm=LAMBDA_MIN_NM,
        wmax_nm=LAMBDA_MAX_NM,
        n_lambda=N_LAMBDA
    )
    lam = lam_nm * 1e-9

    d_grid_nm = np.arange(
        HEATMAP_D_MIN_NM,
        HEATMAP_D_MAX_NM + 1e-12,
        HEATMAP_D_STEP_NM
    )
    theta2_grid_deg = np.arange(
        HEATMAP_THETA2_MIN_DEG,
        HEATMAP_THETA2_MAX_DEG + 1e-12,
        HEATMAP_THETA2_STEP_DEG
    )

    heatmap = compute_dual_objective_heatmap(
        lam=lam,
        R1=R1_i,
        R2=R2_i,
        theta1_fixed=THETA1,
        d_grid_nm=d_grid_nm,
        theta2_grid_deg=theta2_grid_deg,
        n0=N0,
        n1=N1,
        n2=N2,
        pol=POL,
    )

    save_rows_csv(
        "objective_heatmap_d_theta2_axes.csv",
        ["axis_name", "values"],
        [
            ["d_grid_nm", ";".join(f"{x:.6f}" for x in d_grid_nm)],
            ["theta2_grid_deg", ";".join(f"{x:.6f}" for x in theta2_grid_deg)],
        ]
    )

    heatmap_path = OUTPUT_DIR / "objective_heatmap_d_theta2_matrix.csv"
    pd.DataFrame(
        heatmap,
        index=[f"{x:.6f}" for x in theta2_grid_deg],
        columns=[f"{x:.6f}" for x in d_grid_nm],
    ).to_csv(heatmap_path, encoding="utf-8-sig")
    print(f"Saved csv: {heatmap_path}")

    plot_objective_heatmap_d_theta2(
        d_grid_nm=d_grid_nm,
        theta2_grid_deg=theta2_grid_deg,
        heatmap=heatmap,
        out_prefix="objective_heatmap_d_theta2",
    )

def compute_error_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float]:
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    return mae, rmse

def run_compare_80deg_at_fixed_d() -> None:
    w2_nm, R2 = read_reflectance_csv(CSV_FILE_2DEG, y_selector=FIT_Y_SELECTOR_2DEG)

    mask = (w2_nm >= LAMBDA_MIN_NM) & (w2_nm <= LAMBDA_MAX_NM)
    w2_nm = w2_nm[mask]
    R2 = R2[mask]

    if len(w2_nm) < 5:
        raise ValueError("数据点太少，无法进行固定厚度对比。")

    lam_nm = np.linspace(np.min(w2_nm), np.max(w2_nm), N_LAMBDA)
    R2_i = np.interp(lam_nm, w2_nm, R2)
    lam = lam_nm * 1e-9

    d_fixed = FIXED_D_COMPARE_NM * 1e-9
    theta_fixed = FIXED_THETA_COMPARE_DEG

    R_s = thinfilm_reflectance_angle(lam, N0, N1, N2, d_fixed, theta_fixed, pol="s")
    R_p = thinfilm_reflectance_angle(lam, N0, N1, N2, d_fixed, theta_fixed, pol="p")
    R_avg = thinfilm_reflectance_angle(lam, N0, N1, N2, d_fixed, theta_fixed, pol="avg")

    mae_s, rmse_s = compute_error_metrics(R2_i, R_s)
    mae_p, rmse_p = compute_error_metrics(R2_i, R_p)
    mae_avg, rmse_avg = compute_error_metrics(R2_i, R_avg)

    rows = [
        ["s", mae_s, rmse_s],
        ["p", mae_p, rmse_p],
        ["avg", mae_avg, rmse_avg],
    ]
    save_rows_csv(
        "compare_at_fixed_d_metrics.csv",
        ["model_pol", "mae", "rmse"],
        rows
    )

    metric_map = {
        "s": (mae_s, rmse_s),
        "p": (mae_p, rmse_p),
        "avg": (mae_avg, rmse_avg),
    }
    best_pol = min(metric_map, key=lambda k: metric_map[k][1])

    plt.figure(figsize=(9, 6))
    plt.plot(lam_nm, R2_i, label=f"COMSOL {theta_fixed:.1f}deg", linewidth=1.8)
    plt.plot(lam_nm, R_s, "--", label=f"Model s  (RMSE={rmse_s:.3e})", linewidth=1.6)
    plt.plot(lam_nm, R_p, "--", label=f"Model p  (RMSE={rmse_p:.3e})", linewidth=1.6)
    plt.plot(lam_nm, R_avg, "--", label=f"Model avg (RMSE={rmse_avg:.3e})", linewidth=1.6)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Reflectance")
    plt.title(f"{theta_fixed:.1f}deg comparison at fixed d = {FIXED_D_COMPARE_NM:.3f} nm")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "compare_at_fixed_d_overlay.png", dpi=200)
    plt.show()

    plt.figure(figsize=(9, 6))
    plt.plot(lam_nm, R2_i - R_s, label="Residual: COMSOL - s", linewidth=1.5)
    plt.plot(lam_nm, R2_i - R_p, label="Residual: COMSOL - p", linewidth=1.5)
    plt.plot(lam_nm, R2_i - R_avg, label="Residual: COMSOL - avg", linewidth=1.5)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Residual")
    plt.title(f"{theta_fixed:.1f}deg residuals at fixed d = {FIXED_D_COMPARE_NM:.3f} nm")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "compare_at_fixed_d_residuals.png", dpi=200)
    plt.show()

    if best_pol == "s":
        R_best = R_s
    elif best_pol == "p":
        R_best = R_p
    else:
        R_best = R_avg

    plt.figure(figsize=(9, 6))
    plt.plot(lam_nm, R2_i, label=f"COMSOL {theta_fixed:.1f}deg", linewidth=1.8)
    plt.plot(lam_nm, R_best, "--", label=f"Best model = {best_pol}", linewidth=2.0)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Reflectance")
    plt.title(f"Best {theta_fixed:.1f}deg match at fixed d = {FIXED_D_COMPARE_NM:.3f} nm")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "compare_at_fixed_d_best_only.png", dpi=200)
    plt.show()

    lines = [
        f"{theta_fixed:.1f}deg fixed-thickness comparison summary",
        f"csv_file = {CSV_FILE_2DEG}",
        f"fixed_d_nm = {FIXED_D_COMPARE_NM:.6f}",
        f"fixed_theta_deg = {FIXED_THETA_COMPARE_DEG:.6f}",
        "",
        f"s   : MAE = {mae_s:.12e}, RMSE = {rmse_s:.12e}",
        f"p   : MAE = {mae_p:.12e}, RMSE = {rmse_p:.12e}",
        f"avg : MAE = {mae_avg:.12e}, RMSE = {rmse_avg:.12e}",
        "",
        f"best_match_by_rmse = {best_pol}",
    ]
    save_text_report("compare_at_fixed_d_summary.txt", lines)

    save_json_report(
        "compare_at_fixed_d_summary.json",
        {
            "csv_file": str(CSV_FILE_2DEG),
            "fixed_d_nm": float(FIXED_D_COMPARE_NM),
            "fixed_theta_deg": float(FIXED_THETA_COMPARE_DEG),
            "metrics": {
                "s": {"mae": mae_s, "rmse": rmse_s},
                "p": {"mae": mae_p, "rmse": rmse_p},
                "avg": {"mae": mae_avg, "rmse": rmse_avg},
            },
            "best_match_by_rmse": best_pol,
        }
    )

    print("=" * 90)
    print("Angle comparison at fixed thickness")
    print("=" * 90)
    print(f"fixed_d_nm       = {FIXED_D_COMPARE_NM:.6f}")
    print(f"fixed_theta_deg  = {FIXED_THETA_COMPARE_DEG:.6f}")
    print(f"s   -> MAE = {mae_s:.12e}, RMSE = {rmse_s:.12e}")
    print(f"p   -> MAE = {mae_p:.12e}, RMSE = {rmse_p:.12e}")
    print(f"avg -> MAE = {mae_avg:.12e}, RMSE = {rmse_avg:.12e}")
    print(f"best_match_by_rmse = {best_pol}")

def run_theta2_scan_at_fixed_d() -> None:
    w2_nm, R2 = read_reflectance_csv(CSV_FILE_2DEG, y_selector=FIT_Y_SELECTOR_2DEG)

    mask = (w2_nm >= LAMBDA_MIN_NM) & (w2_nm <= LAMBDA_MAX_NM)
    w2_nm = w2_nm[mask]
    R2 = R2[mask]

    if len(w2_nm) < 5:
        raise ValueError("数据点太少，无法进行 theta2 扫描。")

    lam_nm = np.linspace(np.min(w2_nm), np.max(w2_nm), N_LAMBDA)
    R2_i = np.interp(lam_nm, w2_nm, R2)
    lam = lam_nm * 1e-9

    d_fixed_nm = THETA2_SCAN_FIXED_D_NM
    d_fixed = d_fixed_nm * 1e-9

    theta_grid = np.arange(
        THETA2_SCAN_MIN_DEG,
        THETA2_SCAN_MAX_DEG + 1e-12,
        THETA2_SCAN_STEP_DEG
    )

    rows = []
    best_theta = None
    best_rmse = np.inf
    best_mae = np.inf
    best_curve = None

    for theta in theta_grid:
        R_model = thinfilm_reflectance_angle(
            lam, N0, N1, N2, d_fixed, theta, pol=THETA2_SCAN_POL
        )

        mae = float(np.mean(np.abs(R2_i - R_model)))
        rmse = float(np.sqrt(np.mean((R2_i - R_model) ** 2)))

        rows.append([float(theta), mae, rmse])

        if rmse < best_rmse:
            best_theta = float(theta)
            best_mae = mae
            best_rmse = rmse
            best_curve = R_model.copy()

    save_rows_csv(
        "theta2_scan_at_fixed_d.csv",
        ["theta2_deg", "mae", "rmse"],
        rows
    )

    theta_vals = np.array([r[0] for r in rows], dtype=float)
    mae_vals = np.array([r[1] for r in rows], dtype=float)
    rmse_vals = np.array([r[2] for r in rows], dtype=float)

    plt.figure(figsize=(8, 5))
    plt.plot(theta_vals, rmse_vals, linewidth=1.8, label="RMSE")
    plt.axvline(best_theta, linestyle="--", label=f"best theta = {best_theta:.3f} deg")
    plt.xlabel("Theta2 (deg)")
    plt.ylabel("RMSE")
    plt.title(f"Theta2 scan at fixed d = {d_fixed_nm:.3f} nm, pol = {THETA2_SCAN_POL}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "theta2_scan_at_fixed_d_rmse.png", dpi=200)
    plt.show()

    plt.figure(figsize=(8, 5))
    plt.plot(theta_vals, mae_vals, linewidth=1.8, label="MAE")
    plt.axvline(best_theta, linestyle="--", label=f"best theta = {best_theta:.3f} deg")
    plt.xlabel("Theta2 (deg)")
    plt.ylabel("MAE")
    plt.title(f"Theta2 scan at fixed d = {d_fixed_nm:.3f} nm, pol = {THETA2_SCAN_POL}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "theta2_scan_at_fixed_d_mae.png", dpi=200)
    plt.show()

    plt.figure(figsize=(9, 6))
    plt.plot(lam_nm, R2_i, label=f"COMSOL {FIXED_THETA_COMPARE_DEG:.1f}deg", linewidth=1.8)
    plt.plot(lam_nm, best_curve, "--", label=f"Model best theta = {best_theta:.3f} deg", linewidth=2.0)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Reflectance")
    plt.title(f"Best theta2 match at fixed d = {d_fixed_nm:.3f} nm, pol = {THETA2_SCAN_POL}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "theta2_scan_at_fixed_d_best_fit.png", dpi=200)
    plt.show()

    plt.figure(figsize=(9, 6))
    plt.plot(lam_nm, R2_i - best_curve, linewidth=1.6)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Residual")
    plt.title(f"Residual at best theta2 = {best_theta:.3f} deg")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "theta2_scan_at_fixed_d_best_residual.png", dpi=200)
    plt.show()

    lines = [
        "Theta2 scan at fixed thickness summary",
        f"csv_file = {CSV_FILE_2DEG}",
        f"fixed_d_nm = {d_fixed_nm:.6f}",
        f"pol = {THETA2_SCAN_POL}",
        f"theta2_scan_range_deg = [{THETA2_SCAN_MIN_DEG:.6f}, {THETA2_SCAN_MAX_DEG:.6f}]",
        f"theta2_scan_step_deg = {THETA2_SCAN_STEP_DEG:.6f}",
        "",
        f"best_theta2_deg = {best_theta:.6f}",
        f"best_mae = {best_mae:.12e}",
        f"best_rmse = {best_rmse:.12e}",
    ]
    save_text_report("theta2_scan_at_fixed_d_summary.txt", lines)

    save_json_report(
        "theta2_scan_at_fixed_d_summary.json",
        {
            "csv_file": str(CSV_FILE_2DEG),
            "fixed_d_nm": float(d_fixed_nm),
            "pol": THETA2_SCAN_POL,
            "theta2_scan_min_deg": float(THETA2_SCAN_MIN_DEG),
            "theta2_scan_max_deg": float(THETA2_SCAN_MAX_DEG),
            "theta2_scan_step_deg": float(THETA2_SCAN_STEP_DEG),
            "best_theta2_deg": float(best_theta),
            "best_mae": float(best_mae),
            "best_rmse": float(best_rmse),
        }
    )

    print("=" * 90)
    print("Theta2 scan at fixed thickness")
    print("=" * 90)
    print(f"fixed_d_nm      = {d_fixed_nm:.6f}")
    print(f"pol             = {THETA2_SCAN_POL}")
    print(f"best_theta2_deg = {best_theta:.6f}")
    print(f"best_mae        = {best_mae:.12e}")
    print(f"best_rmse       = {best_rmse:.12e}")

def find_batch_pairs(input_dir: Path, label_1: str, label_2: str) -> List[Tuple[str, Path, Path]]:
    input_dir = Path(input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"批量输入目录不存在: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"BATCH_INPUT_DIR 必须是文件夹，而不是单个文件: {input_dir}")

    pattern_1 = f"*_{label_1}.csv"
    files_1 = sorted(input_dir.glob(pattern_1))

    pairs: List[Tuple[str, Path, Path]] = []
    missing: List[Tuple[str, str]] = []

    for f1 in files_1:
        suffix = f"_{label_1}.csv"
        if not f1.name.endswith(suffix):
            continue

        sample_id = f1.name[:-len(suffix)]
        f2 = input_dir / f"{sample_id}_{label_2}.csv"

        if f2.exists():
            pairs.append((sample_id, f1, f2))
        else:
            missing.append((sample_id, str(f2)))

    if missing:
        print("=" * 80)
        print("Warning: 以下样品缺少配对文件")
        for sid, miss_path in missing:
            print(f"  sample_id = {sid}, missing = {miss_path}")
        print("=" * 80)

    return pairs

def parse_true_thickness_nm_from_sample_id(sample_id: str) -> float:
    text = str(sample_id).strip()
    m = re.search(TRUE_THICKNESS_REGEX, text, flags=re.IGNORECASE)
    if m:
        return float(m.group(1))

    if TRUE_THICKNESS_FALLBACK_FIRST_NUMBER:
        m = re.search(r"(\d+(?:\.\d+)?)", text)
        if m:
            return float(m.group(1))

    raise ValueError(
        f"Cannot infer true thickness from sample_id={sample_id!r}. "
        f"Current regex={TRUE_THICKNESS_REGEX!r}"
    )

def run_batch_fit_core() -> List[Dict]:
    print("=" * 100)
    print("Batch fit CSV with theta2 search")
    print("=" * 100)
    print(f"BATCH_INPUT_DIR = {BATCH_INPUT_DIR}")
    print(f"BATCH_LABEL_1   = {BATCH_LABEL_1}")
    print(f"BATCH_LABEL_2   = {BATCH_LABEL_2}")

    pairs = find_batch_pairs(BATCH_INPUT_DIR, BATCH_LABEL_1, BATCH_LABEL_2)
    if len(pairs) == 0:
        print("No usable paired CSV files were found.")
        return []

    results: List[Dict] = []
    for i, (sample_id, f1, f2) in enumerate(pairs, start=1):
        print("\n" + "-" * 100)
        print(f"[{i}/{len(pairs)}] sample_id = {sample_id}")
        print(f"  file1 = {f1}")
        print(f"  file2 = {f2}")

        try:
            result = fit_dual_csv_with_theta2_search_from_files(
                f1, f2, sample_id=sample_id, save_plots=False
            )
            results.append(result)
            print(f"  theta2_fit            = {result['theta2_fit_deg']:.3f} deg")
            print(f"  d_fit_nominal         = {result['d_fit_nominal_nm']:.3f} nm")
            print(f"  d_fit_corrected       = {result['d_fit_corrected_nm']:.3f} nm")
            print(f"  d_fit_nominal_cal     = {result['d_fit_nominal_calibrated_nm']:.3f} nm")
            print(f"  d_fit_corrected_cal   = {result['d_fit_corrected_calibrated_nm']:.3f} nm")
            print(f"  delta_d               = {result['delta_d_nm']:.3f} nm")
            print(f"  objective             = {result['best_objective']:.6e}")
        except Exception as e:
            print(f"  ERROR for sample {sample_id}: {e}")

    if len(results) == 0:
        print("All samples failed during batch fitting.")
        return []

    return results

def save_batch_fit_summary_outputs(results: List[Dict]) -> None:
    if len(results) == 0:
        return

    summary_rows = []
    for r in results:
        summary_rows.append([
            r["sample_id"],
            r["theta1_fixed_deg"],
            r["theta2_nominal_deg"],
            r["theta2_fit_deg"],
            r["d_fit_nominal_nm"],
            r["d_fit_corrected_nm"],
            r["d_fit_nominal_calibrated_nm"],
            r["d_fit_corrected_calibrated_nm"],
            r["delta_d_nm"],
            r["best_objective"],
            r["csv_file_1"],
            r["csv_file_2"],
        ])

    save_rows_csv(
        "batch_fit_summary.csv",
        [
            "sample_id",
            "theta1_fixed_deg",
            "theta2_nominal_deg",
            "theta2_fit_deg",
            "d_fit_nominal_nm",
            "d_fit_corrected_nm",
            "d_fit_nominal_calibrated_nm",
            "d_fit_corrected_calibrated_nm",
            "delta_d_nm",
            "best_objective",
            "csv_file_1",
            "csv_file_2",
        ],
        summary_rows,
    )
    save_json_report("batch_fit_summary.json", {"results": results})

    lines = [
        "Batch fit summary",
        f"input_dir = {BATCH_INPUT_DIR}",
        f"n_samples = {len(results)}",
        "",
    ]
    theta2_fit_list = [r["theta2_fit_deg"] for r in results]
    d_nominal_list = [r["d_fit_nominal_calibrated_nm"] for r in results]
    d_corrected_list = [r["d_fit_corrected_calibrated_nm"] for r in results]
    lines.append(f"theta2_fit_mean = {np.mean(theta2_fit_list):.6f} deg")
    lines.append(f"theta2_fit_std  = {np.std(theta2_fit_list):.6f} deg")
    lines.append(f"d_nominal_mean  = {np.mean(d_nominal_list):.6f} nm")
    lines.append(f"d_corrected_mean= {np.mean(d_corrected_list):.6f} nm")
    lines.append("")

    for r in results:
        lines.append(
            f"{r['sample_id']}: "
            f"theta2_fit={r['theta2_fit_deg']:.3f} deg, "
            f"d_nominal={r['d_fit_nominal_nm']:.3f} nm, "
            f"d_corrected={r['d_fit_corrected_nm']:.3f} nm, "
            f"delta_d={r['delta_d_nm']:.3f} nm"
        )

    save_text_report("batch_fit_summary.txt", lines)

    sample_ids = [r["sample_id"] for r in results]
    x = np.arange(len(sample_ids))
    d_nominal = np.array([r["d_fit_nominal_calibrated_nm"] for r in results])
    d_corrected = np.array([r["d_fit_corrected_calibrated_nm"] for r in results])
    theta2_fit = np.array([r["theta2_fit_deg"] for r in results])

    plt.figure(figsize=(10, 5))
    plt.plot(x, d_nominal, marker="o", label="d nominal")
    plt.plot(x, d_corrected, marker="o", label="d corrected")
    plt.xticks(x, sample_ids, rotation=30)
    plt.xlabel("Sample ID")
    plt.ylabel("Thickness (nm)")
    plt.title("Batch thickness fit summary")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "batch_fit_thickness_summary.png", dpi=200)
    plt.show()

    plt.figure(figsize=(10, 5))
    plt.plot(x, theta2_fit, marker="o", label="theta2 fit")
    plt.axhline(THETA2, linestyle="--", label="theta2 nominal")
    plt.xticks(x, sample_ids, rotation=30)
    plt.xlabel("Sample ID")
    plt.ylabel("Angle (deg)")
    plt.title("Batch theta2 fit summary")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "batch_fit_theta2_summary.png", dpi=200)
    plt.show()

def compute_error_statistics(values: np.ndarray) -> Dict[str, float]:
    values = np.asarray(values, dtype=float).ravel()
    return {
        "mean_error_nm": float(np.mean(values)),
        "mae_nm": float(np.mean(np.abs(values))),
        "rmse_nm": float(np.sqrt(np.mean(values ** 2))),
        "std_nm": float(np.std(values)),
        "max_abs_error_nm": float(np.max(np.abs(values))),
    }

def save_batch_error_analysis_outputs(results: List[Dict]) -> None:
    if len(results) == 0:
        return

    rows = []
    for r in results:
        true_nm = parse_true_thickness_nm_from_sample_id(r["sample_id"])
        err_nominal = float(r["d_fit_nominal_calibrated_nm"] - true_nm)
        err_corrected = float(r["d_fit_corrected_calibrated_nm"] - true_nm)
        rows.append({
            "sample_id": r["sample_id"],
            "true_thickness_nm": true_nm,
            "theta2_fit_deg": float(r["theta2_fit_deg"]),
            "theta2_nominal_deg": float(r["theta2_nominal_deg"]),
            "theta2_shift_deg": float(r["theta2_fit_deg"] - r["theta2_nominal_deg"]),
            "d_fit_nominal_nm": float(r["d_fit_nominal_nm"]),
            "d_fit_corrected_nm": float(r["d_fit_corrected_nm"]),
            "d_fit_nominal_calibrated_nm": float(r["d_fit_nominal_calibrated_nm"]),
            "d_fit_corrected_calibrated_nm": float(r["d_fit_corrected_calibrated_nm"]),
            "error_nominal_nm": err_nominal,
            "error_corrected_nm": err_corrected,
            "abs_error_nominal_nm": abs(err_nominal),
            "abs_error_corrected_nm": abs(err_corrected),
            "delta_d_nm": float(r["delta_d_nm"]),
            "best_objective": float(r["best_objective"]),
            "csv_file_1": r["csv_file_1"],
            "csv_file_2": r["csv_file_2"],
        })

    rows = sorted(rows, key=lambda x: x["true_thickness_nm"])
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "batch_error_analysis.csv", index=False, encoding="utf-8-sig")

    nominal_stats = compute_error_statistics(df["error_nominal_nm"].to_numpy())
    corrected_stats = compute_error_statistics(df["error_corrected_nm"].to_numpy())
    theta_shift = df["theta2_shift_deg"].to_numpy(dtype=float)
    theta_stats = {
        "mean_shift_deg": float(np.mean(theta_shift)),
        "std_shift_deg": float(np.std(theta_shift)),
        "max_abs_shift_deg": float(np.max(np.abs(theta_shift))),
    }

    save_json_report(
        "batch_error_analysis.json",
        {
            "input_dir": str(BATCH_INPUT_DIR),
            "n_samples": int(len(df)),
            "true_thickness_regex": TRUE_THICKNESS_REGEX,
            "nominal_fit_stats": nominal_stats,
            "corrected_fit_stats": corrected_stats,
            "theta2_shift_stats": theta_stats,
            "results": rows,
        },
    )

    lines = [
        "Batch error analysis",
        f"input_dir = {BATCH_INPUT_DIR}",
        f"n_samples = {len(df)}",
        f"true_thickness_regex = {TRUE_THICKNESS_REGEX}",
        "",
        "Corrected thickness error stats:",
        f"mean_error_nm = {corrected_stats['mean_error_nm']:.6f}",
        f"mae_nm = {corrected_stats['mae_nm']:.6f}",
        f"rmse_nm = {corrected_stats['rmse_nm']:.6f}",
        f"std_nm = {corrected_stats['std_nm']:.6f}",
        f"max_abs_error_nm = {corrected_stats['max_abs_error_nm']:.6f}",
        "",
        "Nominal thickness error stats:",
        f"mean_error_nm = {nominal_stats['mean_error_nm']:.6f}",
        f"mae_nm = {nominal_stats['mae_nm']:.6f}",
        f"rmse_nm = {nominal_stats['rmse_nm']:.6f}",
        f"std_nm = {nominal_stats['std_nm']:.6f}",
        f"max_abs_error_nm = {nominal_stats['max_abs_error_nm']:.6f}",
        "",
        "Theta2 shift stats:",
        f"mean_shift_deg = {theta_stats['mean_shift_deg']:.6f}",
        f"std_shift_deg = {theta_stats['std_shift_deg']:.6f}",
        f"max_abs_shift_deg = {theta_stats['max_abs_shift_deg']:.6f}",
        "",
    ]

    for row in rows:
        lines.append(
            f"{row['sample_id']}: true={row['true_thickness_nm']:.3f} nm, "
            f"d_corr={row['d_fit_corrected_calibrated_nm']:.3f} nm, "
            f"err={row['error_corrected_nm']:.3f} nm, "
            f"theta2_fit={row['theta2_fit_deg']:.4f} deg, "
            f"obj={row['best_objective']:.6e}"
        )

    save_text_report("batch_error_analysis.txt", lines)

    true_nm = df["true_thickness_nm"].to_numpy(dtype=float)
    d_corr = df["d_fit_corrected_calibrated_nm"].to_numpy(dtype=float)
    d_nom = df["d_fit_nominal_calibrated_nm"].to_numpy(dtype=float)
    err_corr = df["error_corrected_nm"].to_numpy(dtype=float)
    err_nom = df["error_nominal_nm"].to_numpy(dtype=float)
    theta_fit = df["theta2_fit_deg"].to_numpy(dtype=float)

    x = np.arange(len(df))
    labels = [str(v) for v in df["sample_id"].tolist()]

    plt.figure(figsize=(8, 6))
    mn = float(min(np.min(true_nm), np.min(d_corr), np.min(d_nom)))
    mx = float(max(np.max(true_nm), np.max(d_corr), np.max(d_nom)))
    plt.plot([mn, mx], [mn, mx], "--", label="ideal")
    plt.scatter(true_nm, d_nom, label="nominal fit", s=50)
    plt.scatter(true_nm, d_corr, label="corrected fit", s=50)
    plt.xlabel("True thickness (nm)")
    plt.ylabel("Fitted thickness (nm)")
    plt.title("True vs fitted thickness")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "batch_error_true_vs_fit.png", dpi=200)
    plt.show()

    plt.figure(figsize=(10, 5))
    plt.plot(x, err_nom, marker="o", label="nominal error")
    plt.plot(x, err_corr, marker="o", label="corrected error")
    plt.axhline(0.0, linestyle="--", color="k")
    plt.xticks(x, labels, rotation=30)
    plt.xlabel("Sample ID")
    plt.ylabel("Thickness error (nm)")
    plt.title("Thickness error by sample")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "batch_error_by_sample.png", dpi=200)
    plt.show()

    plt.figure(figsize=(10, 5))
    plt.plot(x, theta_fit, marker="o", label="theta2 fit")
    plt.axhline(THETA2, linestyle="--", label="theta2 nominal")
    plt.xticks(x, labels, rotation=30)
    plt.xlabel("Sample ID")
    plt.ylabel("Angle (deg)")
    plt.title("Theta2 fit by sample")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "batch_error_theta2_fit.png", dpi=200)
    plt.show()

def run_batch_fit_csv() -> None:
    results = run_batch_fit_core()
    save_batch_fit_summary_outputs(results)

def run_batch_error_analysis() -> None:
    results = run_batch_fit_core()
    save_batch_fit_summary_outputs(results)
    save_batch_error_analysis_outputs(results)

def optimize_thickness_for_fixed_configuration(
    lam: np.ndarray,
    R1: np.ndarray,
    theta1: float,
    R2: np.ndarray,
    theta2: float,
    n0: float,
    n1: float,
    n2: float,
    pol: str,
    mix_p_weight: float,
    d_min: float,
    d_max: float,
    lambda_a: float,
    lambda_b: float,
    n_grid: int = 400,
) -> Dict[str, Union[float, Tuple[float, float, float, float], Dict]]:
    d_grid_nm = np.linspace(float(d_min * 1e9), float(d_max * 1e9), n_grid)

    best_idx = 0
    best_err = None
    best_baseline = None
    best_metrics = None
    for idx, d_nm in enumerate(d_grid_nm):
        err, baseline_params, metrics = evaluate_dual_fit_objective(
            lam=lam,
            R1=R1,
            theta1=theta1,
            R2=R2,
            theta2=theta2,
            d=float(d_nm * 1e-9),
            n0=n0,
            n1=n1,
            n2=n2,
            pol=pol,
            mix_p_weight=mix_p_weight,
            lambda_a=lambda_a,
            lambda_b=lambda_b,
            smooth_window=OBJECTIVE_SMOOTH_WINDOW,
            weight_level=OBJECTIVE_WEIGHT_LEVEL,
            weight_shape=OBJECTIVE_WEIGHT_SHAPE,
            weight_slope=OBJECTIVE_WEIGHT_SLOPE,
        )
        if best_err is None or err < best_err:
            best_idx = idx
            best_err = float(err)
            best_baseline = baseline_params
            best_metrics = metrics

    center_nm = float(d_grid_nm[best_idx])
    step_nm = float(d_grid_nm[1] - d_grid_nm[0]) if len(d_grid_nm) >= 2 else 1.0
    left_nm = max(float(d_min * 1e9), center_nm - max(5.0, 5.0 * step_nm))
    right_nm = min(float(d_max * 1e9), center_nm + max(5.0, 5.0 * step_nm))

    if right_nm > left_nm:
        res = minimize_scalar(
            lambda d_nm: evaluate_dual_fit_objective(
                lam=lam,
                R1=R1,
                theta1=theta1,
                R2=R2,
                theta2=theta2,
                d=float(d_nm * 1e-9),
                n0=n0,
                n1=n1,
                n2=n2,
                pol=pol,
                mix_p_weight=mix_p_weight,
                lambda_a=lambda_a,
                lambda_b=lambda_b,
                smooth_window=OBJECTIVE_SMOOTH_WINDOW,
                weight_level=OBJECTIVE_WEIGHT_LEVEL,
                weight_shape=OBJECTIVE_WEIGHT_SHAPE,
                weight_slope=OBJECTIVE_WEIGHT_SLOPE,
            )[0],
            bounds=(left_nm, right_nm),
            method="bounded",
            options={"xatol": 1e-3},
        )
        best_err, best_baseline, best_metrics = evaluate_dual_fit_objective(
            lam=lam,
            R1=R1,
            theta1=theta1,
            R2=R2,
            theta2=theta2,
            d=float(res.x * 1e-9),
            n0=n0,
            n1=n1,
            n2=n2,
            pol=pol,
            mix_p_weight=mix_p_weight,
            lambda_a=lambda_a,
            lambda_b=lambda_b,
            smooth_window=OBJECTIVE_SMOOTH_WINDOW,
            weight_level=OBJECTIVE_WEIGHT_LEVEL,
            weight_shape=OBJECTIVE_WEIGHT_SHAPE,
            weight_slope=OBJECTIVE_WEIGHT_SLOPE,
        )
        center_nm = float(res.x)

    return {
        "d_fit_nm": float(center_nm),
        "best_objective": float(best_err),
        "baseline_params": tuple(float(x) for x in best_baseline),
        "metrics": best_metrics,
    }

def fit_linear_sensitivity(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if len(x) < 2:
        return 0.0, float(y[0]) if len(y) == 1 else 0.0
    slope, intercept = np.polyfit(x, y, deg=1)
    return float(slope), float(intercept)

def infer_true_thickness_for_single_sample() -> Optional[float]:
    if SINGLE_SAMPLE_TRUE_THICKNESS_NM is not None:
        return float(SINGLE_SAMPLE_TRUE_THICKNESS_NM)
    return None

def _load_current_dual_fit_arrays() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    spec_1 = load_reflectance_spec(CSV_FILE_0DEG, y_selector=FIT_Y_SELECTOR_0DEG)
    spec_2 = load_reflectance_spec(CSV_FILE_2DEG, y_selector=FIT_Y_SELECTOR_2DEG)
    validate_dual_fit_inputs(spec_1, THETA1, spec_2, THETA2)
    lam_nm, R1_i, R2_i = unify_two_reflectance_curves(
        spec_1.x_nm, spec_1.y, spec_2.x_nm, spec_2.y,
        wmin_nm=LAMBDA_MIN_NM,
        wmax_nm=LAMBDA_MAX_NM,
        n_lambda=N_LAMBDA,
    )
    return lam_nm, lam_nm * 1e-9, R1_i, R2_i

def _fixed_config_sensitivity_row(
    lam: np.ndarray,
    R1_i: np.ndarray,
    R2_i: np.ndarray,
    theta2: float,
    n1: float,
    n2: float,
    mix_p_weight: float,
    label: str,
    value: float,
) -> Dict[str, float]:
    opt = optimize_thickness_for_fixed_configuration(
        lam=lam,
        R1=R1_i,
        theta1=THETA1,
        R2=R2_i,
        theta2=float(theta2),
        n0=N0,
        n1=float(n1),
        n2=float(n2),
        pol=POL,
        mix_p_weight=mix_p_weight,
        d_min=D_MIN,
        d_max=D_MAX,
        lambda_a=LAMBDA_A,
        lambda_b=LAMBDA_B,
    )
    return {
        label: float(value),
        "d_fit_nm": float(opt["d_fit_nm"]),
        "best_objective": float(opt["best_objective"]),
    }

def _scan_single_sample_theta2(
    lam: np.ndarray,
    R1_i: np.ndarray,
    R2_i: np.ndarray,
    theta_center: float,
    mix_p_weight: float,
) -> pd.DataFrame:
    theta_values = np.arange(
        theta_center - SINGLE_SAMPLE_THETA2_HALF_RANGE_DEG,
        theta_center + SINGLE_SAMPLE_THETA2_HALF_RANGE_DEG + 1e-12,
        SINGLE_SAMPLE_THETA2_STEP_DEG,
    )
    rows = [
        _fixed_config_sensitivity_row(
            lam=lam,
            R1_i=R1_i,
            R2_i=R2_i,
            theta2=float(theta2_test),
            n1=N1,
            n2=N2,
            mix_p_weight=mix_p_weight,
            label="theta2_deg",
            value=float(theta2_test),
        )
        for theta2_test in theta_values
    ]
    return pd.DataFrame(rows)

def _scan_single_sample_n1(
    lam: np.ndarray,
    R1_i: np.ndarray,
    R2_i: np.ndarray,
    theta_center: float,
    mix_p_weight: float,
) -> pd.DataFrame:
    n1_values = np.linspace(
        N1 * (1.0 - SINGLE_SAMPLE_N1_RELATIVE_HALF_RANGE),
        N1 * (1.0 + SINGLE_SAMPLE_N1_RELATIVE_HALF_RANGE),
        SINGLE_SAMPLE_N_SCAN_POINTS,
    )
    rows = [
        _fixed_config_sensitivity_row(
            lam=lam,
            R1_i=R1_i,
            R2_i=R2_i,
            theta2=theta_center,
            n1=float(n1_test),
            n2=N2,
            mix_p_weight=mix_p_weight,
            label="n1",
            value=float(n1_test),
        )
        for n1_test in n1_values
    ]
    return pd.DataFrame(rows)

def _scan_single_sample_n2(
    lam: np.ndarray,
    R1_i: np.ndarray,
    R2_i: np.ndarray,
    theta_center: float,
    mix_p_weight: float,
) -> pd.DataFrame:
    n2_values = np.linspace(
        N2 * (1.0 - SINGLE_SAMPLE_N2_RELATIVE_HALF_RANGE),
        N2 * (1.0 + SINGLE_SAMPLE_N2_RELATIVE_HALF_RANGE),
        SINGLE_SAMPLE_N_SCAN_POINTS,
    )
    rows = [
        _fixed_config_sensitivity_row(
            lam=lam,
            R1_i=R1_i,
            R2_i=R2_i,
            theta2=theta_center,
            n1=N1,
            n2=float(n2_test),
            mix_p_weight=mix_p_weight,
            label="n2",
            value=float(n2_test),
        )
        for n2_test in n2_values
    ]
    return pd.DataFrame(rows)

def _build_single_sample_sensitivity_tables(
    lam: np.ndarray,
    R1_i: np.ndarray,
    R2_i: np.ndarray,
    theta_center: float,
    mix_p_weight: float,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        _scan_single_sample_theta2(lam, R1_i, R2_i, theta_center, mix_p_weight),
        _scan_single_sample_n1(lam, R1_i, R2_i, theta_center, mix_p_weight),
        _scan_single_sample_n2(lam, R1_i, R2_i, theta_center, mix_p_weight),
    )

def _save_single_sample_sensitivity_tables(
    theta_df: pd.DataFrame,
    n1_df: pd.DataFrame,
    n2_df: pd.DataFrame,
) -> None:
    theta_df.to_csv(OUTPUT_DIR / "single_sample_theta2_sensitivity.csv", index=False, encoding="utf-8-sig")
    n1_df.to_csv(OUTPUT_DIR / "single_sample_n1_sensitivity.csv", index=False, encoding="utf-8-sig")
    n2_df.to_csv(OUTPUT_DIR / "single_sample_n2_sensitivity.csv", index=False, encoding="utf-8-sig")

def _plot_single_sample_sensitivity(
    df: pd.DataFrame,
    x_col: str,
    base_value: float,
    base_label: str,
    xlabel: str,
    title: str,
    filename: str,
) -> None:
    plt.figure(figsize=(8, 5))
    plt.plot(df[x_col], df["d_fit_nm"], marker="o")
    plt.axvline(base_value, linestyle="--", label=base_label)
    plt.xlabel(xlabel)
    plt.ylabel("Re-fitted thickness (nm)")
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=200)
    plt.show()

def _plot_single_sample_sensitivity_tables(
    theta_df: pd.DataFrame,
    n1_df: pd.DataFrame,
    n2_df: pd.DataFrame,
    theta_center: float,
) -> None:
    _plot_single_sample_sensitivity(
        theta_df,
        x_col="theta2_deg",
        base_value=theta_center,
        base_label=f"best theta2 = {theta_center:.4f} deg",
        xlabel="Theta2 (deg)",
        title="Single-sample sensitivity: theta2",
        filename="single_sample_theta2_sensitivity.png",
    )
    _plot_single_sample_sensitivity(
        n1_df,
        x_col="n1",
        base_value=N1,
        base_label=f"base n1 = {N1:.4f}",
        xlabel="n1",
        title="Single-sample sensitivity: n1",
        filename="single_sample_n1_sensitivity.png",
    )
    _plot_single_sample_sensitivity(
        n2_df,
        x_col="n2",
        base_value=N2,
        base_label=f"base n2 = {N2:.4f}",
        xlabel="n2",
        title="Single-sample sensitivity: n2",
        filename="single_sample_n2_sensitivity.png",
    )

def _compute_single_sample_sensitivity_summary(
    result: Dict,
    true_thickness_nm: Optional[float],
    theta_df: pd.DataFrame,
    n1_df: pd.DataFrame,
    n2_df: pd.DataFrame,
) -> Dict[str, Optional[float]]:
    theta_slope, _ = fit_linear_sensitivity(theta_df["theta2_deg"], theta_df["d_fit_nm"])
    n1_slope, _ = fit_linear_sensitivity(n1_df["n1"], n1_df["d_fit_nm"])
    n2_slope, _ = fit_linear_sensitivity(n2_df["n2"], n2_df["d_fit_nm"])

    corrected_fit_nm = float(result["d_fit_corrected_calibrated_nm"])
    corrected_error_nm = None if true_thickness_nm is None else float(corrected_fit_nm - true_thickness_nm)

    equivalent_theta_shift = None
    equivalent_n1_shift = None
    equivalent_n2_shift = None
    if corrected_error_nm is not None:
        if abs(theta_slope) > 1e-12:
            equivalent_theta_shift = float(corrected_error_nm / theta_slope)
        if abs(n1_slope) > 1e-12:
            equivalent_n1_shift = float(corrected_error_nm / n1_slope)
        if abs(n2_slope) > 1e-12:
            equivalent_n2_shift = float(corrected_error_nm / n2_slope)

    return {
        "theta_slope": theta_slope,
        "n1_slope": n1_slope,
        "n2_slope": n2_slope,
        "corrected_error_nm": corrected_error_nm,
        "equivalent_theta_shift": equivalent_theta_shift,
        "equivalent_n1_shift": equivalent_n1_shift,
        "equivalent_n2_shift": equivalent_n2_shift,
    }

def _build_single_sample_error_report_lines(
    result: Dict,
    true_thickness_nm: Optional[float],
    mix_p_weight_base: float,
    summary: Dict[str, Optional[float]],
) -> List[str]:
    lines = [
        "Single-sample error analysis",
        f"sample_id = {SINGLE_SAMPLE_REPORT_ID}",
        f"csv1 = {CSV_FILE_0DEG}",
        f"csv2 = {CSV_FILE_2DEG}",
        f"theta2_fit_deg = {result['theta2_fit_deg']:.6f}",
        f"d_fit_nominal_nm = {result['d_fit_nominal_calibrated_nm']:.6f}",
        f"d_fit_corrected_nm = {result['d_fit_corrected_calibrated_nm']:.6f}",
        f"best_objective = {result['best_objective']:.12e}",
        f"mix_p_weight_fit = {mix_p_weight_base:.6f}",
        f"theta2_slope_nm_per_deg = {summary['theta_slope']:.6f}",
        f"n1_slope_nm_per_index = {summary['n1_slope']:.6f}",
        f"n2_slope_nm_per_index = {summary['n2_slope']:.6f}",
    ]
    if true_thickness_nm is not None:
        lines.extend([
            f"true_thickness_nm = {true_thickness_nm:.6f}",
            f"corrected_error_nm = {summary['corrected_error_nm']:.6f}",
            f"equivalent_theta_shift_deg_for_error = {summary['equivalent_theta_shift']:.6f}" if summary["equivalent_theta_shift"] is not None else "equivalent_theta_shift_deg_for_error = None",
            f"equivalent_n1_shift_for_error = {summary['equivalent_n1_shift']:.6f}" if summary["equivalent_n1_shift"] is not None else "equivalent_n1_shift_for_error = None",
            f"equivalent_n2_shift_for_error = {summary['equivalent_n2_shift']:.6f}" if summary["equivalent_n2_shift"] is not None else "equivalent_n2_shift_for_error = None",
        ])
    return lines

def _save_single_sample_error_reports(
    result: Dict,
    true_thickness_nm: Optional[float],
    mix_p_weight_base: float,
    summary: Dict[str, Optional[float]],
) -> None:
    payload = {
        "sample_id": SINGLE_SAMPLE_REPORT_ID,
        "csv_file_1": str(CSV_FILE_0DEG),
        "csv_file_2": str(CSV_FILE_2DEG),
        "true_thickness_nm": true_thickness_nm,
        "fit_result": result,
        "mix_p_weight_base": mix_p_weight_base,
        "theta2_slope_nm_per_deg": summary["theta_slope"],
        "n1_slope_nm_per_index": summary["n1_slope"],
        "n2_slope_nm_per_index": summary["n2_slope"],
        "equivalent_theta_shift_deg_for_error": summary["equivalent_theta_shift"],
        "equivalent_n1_shift_for_error": summary["equivalent_n1_shift"],
        "equivalent_n2_shift_for_error": summary["equivalent_n2_shift"],
    }
    save_json_report("single_sample_error_analysis.json", payload)
    save_text_report(
        "single_sample_error_analysis.txt",
        _build_single_sample_error_report_lines(result, true_thickness_nm, mix_p_weight_base, summary),
    )

def _print_single_sample_error_summary(
    result: Dict,
    true_thickness_nm: Optional[float],
    summary: Dict[str, Optional[float]],
) -> None:
    print("=" * 90)
    print("Single-sample error analysis")
    print("=" * 90)
    print(f"theta2_fit_deg             = {result['theta2_fit_deg']:.6f}")
    print(f"d_fit_corrected_nm         = {result['d_fit_corrected_calibrated_nm']:.6f}")
    if true_thickness_nm is not None:
        print(f"true_thickness_nm          = {true_thickness_nm:.6f}")
        print(f"corrected_error_nm         = {summary['corrected_error_nm']:.6f}")
    print(f"d(theta2)/ddeg             = {summary['theta_slope']:.6f} nm/deg")
    print(f"d(d_fit)/dn1              = {summary['n1_slope']:.6f} nm/index")
    print(f"d(d_fit)/dn2              = {summary['n2_slope']:.6f} nm/index")

def run_single_sample_error_analysis() -> None:
    true_thickness_nm = infer_true_thickness_for_single_sample()
    result = fit_dual_csv_with_theta2_search_from_files(
        CSV_FILE_0DEG,
        CSV_FILE_2DEG,
        sample_id=SINGLE_SAMPLE_REPORT_ID,
        save_plots=False,
    )
    mix_p_weight_base = float(result.get("mix_p_weight_fit", MIX_P_WEIGHT))
    _, lam, R1_i, R2_i = _load_current_dual_fit_arrays()
    theta_center = float(result["theta2_fit_deg"])
    theta_df, n1_df, n2_df = _build_single_sample_sensitivity_tables(
        lam=lam,
        R1_i=R1_i,
        R2_i=R2_i,
        theta_center=theta_center,
        mix_p_weight=mix_p_weight_base,
    )
    summary = _compute_single_sample_sensitivity_summary(result, true_thickness_nm, theta_df, n1_df, n2_df)

    _save_single_sample_sensitivity_tables(theta_df, n1_df, n2_df)
    _plot_single_sample_sensitivity_tables(theta_df, n1_df, n2_df, theta_center)
    _save_single_sample_error_reports(result, true_thickness_nm, mix_p_weight_base, summary)
    _print_single_sample_error_summary(result, true_thickness_nm, summary)

def run_fit_csv_compare_pols() -> None:
    global POL, FIT_MIX_WEIGHT

    original_pol = POL
    original_fit_mix_weight = FIT_MIX_WEIGHT
    results: List[Dict] = []

    try:
        for pol_name in POL_COMPARE_LIST:
            POL = str(pol_name)
            FIT_MIX_WEIGHT = (POL == "mix")
            result = fit_dual_csv_with_theta2_search_from_files(
                CSV_FILE_0DEG,
                CSV_FILE_2DEG,
                sample_id=f"{POL_COMPARE_REPORT_ID}_{pol_name}",
                save_plots=False,
            )
            result["pol_model"] = pol_name
            results.append(result)
    finally:
        POL = original_pol
        FIT_MIX_WEIGHT = original_fit_mix_weight

    rows = []
    for r in results:
        rows.append([
            r["pol_model"],
            r["theta2_fit_deg"],
            r["d_fit_nominal_nm"],
            r["d_fit_corrected_nm"],
            r["delta_d_nm"],
            r.get("mix_p_weight_fit", ""),
            r["best_objective"],
        ])

    save_rows_csv(
        "fit_csv_compare_pols.csv",
        [
            "pol_model",
            "theta2_fit_deg",
            "d_fit_nominal_nm",
            "d_fit_corrected_nm",
            "delta_d_nm",
            "mix_p_weight_fit",
            "best_objective",
        ],
        rows,
    )
    save_json_report("fit_csv_compare_pols.json", {"results": results})

    lines = [
        "Single-case polarization comparison",
        f"csv1 = {CSV_FILE_0DEG}",
        f"csv2 = {CSV_FILE_2DEG}",
        f"pol_list = {list(POL_COMPARE_LIST)}",
        "",
    ]

    for r in sorted(results, key=lambda x: x["best_objective"]):
        lines.append(
            f"{r['pol_model']}: "
            f"d_corr={r['d_fit_corrected_nm']:.6f} nm, "
            f"theta2_fit={r['theta2_fit_deg']:.6f} deg, "
            f"mix_p_weight={r.get('mix_p_weight_fit', float('nan')):.6f}, "
            f"obj={r['best_objective']:.12e}"
        )

    save_text_report("fit_csv_compare_pols.txt", lines)

    labels = [str(r["pol_model"]) for r in results]
    x = np.arange(len(labels))
    d_corr = np.array([r["d_fit_corrected_nm"] for r in results], dtype=float)
    objectives = np.array([r["best_objective"] for r in results], dtype=float)

    plt.figure(figsize=(8, 5))
    plt.bar(x, d_corr)
    plt.xticks(x, labels)
    plt.xlabel("Model polarization")
    plt.ylabel("Corrected thickness (nm)")
    plt.title("Thickness comparison across polarization models")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fit_csv_compare_pols_thickness.png", dpi=200)
    plt.show()

    plt.figure(figsize=(8, 5))
    plt.bar(x, objectives)
    plt.xticks(x, labels)
    plt.xlabel("Model polarization")
    plt.ylabel("Best objective")
    plt.title("Objective comparison across polarization models")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fit_csv_compare_pols_objective.png", dpi=200)
    plt.show()

    print("=" * 90)
    print("CSV fit polarization comparison")
    print("=" * 90)
    for r in sorted(results, key=lambda x: x["best_objective"]):
        print(
            f"{r['pol_model']:>3} | "
            f"d_fit_corrected = {r['d_fit_corrected_nm']:.6f} nm | "
            f"theta2_fit = {r['theta2_fit_deg']:.6f} deg | "
            f"mix_p_weight = {r.get('mix_p_weight_fit', float('nan')):.6f} | "
            f"objective = {r['best_objective']:.12e}"
        )

def run_preview_csv() -> None:
    spec = preview_csv(PREVIEW_CSV_FILE, y_selector=PREVIEW_Y_SELECTOR, save_plot=True)

    if spec.y_kind != "reflectance":
        print("\n提示：当前文件可以用于“预览”或“清洗导出”，但不能直接用于膜厚拟合。")
        print(f"当前选中的 y 列为: {spec.y_label}")
        print("如果它是 freq/THz，请把 y_selector 改到反射率列。")

def run_export_clean_csv() -> None:
    spec = export_clean_csv(
        EXPORT_CLEAN_INPUT_FILE,
        EXPORT_CLEAN_OUTPUT_FILE,
        y_selector=EXPORT_Y_SELECTOR,
    )
    print("=" * 90)
    print("Export clean csv finished")
    print("=" * 90)
    print(f"input_file   = {EXPORT_CLEAN_INPUT_FILE}")
    print(f"output_file  = {EXPORT_CLEAN_OUTPUT_FILE}")
    print(f"y_label      = {spec.y_label}")
    print(f"y_kind       = {spec.y_kind}")

def run_fit_csv() -> None:
    result = fit_dual_csv_from_files(
        CSV_FILE_0DEG,
        CSV_FILE_2DEG,
        sample_id="single_case",
        save_plots=True,
    )

    print("=" * 90)
    print("CSV fit")
    print("=" * 90)
    print(f"use_dispersion       = {result['use_dispersion']}")
    print(f"d_fit              = {result['d_fit_nm']:.6f} nm")
    print(f"d_fit_calibrated   = {result['d_fit_calibrated_nm']:.6f} nm")

    lines = [
        "CSV fit summary",
        f"csv_angle1 = {CSV_FILE_0DEG}",
        f"csv_angle2 = {CSV_FILE_2DEG}",
        f"theta_angle1 = {THETA1:.6f}",
        f"theta_angle2 = {THETA2:.6f}",
        f"use_dispersion = {result['use_dispersion']}",
        f"d_fit_nm = {result['d_fit_nm']:.6f}",
        f"d_fit_calibrated_nm = {result['d_fit_calibrated_nm']:.6f}",
    ]
    save_text_report("fit_csv_summary.txt", lines)
    save_json_report("fit_csv_summary.json", result)

def run_fit_csv_with_theta2_search() -> None:
    result = fit_dual_csv_with_theta2_search_from_files(
        CSV_FILE_0DEG,
        CSV_FILE_2DEG,
        sample_id="single_case",
        save_plots=True,
    )

    print("=" * 90)
    print("CSV fit with theta2 search")
    print("=" * 90)
    print(f"use_dispersion         = {result['use_dispersion']}")
    print(f"theta1_fixed           = {result['theta1_fixed_deg']:.6f} deg")
    print(f"theta2_nominal         = {result['theta2_nominal_deg']:.6f} deg")
    print(f"theta2_fit             = {result['theta2_fit_deg']:.6f} deg")
    print(f"d_fit_nominal          = {result['d_fit_nominal_nm']:.6f} nm")
    print(f"d_fit_corrected        = {result['d_fit_corrected_nm']:.6f} nm")
    print(f"d_fit_nominal_cal      = {result['d_fit_nominal_calibrated_nm']:.6f} nm")
    print(f"d_fit_corrected_cal    = {result['d_fit_corrected_calibrated_nm']:.6f} nm")
    print(f"delta_d                = {result['delta_d_nm']:.6f} nm")
    print(f"best_objective         = {result['best_objective']:.12e}")

    save_text_report(
        "fit_csv_with_theta2_search_summary.txt",
        [
            "CSV fit with theta2 search",
            f"csv_angle1 = {CSV_FILE_0DEG}",
            f"csv_angle2 = {CSV_FILE_2DEG}",
            f"use_dispersion = {result['use_dispersion']}",
            f"theta1_fixed_deg = {result['theta1_fixed_deg']:.6f}",
            f"theta2_nominal_deg = {result['theta2_nominal_deg']:.6f}",
            f"theta2_fit_deg = {result['theta2_fit_deg']:.6f}",
            f"d_fit_nominal_nm = {result['d_fit_nominal_nm']:.6f}",
            f"d_fit_corrected_nm = {result['d_fit_corrected_nm']:.6f}",
            f"d_fit_nominal_calibrated_nm = {result['d_fit_nominal_calibrated_nm']:.6f}",
            f"d_fit_corrected_calibrated_nm = {result['d_fit_corrected_calibrated_nm']:.6f}",
            f"delta_d_nm = {result['delta_d_nm']:.6f}",
            f"best_objective = {result['best_objective']:.12e}",
        ],
    )
    save_json_report("fit_csv_with_theta2_search_summary.json", result)
    save_rows_csv(
        "fit_csv_with_theta2_search_result.csv",
        [
            "theta1_fixed_deg",
            "theta2_nominal_deg",
            "theta2_fit_deg",
            "d_fit_nominal_nm",
            "d_fit_corrected_nm",
            "d_fit_nominal_calibrated_nm",
            "d_fit_corrected_calibrated_nm",
            "delta_d_nm",
            "best_objective",
        ],
        [[
            result["theta1_fixed_deg"],
            result["theta2_nominal_deg"],
            result["theta2_fit_deg"],
            result["d_fit_nominal_nm"],
            result["d_fit_corrected_nm"],
            result["d_fit_nominal_calibrated_nm"],
            result["d_fit_corrected_calibrated_nm"],
            result["delta_d_nm"],
            result["best_objective"],
        ]],
    )

