"""Forward TMM solver for arbitrary, dispersive material stacks."""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

from .design_models import StackDesign
from .materials import canonical_material_name, material_complex_index, material_display_info
from .experiment_evaluation import evaluate_experiment
from .stack_insights import build_phase_evidence, compute_field_profile


MAX_LAYERS = 200
MAX_SPECTRUM_POINTS = 5000


def _validate_design(design: StackDesign) -> tuple[StackDesign, list[str]]:
    catalog = {row["id"]: row for row in material_display_info()}
    material_ids = [
        design.incident_material_id,
        design.substrate_material_id,
        *(layer.material_id for layer in design.layers),
    ]
    unknown = sorted({item for item in material_ids if canonical_material_name(item) not in catalog})
    if unknown:
        raise ValueError(f"Unknown material_id(s): {', '.join(unknown)}")
    if not design.layers:
        raise ValueError("At least one layer is required.")
    if len(design.layers) > MAX_LAYERS:
        raise ValueError(f"A design may contain at most {MAX_LAYERS} layers.")
    if len({layer.id for layer in design.layers}) != len(design.layers):
        raise ValueError("Layer ids must be unique.")
    for layer in design.layers:
        if not layer.material_id:
            raise ValueError(f"Layer '{layer.id}' has no material_id.")
        if not math.isfinite(layer.thickness_nm) or layer.thickness_nm <= 0:
            raise ValueError(f"Layer '{layer.id}' thickness_nm must be a positive finite number.")
    spectrum = design.spectrum
    if not math.isfinite(spectrum.start_nm) or not math.isfinite(spectrum.stop_nm):
        raise ValueError("Spectrum limits must be finite.")
    if spectrum.start_nm <= 0 or spectrum.stop_nm <= spectrum.start_nm:
        raise ValueError("Spectrum requires 0 < start_nm < stop_nm.")
    if spectrum.points < 2 or spectrum.points > MAX_SPECTRUM_POINTS:
        raise ValueError(f"Spectrum points must be between 2 and {MAX_SPECTRUM_POINTS}.")
    if not math.isfinite(design.angle_deg) or not 0 <= design.angle_deg < 90:
        raise ValueError("angle_deg must be in [0, 90).")
    if design.polarization not in {"s", "p"}:
        raise ValueError("polarization must be 's' or 'p'.")
    if design.out_of_range_policy not in {"error", "clip"}:
        raise ValueError("out_of_range_policy must be 'error' or 'clip'.")

    warnings: list[str] = []
    for material_id in dict.fromkeys(material_ids):
        info = catalog[canonical_material_name(material_id)]
        lo, hi = float(info["lambda_min_nm"]), float(info["lambda_max_nm"])
        if spectrum.start_nm < lo or spectrum.stop_nm > hi:
            message = (
                f"{canonical_material_name(material_id)} valid range is {lo:g}-{hi:g} nm; "
                f"requested {spectrum.start_nm:g}-{spectrum.stop_nm:g} nm."
            )
            if design.out_of_range_policy == "error":
                raise ValueError(message)
            warnings.append(message + " Values outside the range were clipped.")
    return design, warnings


def _index(material_id: str, wavelengths_nm: np.ndarray, policy: str) -> np.ndarray:
    return np.asarray(
        material_complex_index(
            canonical_material_name(material_id),
            wavelengths_nm,
            out_of_range_policy=policy,
        ),
        dtype=complex,
    )


def _linear_crossing(x1: float, y1: float, x2: float, y2: float, level: float) -> float:
    if abs(y2 - y1) < 1e-15:
        return float(x1)
    return float(x1 + (level - y1) * (x2 - x1) / (y2 - y1))


def _largest_threshold_band(
    wavelengths: np.ndarray,
    values: np.ndarray,
    threshold: float,
) -> dict[str, Any] | None:
    indices = np.flatnonzero(values >= threshold)
    if indices.size == 0:
        return None
    groups = np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1)
    group = max(groups, key=lambda item: float(wavelengths[item[-1]] - wavelengths[item[0]]))
    start, stop = int(group[0]), int(group[-1])
    left = float(wavelengths[start])
    right = float(wavelengths[stop])
    if start > 0:
        left = _linear_crossing(
            float(wavelengths[start - 1]), float(values[start - 1]),
            float(wavelengths[start]), float(values[start]), threshold,
        )
    if stop < len(values) - 1:
        right = _linear_crossing(
            float(wavelengths[stop]), float(values[stop]),
            float(wavelengths[stop + 1]), float(values[stop + 1]), threshold,
        )
    return {
        "threshold": threshold,
        "start_nm": left,
        "stop_nm": right,
        "width_nm": max(0.0, right - left),
    }


