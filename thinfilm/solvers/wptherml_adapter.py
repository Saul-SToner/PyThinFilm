from __future__ import annotations

from typing import Any

import contextlib
import io

from .registry import solver_status


def status() -> dict[str, Any]:
    return solver_status("wptherml")


def build_multilayer(*, materials: list[str], thickness_m: list[float], wavelength_range_m: tuple[float, float, int], temperature_k: float = 300.0, cooling: bool = False) -> Any:
    """Create a WPTherml multilayer model without importing it eagerly."""
    if not status()["available"]:
        raise RuntimeError("WPTherml is not installed; install the optional thermal backend")
    from wptherml.em import TmmDriver

    structure = {
        "material_list": materials,
        "thickness_list": thickness_m,
        "wavelength_list": list(wavelength_range_m),
        "temperature": float(temperature_k),
    }
    if cooling:
        structure["cooling"] = True
    # Upstream prints a non-ASCII status line; keep the adapter quiet so a
    # Windows GBK console cannot turn a valid computation into an exception.
    with contextlib.redirect_stdout(io.StringIO()):
        return TmmDriver(structure)


def spectrum(*, materials: list[str], thickness_m: list[float], wavelength_range_m: tuple[float, float, int], temperature_k: float = 300.0) -> dict[str, Any]:
    model = build_multilayer(materials=materials, thickness_m=thickness_m, wavelength_range_m=wavelength_range_m, temperature_k=temperature_k)
    return {
        "solver": "wptherml",
        "wavelength_m": model.wavelength_array.tolist(),
        "R": model.reflectivity_array.tolist(),
        "T": model.transmissivity_array.tolist(),
        "A": model.emissivity_array.tolist(),
        "temperature_k": float(temperature_k),
    }
