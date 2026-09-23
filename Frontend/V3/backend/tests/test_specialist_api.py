from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_rcwa_specialist_endpoint_is_explicit() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/specialist/rcwa",
        json={
            "wavelength_start_um": 0.50,
            "wavelength_stop_um": 0.52,
            "wavelength_points": 2,
            "period_um": 0.7,
            "thickness_um": 0.2,
            "n_grating": 2.0,
            "n_void": 1.0,
            "harmonics": 3,
        },
    )
    assert response.status_code in {200, 503}
    if response.status_code == 200:
        payload = response.json()
        assert payload["solver"] == "rcwa"
        assert len(payload["wavelength_um"]) == 2
        assert len(payload["R"]) == 2


def test_all_tamm_cases_use_material_resolved_generaltmm_stack() -> None:
    client = TestClient(app)
    expected_curve_labels = {
        "tamm_interface_priority": "p 偏振反射率",
        "tamm_phase_bundle": "p 偏振反射相位",
        "tamm_phase_candidates": "p 偏振吸收率",
        "tamm_phase_focus": "偏振吸收率",
        "tamm_reflection_phase_screen": "p 偏振相位",
        "tamm_interface_window_bundle": "p 偏振界面窗口",
        "tamm_interface_window_scan": "角度窗口",
    }
    for case_id, expected_label in expected_curve_labels.items():
        response = client.post("/api/specialist/generaltmm", json={"case_id": case_id, "wavelength_start_nm": 500, "wavelength_stop_nm": 510, "wavelength_points": 2})
        assert response.status_code == 200
        payload = response.json()
        assert payload["solver"] == "generaltmm"
        assert payload["layer_count"] == 8
        assert payload["materials"][0] == "Ag"
        assert len(payload["R"]) == 2
        assert payload["curves"]
        assert any(expected_label in curve["label"] for curve in payload["curves"])
        assert payload["x_label"]
        assert payload["y_label"]
        field = payload["field_comparison"]
        assert field["field_quantity"] == "|E|^2 / |E_inc|^2"
        assert len(field["profiles"]) == 2
        assert len(field["profiles"][0]["depth_nm"]) == 601
        assert field["validation"]["energy_conservation_passed"] is True
        assert field["validation"]["tangential_e_continuity_passed"] is True
        assert 500 <= field["resonance_wavelength_nm"] <= 510


def test_pdrc_uses_exported_sio2_tio2_ag_stack() -> None:
    client = TestClient(app)
    response = client.post("/api/specialist/wptherml", json={"case_id": "pdrc_cooling_bundle", "wavelength_start_nm": 400, "wavelength_stop_nm": 800, "wavelength_points": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["solver"] == "wptherml"
    assert payload["materials"] == ["Air", "SiO2", "TiO2", "SiO2", "TiO2", "SiO2", "Ag", "Air"]
    assert len(payload["R"]) == len(payload["wavelength_nm"])


def test_tamm_virtual_experiment_rebuilds_stack_and_field() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/specialist/generaltmm",
        json={
            "case_id": "tamm_phase_focus",
            "wavelength_start_nm": 560,
            "wavelength_stop_nm": 720,
            "wavelength_points": 41,
            "ag_thickness_nm": 42,
            "dbr_periods": 2,
            "beta": 0.2,
            "polarization": "s",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["layer_count"] == 6
    assert payload["layer_thickness_nm"][0] == 42
    assert payload["experiment_params"] == {"ag_thickness_nm": 42, "dbr_periods": 2, "beta": 0.2, "polarization": "s"}
    assert payload["comparison_curve"]["label"] == "s 偏振吸收率"
    assert payload["field_comparison"]["polarization"] == "s"
    assert payload["field_comparison"]["interface_nm"] == 42


def test_absorbing_cases_keep_formal_evidence_results() -> None:
    client = TestClient(app)
    for case_id in ["absorbing_baseline_template", "absorbing_surface_bundle", "absorbing_surface_gain", "absorbing_surface_gain_trend"]:
        response = client.get(f"/api/case-library/{case_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["evidence_status"]
        assert payload["summary_cards"] or payload["series"] or payload["table"]["rows"]
