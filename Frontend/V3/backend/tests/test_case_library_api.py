from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_case_library_exposes_all_40_physical_cases() -> None:
    response = client.get("/api/case-library?include_archived=true")
    assert response.status_code == 200
    payload = response.json()
    assert payload["physical_case_count"] == 40
    assert payload["interactive_case_count"] == 18
    assert payload["static_case_count"] == 22
    assert payload["category_breakdown"] == {
        "teaching_thinfilm": 18,
        "teaching_emt": 1,
        "engineering_applications": 5,
        "research_extension": 16,
    }
    assert len(payload["cases"]) == 40
    assert "guided_grating_demo" not in {case["case_id"] for case in payload["cases"]}


def test_app_catalog_only_exposes_released_teaching_cases() -> None:
    payload = client.get('/api/case-library').json()
    assert payload['physical_case_count'] == len(payload['cases']) == 22
    assert payload['interactive_case_count'] == 18
    assert payload['static_case_count'] == 4
    restored = {c['case_id']: c for c in payload['cases'] if c['category'] == 'research_extension'}
    assert set(restored) == {'tamm_interface_priority', 'tamm_phase_bundle', 'tamm_phase_focus'}
    assert all('Ag/DBR' in c['title_cn'] and c['system_experiment'] is None and not c['optiland']['enabled'] for c in restored.values())
    assert 'guided_grating_emt' in {c['case_id'] for c in payload['cases']}


def test_released_tamm_cases_compute_current_model_at_default_settings() -> None:
    import math
    for case in client.get('/api/case-library').json()['cases']:
        if not case['case_id'].startswith('tamm_'):
            continue
        response = client.post('/api/specialist/generaltmm', json={'case_id': case['case_id']})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['materials'][0] == 'Ag'
        assert all(len(c['x']) == len(c['y']) > 1 and all(math.isfinite(v) for v in c['y']) for c in result['curves'])
        assert result['field_comparison']['validation']['energy_conservation_passed']
        assert result['field_comparison']['validation']['tangential_e_continuity_passed']


def test_every_catalog_case_has_readable_detail() -> None:
    cases = client.get("/api/case-library").json()["cases"]
    for case in cases:
        response = client.get(f"/api/case-library/{case['case_id']}")
        assert response.status_code == 200, case["case_id"]
        detail = response.json()
        assert detail["case_id"] == case["case_id"]
        assert isinstance(detail["series"], list)
        assert isinstance(detail["summary_cards"], list)
        assert isinstance(detail["limitations"], list)


def test_every_catalog_case_has_plot_ready_series() -> None:
    cases = client.get("/api/case-library").json()["cases"]
    for case in cases:
        detail = client.get(f"/api/case-library/{case['case_id']}").json()
        series = detail["series"]
        assert series, f"{case['case_id']} has no plot-ready series"
        for trace in series:
            assert len(trace["x"]) == len(trace["y"]) >= 2


def test_evidence_case_preserves_scientific_limitations() -> None:
    response = client.get("/api/case-library/tamm_interface_priority")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_kind"] == "evidence"
    assert payload["has_live_simulation"] is False
    assert payload["summary_cards"]
    assert payload["limitations"]


def test_unknown_case_returns_404() -> None:
    response = client.get("/api/case-library/not-a-case")
    assert response.status_code == 404
