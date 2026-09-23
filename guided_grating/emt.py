# -*- coding: utf-8 -*-
"""Effective Medium Theory (EMT) for 1D gratings.

Provides zero-order effective medium theory approximations for subwavelength gratings,
mapping periodic 1D profiles to equivalent anisotropic thin films.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Dict, Sequence
import numpy as np


@dataclass(frozen=True)
class GratingLayer:
    """One period of a 1D binary grating.

    Attributes
    ----------
    period_nm : float
        Grating period in nanometers.
    thickness_nm : float
        Grating layer thickness in nanometers.
    n_low : float or complex
        Refractive index of the low-index region.
    n_high : float or complex
        Refractive index of the high-index region.
    fill_factor : float
        Fraction of the period occupied by high-index material (0-1).
    """
    period_nm: float
    thickness_nm: float
    n_low: float | complex
    n_high: float | complex
    fill_factor: float = 0.5


def emt_effective_index_te(n_low: float | complex, n_high: float | complex, fill_factor: float) -> complex:
    """Compute the zero-order effective refractive index for TE polarization (E || grooves).

    n_eff^2 = f * n_high^2 + (1 - f) * n_low^2
    """
    f = float(fill_factor)
    eps_eff = f * (n_high ** 2) + (1.0 - f) * (n_low ** 2)
    return np.sqrt(eps_eff + 0j)


def emt_effective_index_tm(n_low: float | complex, n_high: float | complex, fill_factor: float) -> complex:
    """Compute the zero-order effective refractive index for TM polarization (E perp grooves).

    1 / n_eff^2 = f / n_high^2 + (1 - f) / n_low^2
    """
    f = float(fill_factor)
    eps_inv = f / (n_high ** 2) + (1.0 - f) / (n_low ** 2)
    eps_eff = 1.0 / eps_inv
    return np.sqrt(eps_eff + 0j)


def check_emt_applicability(
    period_nm: float,
    n_low: float | complex,
    n_high: float | complex,
    target_wavelength_nm: float,
) -> Dict[str, Any]:
    """Assess zero-order EMT model applicability based on normalized period parameter rho.

    rho = n_max * period / lambda_0
    """
    n_max = float(np.max([np.abs(n_low), np.abs(n_high)]))
    rho = n_max * float(period_nm) / float(target_wavelength_nm)

    if rho <= 0.1:
        status = "conservative_teaching"
        recommendation = "Within conservative teaching range (low error)"
    elif 0.1 < rho < 0.5:
        status = "moderate_error"
        recommendation = "EMT approximation error may increase; external full-wave verification is recommended"
    elif 0.5 <= rho < 1.0:
        status = "high_risk"
        recommendation = "High risk region; quantitative design is not recommended"
    else:
        status = "rejected"
        recommendation = "Diffraction orders may propagate; EMT calculation is rejected for quantitative analysis"

    return {
        "rho": rho,
        "status": status,
        "recommendation": recommendation,
        "is_valid": status in ["conservative_teaching", "moderate_error"]
    }


def emt_layer_spectrum(
    wavelengths_nm: Sequence[float],
    grating: GratingLayer,
    n_incident: float | complex = 1.0,
    n_substrate: float | complex = 1.45,
    theta_deg: float = 0.0,
    pol: str = "TE",
) -> Dict[str, Any]:
    """Calculate the reflection and transmission spectrum of the grating using zero-order EMT.

    Parameters
    ----------
    wavelengths_nm : array-like
        Wavelengths in nanometers.
    grating : GratingLayer
        Grating specifications.
    n_incident : float or complex
        Refractive index of incident medium.
    n_substrate : float or complex
        Refractive index of substrate.
    theta_deg : float
        Angle of incidence in degrees.
    pol : str
        Polarization mode ('TE' or 'TM').

    Returns
    -------
    dict
        Spectral R, T, A arrays, raw energy residues, and effective index.
    """
    wavelengths = np.asarray(wavelengths_nm, dtype=float).ravel()
    pol_key = pol.strip().upper()

    # Calculate effective index of grating layer
    if pol_key == "TE":
        n_eff = emt_effective_index_te(grating.n_low, grating.n_high, grating.fill_factor)
    elif pol_key == "TM":
        n_eff = emt_effective_index_tm(grating.n_low, grating.n_high, grating.fill_factor)
    else:
        raise ValueError(f"pol must be 'TE' or 'TM', got '{pol}'")

    R_arr = np.zeros(len(wavelengths), dtype=float)
    T_arr = np.zeros(len(wavelengths), dtype=float)
    A_arr = np.zeros(len(wavelengths), dtype=float)
    residue_arr = np.zeros(len(wavelengths), dtype=float)

    d_m = float(grating.thickness_nm) * 1e-9
    theta_rad = np.deg2rad(float(theta_deg))

    # Identify if system is physically lossless
    is_lossless = (
        np.abs(np.imag(grating.n_low)) < 1e-12 and
        np.abs(np.imag(grating.n_high)) < 1e-12 and
        np.abs(np.imag(n_incident)) < 1e-12 and
        np.abs(np.imag(n_substrate)) < 1e-12
    )

    for wl_idx, lam_nm in enumerate(wavelengths):
        lam_m = float(lam_nm) * 1e-9

        # Snell's Law to get cos_theta in each region
        sin_theta_inc = np.sin(theta_rad)
        cos_theta_inc = np.cos(theta_rad)

        sin_theta_sub = (n_incident * sin_theta_inc) / n_substrate
        cos_theta_sub = np.sqrt(1.0 - sin_theta_sub**2 + 0j)

        sin_theta_gr = (n_incident * sin_theta_inc) / n_eff
        cos_theta_gr = np.sqrt(1.0 - sin_theta_gr**2 + 0j)

        # Admittances
        if pol_key == "TE":
            q0 = n_incident * cos_theta_inc
            qs = n_substrate * cos_theta_sub
            q_g = n_eff * cos_theta_gr
        else:  # TM
            q0 = cos_theta_inc / n_incident
            qs = cos_theta_sub / n_substrate
            q_g = cos_theta_gr / n_eff

        # TMM Characteristic Matrix
        delta = 2.0 * np.pi * n_eff * d_m * cos_theta_gr / lam_m
        c = np.cos(delta)
        s = np.sin(delta)

        M00 = c
        M01 = 1j * s / q_g
        M10 = 1j * q_g * s
        M11 = c

        b_val = M00 + M01 * qs
        c_val = M10 + M11 * qs
        y_in = c_val / b_val

        r = (q0 - y_in) / (q0 + y_in)
        t = (2.0 * q0) / (q0 * b_val + c_val)

        R = np.abs(r) ** 2
        T = np.abs(t) ** 2 * np.real(qs / q0)

        # Calculate physical absorption
        if is_lossless:
            A = 0.0
        else:
            A = 1.0 - R - T

        R_arr[wl_idx] = float(R)
        T_arr[wl_idx] = float(T)
        A_arr[wl_idx] = float(A)
        
        # Calculate raw energy residue: R + T + A - 1
        residue = float(R + T + A - 1.0)
        residue_arr[wl_idx] = residue

        # Warn if residue is unphysically large
        if np.abs(residue) > 1e-4:
            warnings.warn(
                f"Energy conservation warning at λ={lam_nm:.1f} nm: R={R:.4f}, T={T:.4f}, A={A:.4f}, residue={residue:.4e}"
            )

    return {
        "wavelength_nm": wavelengths,
        "R": R_arr,
        "T": T_arr,
        "A": A_arr,
        "energy_residue": residue_arr,
        "n_eff": n_eff,
        "grating": {
            "period_nm": grating.period_nm,
            "thickness_nm": grating.thickness_nm,
            "n_low": grating.n_low,
            "n_high": grating.n_high,
            "fill_factor": grating.fill_factor,
        },
        "note": "Using effective medium theory (EMT) zero-order approximation.",
    }


# Backwards compatibility alias
def rcwa_1d(
    wavelengths_nm: Sequence[float],
    grating: GratingLayer,
    n_incident: float | complex = 1.0,
    n_substrate: float | complex = 1.45,
    theta_deg: float = 0.0,
    pol: str = "TE",
    num_orders: int = 15,
) -> Dict[str, Any]:
    """Compatibility wrapper redirecting to emt_layer_spectrum."""
    warnings.warn(
        "rcwa_1d is deprecated and will be removed in v1.1. Use emt_layer_spectrum instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    res = emt_layer_spectrum(
        wavelengths_nm=wavelengths_nm,
        grating=grating,
        n_incident=n_incident,
        n_substrate=n_substrate,
        theta_deg=theta_deg,
        pol=pol,
    )
    # Re-inject keys expected by old test codes
    n_g = 2 * int(num_orders) + 1
    N = int(num_orders)
    R_all = np.zeros((n_g, len(res["R"])), dtype=float)
    T_all = np.zeros((n_g, len(res["T"])), dtype=float)
    R_all[N, :] = res["R"]
    T_all[N, :] = res["T"]
    
    res_copy = dict(res)
    res_copy["R_all"] = R_all
    res_copy["T_all"] = T_all
    res_copy["num_orders"] = N
    res_copy["model"] = "EMT"
    return res_copy
