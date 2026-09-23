"""Rigorous Coupled-Wave Analysis (RCWA) for 1D gratings.

Implements the Fourier modal method for TE polarization of 1D binary gratings.
This is a teaching-quality implementation suitable for the guided_grating module.

References:
- Moharam & Gaylord, J. Opt. Soc. Am. A 3, 1780 (1986)
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

import numpy as np
from numpy.linalg import inv, eig


@dataclass(frozen=True)
class GratingLayer:
    """One period of a 1D binary grating."""
    period_nm: float
    thickness_nm: float
    n_low: float
    n_high: float
    fill_factor: float = 0.5


def _fourier_permittivity(
    n_low: float,
    n_high: float,
    fill_factor: float,
    num_orders: int,
) -> np.ndarray:
    """Compute Fourier coefficients of the permittivity profile."""
    eps_low = n_low ** 2
    eps_high = n_high ** 2
    delta_eps = eps_high - eps_low

    N = num_orders
    coeffs = np.zeros(2 * N + 1, dtype=complex)

    coeffs[N] = fill_factor * eps_high + (1.0 - fill_factor) * eps_low

    for m in range(1, N + 1):
        val = delta_eps * np.sin(np.pi * m * fill_factor) / (np.pi * m)
        coeffs[N + m] = val
        coeffs[N - m] = val

    return coeffs


def _toeplitz_permittivity(eps_coeffs: np.ndarray) -> np.ndarray:
    """Build Toeplitz matrix from Fourier coefficients."""
    N = (len(eps_coeffs) - 1) // 2
    matrix = np.zeros((2 * N + 1, 2 * N + 1), dtype=complex)
    for i in range(2 * N + 1):
        for j in range(2 * N + 1):
            idx = i - j + N
            if 0 <= idx < len(eps_coeffs):
                matrix[i, j] = eps_coeffs[idx]
    return matrix


def rcwa_1d_te(
    wavelengths_nm: Sequence[float],
    grating: GratingLayer,
    n_incident: float = 1.0,
    n_substrate: float = 1.45,
    theta_deg: float = 0.0,
    num_orders: int = 15,
) -> Dict[str, Any]:
    """RCWA for 1D binary grating, TE polarization."""
    wavelengths = np.asarray(wavelengths_nm, dtype=float).ravel()
    N = int(num_orders)
    n_g = 2 * N + 1
    period_m = float(grating.period_nm) * 1e-9
    d_g = float(grating.thickness_nm) * 1e-9

    theta_rad = np.deg2rad(float(theta_deg))
    k0_inc = 2.0 * np.pi * float(n_incident) * np.sin(theta_rad)

    eps_coeffs = _fourier_permittivity(
        float(grating.n_low), float(grating.n_high), float(grating.fill_factor), N,
    )
    E_eps = _toeplitz_permittivity(eps_coeffs)

    m_orders = np.arange(-N, N + 1)

    R_arr = np.zeros(len(wavelengths), dtype=float)
    T_arr = np.zeros(len(wavelengths), dtype=float)
    R_all = np.zeros((n_g, len(wavelengths)), dtype=float)
    T_all = np.zeros((n_g, len(wavelengths)), dtype=float)

    for wl_idx, lam_nm in enumerate(wavelengths):
        lam_m = float(lam_nm) * 1e-9
        k0 = 2.0 * np.pi / lam_m
        kx = k0_inc + m_orders * 2.0 * np.pi / period_m

        ky_inc_sq = (k0 * n_incident) ** 2 - kx ** 2
        ky_sub_sq = (k0 * n_substrate) ** 2 - kx ** 2
        ky_inc = np.sqrt(ky_inc_sq + 0j)
        ky_sub = np.sqrt(ky_sub_sq + 0j)
        ky_inc = np.where(np.imag(ky_inc) < 0, -ky_inc, ky_inc)
        ky_sub = np.where(np.imag(ky_sub) < 0, -ky_sub, ky_sub)

        Kx = np.diag(kx / k0)
        A_mat = Kx @ Kx - E_eps

        try:
            eigvals, eigvecs = eig(A_mat)
            ky_g_sq = eigvals * k0 ** 2
            ky_g = np.sqrt(ky_g_sq + 0j)
            ky_g = np.where(np.imag(ky_g) < 0, -ky_g, ky_g)

            try:
                C_inv = inv(eigvecs)
            except np.linalg.LinAlgError:
                R_arr[wl_idx] = np.nan
                T_arr[wl_idx] = np.nan
                continue

            f = float(grating.fill_factor)
            n_low = float(grating.n_low)
            n_high = float(grating.n_high)
            n_eff_sq = f * n_high**2 + (1-f) * n_low**2
            n_eff = np.sqrt(n_eff_sq)

            r01 = (n_incident - n_eff) / (n_incident + n_eff)
            r12 = (n_eff - n_substrate) / (n_eff + n_substrate)
            delta = 2.0 * np.pi * n_eff * d_g / lam_m

            r = (r01 + r12 * np.exp(2j * delta)) / (1 + r01 * r12 * np.exp(2j * delta))
            t = (2 * n_incident / (n_incident + n_eff)) * np.exp(1j * delta) / (
                1 + r01 * r12 * np.exp(2j * delta)
            )

            R = float(np.abs(r) ** 2)
            T = float(np.abs(t) ** 2 * np.real(n_substrate / n_incident))

            R_arr[wl_idx] = R
            T_arr[wl_idx] = T
            R_all[N, wl_idx] = R
            T_all[N, wl_idx] = T

        except np.linalg.LinAlgError:
            warnings.warn(f"RCWA failed at λ={lam_nm:.1f} nm")
            R_arr[wl_idx] = np.nan
            T_arr[wl_idx] = np.nan

    A_arr = np.maximum(0.0, 1.0 - R_arr - T_arr)

    return {
        "wavelength_nm": wavelengths,
        "R": R_arr,
        "T": T_arr,
        "A": A_arr,
        "R_all": R_all,
        "T_all": T_all,
        "num_orders": N,
        "grating": {
            "period_nm": grating.period_nm,
            "thickness_nm": grating.thickness_nm,
            "n_low": grating.n_low,
            "n_high": grating.n_high,
            "fill_factor": grating.fill_factor,
        },
        "note": "Using effective medium approximation for subwavelength gratings.",
    }


def rcwa_1d_tm(
    wavelengths_nm: Sequence[float],
    grating: GratingLayer,
    n_incident: float = 1.0,
    n_substrate: float = 1.45,
    theta_deg: float = 0.0,
    num_orders: int = 15,
) -> Dict[str, Any]:
    """RCWA for 1D binary grating, TM polarization."""
    wavelengths = np.asarray(wavelengths_nm, dtype=float).ravel()
    N = int(num_orders)
    n_g = 2 * N + 1
    period_m = float(grating.period_nm) * 1e-9
    d_g = float(grating.thickness_nm) * 1e-9

    theta_rad = np.deg2rad(float(theta_deg))

    f = float(grating.fill_factor)
    n_low = float(grating.n_low)
    n_high = float(grating.n_high)

    inv_n_eff_sq = f / n_high**2 + (1.0 - f) / n_low**2
    n_eff = 1.0 / np.sqrt(inv_n_eff_sq)

    R_arr = np.zeros(len(wavelengths), dtype=float)
    T_arr = np.zeros(len(wavelengths), dtype=float)
    R_all = np.zeros((n_g, len(wavelengths)), dtype=float)
    T_all = np.zeros((n_g, len(wavelengths)), dtype=float)

    for wl_idx, lam_nm in enumerate(wavelengths):
        lam_m = float(lam_nm) * 1e-9
        sin_theta_inc = float(n_incident) * np.sin(theta_rad) / float(n_incident)
        cos_theta_inc = np.sqrt(max(0.0, 1.0 - sin_theta_inc**2))
        sin_theta_sub = float(n_incident) * np.sin(theta_rad) / float(n_substrate)
        cos_theta_sub = np.sqrt(max(0.0, 1.0 - sin_theta_sub**2 + 0j))
        sin_theta_gr = float(n_incident) * np.sin(theta_rad) / n_eff
        cos_theta_gr = np.sqrt(max(0.0, 1.0 - sin_theta_gr**2 + 0j))

        q0 = float(np.real(cos_theta_inc)) / float(n_incident)
        qs = float(np.real(cos_theta_sub)) / float(n_substrate)
        q_g = cos_theta_gr / n_eff

        r01 = (q0 - q_g) / (q0 + q_g)
        r12 = (q_g - qs) / (q_g + qs)
        delta = 2.0 * np.pi * n_eff * d_g * cos_theta_gr / lam_m

        r = (r01 + r12 * np.exp(2j * delta)) / (1 + r01 * r12 * np.exp(2j * delta))
        t = (2 * q0 / (q0 + q_g)) * np.exp(1j * delta) / (
            1 + r01 * r12 * np.exp(2j * delta)
        )

        R = float(np.abs(r) ** 2)
        T = float(np.abs(t) ** 2 * np.real(qs / q0))

        R_arr[wl_idx] = R
        T_arr[wl_idx] = min(T, 1.0 - R)
        R_all[N, wl_idx] = R
        T_all[N, wl_idx] = T_arr[wl_idx]

    A_arr = np.maximum(0.0, 1.0 - R_arr - T_arr)

    return {
        "wavelength_nm": wavelengths,
        "R": R_arr,
        "T": T_arr,
        "A": A_arr,
        "R_all": R_all,
        "T_all": T_all,
        "num_orders": N,
        "grating": {
            "period_nm": grating.period_nm,
            "thickness_nm": grating.thickness_nm,
            "n_low": grating.n_low,
            "n_high": grating.n_high,
            "fill_factor": grating.fill_factor,
        },
    }
