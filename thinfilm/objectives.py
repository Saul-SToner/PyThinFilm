"""Objective functions and signal-shape scoring helpers."""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from .optics import thinfilm_reflectance_angle


def fit_linear_baseline(
    residual: np.ndarray,
    x: np.ndarray,
    lambda_a: float = 1.0,
    lambda_b: float = 1.0,
) -> Tuple[float, float]:
    X = np.column_stack([np.ones_like(x), x])
    L = np.diag([lambda_a, lambda_b])
    beta = np.linalg.solve(X.T @ X + L, X.T @ residual)
    a_fit, b_fit = beta
    return float(a_fit), float(b_fit)

def _safe_scale(value: float, eps: float = 1e-12) -> float:
    return max(float(value), eps)

def _ensure_odd_window(window: int) -> int:
    window = max(int(window), 1)
    if window % 2 == 0:
        window += 1
    return window

def smooth_signal_1d(y: np.ndarray, window: int = 1) -> np.ndarray:
    y = np.asarray(y, dtype=float).ravel()
    window = _ensure_odd_window(window)
    if window <= 1 or window >= len(y):
        return y.copy()

    pad = window // 2
    kernel = np.ones(window, dtype=float) / float(window)
    y_pad = np.pad(y, (pad, pad), mode="edge")
    return np.convolve(y_pad, kernel, mode="valid")

def standardize_signal(y: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    y = np.asarray(y, dtype=float).ravel()
    return (y - np.mean(y)) / _safe_scale(np.std(y), eps=eps)

def evaluate_curve_objective(
    lam: np.ndarray,
    y_obs: np.ndarray,
    y_model: np.ndarray,
    lambda_a: float,
    lambda_b: float,
    smooth_window: int,
    weight_level: float,
    weight_shape: float,
    weight_slope: float,
) -> Tuple[float, Tuple[float, float], Dict[str, float]]:
    lam = np.asarray(lam, dtype=float).ravel()
    y_obs = np.asarray(y_obs, dtype=float).ravel()
    y_model = np.asarray(y_model, dtype=float).ravel()

    lam_span = _safe_scale(np.max(lam) - np.min(lam), eps=1e-18)
    lam_norm = (lam - np.mean(lam)) / lam_span

    a_fit, b_fit = fit_linear_baseline(
        y_obs - y_model,
        lam_norm,
        lambda_a=lambda_a,
        lambda_b=lambda_b,
    )
    y_model_adj = y_model + a_fit + b_fit * lam_norm

    y_obs_s = smooth_signal_1d(y_obs, window=smooth_window)
    y_model_s = smooth_signal_1d(y_model_adj, window=smooth_window)

    level_err = float(
        np.mean((y_obs_s - y_model_s) ** 2) / _safe_scale(np.var(y_obs_s))
    )

    y_obs_shape = standardize_signal(y_obs_s)
    y_model_shape = standardize_signal(y_model_s)
    shape_err = float(np.mean((y_obs_shape - y_model_shape) ** 2))

    slope_obs = standardize_signal(np.gradient(y_obs_s, lam_norm))
    slope_model = standardize_signal(np.gradient(y_model_s, lam_norm))
    slope_err = float(np.mean((slope_obs - slope_model) ** 2))

    total_err = float(
        weight_level * level_err
        + weight_shape * shape_err
        + weight_slope * slope_err
    )

    metrics = {
        "level_err": level_err,
        "shape_err": shape_err,
        "slope_err": slope_err,
        "a_fit": float(a_fit),
        "b_fit": float(b_fit),
    }
    return total_err, (float(a_fit), float(b_fit)), metrics

def evaluate_dual_fit_objective(
    lam: np.ndarray,
    R1: np.ndarray,
    theta1: float,
    R2: np.ndarray,
    theta2: float,
    d: float,
    n0: float,
    n1: float,
    n2: float,
    pol: str,
    mix_p_weight: float,
    lambda_a: float,
    lambda_b: float,
    smooth_window: int,
    weight_level: float,
    weight_shape: float,
    weight_slope: float,
) -> Tuple[float, Tuple[float, float, float, float], Dict[str, Dict[str, float]]]:
    Rm1 = thinfilm_reflectance_angle(lam, n0, n1, n2, d, theta1, pol=pol, mix_p_weight=mix_p_weight)
    Rm2 = thinfilm_reflectance_angle(lam, n0, n1, n2, d, theta2, pol=pol, mix_p_weight=mix_p_weight)
    lam_span = _safe_scale(np.max(lam) - np.min(lam), eps=1e-18)
    lam_norm = (lam - np.mean(lam)) / lam_span

    err1, (a1, b1), metrics1 = evaluate_curve_objective(
        lam=lam,
        y_obs=R1,
        y_model=Rm1,
        lambda_a=lambda_a,
        lambda_b=lambda_b,
        smooth_window=smooth_window,
        weight_level=weight_level,
        weight_shape=weight_shape,
        weight_slope=weight_slope,
    )
    err2, (a2, b2), metrics2 = evaluate_curve_objective(
        lam=lam,
        y_obs=R2,
        y_model=Rm2,
        lambda_a=lambda_a,
        lambda_b=lambda_b,
        smooth_window=smooth_window,
        weight_level=weight_level,
        weight_shape=weight_shape,
        weight_slope=weight_slope,
    )

    Rm1_adj = Rm1 + a1 + b1 * lam_norm
    Rm2_adj = Rm2 + a2 + b2 * lam_norm

    delta_obs = smooth_signal_1d(R2 - R1, window=smooth_window)
    delta_model = smooth_signal_1d(Rm2_adj - Rm1_adj, window=smooth_window)
    delta_shape_err = float(
        np.mean((standardize_signal(delta_obs) - standardize_signal(delta_model)) ** 2)
    )
    delta_slope_err = float(
        np.mean(
            (
                standardize_signal(np.gradient(delta_obs, lam_norm))
                - standardize_signal(np.gradient(delta_model, lam_norm))
            ) ** 2
        )
    )

    common_err = float(0.5 * (err1 + err2))
    delta_err = float(0.35 * delta_shape_err + 0.65 * delta_slope_err)
    total_err = float(0.55 * common_err + 0.45 * delta_err)
    baseline_params = (float(a1), float(b1), float(a2), float(b2))
    metrics = {
        "curve_1": metrics1,
        "curve_2": metrics2,
        "cross_angle": {
            "delta_shape_err": delta_shape_err,
            "delta_slope_err": delta_slope_err,
            "common_err": common_err,
            "delta_err": delta_err,
        },
    }
    return total_err, baseline_params, metrics

def pick_distinct_search_seeds(
    heatmap: np.ndarray,
    d_grid_nm: np.ndarray,
    theta_grid_deg: np.ndarray,
    top_k: int,
    min_d_separation_nm: float,
    min_theta_separation_deg: float,
) -> List[Dict[str, float]]:
    seeds: List[Dict[str, float]] = []
    flat_order = np.argsort(heatmap, axis=None)

    for flat_idx in flat_order:
        i, j = np.unravel_index(flat_idx, heatmap.shape)
        cand = {
            "d_nm": float(d_grid_nm[j]),
            "theta2_deg": float(theta_grid_deg[i]),
            "objective": float(heatmap[i, j]),
        }

        is_far_enough = True
        for seed in seeds:
            if (
                abs(cand["d_nm"] - seed["d_nm"]) < min_d_separation_nm
                and abs(cand["theta2_deg"] - seed["theta2_deg"]) < min_theta_separation_deg
            ):
                is_far_enough = False
                break

        if is_far_enough:
            seeds.append(cand)
            if len(seeds) >= top_k:
                break

    return seeds

