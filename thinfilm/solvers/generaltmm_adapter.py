from __future__ import annotations

from typing import Any

import numpy as np

from .registry import solver_status


def status() -> dict[str, Any]:
    return solver_status("generaltmm")


def solve_interface(*, wavelength_nm: float, n_incident: complex, n_layer: complex, n_substrate: complex, thickness_nm: float, beta: float = 0.0) -> dict[str, Any]:
    """Evaluate a planar interface/film with GeneralTmm when installed."""
    if not status()["available"]:
        raise RuntimeError("GeneralTmm is not installed; install the optional interface backend")
    from GeneralTmm import Material, Tmm

    solver = Tmm(wl=float(wavelength_nm) * 1e-9, beta=float(beta))
    solver.AddIsotropicLayer(float("inf"), Material.Static(n_incident))
    solver.AddIsotropicLayer(float(thickness_nm) * 1e-9, Material.Static(n_layer))
    solver.AddIsotropicLayer(float("inf"), Material.Static(n_substrate))
    result = solver.Sweep("beta", np.asarray([float(beta)], dtype=float))
    return {
        "solver": "generaltmm",
        "wavelength_nm": float(wavelength_nm),
        "beta": float(beta),
        "R_p": np.asarray(result["R11"]).tolist(),
        "R_s": np.asarray(result["R22"]).tolist(),
        "T_p": np.asarray(result["T31"]).tolist(),
        "T_s": np.asarray(result["T42"]).tolist(),
    }


def sweep_interface(*, wavelengths_nm: list[float], n_incident: complex = 1.5, n_layer: complex = 2.0, n_substrate: complex = 1.0, thickness_nm: float = 100.0, beta: float = 0.0) -> dict[str, Any]:
    rows = [solve_interface(wavelength_nm=float(wavelength), n_incident=n_incident, n_layer=n_layer, n_substrate=n_substrate, thickness_nm=thickness_nm, beta=beta) for wavelength in wavelengths_nm]
    return {
        "solver": "generaltmm",
        "wavelength_nm": [row["wavelength_nm"] for row in rows],
        "R": [row["R_p"] for row in rows],
        "T": [row["T_p"] for row in rows],
        "A": [1.0 - float(row["R_p"][0] if isinstance(row["R_p"], list) else row["R_p"]) - float(row["T_p"][0] if isinstance(row["T_p"], list) else row["T_p"]) for row in rows],
        "beta": float(beta),
        "thickness_nm": float(thickness_nm),
    }


def sweep_multilayer(*, wavelengths_nm: list[float], n_incident: complex, layer_indices: list[complex], layer_thickness_nm: list[float], n_substrate: complex, beta: float = 0.0) -> dict[str, Any]:
    """Compute a material-resolved isotropic multilayer spectrum."""
    if len(layer_indices) != len(layer_thickness_nm):
        raise ValueError("layer_indices and layer_thickness_nm must have equal length")
    if not status()["available"]:
        raise RuntimeError("GeneralTmm is not installed; install the optional interface backend")
    from GeneralTmm import Material, Tmm

    r_values: list[float] = []
    t_values: list[float] = []
    r_s_values: list[float] = []
    t_s_values: list[float] = []
    phase_p_values: list[float] = []
    phase_s_values: list[float] = []
    for wavelength_nm in wavelengths_nm:
        solver = Tmm(wl=float(wavelength_nm) * 1e-9, beta=float(beta))
        solver.AddIsotropicLayer(float("inf"), Material.Static(n_incident))
        for index, thickness_nm in zip(layer_indices, layer_thickness_nm):
            solver.AddIsotropicLayer(float(thickness_nm) * 1e-9, Material.Static(index))
        solver.AddIsotropicLayer(float("inf"), Material.Static(n_substrate))
        result = solver.Sweep("beta", np.asarray([float(beta)], dtype=float))
        r_values.append(float(np.asarray(result["R11"]).reshape(-1)[0]))
        t_values.append(float(np.asarray(result["T31"]).reshape(-1)[0]))
        r_s_values.append(float(np.asarray(result["R22"]).reshape(-1)[0]))
        t_s_values.append(float(np.asarray(result["T42"]).reshape(-1)[0]))
        phase_p_values.append(float(np.angle(complex(np.asarray(result["r11"]).reshape(-1)[0]), deg=True)))
        phase_s_values.append(float(np.angle(complex(np.asarray(result["r22"]).reshape(-1)[0]), deg=True)))
    return {
        "solver": "generaltmm",
        "wavelength_nm": [float(value) for value in wavelengths_nm],
        "R": r_values,
        "T": t_values,
        "A": [1.0 - r - t for r, t in zip(r_values, t_values)],
        "R_s": r_s_values,
        "T_s": t_s_values,
        "A_s": [1.0 - r - t for r, t in zip(r_s_values, t_s_values)],
        "phase_p_deg": phase_p_values,
        "phase_s_deg": phase_s_values,
        "beta": float(beta),
        "layer_count": len(layer_indices),
        "layer_thickness_nm": [float(value) for value in layer_thickness_nm],
    }


