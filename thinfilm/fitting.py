"""Thickness inversion and theta-search fitting helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize_scalar

from .config import *
from .io import resolve_dual_fit_curves
from .objectives import evaluate_curve_objective, evaluate_dual_fit_objective, fit_linear_baseline, pick_distinct_search_seeds
from .optics import thinfilm_reflectance_angle


@dataclass
class DualSearchContext:
    lam: np.ndarray
    R1: np.ndarray
    theta1_fixed: float
    R2: np.ndarray
    theta2_nominal: float
    n0: float
    n1: float
    n2: float
    pol: str
    mix_p_weight: float
    lambda_a: float
    lambda_b: float
    smooth_window: int
    weight_level: float
    weight_shape: float
    weight_slope: float

def _make_dual_search_context(
    lam: np.ndarray,
    R1: np.ndarray,
    theta1_fixed: float,
    R2: np.ndarray,
    theta2_nominal: float,
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
) -> DualSearchContext:
    return DualSearchContext(
        lam=lam,
        R1=R1,
        theta1_fixed=theta1_fixed,
        R2=R2,
        theta2_nominal=theta2_nominal,
        n0=n0,
        n1=n1,
        n2=n2,
        pol=pol,
        mix_p_weight=mix_p_weight,
        lambda_a=lambda_a,
        lambda_b=lambda_b,
        smooth_window=smooth_window,
        weight_level=weight_level,
        weight_shape=weight_shape,
        weight_slope=weight_slope,
    )

def _evaluate_dual_search_objective(
    ctx: DualSearchContext,
    d_nm: float,
    theta2_deg: float,
) -> Tuple[float, Tuple[float, float, float, float], Dict[str, Dict[str, float]]]:
    return evaluate_dual_fit_objective(
        lam=ctx.lam,
        R1=ctx.R1,
        theta1=ctx.theta1_fixed,
        R2=ctx.R2,
        theta2=theta2_deg,
        d=d_nm * 1e-9,
        n0=ctx.n0,
        n1=ctx.n1,
        n2=ctx.n2,
        pol=ctx.pol,
        mix_p_weight=ctx.mix_p_weight,
        lambda_a=ctx.lambda_a,
        lambda_b=ctx.lambda_b,
        smooth_window=ctx.smooth_window,
        weight_level=ctx.weight_level,
        weight_shape=ctx.weight_shape,
        weight_slope=ctx.weight_slope,
    )

def _make_dual_search_grids(
    d_min_nm: float,
    d_max_nm: float,
    theta2_min: float,
    theta2_max: float,
    theta2_nominal: float,
    coarse_d_step_nm: float,
    coarse_theta_step_deg: float,
) -> Tuple[np.ndarray, np.ndarray]:
    d_grid_nm = np.arange(d_min_nm, d_max_nm + 1e-12, coarse_d_step_nm)
    theta_grid_deg = np.arange(theta2_min, theta2_max + 1e-12, coarse_theta_step_deg)
    if len(theta_grid_deg) == 0:
        theta_grid_deg = np.array([theta2_nominal], dtype=float)
    return d_grid_nm, theta_grid_deg

def _search_point(
    d_nm: float,
    theta2_deg: float,
    objective: float,
    baseline_params: Optional[Tuple[float, float, float, float]] = None,
    metrics: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict:
    point = {
        "d_nm": float(d_nm),
        "theta2_deg": float(theta2_deg),
        "objective": float(objective),
    }
    if baseline_params is not None:
        point["baseline_params"] = baseline_params
    if metrics is not None:
        point["metrics"] = metrics
    return point

def _optimize_d_for_fixed_theta(
    ctx: DualSearchContext,
    theta2_deg: float,
    d_left_nm: float,
    d_right_nm: float,
    d_step_nm: float,
) -> Dict:
    local_d_grid_nm = np.arange(d_left_nm, d_right_nm + 1e-12, d_step_nm)
    if len(local_d_grid_nm) == 0:
        local_d_grid_nm = np.array([d_left_nm], dtype=float)

    best_idx = 0
    best_pack = None
    for idx, d_nm in enumerate(local_d_grid_nm):
        err, baseline_params, metrics = _evaluate_dual_search_objective(ctx, float(d_nm), float(theta2_deg))
        if best_pack is None or err < best_pack["objective"]:
            best_idx = idx
            best_pack = _search_point(d_nm, theta2_deg, err, baseline_params, metrics)

    center_nm = float(local_d_grid_nm[best_idx])
    refine_half_window_nm = max(4.0 * d_step_nm, 6.0)
    left_nm = max(d_left_nm, center_nm - refine_half_window_nm)
    right_nm = min(d_right_nm, center_nm + refine_half_window_nm)

    if right_nm > left_nm:
        res_d = minimize_scalar(
            lambda d_nm: _evaluate_dual_search_objective(ctx, float(d_nm), float(theta2_deg))[0],
            bounds=(left_nm, right_nm),
            method="bounded",
            options={"xatol": 1e-3},
        )
        err_try, baseline_try, metrics_try = _evaluate_dual_search_objective(ctx, float(res_d.x), float(theta2_deg))
        if err_try < best_pack["objective"]:
            best_pack = _search_point(res_d.x, theta2_deg, err_try, baseline_try, metrics_try)

    return best_pack

def _coarse_dual_search(
    ctx: DualSearchContext,
    d_grid_nm: np.ndarray,
    theta_grid_deg: np.ndarray,
    d_min_nm: float,
    d_max_nm: float,
    coarse_d_step_nm: float,
) -> Tuple[np.ndarray, List[Dict]]:
    heatmap = np.zeros((len(theta_grid_deg), len(d_grid_nm)), dtype=float)
    theta_candidates = []

    for i, theta2_test in enumerate(theta_grid_deg):
        for j, d_nm in enumerate(d_grid_nm):
            err, _, _ = _evaluate_dual_search_objective(ctx, float(d_nm), float(theta2_test))
            heatmap[i, j] = err

        theta_candidates.append(
            _optimize_d_for_fixed_theta(
                ctx=ctx,
                theta2_deg=float(theta2_test),
                d_left_nm=d_min_nm,
                d_right_nm=d_max_nm,
                d_step_nm=coarse_d_step_nm,
            )
        )

    return heatmap, theta_candidates

def _select_dual_search_seeds_from_candidates(
    theta_candidates: List[Dict],
    top_k: int,
    min_d_separation_nm: float,
    min_theta_separation_deg: float,
) -> List[Dict[str, float]]:
    seeds = []
    for cand in sorted(theta_candidates, key=lambda x: x["objective"]):
        is_far_enough = True
        for seed in seeds:
            if (
                abs(cand["d_nm"] - seed["d_nm"]) < min_d_separation_nm
                and abs(cand["theta2_deg"] - seed["theta2_deg"]) < min_theta_separation_deg
            ):
                is_far_enough = False
                break

        if is_far_enough:
            seeds.append(_search_point(cand["d_nm"], cand["theta2_deg"], cand["objective"]))
            if len(seeds) >= top_k:
                break

    return seeds

def _local_theta_grid(theta_left: float, theta_right: float, theta_best: float, theta_window_deg: float) -> np.ndarray:
    if theta_right > theta_left:
        theta_step = max(theta_window_deg / 8.0, 0.01)
        return np.arange(theta_left, theta_right + 1e-12, theta_step)
    return np.array([theta_best], dtype=float)

def _refine_dual_search_seed(
    ctx: DualSearchContext,
    seed: Dict[str, float],
    d_min_nm: float,
    d_max_nm: float,
    theta2_min: float,
    theta2_max: float,
) -> Dict:
    d_best_nm = float(seed["d_nm"])
    theta_best = float(seed["theta2_deg"])
    best_err, baseline_params, metrics = _evaluate_dual_search_objective(ctx, d_best_nm, theta_best)
    stage_trace = [{
        "stage": "seed",
        "d_nm": d_best_nm,
        "theta2_deg": theta_best,
        "objective": float(best_err),
    }]

    for d_window_nm, theta_window_deg in zip(REFINE_D_WINDOWS_NM, REFINE_THETA_WINDOWS_DEG):
        d_left = max(d_min_nm, d_best_nm - d_window_nm)
        d_right = min(d_max_nm, d_best_nm + d_window_nm)
        theta_left = max(theta2_min, theta_best - theta_window_deg)
        theta_right = min(theta2_max, theta_best + theta_window_deg)
        local_d_step_nm = max(d_window_nm / 18.0, 0.08)

        local_best = None
        for theta2_test in _local_theta_grid(theta_left, theta_right, theta_best, theta_window_deg):
            cand = _optimize_d_for_fixed_theta(
                ctx=ctx,
                theta2_deg=float(theta2_test),
                d_left_nm=d_left,
                d_right_nm=d_right,
                d_step_nm=local_d_step_nm,
            )
            if local_best is None or cand["objective"] < local_best["objective"]:
                local_best = cand

        d_best_nm = float(local_best["d_nm"])
        theta_best = float(local_best["theta2_deg"])
        best_err = float(local_best["objective"])
        baseline_params = local_best["baseline_params"]
        metrics = local_best["metrics"]

        if theta_right > theta_left:
            cand = _refine_theta_for_dual_window(
                ctx=ctx,
                theta_left=theta_left,
                theta_right=theta_right,
                d_left=d_left,
                d_right=d_right,
                local_d_step_nm=local_d_step_nm,
            )
            if cand["objective"] < best_err:
                d_best_nm = float(cand["d_nm"])
                theta_best = float(cand["theta2_deg"])
                best_err = float(cand["objective"])
                baseline_params = cand["baseline_params"]
                metrics = cand["metrics"]

        stage_trace.append({
            "stage": f"window_d_{d_window_nm:.3f}_theta_{theta_window_deg:.3f}",
            "d_nm": float(d_best_nm),
            "theta2_deg": float(theta_best),
            "objective": float(best_err),
        })

    return {
        "d_fit_m": float(d_best_nm * 1e-9),
        "d_fit_nm": float(d_best_nm),
        "theta2_fit_deg": float(theta_best),
        "best_objective": float(best_err),
        "baseline_params": tuple(float(x) for x in baseline_params),
        "metrics": metrics,
        "stage_trace": stage_trace,
    }

def _refine_theta_for_dual_window(
    ctx: DualSearchContext,
    theta_left: float,
    theta_right: float,
    d_left: float,
    d_right: float,
    local_d_step_nm: float,
) -> Dict:
    refined_d_step = max(local_d_step_nm / 2.0, 0.05)
    res_theta = minimize_scalar(
        lambda theta_deg: _optimize_d_for_fixed_theta(
            ctx=ctx,
            theta2_deg=float(theta_deg),
            d_left_nm=d_left,
            d_right_nm=d_right,
            d_step_nm=refined_d_step,
        )["objective"],
        bounds=(theta_left, theta_right),
        method="bounded",
        options={"xatol": 1e-4},
    )
    return _optimize_d_for_fixed_theta(
        ctx=ctx,
        theta2_deg=float(res_theta.x),
        d_left_nm=d_left,
        d_right_nm=d_right,
        d_step_nm=refined_d_step,
    )

def multiscale_dual_search(
    lam: np.ndarray,
    R1: np.ndarray,
    theta1_fixed: float,
    R2: np.ndarray,
    theta2_nominal: float,
    n0: float,
    n1: float,
    n2: float,
    pol: str,
    mix_p_weight: float,
    d_min: float,
    d_max: float,
    lambda_a: float,
    lambda_b: float,
    theta2_min: float,
    theta2_max: float,
    smooth_window: int = OBJECTIVE_SMOOTH_WINDOW,
    weight_level: float = OBJECTIVE_WEIGHT_LEVEL,
    weight_shape: float = OBJECTIVE_WEIGHT_SHAPE,
    weight_slope: float = OBJECTIVE_WEIGHT_SLOPE,
    coarse_d_step_nm: float = SEARCH_COARSE_D_STEP_NM,
    coarse_theta_step_deg: float = SEARCH_COARSE_THETA_STEP_DEG,
    top_k: int = SEARCH_TOP_K,
    min_d_separation_nm: float = SEARCH_MIN_D_SEPARATION_NM,
    min_theta_separation_deg: float = SEARCH_MIN_THETA_SEPARATION_DEG,
) -> Dict:
    d_min_nm = float(d_min * 1e9)
    d_max_nm = float(d_max * 1e9)

    ctx = _make_dual_search_context(
        lam=lam,
        R1=R1,
        theta1_fixed=theta1_fixed,
        R2=R2,
        theta2_nominal=theta2_nominal,
        n0=n0,
        n1=n1,
        n2=n2,
        pol=pol,
        mix_p_weight=mix_p_weight,
        lambda_a=lambda_a,
        lambda_b=lambda_b,
        smooth_window=smooth_window,
        weight_level=weight_level,
        weight_shape=weight_shape,
        weight_slope=weight_slope,
    )
    d_grid_nm, theta_grid_deg = _make_dual_search_grids(
        d_min_nm=d_min_nm,
        d_max_nm=d_max_nm,
        theta2_min=theta2_min,
        theta2_max=theta2_max,
        theta2_nominal=theta2_nominal,
        coarse_d_step_nm=coarse_d_step_nm,
        coarse_theta_step_deg=coarse_theta_step_deg,
    )
    heatmap, theta_candidates = _coarse_dual_search(
        ctx=ctx,
        d_grid_nm=d_grid_nm,
        theta_grid_deg=theta_grid_deg,
        d_min_nm=d_min_nm,
        d_max_nm=d_max_nm,
        coarse_d_step_nm=coarse_d_step_nm,
    )
    seeds = _select_dual_search_seeds_from_candidates(
        theta_candidates=theta_candidates,
        top_k=top_k,
        min_d_separation_nm=min_d_separation_nm,
        min_theta_separation_deg=min_theta_separation_deg,
    )

    if len(seeds) == 0:
        raise ValueError("Multiscale search failed to find a valid seed.")

    best_solution = None
    search_trace = []
    for seed in seeds:
        candidate = _refine_dual_search_seed(
            ctx=ctx,
            seed=seed,
            d_min_nm=d_min_nm,
            d_max_nm=d_max_nm,
            theta2_min=theta2_min,
            theta2_max=theta2_max,
        )
        search_trace.append(candidate)
        if best_solution is None or candidate["best_objective"] < best_solution["best_objective"]:
            best_solution = candidate

    best_solution["coarse_heatmap"] = heatmap
    best_solution["coarse_d_grid_nm"] = d_grid_nm
    best_solution["coarse_theta2_grid_deg"] = theta_grid_deg
    best_solution["coarse_seeds"] = seeds
    best_solution["all_candidates"] = search_trace
    return best_solution

def invert_thickness_single_only(
    lam: np.ndarray,
    R_target: np.ndarray,
    n0: float,
    n1: float,
    n2: float,
    theta_deg: float,
    pol: str = "avg",
    d_min: float = 20e-9,
    d_max: float = 300e-9,
    n_grid: int = 1500,
) -> float:
    def objective(d: float) -> float:
        R_model = thinfilm_reflectance_angle(lam, n0, n1, n2, d, theta_deg, pol=pol)
        return float(np.mean((R_model - R_target) ** 2))

    d_grid = np.linspace(d_min, d_max, n_grid)
    err_grid = np.array([objective(d) for d in d_grid])
    d0 = float(d_grid[np.argmin(err_grid)])

    left = max(d_min, d0 - 20e-9)
    right = min(d_max, d0 + 20e-9)

    result = minimize_scalar(
        objective,
        bounds=(left, right),
        method="bounded",
        options={"xatol": 1e-12},
    )
    return float(result.x)

def invert_thickness_single_detrend(
    lam: np.ndarray,
    R_target: np.ndarray,
    n0: float,
    n1: float,
    n2: float,
    theta_deg: float,
    pol: str = "avg",
    d_min: float = 20e-9,
    d_max: float = 300e-9,
    lambda_a: float = 1.0,
    lambda_b: float = 1.0,
    n_iter: int = 2,
    n_grid: int = 1500,
) -> Tuple[float, float, float, np.ndarray]:
    lam_norm = (lam - lam.mean()) / (lam.max() - lam.min())
    R_work = R_target.copy()

    a_total = 0.0
    b_total = 0.0
    d_fit = None

    for _ in range(n_iter):
        d_fit = invert_thickness_single_only(
            lam, R_work, n0, n1, n2, theta_deg, pol=pol,
            d_min=d_min, d_max=d_max, n_grid=n_grid
        )

        R_model = thinfilm_reflectance_angle(lam, n0, n1, n2, d_fit, theta_deg, pol=pol)
        residual = R_work - R_model

        a_fit, b_fit = fit_linear_baseline(
            residual, lam_norm, lambda_a=lambda_a, lambda_b=lambda_b
        )

        R_work = R_work - (a_fit + b_fit * lam_norm)
        a_total += a_fit
        b_total += b_fit

    return float(d_fit), float(a_total), float(b_total), R_work

def invert_thickness_dual_only(
    lam: np.ndarray,
    R1: np.ndarray,
    theta1: float,
    R2: np.ndarray,
    theta2: float,
    n0: float,
    n1: float,
    n2: float,
    pol: str = "avg",
    d_min: float = 20e-9,
    d_max: float = 300e-9,
    n_grid: int = 1500,
) -> float:
    def objective(d: float) -> float:
        Rm1 = thinfilm_reflectance_angle(lam, n0, n1, n2, d, theta1, pol=pol)
        Rm2 = thinfilm_reflectance_angle(lam, n0, n1, n2, d, theta2, pol=pol)
        e1 = np.mean((Rm1 - R1) ** 2)
        e2 = np.mean((Rm2 - R2) ** 2)
        return float(0.5 * (e1 + e2))

    d_grid = np.linspace(d_min, d_max, n_grid)
    err_grid = np.array([objective(d) for d in d_grid])
    d0 = float(d_grid[np.argmin(err_grid)])

    left = max(d_min, d0 - 20e-9)
    right = min(d_max, d0 + 20e-9)

    result = minimize_scalar(
        objective,
        bounds=(left, right),
        method="bounded",
        options={"xatol": 1e-12},
    )
    return float(result.x)

def invert_thickness_dual_detrend(
    lam: np.ndarray,
    R1: np.ndarray,
    theta1: float,
    R2: np.ndarray,
    theta2: float,
    n0: float,
    n1: float,
    n2: float,
    pol: str = "avg",
    d_min: float = 20e-9,
    d_max: float = 300e-9,
    lambda_a: float = 1.0,
    lambda_b: float = 1.0,
    n_iter: int = 2,
    n_grid: int = 1500,
) -> Tuple[float, np.ndarray, np.ndarray, Tuple[float, float, float, float]]:
    lam_norm = (lam - lam.mean()) / (lam.max() - lam.min())
    R1_work = R1.copy()
    R2_work = R2.copy()

    a1_total = 0.0
    b1_total = 0.0
    a2_total = 0.0
    b2_total = 0.0

    d_fit = None

    for _ in range(n_iter):
        d_fit = invert_thickness_dual_only(
            lam, R1_work, theta1, R2_work, theta2, n0, n1, n2,
            pol=pol, d_min=d_min, d_max=d_max, n_grid=n_grid
        )

        Rm1 = thinfilm_reflectance_angle(lam, n0, n1, n2, d_fit, theta1, pol=pol)
        Rm2 = thinfilm_reflectance_angle(lam, n0, n1, n2, d_fit, theta2, pol=pol)

        res1 = R1_work - Rm1
        res2 = R2_work - Rm2

        a1, b1 = fit_linear_baseline(res1, lam_norm, lambda_a=lambda_a, lambda_b=lambda_b)
        a2, b2 = fit_linear_baseline(res2, lam_norm, lambda_a=lambda_a, lambda_b=lambda_b)

        R1_work = R1_work - (a1 + b1 * lam_norm)
        R2_work = R2_work - (a2 + b2 * lam_norm)

        a1_total += a1
        b1_total += b1
        a2_total += a2
        b2_total += b2

    baseline_params = (float(a1_total), float(b1_total), float(a2_total), float(b2_total))
    return float(d_fit), R1_work, R2_work, baseline_params

def invert_thickness_dual_with_theta2_search(
    lam: np.ndarray,
    R1: np.ndarray,
    theta1_nominal: float,
    R2: np.ndarray,
    theta2_nominal: float,
    n0: float,
    n1: float,
    n2: float,
    pol: str = "avg",
    d_min: float = 20e-9,
    d_max: float = 300e-9,
    lambda_a: float = 1.0,
    lambda_b: float = 1.0,
    n_iter: int = 2,
    n_grid: int = 1500,
    theta2_search_min: float = -3.0,
    theta2_search_max: float = 3.0,
    theta2_search_step: float = 0.25,
) -> Tuple[float, float, float, Tuple[float, float, float, float]]:
    theta2_candidates = np.arange(
        theta2_nominal + theta2_search_min,
        theta2_nominal + theta2_search_max + 1e-12,
        theta2_search_step,
    )

    best_err = np.inf
    d_fit_best = None
    theta2_best = None
    baseline_params_best = None

    for theta2_test in theta2_candidates:
        d_fit, R1_corr, R2_corr, baseline_params = invert_thickness_dual_detrend(
            lam, R1, theta1_nominal, R2, theta2_test, n0, n1, n2,
            pol=pol,
            d_min=d_min, d_max=d_max,
            lambda_a=lambda_a, lambda_b=lambda_b,
            n_iter=n_iter, n_grid=n_grid
        )

        Rm1 = thinfilm_reflectance_angle(lam, n0, n1, n2, d_fit, theta1_nominal, pol=pol)
        Rm2 = thinfilm_reflectance_angle(lam, n0, n1, n2, d_fit, theta2_test, pol=pol)

        err1 = np.mean((Rm1 - R1_corr) ** 2)
        err2 = np.mean((Rm2 - R2_corr) ** 2)
        total_err = float(0.5 * (err1 + err2))

        if total_err < best_err:
            best_err = total_err
            d_fit_best = d_fit
            theta2_best = float(theta2_test)
            baseline_params_best = baseline_params

    return float(d_fit_best), float(theta2_best), float(best_err), baseline_params_best

def plot_dual_fit(
    lam_nm: np.ndarray,
    R1_raw: np.ndarray,
    R2_raw: np.ndarray,
    d_fit: float,
    baseline_params: Tuple[float, float, float, float],
    theta1_used: float,
    theta2_used: float,
    mix_p_weight: float = 0.5,
    out_prefix: str = "fit",
) -> None:
    a1, b1, a2, b2 = baseline_params
    lam = lam_nm * 1e-9
    lam_norm = (lam - lam.mean()) / (lam.max() - lam.min())

    Rm1 = thinfilm_reflectance_angle(lam, N0, N1, N2, d_fit, theta1_used, pol=POL, mix_p_weight=mix_p_weight)
    Rm2 = thinfilm_reflectance_angle(lam, N0, N1, N2, d_fit, theta2_used, pol=POL, mix_p_weight=mix_p_weight)

    baseline1 = a1 + b1 * lam_norm
    baseline2 = a2 + b2 * lam_norm

    Rfit1 = Rm1 + baseline1
    Rfit2 = Rm2 + baseline2

    plt.figure(figsize=(8, 5))
    plt.plot(lam_nm, R1_raw, label=f"Exp {theta1_used:.1f}°", linewidth=1.5)
    plt.plot(lam_nm, Rfit1, "--", label=f"Fit {theta1_used:.1f}°", linewidth=2)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Reflectance")
    plt.title(f"Dual-angle fit at {theta1_used:.1f}°")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{out_prefix}_{str(theta1_used).replace('.', '_')}deg.png", dpi=200)
    plt.show()

    plt.figure(figsize=(8, 5))
    plt.plot(lam_nm, R2_raw, label=f"Exp {theta2_used:.1f}°", linewidth=1.5)
    plt.plot(lam_nm, Rfit2, "--", label=f"Fit {theta2_used:.1f}°", linewidth=2)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Reflectance")
    plt.title(f"Dual-angle fit at {theta2_used:.1f}°")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{out_prefix}_{str(theta2_used).replace('.', '_')}deg.png", dpi=200)
    plt.show()

    plt.figure(figsize=(8, 5))
    plt.plot(lam_nm, R1_raw - Rfit1, label=f"Residual {theta1_used:.1f}°")
    plt.plot(lam_nm, R2_raw - Rfit2, label=f"Residual {theta2_used:.1f}°")
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Residual")
    plt.title("Dual-angle residuals")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{out_prefix}_residuals.png", dpi=200)
    plt.show()

def run_dual_theta2_search_once(
    lam: np.ndarray,
    R1_i: np.ndarray,
    R2_i: np.ndarray,
    mix_p_weight: float,
) -> Tuple[Dict, Dict]:
    nominal_search = multiscale_dual_search(
        lam=lam,
        R1=R1_i,
        theta1_fixed=THETA1,
        R2=R2_i,
        theta2_nominal=THETA2,
        n0=N0,
        n1=N1,
        n2=N2,
        pol=POL,
        mix_p_weight=mix_p_weight,
        d_min=D_MIN,
        d_max=D_MAX,
        lambda_a=LAMBDA_A,
        lambda_b=LAMBDA_B,
        theta2_min=THETA2,
        theta2_max=THETA2,
    )
    corrected_search = multiscale_dual_search(
        lam=lam,
        R1=R1_i,
        theta1_fixed=THETA1,
        R2=R2_i,
        theta2_nominal=THETA2,
        n0=N0,
        n1=N1,
        n2=N2,
        pol=POL,
        mix_p_weight=mix_p_weight,
        d_min=D_MIN,
        d_max=D_MAX,
        lambda_a=LAMBDA_A,
        lambda_b=LAMBDA_B,
        theta2_min=THETA2 + THETA2_SEARCH_MIN,
        theta2_max=THETA2 + THETA2_SEARCH_MAX,
    )
    return nominal_search, corrected_search

def fit_mix_weight_from_dual_csv(
    lam: np.ndarray,
    R1_i: np.ndarray,
    R2_i: np.ndarray,
) -> Tuple[float, Dict, Dict]:
    weight_candidates = np.arange(
        MIX_WEIGHT_SEARCH_MIN,
        MIX_WEIGHT_SEARCH_MAX + 1e-12,
        MIX_WEIGHT_SEARCH_STEP,
    )
    if len(weight_candidates) == 0:
        weight_candidates = np.array([MIX_P_WEIGHT], dtype=float)

    best_pack = None
    for eta in weight_candidates:
        nominal_search, corrected_search = run_dual_theta2_search_once(
            lam=lam,
            R1_i=R1_i,
            R2_i=R2_i,
            mix_p_weight=float(eta),
        )
        objective = float(corrected_search["best_objective"])
        if best_pack is None or objective < best_pack["objective"]:
            best_pack = {
                "mix_p_weight": float(eta),
                "objective": objective,
                "nominal_search": nominal_search,
                "corrected_search": corrected_search,
            }

    left = max(MIX_WEIGHT_SEARCH_MIN, best_pack["mix_p_weight"] - max(MIX_WEIGHT_SEARCH_STEP, 0.05))
    right = min(MIX_WEIGHT_SEARCH_MAX, best_pack["mix_p_weight"] + max(MIX_WEIGHT_SEARCH_STEP, 0.05))
    if right > left:
        res = minimize_scalar(
            lambda eta: run_dual_theta2_search_once(
                lam=lam,
                R1_i=R1_i,
                R2_i=R2_i,
                mix_p_weight=float(eta),
            )[1]["best_objective"],
            bounds=(left, right),
            method="bounded",
            options={"xatol": 1e-3},
        )
        nominal_search, corrected_search = run_dual_theta2_search_once(
            lam=lam,
            R1_i=R1_i,
            R2_i=R2_i,
            mix_p_weight=float(res.x),
        )
        if float(corrected_search["best_objective"]) < best_pack["objective"]:
            best_pack = {
                "mix_p_weight": float(res.x),
                "objective": float(corrected_search["best_objective"]),
                "nominal_search": nominal_search,
                "corrected_search": corrected_search,
            }

    return (
        float(best_pack["mix_p_weight"]),
        best_pack["nominal_search"],
        best_pack["corrected_search"],
    )

def _calibrated_thickness_nm(d_nm: float) -> float:
    return float(
        calibrate_thickness_nm(
            d_nm,
            use_calibration=USE_THICKNESS_CALIBRATION,
            a=CAL_A,
            b=CAL_B,
        )
    )

def _add_fit_input_metadata(result: Dict, input_meta: Dict) -> Dict:
    result.update({
        "input_mode": str(input_meta["input_mode"]),
        "curve_1_source": str(input_meta["curve_1_source"]),
        "curve_2_source": str(input_meta["curve_2_source"]),
        "use_dispersion": bool(USE_DISPERSION),
        "dispersion_form": str(DISPERSION_FORM),
        "n1_dispersion_b": float(N1_DISPERSION_B),
        "n1_dispersion_c": float(N1_DISPERSION_C),
        "n2_dispersion_b": float(N2_DISPERSION_B),
        "n2_dispersion_c": float(N2_DISPERSION_C),
    })
    if "mix_source_p_weight" in input_meta:
        result["mix_source_p_weight"] = float(input_meta["mix_source_p_weight"])
        result["mix_source_0deg_mode"] = str(input_meta["mix_source_0deg_mode"])
        result["mix_source_2deg_mode"] = str(input_meta["mix_source_2deg_mode"])
    return result

def _run_fixed_theta_dual_search(lam: np.ndarray, R1_i: np.ndarray, R2_i: np.ndarray) -> Dict:
    return multiscale_dual_search(
        lam=lam,
        R1=R1_i,
        theta1_fixed=THETA1,
        R2=R2_i,
        theta2_nominal=THETA2,
        n0=N0,
        n1=N1,
        n2=N2,
        pol=POL,
        mix_p_weight=MIX_P_WEIGHT,
        d_min=D_MIN,
        d_max=D_MAX,
        lambda_a=LAMBDA_A,
        lambda_b=LAMBDA_B,
        theta2_min=THETA2,
        theta2_max=THETA2,
    )

def _build_fixed_theta_fit_result(
    csv_file_1: Path,
    csv_file_2: Path,
    sample_id: str,
    nominal_search: Dict,
    input_meta: Dict,
) -> Dict:
    d_fit_nm = float(nominal_search["d_fit_nm"])
    result = {
        "sample_id": sample_id,
        "csv_file_1": str(csv_file_1),
        "csv_file_2": str(csv_file_2),
        "theta1_fixed_deg": THETA1,
        "theta2_fixed_deg": THETA2,
        "d_fit_nm": d_fit_nm,
        "d_fit_calibrated_nm": _calibrated_thickness_nm(d_fit_nm),
        "search_method": SEARCH_METHOD,
        "best_objective": float(nominal_search["best_objective"]),
    }
    return _add_fit_input_metadata(result, input_meta)

def fit_dual_csv_from_files(
    csv_file_1: Path,
    csv_file_2: Path,
    sample_id: str = "sample",
    save_plots: bool = True,
) -> Dict:
    sync_angle_config_aliases()
    lam_nm, R1_i, R2_i, input_meta = resolve_dual_fit_curves(csv_file_1, csv_file_2)
    lam = lam_nm * 1e-9

    nominal_search = _run_fixed_theta_dual_search(lam, R1_i, R2_i)
    d_fit = float(nominal_search["d_fit_m"])
    baseline_params = nominal_search["baseline_params"]

    if save_plots:
        plot_dual_fit(
            lam_nm, R1_i, R2_i, d_fit, baseline_params,
            THETA1, THETA2, mix_p_weight=MIX_P_WEIGHT, out_prefix=f"{sample_id}_fit"
        )

    return _build_fixed_theta_fit_result(csv_file_1, csv_file_2, sample_id, nominal_search, input_meta)

def _run_theta2_search_or_mix_fit(lam: np.ndarray, R1_i: np.ndarray, R2_i: np.ndarray) -> Tuple[float, Dict, Dict]:
    mix_p_weight_fit = float(MIX_P_WEIGHT)
    if POL == "mix" and FIT_MIX_WEIGHT:
        mix_p_weight_fit, nominal_search, corrected_search = fit_mix_weight_from_dual_csv(
            lam=lam,
            R1_i=R1_i,
            R2_i=R2_i,
        )
    else:
        nominal_search, corrected_search = run_dual_theta2_search_once(
            lam=lam,
            R1_i=R1_i,
            R2_i=R2_i,
            mix_p_weight=mix_p_weight_fit,
        )
    return mix_p_weight_fit, nominal_search, corrected_search

def _plot_theta2_search_fit_results(
    lam_nm: np.ndarray,
    R1_i: np.ndarray,
    R2_i: np.ndarray,
    sample_id: str,
    mix_p_weight_fit: float,
    nominal_search: Dict,
    corrected_search: Dict,
) -> None:
    plot_dual_fit(
        lam_nm, R1_i, R2_i,
        float(nominal_search["d_fit_m"]),
        nominal_search["baseline_params"],
        THETA1, THETA2,
        mix_p_weight=mix_p_weight_fit,
        out_prefix=f"{sample_id}_nominal",
    )
    plot_dual_fit(
        lam_nm, R1_i, R2_i,
        float(corrected_search["d_fit_m"]),
        corrected_search["baseline_params"],
        THETA1, float(corrected_search["theta2_fit_deg"]),
        mix_p_weight=mix_p_weight_fit,
        out_prefix=f"{sample_id}_corrected",
    )

def _build_theta2_search_fit_result(
    csv_file_1: Path,
    csv_file_2: Path,
    sample_id: str,
    mix_p_weight_fit: float,
    nominal_search: Dict,
    corrected_search: Dict,
    input_meta: Dict,
) -> Dict:
    d_nominal_nm = float(nominal_search["d_fit_nm"])
    d_corrected_nm = float(corrected_search["d_fit_nm"])
    result = {
        "sample_id": sample_id,
        "csv_file_1": str(csv_file_1),
        "csv_file_2": str(csv_file_2),
        "theta1_fixed_deg": THETA1,
        "theta2_nominal_deg": THETA2,
        "theta2_fit_deg": float(corrected_search["theta2_fit_deg"]),
        "d_fit_nominal_nm": d_nominal_nm,
        "d_fit_corrected_nm": d_corrected_nm,
        "d_fit_nominal_calibrated_nm": _calibrated_thickness_nm(d_nominal_nm),
        "d_fit_corrected_calibrated_nm": _calibrated_thickness_nm(d_corrected_nm),
        "delta_d_nm": float(d_corrected_nm - d_nominal_nm),
        "best_objective": float(corrected_search["best_objective"]),
        "nominal_objective": float(nominal_search["best_objective"]),
        "search_method": SEARCH_METHOD,
        "mix_p_weight_fit": mix_p_weight_fit,
        "nominal_search_trace": nominal_search["stage_trace"],
        "corrected_search_trace": corrected_search["stage_trace"],
        "coarse_seeds": corrected_search["coarse_seeds"],
    }
    return _add_fit_input_metadata(result, input_meta)

def fit_dual_csv_with_theta2_search_from_files(
    csv_file_1: Path,
    csv_file_2: Path,
    sample_id: str = "sample",
    save_plots: bool = True,
) -> Dict:
    sync_angle_config_aliases()
    lam_nm, R1_i, R2_i, input_meta = resolve_dual_fit_curves(csv_file_1, csv_file_2)
    lam = lam_nm * 1e-9

    mix_p_weight_fit, nominal_search, corrected_search = _run_theta2_search_or_mix_fit(lam, R1_i, R2_i)

    if save_plots:
        _plot_theta2_search_fit_results(
            lam_nm=lam_nm,
            R1_i=R1_i,
            R2_i=R2_i,
            sample_id=sample_id,
            mix_p_weight_fit=mix_p_weight_fit,
            nominal_search=nominal_search,
            corrected_search=corrected_search,
        )

    return _build_theta2_search_fit_result(
        csv_file_1=csv_file_1,
        csv_file_2=csv_file_2,
        sample_id=sample_id,
        mix_p_weight_fit=mix_p_weight_fit,
        nominal_search=nominal_search,
        corrected_search=corrected_search,
        input_meta=input_meta,
    )

