"""Stable isotropic TMM path for Tamm cases in frozen Windows builds."""

from __future__ import annotations

import numpy as np

from thinfilm.education import LayerSpec, multilayer_rt_spectrum


def _angle(n_incident: complex, beta: float) -> float:
    if abs(n_incident.imag) > 1e-12 or beta >= n_incident.real:
        raise ValueError("The packaged isotropic TMM requires a propagating incident wave")
    return float(np.degrees(np.arcsin(beta / n_incident.real)))


def _spectrum(wavelengths_nm, n_incident, layer_indices, layer_thickness_nm, n_substrate, beta):
    layers = [LayerSpec(str(index), value, thickness) for index, (value, thickness) in enumerate(zip(layer_indices, layer_thickness_nm))]
    theta = _angle(n_incident, beta)
    return {
        pol: multilayer_rt_spectrum(wavelengths_nm, layers, n_incident, n_substrate, theta, pol)
        for pol in ("p", "s")
    }


def sweep_multilayer(*, wavelengths_nm, n_incident, layer_indices, layer_thickness_nm, n_substrate, beta=0.0):
    if len(layer_indices) != len(layer_thickness_nm):
        raise ValueError("layer_indices and layer_thickness_nm must have equal length")
    spectra = _spectrum(wavelengths_nm, n_incident, layer_indices, layer_thickness_nm, n_substrate, beta)
    p, s = spectra["p"], spectra["s"]
    return {
        "solver": "pythinfilm-isotropic-tmm",
        "wavelength_nm": [float(value) for value in wavelengths_nm],
        "R": p["R"].tolist(), "T": p["T"].tolist(), "A": p["A"].tolist(),
        "R_s": s["R"].tolist(), "T_s": s["T"].tolist(), "A_s": s["A"].tolist(),
        # GeneralTmm chooses the opposite reflected-mode phase branch at beta=0.
        "phase_p_deg": np.angle((-1 if beta == 0 else 1) * p["r_complex"], deg=True).tolist(),
        "phase_s_deg": np.angle((-1 if beta == 0 else 1) * s["r_complex"], deg=True).tolist(),
        "beta": float(beta),
        "layer_count": len(layer_indices),
        "layer_thickness_nm": [float(value) for value in layer_thickness_nm],
    }


def sweep_interface(*, wavelengths_nm, n_incident=1.5, n_layer=2.0, n_substrate=1.0, thickness_nm=100.0, beta=0.0):
    result = sweep_multilayer(
        wavelengths_nm=wavelengths_nm, n_incident=n_incident,
        layer_indices=[n_layer], layer_thickness_nm=[thickness_nm],
        n_substrate=n_substrate, beta=beta,
    )
    result["thickness_nm"] = float(thickness_nm)
    return result


def _field(wavelength_nm, depth_nm, n_incident, layer_indices, layer_thickness_nm, n_substrate, beta, polarization):
    theta = _angle(n_incident, beta)
    n0, ns = np.conj(complex(n_incident)), np.conj(complex(n_substrate))
    indices = [np.conj(complex(value)) for value in layer_indices]
    cosines = [np.sqrt(1 - (beta / value) ** 2 + 0j) for value in (n0, *indices, ns)]
    admittances = [value * cosine if polarization == "s" else cosine / value for value, cosine in zip((n0, *indices, ns), cosines)]
    k0 = 2 * np.pi / wavelength_nm
    matrices = []
    for value, cosine, admittance, thickness in zip(indices, cosines[1:-1], admittances[1:-1], layer_thickness_nm):
        phase = k0 * value * cosine * thickness
        matrices.append(np.array([[np.cos(phase), 1j * np.sin(phase) / admittance], [1j * admittance * np.sin(phase), np.cos(phase)]], dtype=complex))
    total = np.eye(2, dtype=complex)
    for matrix in matrices:
        total = total @ matrix
    b, c = total @ np.array([1, admittances[-1]], dtype=complex)
    transmission = 2 * admittances[0] / (admittances[0] * b + c)
    interface = [transmission * np.array([1, admittances[-1]], dtype=complex)]
    for matrix in reversed(matrices):
        interface.insert(0, matrix @ interface[0])

    edges = np.concatenate(([0.0], np.cumsum(layer_thickness_nm)))
    intensity = []
    tangential = []
    for depth in depth_nm:
        if depth < 0:
            region, distance, state = 0, depth, interface[0]
        elif depth >= edges[-1]:
            region, distance, state = len(indices) + 1, depth - edges[-1], interface[-1]
        else:
            region = int(np.searchsorted(edges, depth, side="right"))
            distance, state = depth - edges[region - 1], interface[region - 1]
        n = (n0, *indices, ns)[region]
        q = admittances[region]
        phase = k0 * n * cosines[region] * distance
        inverse = np.array([[np.cos(phase), -1j * np.sin(phase) / q], [-1j * q * np.sin(phase), np.cos(phase)]], dtype=complex)
        electric, magnetic = inverse @ state
        if polarization == "p":
            normal = beta * electric / (n * n)
            tangential.append(magnetic)
            intensity.append(float(abs(magnetic) ** 2 + abs(normal) ** 2))
        else:
            tangential.append(electric)
            intensity.append(float(abs(electric) ** 2))
    return np.asarray(intensity), np.asarray(tangential)


