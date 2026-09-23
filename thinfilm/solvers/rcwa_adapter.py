from __future__ import annotations

from typing import Any

from .registry import solver_status


def status() -> dict[str, Any]:
    return solver_status("rcwa")


def solve_periodic_stack(*, wavelength_um: float, period_um: float, thickness_um: float, n_grating: float, n_void: float = 1.0, harmonics: int = 11) -> dict[str, Any]:
    """Solve a rectangular 1D grating through the optional ``rcwa`` package."""
    if not status()["available"]:
        raise RuntimeError("rcwa is not installed; install the optional RCWA backend")
    from rcwa import Crystal, Layer, LayerStack, RectangularGrating, Solver, Source

    incident = Layer(er=1.0, ur=1.0)
    transmission = Layer(er=1.0, ur=1.0)
    grating = RectangularGrating(period=period_um, thickness=thickness_um, n=n_grating, n_void=n_void, nx=256)
    source = Source(wavelength=wavelength_um)
    stack = LayerStack(grating, incident_layer=incident, transmission_layer=transmission)
    result = Solver(stack, source, harmonics).solve()
    # Keep the adapter boundary JSON-friendly; the upstream Results object
    # contains Crystal/Source instances that should not leak into API payloads.
    return {
        "solver": "rcwa",
        "R": result["R"].tolist(),
        "T": result["T"].tolist(),
        "R_total": float(result["RTot"]),
        "T_total": float(result["TTot"]),
        "conservation": float(result["conservation"]),
        "harmonics": int(harmonics),
        "wavelength_um": float(wavelength_um),
        "period_um": float(period_um),
        "thickness_um": float(thickness_um),
    }


def sweep_periodic_stack(*, wavelengths_um: list[float], period_um: float, thickness_um: float, n_grating: float, n_void: float = 1.0, harmonics: int = 11) -> dict[str, Any]:
    """Return a wavelength sweep with total R/T and energy conservation."""
    rows = [
        solve_periodic_stack(
            wavelength_um=float(wavelength),
            period_um=period_um,
            thickness_um=thickness_um,
            n_grating=n_grating,
            n_void=n_void,
            harmonics=harmonics,
        )
        for wavelength in wavelengths_um
    ]
    return {
        "solver": "rcwa",
        "wavelength_um": [row["wavelength_um"] for row in rows],
        "R": [row["R_total"] for row in rows],
        "T": [row["T_total"] for row in rows],
        "A": [1.0 - row["R_total"] - row["T_total"] for row in rows],
        "conservation": [row["conservation"] for row in rows],
        "period_um": float(period_um),
        "thickness_um": float(thickness_um),
        "n_grating": float(n_grating),
        "n_void": float(n_void),
        "harmonics": int(harmonics),
    }
