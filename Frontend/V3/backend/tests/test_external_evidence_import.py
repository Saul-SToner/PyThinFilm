from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_comsol_template_declares_roles_and_canonical_header() -> None:
    response = client.get("/api/evidence/comsol-template/absorbing_surface_gain")
    assert response.status_code == 200
    payload = response.json()
    assert payload["roles"] == ["rough_surface", "planar_baseline"]
    assert payload["canonical_header"] == "wavelength_nm,R,T,A"


def test_canonical_comsol_csv_is_validated_and_hashed() -> None:
    response = client.post(
        "/api/evidence/validate-comsol-csv",
        json={
            "case_id": "advanced_ar_bundle",
            "role": "single_ar",
            "csv_text": "wavelength_nm,R\n500,0.04\n550,0.01\n600,0.03\n",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["row_count"] == 3
    assert payload["quantity_mapping"] == {"wavelength_nm": "wavelength_nm", "R": "R"}
    assert len(payload["sha256"]) == 64


def test_native_comsol_header_is_recognized() -> None:
    response = client.post(
        "/api/evidence/validate-comsol-csv",
        json={
            "case_id": "porous_double_ar_topic_bundle",
            "role": "theta",
            "csv_text": "% theta (rad),lam/1[nm] (1),abs(ewfd.S11)^2 (1)\n0,500,0.04\n0.1,550,0.02\n",
        },
    )
    assert response.status_code == 200
    assert response.json()["quantity_mapping"]["R"] == "abs(ewfd.S11)^2 (1)"


def test_invalid_power_range_is_rejected() -> None:
    response = client.post(
        "/api/evidence/validate-comsol-csv",
        json={"case_id": "absorbing_surface_gain", "role": "rough_surface", "csv_text": "wavelength_nm,A\n500,0.8\n550,1.2\n"},
    )
    assert response.status_code == 422
    assert "within [0, 1]" in response.json()["detail"]