def multilayer_field_comparison(
    *,
    spectrum: dict[str, Any],
    n_incident: complex,
    layer_indices: list[complex],
    layer_thickness_nm: list[float],
    n_substrate: complex,
    beta: float = 0.0,
    polarization: str = "p",
    points: int = 601,
) -> dict[str, Any]:
    """Compare the real p-polarized electric-field profile on and off resonance."""
    if len(layer_indices) != len(layer_thickness_nm) or not layer_indices:
        raise ValueError("A non-empty, length-matched multilayer is required")
    if points < 101:
        raise ValueError("At least 101 field samples are required")
    wavelengths = np.asarray(spectrum["wavelength_nm"], dtype=float)
    if polarization not in {"p", "s"}:
        raise ValueError("polarization must be 'p' or 's'")
    channel_suffix = "" if polarization == "p" else "_s"
    reflectance = np.asarray(spectrum[f"R{channel_suffix}"], dtype=float)
    if wavelengths.size < 2 or wavelengths.size != reflectance.size:
        raise ValueError("A wavelength spectrum with at least two R samples is required")
    resonance_index = int(np.argmin(reflectance))
    reference_index = int(np.argmax(reflectance))
    resonance_nm = float(wavelengths[resonance_index])
    reference_nm = float(wavelengths[reference_index])
    total_nm = float(sum(layer_thickness_nm))
    padding_nm = max(40.0, min(100.0, 0.12 * total_nm))
    depth_nm = np.linspace(-padding_nm, total_nm + padding_nm, points)

    from GeneralTmm import Material, Tmm

    def build_solver(wavelength_nm: float) -> Any:
        solver = Tmm(wl=wavelength_nm * 1e-9, beta=float(beta))
        solver.AddIsotropicLayer(float("inf"), Material.Static(n_incident))
        for index, thickness_nm in zip(layer_indices, layer_thickness_nm):
            solver.AddIsotropicLayer(thickness_nm * 1e-9, Material.Static(index))
        solver.AddIsotropicLayer(float("inf"), Material.Static(n_substrate))
        return solver

    profiles: list[dict[str, Any]] = []
    profile_arrays: dict[str, np.ndarray] = {}
    for key, label, wavelength_nm in (
        ("resonance", "共振波长", resonance_nm),
        ("reference", "非共振对照", reference_nm),
    ):
        solver = build_solver(wavelength_nm)
        polarization_vector = np.asarray([1.0, 0.0] if polarization == "p" else [0.0, 1.0], dtype=float)
        electric, _ = solver.CalcFields1D(depth_nm * 1e-9, polarization_vector)
        intensity = np.sum(np.abs(np.asarray(electric)) ** 2, axis=1).real
        profile_arrays[key] = intensity
        profiles.append({
            "key": key,
            "label": label,
            "wavelength_nm": wavelength_nm,
            "depth_nm": depth_nm.tolist(),
            "electric_intensity": intensity.tolist(),
        })

    boundaries_nm = np.concatenate(([0.0], np.cumsum(np.asarray(layer_thickness_nm, dtype=float))))
    structure_mask = (depth_nm >= 0.0) & (depth_nm <= total_nm)
    interface_nm = float(layer_thickness_nm[0])
    interface_index = int(np.argmin(np.abs(depth_nm - interface_nm)))
    resonance_inside = profile_arrays["resonance"][structure_mask]
    reference_inside = profile_arrays["reference"][structure_mask]
    inside_depth = depth_nm[structure_mask]
    resonance_peak_index = int(np.argmax(resonance_inside))

    # Tangential E must remain continuous. Sample immediately to either side
    # of every internal boundary and report the largest relative mismatch.
    continuity_errors: list[float] = []
    epsilon_nm = 1e-5
    continuity_solver = build_solver(resonance_nm)
    for boundary_nm in boundaries_nm[1:-1]:
        electric, _ = continuity_solver.CalcFields1D(
            np.asarray([boundary_nm - epsilon_nm, boundary_nm + epsilon_nm]) * 1e-9,
            np.asarray([1.0, 0.0] if polarization == "p" else [0.0, 1.0], dtype=float),
        )
        tangential_left = np.asarray(electric[0])[1:]
        tangential_right = np.asarray(electric[1])[1:]
        scale = max(float(np.linalg.norm(tangential_left)), float(np.linalg.norm(tangential_right)), 1e-12)
        continuity_errors.append(float(np.linalg.norm(tangential_left - tangential_right) / scale))

    resonance_r = float(np.asarray(spectrum[f"R{channel_suffix}"])[resonance_index])
    resonance_t = float(np.asarray(spectrum[f"T{channel_suffix}"])[resonance_index])
    resonance_a = float(np.asarray(spectrum[f"A{channel_suffix}"])[resonance_index])
    return {
        "polarization": polarization,
        "normalization": "incident electric-field intensity",
        "selection_basis": f"minimum {polarization}-polarized reflectance in the requested wavelength scan",
        "resonance_wavelength_nm": resonance_nm,
        "reference_wavelength_nm": reference_nm,
        "depth_unit": "nm",
        "field_quantity": "|E|^2 / |E_inc|^2",
        "interface_nm": interface_nm,
        "layer_boundaries_nm": boundaries_nm.tolist(),
        "profiles": profiles,
        "metrics": {
            "resonance_R": resonance_r,
            "resonance_T": resonance_t,
            "resonance_A": resonance_a,
            "energy_deviation": abs(resonance_r + resonance_t + resonance_a - 1.0),
            "resonance_peak_inside": float(resonance_inside[resonance_peak_index]),
            "resonance_peak_depth_nm": float(inside_depth[resonance_peak_index]),
            "resonance_interface_intensity": float(profile_arrays["resonance"][interface_index]),
            "reference_peak_inside": float(np.max(reference_inside)),
            "interface_enhancement_ratio": float(profile_arrays["resonance"][interface_index] / max(profile_arrays["reference"][interface_index], 1e-15)),
        },
        "validation": {
            "energy_conservation_passed": abs(resonance_r + resonance_t + resonance_a - 1.0) <= 1e-8,
            "max_tangential_e_relative_jump": max(continuity_errors, default=0.0),
            "tangential_e_continuity_passed": max(continuity_errors, default=0.0) <= 1e-4,
        },
    }
