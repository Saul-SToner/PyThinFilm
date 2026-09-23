from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_all_40_cases_have_an_honest_acceptance_classification() -> None:
    response = client.get("/api/case-acceptance")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] == 40
    assert payload["classification_counts"] == {
        "complete_interactive": 18,
        "specialist_solver": 9,
        "formal_evidence": 13,
        "pending_physics": 0,
    }
    assert payload["status_counts"] == {"passed": 40, "attention": 0, "failed": 0}


def test_every_case_is_plot_ready_finite_and_teaching_bound() -> None:
    payload = client.get("/api/case-acceptance").json()
    assert payload["all_plot_ready"] is True
    assert payload["all_finite"] is True
    assert payload["all_teaching_routes_ready"] is True
    assert payload["all_system_bindings_ready"] is True
    assert not [row for row in payload["rows"] if row["blocking_failures"]]


def test_external_evidence_cases_are_promoted_only_with_hashed_provenance() -> None:
    payload = client.get("/api/case-acceptance").json()
    external_cases = {
        "absorbing_surface_gain",
        "absorbing_surface_gain_trend",
        "advanced_ar_bundle",
        "porous_double_ar_topic_bundle",
    }
    rows = {row["case_id"]: row for row in payload["rows"]}
    assert all(rows[case_id]["classification"] == "formal_evidence" for case_id in external_cases)
    assert all(rows[case_id]["external_provenance_ready"] is True for case_id in external_cases)


def test_specialist_cases_have_explicit_solver_endpoints() -> None:
    payload = client.get("/api/case-acceptance").json()
    specialist = [row for row in payload["rows"] if row["classification"] == "specialist_solver"]
    assert len(specialist) == 9
    assert {row["solver"] for row in specialist} == {"RCWA", "GeneralTmm", "WPTherml"}
    assert all(row["endpoint"].startswith("/api/specialist/") for row in specialist)
