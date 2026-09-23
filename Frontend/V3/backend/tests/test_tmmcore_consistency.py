from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _request(layers: list[dict], *, start: float, stop: float, points: int = 121) -> dict:
    return {
        "schema_version": "1.0",
        "request_id": "solver-consistency",
        "incident_material_id": "Air",
        "substrate_material_id": "N-BK7",
        "layers": layers,
        "spectrum": {"start_nm": start, "stop_nm": stop, "points": points},
        "angle_deg": 0.0,
        "polarization": "p",
        "out_of_range_policy": "error",
        "probe_wavelength_nm": 0.5 * (start + stop),
    }


def _layer(layer_id: str, material_id: str, thickness_nm: float) -> dict:
    return {"id": layer_id, "material_id": material_id, "thickness_nm": thickness_nm, "enabled": True}


def _benchmarks() -> list[tuple[str, dict]]:
    single = _request([_layer("ar", "MgF2", 99.6)], start=500, stop=600)

    bragg_layers = []
    for index in range(4):
        bragg_layers.extend(
            [
                _layer(f"h-{index}", "TiO2", 550 / (4 * 2.15)),
                _layer(f"l-{index}", "SiO2", 550 / (4 * 1.46)),
            ]
        )
    bragg = _request(bragg_layers, start=450, stop=700)

    fp_layers = []
    for index in range(3):
        fp_layers.extend(
            [
                _layer(f"left-h-{index}", "TiO2", 550 / (4 * 2.15)),
                _layer(f"left-l-{index}", "SiO2", 550 / (4 * 1.46)),
            ]
        )
    fp_layers.append(_layer("cavity", "SiO2", 550 / (2 * 1.46)))
    for index in range(3):
        fp_layers.extend(
            [
                _layer(f"right-l-{index}", "SiO2", 550 / (4 * 1.46)),
                _layer(f"right-h-{index}", "TiO2", 550 / (4 * 2.15)),
            ]
        )
    fp = _request(fp_layers, start=450, stop=700)
    return [("single-layer-ar", single), ("bragg", bragg), ("fp-cavity", fp)]


@pytest.mark.parametrize(("name", "payload"), _benchmarks())
def test_tmmcore_matches_pythinfilm_for_core_benchmarks(name: str, payload: dict) -> None:
    python_response = client.post("/api/designs/simulate", json={**payload, "solver": "pythinfilm"})
    tmmcore_response = client.post("/api/designs/simulate", json={**payload, "solver": "tmmcore"})
    assert python_response.status_code == 200, python_response.text
    assert tmmcore_response.status_code == 200, tmmcore_response.text

    python_result = python_response.json()
    tmmcore_result = tmmcore_response.json()
    for quantity in ("R", "T", "A"):
        difference = np.max(
            np.abs(np.asarray(python_result["series"][quantity]) - np.asarray(tmmcore_result["series"][quantity]))
        )
        assert difference < 1e-10, f"{name} {quantity}: max difference={difference}"
    assert tmmcore_result["solver"]["spectral_engine"] == "tmmcore"
    assert tmmcore_result["solver"]["teaching_insights_engine"] == "pythinfilm"


def test_diagnostics_reports_tmmcore_runtime() -> None:
    response = client.get("/api/diagnostics")
    assert response.status_code == 200
    status = response.json()["tmmcore"]
    assert status["version"] == "0.4.0"
    assert status["available"] is True


@pytest.mark.parametrize("case_id", [
    "quarter_wave_single_layer", "half_wave_single_layer", "single_ar",
    "porous_sio2_layer", "double_ar", "porous_double_ar", "triple_ar",
    "high_reflector", "quarter_wave_stack", "bragg_reflector", "fp_filter",
    "fp_double_halfwave", "narrowband_filter", "neutral_beamsplitter",
    "rugate_filter", "moth_eye_effective_gradient",
])
def test_teaching_baselines_use_tmmcore(case_id: str) -> None:
    response = client.post("/api/simulations", json={"case_id": case_id, "params": {}})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["case_id"] == case_id
    assert result["solver"]["spectral_engine"] == "tmmcore"
    assert len(result["series"]["wavelength_nm"]) >= 2
    assert len(result["series"]["R"]) == len(result["series"]["T"]) == len(result["series"]["A"])

    if case_id in {"rugate_filter", "moth_eye_effective_gradient"}:
        assert result["solver"]["discretization"] == "layer_sliced_approximation"


@pytest.mark.parametrize("polarization", ["s", "p"])
def test_tmmcore_matches_absorbing_oblique_stack_conventions(polarization: str) -> None:
    payload = _request([_layer("silver", "Ag", 30.0)], start=450, stop=800, points=101)
    payload.update({"angle_deg": 30.0, "polarization": polarization, "probe_wavelength_nm": 550.0})
    python_result = client.post("/api/designs/simulate", json={**payload, "solver": "pythinfilm"}).json()
    tmmcore_result = client.post("/api/designs/simulate", json={**payload, "solver": "tmmcore"}).json()
    for quantity in ("R", "T", "A"):
        assert np.allclose(
            python_result["series"][quantity],
            tmmcore_result["series"][quantity],
            atol=1e-10,
            rtol=0,
        )
