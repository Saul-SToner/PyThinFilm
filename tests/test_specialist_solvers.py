from __future__ import annotations

import pytest

from thinfilm.solvers import specialist_solver_status
from thinfilm.solvers.generaltmm_adapter import solve_interface
from thinfilm.solvers.rcwa_adapter import solve_periodic_stack
from thinfilm.solvers.wptherml_adapter import build_multilayer


def test_specialist_registry_is_lazy_and_complete() -> None:
    status = specialist_solver_status()
    assert set(status) == {"rcwa", "generaltmm", "wptherml"}
    assert all("source" in value and "problems" in value for value in status.values())


def test_optional_adapters_fail_explicitly_when_not_installed() -> None:
    status = specialist_solver_status()
    if not status["rcwa"]["available"]:
        with pytest.raises(RuntimeError, match="rcwa is not installed"):
            solve_periodic_stack(wavelength_um=0.55, period_um=0.7, thickness_um=0.2, n_grating=2.0)
    if not status["generaltmm"]["available"]:
        with pytest.raises(RuntimeError, match="GeneralTmm is not installed"):
            solve_interface(wavelength_nm=550, n_incident=1, n_layer=2, n_substrate=1.5, thickness_nm=100)
    if not status["wptherml"]["available"]:
        with pytest.raises(RuntimeError, match="WPTherml is not installed"):
            build_multilayer(materials=["Air", "SiO2", "Air"], thickness_m=[0, 100e-9, 0], wavelength_range_m=(400e-9, 800e-9, 10))


def test_wptherml_uses_requested_wavelength_grid() -> None:
    if not specialist_solver_status()["wptherml"]["available"]:
        pytest.skip("WPTherml is optional")
    model = build_multilayer(
        materials=["Air", "SiO2", "Air"],
        thickness_m=[0, 100e-9, 0],
        wavelength_range_m=(400e-9, 800e-9, 4),
    )
    assert len(model.wavelength_array) == 4
    assert model.wavelength_array[0] == pytest.approx(400e-9)
    assert model.wavelength_array[-1] == pytest.approx(800e-9)
