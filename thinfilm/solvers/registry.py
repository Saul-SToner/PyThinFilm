from __future__ import annotations

import importlib.util
from typing import Any


SPECIALIST_SOLVERS: dict[str, dict[str, Any]] = {
    "rcwa": {
        "package": "rcwa",
        "source": "https://github.com/edmundsj/rcwa",
        "license": "MIT",
        "problems": ["periodic_grating", "photonic_crystal", "guided_grating"],
    },
    "generaltmm": {
        "package": "GeneralTmm",
        "source": "https://github.com/ardiloot/GeneralTmm",
        "license": "MIT",
        "problems": ["tamm_interface", "spp", "anisotropic_multilayer"],
    },
    "wptherml": {
        "package": "wptherml",
        "source": "https://github.com/FoleyLab/wptherml",
        "license": "check-upstream",
        "problems": ["radiative_cooling", "thermal_emission", "photothermal_absorption"],
    },
}


def solver_status(name: str) -> dict[str, Any]:
    """Return availability and provenance for one optional solver."""
    entry = SPECIALIST_SOLVERS.get(name)
    if entry is None:
        return {"name": name, "available": False, "error": "unknown solver"}
    package = str(entry["package"])
    return {
        "name": name,
        "package": package,
        "available": importlib.util.find_spec(package) is not None,
        "source": entry["source"],
        "license": entry["license"],
        "problems": list(entry["problems"]),
    }


def specialist_solver_status() -> dict[str, dict[str, Any]]:
    return {name: solver_status(name) for name in SPECIALIST_SOLVERS}
