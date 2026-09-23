"""Field and phase evidence for an arbitrary real-material thin-film stack."""

from __future__ import annotations

from typing import Any

import numpy as np

from .design_models import StackDesign
from .materials import canonical_material_name, material_complex_index


def _index(material_id: str, wavelength_nm: float, policy: str) -> complex:
    return complex(
        np.asarray(
            material_complex_index(
                canonical_material_name(material_id),
                wavelength_nm,
                out_of_range_policy=policy,
            )
        ).item()
    )


def _cosine(n0: complex, n: complex, sin_theta0: float) -> complex:
    value = np.sqrt(1.0 - (n0 * sin_theta0 / n) ** 2 + 0j)
    return -value if np.real(value) < 0 else value


def _admittance(n: complex, cosine: complex, polarization: str) -> complex:
    return n * cosine if polarization == "s" else cosine / n


def compute_field_profile(design: StackDesign, wavelength_nm: float) -> dict[str, Any]:
    """Compute a bounded-size 1D field profile at one probe wavelength."""
    enabled = [layer for layer in design.layers if layer.enabled]
    policy = design.out_of_range_policy
    n0 = np.conj(_index(design.incident_material_id, wavelength_nm, policy))
    ns = np.conj(_index(design.substrate_material_id, wavelength_nm, policy))
    sin_theta0 = float(np.sin(np.deg2rad(design.angle_deg)))
    cos0, coss = _cosine(n0, n0, sin_theta0), _cosine(n0, ns, sin_theta0)
    q0 = _admittance(n0, cos0, design.polarization)
    qs = _admittance(ns, coss, design.polarization)
    k0 = 2.0 * np.pi / wavelength_nm

    layer_values: list[tuple[Any, complex, complex, complex]] = []
    matrices: list[np.ndarray] = []
    for layer in enabled:
        n_layer = np.conj(_index(layer.material_id, wavelength_nm, policy))
        cosine = _cosine(n0, n_layer, sin_theta0)
        q_layer = _admittance(n_layer, cosine, design.polarization)
        delta = k0 * n_layer * cosine * layer.thickness_nm
        matrix = np.asarray(
            [
                [np.cos(delta), 1j * np.sin(delta) / q_layer],
                [1j * q_layer * np.sin(delta), np.cos(delta)],
            ],
            dtype=complex,
        )
        layer_values.append((layer, n_layer, cosine, q_layer))
        matrices.append(matrix)

    total_matrix = np.eye(2, dtype=complex)
    for matrix in matrices:
        total_matrix = total_matrix @ matrix
    b_value = total_matrix[0, 0] + total_matrix[0, 1] * qs
    c_value = total_matrix[1, 0] + total_matrix[1, 1] * qs
    y_in = c_value / b_value
    r_coef = (q0 - y_in) / (q0 + y_in)
    t_coef = 2.0 * q0 / (q0 * b_value + c_value)

    interface_vectors = [np.asarray([t_coef, qs * t_coef], dtype=complex)]
    for matrix in reversed(matrices):
        interface_vectors.insert(0, matrix @ interface_vectors[0])

    total_thickness = float(sum(layer.thickness_nm for layer in enabled))
    padding = float(np.clip(total_thickness * 0.08, 30.0, 100.0))
    target_step = max(0.5, total_thickness / 1400.0)
    z_values: list[float] = []
    e2_values: list[float] = []
    regions: list[str] = []

    entrance = interface_vectors[0]
    for z_value in np.linspace(-padding, 0.0, 61, endpoint=False):
        delta = k0 * n0 * cos0 * z_value
        propagation = np.asarray(
            [[np.cos(delta), 1j * np.sin(delta) / q0], [1j * q0 * np.sin(delta), np.cos(delta)]],
            dtype=complex,
        )
        field = propagation @ entrance
        z_values.append(float(z_value))
        e2_values.append(float(abs(field[0]) ** 2))
        regions.append("incident")

    boundaries: list[dict[str, Any]] = []
    cursor = 0.0
    layer_phase: list[dict[str, Any]] = []
    for index, (layer, n_layer, cosine, q_layer) in enumerate(layer_values):
        count = max(3, int(np.ceil(layer.thickness_nm / target_step)))
        start = cursor
        for distance in np.linspace(0.0, layer.thickness_nm, count, endpoint=False):
            delta = k0 * n_layer * cosine * distance
            inverse = np.asarray(
                [[np.cos(delta), -1j * np.sin(delta) / q_layer], [-1j * q_layer * np.sin(delta), np.cos(delta)]],
                dtype=complex,
            )
            field = inverse @ interface_vectors[index]
            z_values.append(float(cursor + distance))
            e2_values.append(float(abs(field[0]) ** 2))
            regions.append(layer.id)
        cursor += layer.thickness_nm
        optical_thickness = float(np.real(np.conj(n_layer) * cosine) * layer.thickness_nm)
        one_way_phase = 360.0 * optical_thickness / wavelength_nm
        boundaries.append(
            {
                "layer_id": layer.id,
                "material_id": canonical_material_name(layer.material_id),
                "start_nm": start,
                "stop_nm": cursor,
            }
        )
        layer_phase.append(
            {
                "layer_id": layer.id,
                "material_id": canonical_material_name(layer.material_id),
                "optical_thickness_nm": optical_thickness,
                "one_way_phase_deg": one_way_phase,
                "round_trip_phase_deg": 2.0 * one_way_phase,
            }
        )

    substrate_start = interface_vectors[-1][0]
    for distance in np.linspace(0.0, padding, 61):
        field = substrate_start * np.exp(-1j * k0 * ns * coss * distance)
        z_values.append(float(cursor + distance))
        e2_values.append(float(abs(field) ** 2))
        regions.append("substrate")

    e2_array = np.asarray(e2_values, dtype=float)
    peak_index = int(np.argmax(e2_array))
    transmittance = float(np.real(qs / q0) * abs(t_coef) ** 2)
    reflectance = float(abs(r_coef) ** 2)
    return {
        "wavelength_nm": wavelength_nm,
        "z_nm": z_values,
        "E2": e2_values,
        "regions": regions,
        "boundaries": boundaries,
        "peak_E2": float(e2_array[peak_index]),
        "peak_z_nm": float(z_values[peak_index]),
        "R": reflectance,
        "T": transmittance,
        "A": float(1.0 - reflectance - transmittance),
        "layer_phase": layer_phase,
    }

