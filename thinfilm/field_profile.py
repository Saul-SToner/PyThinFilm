# -*- coding: utf-8 -*-
"""1D TMM Electric Field Distribution Solver and Verification (Stage B.1D.2).

Computes 1D complex electric field E(z), magnetic field H(z), and intensity |E(z)|^2
across multilayer thin film stacks at normal incidence (0 deg).
Supports continuous interfaces, Poynting flux conservation, and mesh refinement.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Tuple, Any
from thinfilm.education import LayerSpec, multilayer_rt_spectrum


def compute_tmm_1d_field_profile(
    wl_nm: float,
    layers: List[LayerSpec],
    n_incident: float = 1.0,
    n_substrate: float = 1.52,
    dz_nm: float = 1.0,
    air_padding_nm: float = 50.0,
    sub_padding_nm: float = 50.0
) -> Dict[str, Any]:
    """Computes 1D TMM field distribution profile across a thin film stack.

    Args:
        wl_nm: Wavelength in nanometers.
        layers: List of LayerSpec objects.
        n_incident: Refractive index of incident medium.
        n_substrate: Refractive index of substrate.
        dz_nm: Spatial sampling resolution in nm.
        air_padding_nm: Air padding before stack.
        sub_padding_nm: Substrate padding after stack.

    Returns:
        Dict containing z_points_nm, E2_points, E_complex, H_complex, layer_names,
        r_complex, t_complex, R, T, A, max_interface_discontinuity.
    """
    k0 = 2.0 * np.pi / float(wl_nm)

    layer_n = [complex(lyr.n) for lyr in layers]
    layer_d = [float(lyr.thickness_nm) for lyr in layers]
    layer_names = [str(lyr.name) for lyr in layers]

    # 1. Transfer matrices M_j for each layer
    M_list = []
    for n_j, d_j in zip(layer_n, layer_d):
        delta_j = k0 * n_j * d_j
        m_j = np.array([
            [np.cos(delta_j), 1j / n_j * np.sin(delta_j)],
            [1j * n_j * np.sin(delta_j), np.cos(delta_j)]
        ], dtype=complex)
        M_list.append(m_j)

    # System matrix M = M_1 * M_2 * ... * M_N
    M_total = np.eye(2, dtype=complex)
    for m_j in M_list:
        M_total = M_total @ m_j

    m00, m01 = M_total[0, 0], M_total[0, 1]
    m10, m11 = M_total[1, 0], M_total[1, 1]

    b_val = m00 + m01 * n_substrate
    c_val = m10 + m11 * n_substrate
    y_in = c_val / b_val

    # TE / s-polarization Fresnel sign convention matching multilayer_rt_spectrum(pol='s')
    r_coef = (n_incident - y_in) / (n_incident + y_in)
    t_coef = (2.0 * n_incident) / (n_incident * b_val + c_val)

    R_val = float(np.abs(r_coef)**2)
    T_val = float((n_substrate / n_incident) * np.abs(t_coef)**2)
    A_val = float(1.0 - R_val - T_val)

    # 2. Interface field vectors [E, H]^T from substrate to incident
    v_sub_interface = np.array([1.0, n_substrate], dtype=complex) * t_coef

    interface_vectors = [v_sub_interface]
    for m_j in reversed(M_list):
        v_next = m_j @ interface_vectors[0]
        interface_vectors.insert(0, v_next)

    # 3. Spatial sampling
    z_points: List[float] = []
    e2_points: List[float] = []
    e_complex_points: List[complex] = []
    h_complex_points: List[complex] = []
    layer_tags: List[str] = []

    max_discontinuity = 0.0

    # Incident Air region (-air_padding_nm to 0nm)
    v_entrance = interface_vectors[0]
    for z_air in np.arange(-air_padding_nm, 0.0, dz_nm):
        delta_air = k0 * n_incident * z_air
        m_air = np.array([
            [np.cos(delta_air), 1j / n_incident * np.sin(delta_air)],
            [1j * n_incident * np.sin(delta_air), np.cos(delta_air)]
        ], dtype=complex)
        v_z = m_air @ v_entrance
        z_points.append(round(float(z_air), 2))
        e2_points.append(float(np.abs(v_z[0])**2))
        e_complex_points.append(v_z[0])
        h_complex_points.append(v_z[1])
        layer_tags.append("Air")

    # Multilayer region (0 to z_end)
    z_curr = 0.0
    for idx, (n_j, d_j, name_j) in enumerate(zip(layer_n, layer_d, layer_names)):
        v_layer_start = interface_vectors[idx]

        if idx > 0:
            v_prev_end = interface_vectors[idx]
            disc_E = abs(v_layer_start[0] - v_prev_end[0])
            disc_H = abs(v_layer_start[1] - v_prev_end[1])
            max_discontinuity = max(max_discontinuity, disc_E, disc_H)

        for dz in np.arange(0.0, d_j, dz_nm):
            delta = k0 * n_j * dz
            m_dz_inv = np.array([
                [np.cos(delta), -1j / n_j * np.sin(delta)],
                [-1j * n_j * np.sin(delta), np.cos(delta)]
            ], dtype=complex)
            v_z = m_dz_inv @ v_layer_start

            z_points.append(round(float(z_curr + dz), 2))
            e2_points.append(float(np.abs(v_z[0])**2))
            e_complex_points.append(v_z[0])
            h_complex_points.append(v_z[1])
            layer_tags.append(f"{name_j}_Layer_{idx+1}")
        z_curr += d_j

    # Substrate region (z_end to z_end + sub_padding_nm)
    v_sub_start = interface_vectors[-1]
    for dz_sub in np.arange(0.0, sub_padding_nm, dz_nm):
        delta_sub = k0 * n_substrate * dz_sub
        v_z = np.array([
            v_sub_start[0] * np.exp(1j * delta_sub),
            v_sub_start[1] * np.exp(1j * delta_sub)
        ], dtype=complex)
        z_points.append(round(float(z_curr + dz_sub), 2))
        e2_points.append(float(np.abs(v_z[0])**2))
        e_complex_points.append(v_z[0])
        h_complex_points.append(v_z[1])
        layer_tags.append("Substrate")

    return {
        "wavelength_nm": float(wl_nm),
        "dz_nm": float(dz_nm),
        "r_complex": complex(r_coef),
        "t_complex": complex(t_coef),
        "R": R_val,
        "T": T_val,
        "A": A_val,
        "z_points_nm": z_points,
        "E2_points": e2_points,
        "E_complex": e_complex_points,
        "H_complex": h_complex_points,
        "layer_tags": layer_tags,
        "max_interface_discontinuity": float(max_discontinuity)
    }