def _dominant_peak_linewidth(wavelengths: np.ndarray, values: np.ndarray) -> dict[str, Any]:
    peak_index = int(np.argmax(values))
    peak_value = float(values[peak_index])
    peak_wavelength = float(wavelengths[peak_index])
    edge_count = max(1, len(values) // 10)
    background = float(min(np.min(values[:edge_count]), np.min(values[-edge_count:])))
    half_level = background + 0.5 * (peak_value - background)
    left_candidates = np.flatnonzero(values[:peak_index] <= half_level)
    right_candidates = np.flatnonzero(values[peak_index + 1 :] <= half_level)
    if left_candidates.size == 0 or right_candidates.size == 0 or peak_value - background <= 1e-8:
        return {
            "status": "not_available",
            "peak_wavelength_nm": peak_wavelength,
            "peak_value": peak_value,
            "background": background,
            "half_level": half_level,
            "fwhm_nm": None,
            "q_factor": None,
        }
    left_index = int(left_candidates[-1])
    right_index = int(right_candidates[0] + peak_index + 1)
    left = _linear_crossing(
        float(wavelengths[left_index]), float(values[left_index]),
        float(wavelengths[left_index + 1]), float(values[left_index + 1]), half_level,
    )
    right = _linear_crossing(
        float(wavelengths[right_index - 1]), float(values[right_index - 1]),
        float(wavelengths[right_index]), float(values[right_index]), half_level,
    )
    width = right - left
    return {
        "status": "available" if width > 0 else "not_available",
        "peak_wavelength_nm": peak_wavelength,
        "peak_value": peak_value,
        "background": background,
        "half_level": half_level,
        "left_half_nm": left if width > 0 else None,
        "right_half_nm": right if width > 0 else None,
        "fwhm_nm": width if width > 0 else None,
        "q_factor": peak_wavelength / width if width > 0 else None,
    }


def analyze_spectrum(
    wavelengths: np.ndarray,
    reflectance: np.ndarray,
    transmittance: np.ndarray,
    absorption: np.ndarray,
) -> dict[str, Any]:
    """Return general-purpose, measurement-like metrics for the V1 lab UI."""
    center_nm = 0.5 * (float(wavelengths[0]) + float(wavelengths[-1]))
    center_index = int(np.argmin(np.abs(wavelengths - center_nm)))

    def extrema(values: np.ndarray) -> dict[str, float]:
        min_index, max_index = int(np.argmin(values)), int(np.argmax(values))
        return {
            "minimum": float(values[min_index]),
            "minimum_wavelength_nm": float(wavelengths[min_index]),
            "maximum": float(values[max_index]),
            "maximum_wavelength_nm": float(wavelengths[max_index]),
            "mean": float(np.mean(values)),
            "at_center": float(values[center_index]),
        }

    return {
        "center_wavelength_nm": float(wavelengths[center_index]),
        "R": extrema(reflectance),
        "T": extrema(transmittance),
        "A": extrema(absorption),
        "high_reflection_band": _largest_threshold_band(wavelengths, reflectance, 0.9),
        "transmission_peak_linewidth": _dominant_peak_linewidth(wavelengths, transmittance),
    }


def simulate_custom_stack(payload: Mapping[str, Any] | StackDesign) -> dict[str, Any]:
    """Simulate an arbitrary ordered layer array with real n/k dispersion.

    The input may be a :class:`StackDesign` or a JSON-like mapping.  Returned
    arrays are NumPy arrays so callers can retain precision or serialise them.
    """
    raw_payload: Mapping[str, Any] = {} if isinstance(payload, StackDesign) else payload
    experiment_task_id = str(raw_payload.get("experiment_task_id") or "") or None
    raw_probe = raw_payload.get("probe_wavelength_nm")
    design = payload if isinstance(payload, StackDesign) else StackDesign.from_mapping(payload)
    design, warning_messages = _validate_design(design)
    probe_wavelength_nm = (
        float(raw_probe)
        if raw_probe is not None
        else 0.5 * (design.spectrum.start_nm + design.spectrum.stop_nm)
    )
    if not math.isfinite(probe_wavelength_nm) or not design.spectrum.start_nm <= probe_wavelength_nm <= design.spectrum.stop_nm:
        raise ValueError("probe_wavelength_nm must be finite and inside the spectrum range.")
    wavelengths = np.linspace(
        design.spectrum.start_nm,
        design.spectrum.stop_nm,
        design.spectrum.points,
        dtype=float,
    )
    policy = design.out_of_range_policy
    n0 = np.conj(_index(design.incident_material_id, wavelengths, policy))
    ns = np.conj(_index(design.substrate_material_id, wavelengths, policy))

    sin_theta0 = np.sin(np.deg2rad(design.angle_deg))
    cos_theta0 = np.sqrt(1.0 - (n0 * sin_theta0 / n0) ** 2 + 0j)
    cos_thetas = np.sqrt(1.0 - (n0 * sin_theta0 / ns) ** 2 + 0j)
    cos_theta0 = np.where(np.real(cos_theta0) < 0, -cos_theta0, cos_theta0)
    cos_thetas = np.where(np.real(cos_thetas) < 0, -cos_thetas, cos_thetas)
    if design.polarization == "s":
        q0, qs = n0 * cos_theta0, ns * cos_thetas
    else:
        q0, qs = cos_theta0 / n0, cos_thetas / ns

    matrix = (
        np.ones_like(wavelengths, dtype=complex),
        np.zeros_like(wavelengths, dtype=complex),
        np.zeros_like(wavelengths, dtype=complex),
        np.ones_like(wavelengths, dtype=complex),
    )
    resolved_layers: list[dict[str, Any]] = []
    any_lossy = np.zeros_like(wavelengths, dtype=bool)
    enabled_layers = [layer for layer in design.layers if layer.enabled]
    for layer in design.layers:
        center_index = _index(layer.material_id, np.asarray([(design.spectrum.start_nm + design.spectrum.stop_nm) / 2]), policy)[0]
        resolved_layers.append(
            {
                "id": layer.id,
                "material_id": canonical_material_name(layer.material_id),
                "thickness_nm": float(layer.thickness_nm),
                "enabled": layer.enabled,
                "n_center": float(np.real(center_index)),
                "k_center": float(np.imag(center_index)),
            }
        )
        if not layer.enabled:
            continue
        n_layer = np.conj(_index(layer.material_id, wavelengths, policy))
        any_lossy |= np.abs(np.imag(n_layer)) > 1e-12
        cos_layer = np.sqrt(1.0 - (n0 * sin_theta0 / n_layer) ** 2 + 0j)
        cos_layer = np.where(np.real(cos_layer) < 0, -cos_layer, cos_layer)
        q_layer = n_layer * cos_layer if design.polarization == "s" else cos_layer / n_layer
        delta = 2.0 * np.pi * n_layer * layer.thickness_nm * 1e-9 * cos_layer / (wavelengths * 1e-9)
        c, s = np.cos(delta), np.sin(delta)
        a00, a01, a10, a11 = c, 1j * s / q_layer, 1j * q_layer * s, c
        m00, m01, m10, m11 = matrix
        matrix = (
            m00 * a00 + m01 * a10,
            m00 * a01 + m01 * a11,
            m10 * a00 + m11 * a10,
            m10 * a01 + m11 * a11,
        )

    m00, m01, m10, m11 = matrix
    b_val, c_val = m00 + m01 * qs, m10 + m11 * qs
    y_in = c_val / b_val
    r_complex = (q0 - y_in) / (q0 + y_in)
    t_complex = 2.0 * q0 / (q0 * b_val + c_val)
    reflectance = np.abs(r_complex) ** 2
    transmittance = np.abs(t_complex) ** 2 * np.real(qs / q0)
    lossless = (
        (np.abs(np.imag(n0)) < 1e-12)
        & (np.abs(np.imag(ns)) < 1e-12)
        & (~any_lossy)
    )
    absorption = np.where(lossless, 0.0, 1.0 - reflectance - transmittance)
    absorption_display = np.maximum(0.0, absorption)
    residue = np.abs(reflectance + transmittance + absorption_display - 1.0)
    metrics = analyze_spectrum(wavelengths, reflectance, transmittance, absorption_display)
    field = compute_field_profile(design, probe_wavelength_nm)
    phase = build_phase_evidence(design, wavelengths, r_complex, t_complex, field)
    evaluation = evaluate_experiment(
        experiment_task_id,
        design,
        wavelengths,
        reflectance,
        transmittance,
        metrics,
    )

    return {
        "design": {
            "incident_material_id": canonical_material_name(design.incident_material_id),
            "substrate_material_id": canonical_material_name(design.substrate_material_id),
            "layers": resolved_layers,
            "spectrum": {
                "start_nm": design.spectrum.start_nm,
                "stop_nm": design.spectrum.stop_nm,
                "points": design.spectrum.points,
            },
            "angle_deg": design.angle_deg,
            "polarization": design.polarization,
            "out_of_range_policy": design.out_of_range_policy,
            "probe_wavelength_nm": probe_wavelength_nm,
            "experiment_task_id": experiment_task_id,
        },
        "wavelength_nm": wavelengths,
        "R": reflectance.astype(float),
        "T": transmittance.astype(float),
        "A": absorption.astype(float),
        "summary": {
            "layer_count": len(enabled_layers),
            "total_thickness_nm": float(sum(layer.thickness_nm for layer in enabled_layers)),
            "max_energy_residue": float(np.max(residue)),
            "mean_R": float(np.mean(reflectance)),
            "mean_T": float(np.mean(transmittance)),
            "mean_A": float(np.mean(absorption_display)),
        },
        "metrics": metrics,
        "field": field,
        "phase": phase,
        "evaluation": evaluation,
        "warnings": warning_messages,
    }
