from fastapi.testclient import TestClient

from app.main import PYTHINFILM_ROOT, app


client = TestClient(app)


def _payload():
    return {
        "schema_version": "1.0",
        "request_id": "test-1",
        "incident_material_id": "Air",
        "substrate_material_id": "N-BK7",
        "layers": [{"id": "l1", "material_id": "MgF2", "thickness_nm": 99.6, "enabled": True}],
        "spectrum": {"start_nm": 500, "stop_nm": 600, "points": 31},
        "angle_deg": 0,
        "polarization": "p",
        "out_of_range_policy": "error",
        "probe_wavelength_nm": 550,
        "experiment_task_id": "single-layer-ar",
    }


def test_backend_uses_outer_physics_core():
    assert (PYTHINFILM_ROOT / "thinfilm" / "custom_stack.py").exists()


def test_design_simulation_contract():
    response = client.post("/api/designs/simulate", json=_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["request_id"] == "test-1"
    assert len(body["series"]["R"]) == 31
    assert body["design"]["layers"][0]["material_id"] == "MgF2"
    assert body["metrics"]["center_wavelength_nm"] == 550.0
    assert body["field"]["wavelength_nm"] == 550.0
    assert len(body["phase"]["reflection_phase_deg"]) == 31
    assert body["evaluation"]["status"] == "available"


def test_design_simulation_rejects_unknown_material():
    payload = _payload()
    payload["layers"][0]["material_id"] = "Unobtainium"
    response = client.post("/api/designs/simulate", json=payload)
    assert response.status_code == 422