def build_phase_evidence(
    design: StackDesign,
    wavelengths_nm: np.ndarray,
    r_complex: np.ndarray,
    t_complex: np.ndarray,
    field: dict[str, Any],
) -> dict[str, Any]:
    reflection_wrapped = np.degrees(np.angle(np.conj(r_complex)))
    transmission_wrapped = np.degrees(np.angle(np.conj(t_complex)))
    reflection_unwrapped = np.degrees(np.unwrap(np.angle(np.conj(r_complex))))
    probe_index = int(np.argmin(np.abs(wavelengths_nm - float(field["wavelength_nm"]))))
    probe_r = float(field["R"])
    if probe_r <= 0.1:
        interpretation = "该波长处整体反射较弱，多个界面反射分量主要表现为相消叠加。"
    elif probe_r >= 0.9:
        interpretation = "该波长处整体反射很强，多个界面反射分量主要表现为相长叠加。"
    else:
        interpretation = "该波长处反射分量仅部分抵消，需要结合层内场强和各层相位厚度判断。"
    return {
        "wavelength_nm": wavelengths_nm,
        "reflection_phase_deg": reflection_wrapped,
        "reflection_phase_unwrapped_deg": reflection_unwrapped,
        "transmission_phase_deg": transmission_wrapped,
        "probe": {
            "wavelength_nm": float(wavelengths_nm[probe_index]),
            "reflection_phase_deg": float(reflection_wrapped[probe_index]),
            "transmission_phase_deg": float(transmission_wrapped[probe_index]),
        },
        "layer_phase": field["layer_phase"],
        "explanations": [
            interpretation,
            "单层相位厚度表示光在该层单程传播积累的相位；约90°对应四分之一波长光学厚度。",
            f"场强峰值 |E|²={field['peak_E2']:.3f}，位置 z={field['peak_z_nm']:.2f} nm。",
        ],
    }