def multilayer_field_comparison(*, spectrum, n_incident, layer_indices, layer_thickness_nm, n_substrate, beta=0.0, polarization="p", points=601):
    if len(layer_indices) != len(layer_thickness_nm) or not layer_indices:
        raise ValueError("A non-empty, length-matched multilayer is required")
    if polarization not in {"p", "s"} or points < 101:
        raise ValueError("Invalid polarization or field sample count")
    suffix = "" if polarization == "p" else "_s"
    wavelengths = np.asarray(spectrum["wavelength_nm"], dtype=float)
    reflectance = np.asarray(spectrum[f"R{suffix}"], dtype=float)
    if wavelengths.size < 2 or wavelengths.size != reflectance.size:
        raise ValueError("A wavelength spectrum with at least two R samples is required")
    resonance_index, reference_index = int(np.argmin(reflectance)), int(np.argmax(reflectance))
    total_nm = float(sum(layer_thickness_nm))
    padding = max(40.0, min(100.0, 0.12 * total_nm))
    depth = np.linspace(-padding, total_nm + padding, points)
    boundaries = np.concatenate(([0.0], np.cumsum(layer_thickness_nm)))
    profiles, arrays = [], {}
    for key, label, index in (("resonance", "共振波长", resonance_index), ("reference", "非共振对照", reference_index)):
        intensity, _ = _field(float(wavelengths[index]), depth, n_incident, layer_indices, layer_thickness_nm, n_substrate, beta, polarization)
        arrays[key] = intensity
        profiles.append({"key": key, "label": label, "wavelength_nm": float(wavelengths[index]), "depth_nm": depth.tolist(), "electric_intensity": intensity.tolist()})
    inside = (depth >= 0) & (depth <= total_nm)
    inside_depth = depth[inside]
    peak_index = int(np.argmax(arrays["resonance"][inside]))
    interface_index = int(np.argmin(abs(depth - layer_thickness_nm[0])))
    jumps = []
    for boundary in boundaries[1:-1]:
        _, fields = _field(float(wavelengths[resonance_index]), np.asarray([boundary - 1e-5, boundary + 1e-5]), n_incident, layer_indices, layer_thickness_nm, n_substrate, beta, polarization)
        jumps.append(float(abs(fields[0] - fields[1]) / max(abs(fields[0]), abs(fields[1]), 1e-12)))
    r, t, a = (float(spectrum[f"{key}{suffix}"][resonance_index]) for key in ("R", "T", "A"))
    return {
        "polarization": polarization,
        "normalization": "incident electric-field intensity",
        "selection_basis": f"minimum {polarization}-polarized reflectance in the requested wavelength scan",
        "resonance_wavelength_nm": float(wavelengths[resonance_index]),
        "reference_wavelength_nm": float(wavelengths[reference_index]),
        "depth_unit": "nm", "field_quantity": "|E|^2 / |E_inc|^2",
        "interface_nm": float(layer_thickness_nm[0]), "layer_boundaries_nm": boundaries.tolist(),
        "profiles": profiles,
        "metrics": {
            "resonance_R": r, "resonance_T": t, "resonance_A": a,
            "energy_deviation": abs(r + t + a - 1.0),
            "resonance_peak_inside": float(arrays["resonance"][inside][peak_index]),
            "resonance_peak_depth_nm": float(inside_depth[peak_index]),
            "resonance_interface_intensity": float(arrays["resonance"][interface_index]),
            "reference_peak_inside": float(np.max(arrays["reference"][inside])),
            "interface_enhancement_ratio": float(arrays["resonance"][interface_index] / max(arrays["reference"][interface_index], 1e-15)),
        },
        "validation": {
            "energy_conservation_passed": abs(r + t + a - 1.0) <= 1e-8,
            "max_tangential_e_relative_jump": max(jumps, default=0.0),
            "tangential_e_continuity_passed": max(jumps, default=0.0) <= 1e-4,
        },
    }
