"""Thin-film optical forward model helpers."""

from __future__ import annotations

from typing import Tuple

import numpy as np

from .config import *


def build_endpoint_blend_curve(
    spec_s: SpectrumData,
    spec_p: SpectrumData,
    source_mode: str,
    mix_p_weight: float,
) -> Tuple[np.ndarray, np.ndarray, str]:
    mode = str(source_mode).strip().lower()
    if mode == "s":
        return spec_s.x_nm, spec_s.y, f"s:{spec_s.path.name}"
    if mode == "p":
        return spec_p.x_nm, spec_p.y, f"p:{spec_p.path.name}"
    if mode != "blend":
        raise ValueError(
            f"Unsupported mixed-source mode '{source_mode}'. Use 's', 'p', or 'blend'."
        )

    blend_weight = float(np.clip(mix_p_weight, 0.0, 1.0))
    grid_nm, Rs_i, Rp_i = unify_two_reflectance_curves(
        spec_s.x_nm,
        spec_s.y,
        spec_p.x_nm,
        spec_p.y,
        wmin_nm=LAMBDA_MIN_NM,
        wmax_nm=LAMBDA_MAX_NM,
        n_lambda=max(len(spec_s.x_nm), len(spec_p.x_nm), N_LAMBDA),
    )
    R_mix = blend_weight * Rp_i + (1.0 - blend_weight) * Rs_i
    source_desc = (
        f"blend(eta_p={blend_weight:.6f}):"
        f"{spec_p.path.name}+{spec_s.path.name}"
    )
    return grid_nm, R_mix, source_desc

def interpolate_to_grid(w_nm: np.ndarray, y: np.ndarray, grid_nm: np.ndarray) -> np.ndarray:
    return np.interp(grid_nm, w_nm, y)

def unify_two_reflectance_curves(
    w1_nm: np.ndarray,
    R1: np.ndarray,
    w2_nm: np.ndarray,
    R2: np.ndarray,
    wmin_nm: float = 400.0,
    wmax_nm: float = 800.0,
    n_lambda: int = 300,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    w_min = max(np.min(w1_nm), np.min(w2_nm), wmin_nm)
    w_max = min(np.max(w1_nm), np.max(w2_nm), wmax_nm)

    if w_max <= w_min:
        raise ValueError("两条曲线没有共同波长区间。")

    grid_nm = np.linspace(w_min, w_max, n_lambda)
    R1_i = interpolate_to_grid(w1_nm, R1, grid_nm)
    R2_i = interpolate_to_grid(w2_nm, R2, grid_nm)
    return grid_nm, R1_i, R2_i

def evaluate_dispersion_profile(
    lam: np.ndarray,
    n_base: float,
    b_term: float,
    c_term: float,
) -> np.ndarray:
    lam = np.asarray(lam, dtype=float)
    if not USE_DISPERSION:
        return np.full_like(lam, float(n_base), dtype=float)

    form = str(DISPERSION_FORM).strip().lower()
    if form != "cauchy_um":
        raise ValueError(
            f"Unsupported DISPERSION_FORM '{DISPERSION_FORM}'. "
            "Currently only 'cauchy_um' is supported."
        )

    lam_um = lam * 1e6
    lam_um = np.clip(lam_um, 1e-9, None)
    return (
        float(n_base)
        + float(b_term) / (lam_um ** 2)
        + float(c_term) / (lam_um ** 4)
    )

def thinfilm_reflectance_angle(
    lam: np.ndarray,
    n0: float,
    n1: float,
    n2: float,
    d: float,
    theta0_deg: float,
    pol: str = "avg",
    mix_p_weight: float = 0.5,
) -> np.ndarray:
    lam = np.asarray(lam, dtype=float)
    theta0 = np.deg2rad(theta0_deg)
    n0_arr = np.full_like(lam, float(n0), dtype=float)
    n1_arr = evaluate_dispersion_profile(lam, n1, N1_DISPERSION_B, N1_DISPERSION_C)
    n2_arr = evaluate_dispersion_profile(lam, n2, N2_DISPERSION_B, N2_DISPERSION_C)

    sin_theta1 = n0_arr * np.sin(theta0) / n1_arr
    sin_theta2 = n0_arr * np.sin(theta0) / n2_arr

    sin_theta1 = np.clip(sin_theta1, -1.0, 1.0)
    sin_theta2 = np.clip(sin_theta2, -1.0, 1.0)

    theta1 = np.arcsin(sin_theta1)
    theta2 = np.arcsin(sin_theta2)

    c0 = np.cos(theta0)
    c1 = np.cos(theta1)
    c2 = np.cos(theta2)

    beta = 2 * np.pi * n1_arr * d * c1 / lam

    r01_s = (n0_arr * c0 - n1_arr * c1) / (n0_arr * c0 + n1_arr * c1)
    r12_s = (n1_arr * c1 - n2_arr * c2) / (n1_arr * c1 + n2_arr * c2)
    r_s = (r01_s + r12_s * np.exp(2j * beta)) / (1 + r01_s * r12_s * np.exp(2j * beta))
    R_s = np.abs(r_s) ** 2

    r01_p = (n1_arr * c0 - n0_arr * c1) / (n1_arr * c0 + n0_arr * c1)
    r12_p = (n2_arr * c1 - n1_arr * c2) / (n2_arr * c1 + n1_arr * c2)
    r_p = (r01_p + r12_p * np.exp(2j * beta)) / (1 + r01_p * r12_p * np.exp(2j * beta))
    R_p = np.abs(r_p) ** 2

    if pol == "s":
        return R_s
    if pol == "p":
        return R_p
    if pol == "avg":
        return 0.5 * (R_s + R_p)
    if pol == "mix":
        eta = float(np.clip(mix_p_weight, 0.0, 1.0))
        return eta * R_p + (1.0 - eta) * R_s
    raise ValueError("pol 必须是 's'、'p' 或 'avg'")

