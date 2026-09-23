import numpy as np
import pytest

from thinfilm.api import simulate_custom_stack


def _design(**overrides):
    value = {
        "incident_material_id": "Air",
        "substrate_material_id": "N-BK7",
        "layers": [{"id": "layer-1", "material_id": "MgF2", "thickness_nm": 99.6, "enabled": True}],
        "spectrum": {"start_nm": 500.0, "stop_nm": 600.0, "points": 101},
        "angle_deg": 0.0,
        "polarization": "p",
        "out_of_range_policy": "error",
    }
    value.update(overrides)
    return value


def test_ar_stack_returns_conservative_spectrum():
    result = simulate_custom_stack(_design())
    assert len(result["wavelength_nm"]) == 101
    assert np.max(np.abs(result["R"] + result["T"] + result["A"] - 1.0)) < 1e-9
    assert result["summary"]["layer_count"] == 1
    assert result["summary"]["total_thickness_nm"] == pytest.approx(99.6)
    assert result["metrics"]["R"]["minimum_wavelength_nm"] >= 500.0
    assert result["metrics"]["R"]["maximum_wavelength_nm"] <= 600.0
    assert result["metrics"]["center_wavelength_nm"] == pytest.approx(550.0)


def test_layer_order_and_enabled_state_are_preserved():
    layers = [
        {"id": "high", "material_id": "TiO2", "thickness_nm": 60.0, "enabled": False},
        {"id": "low", "material_id": "SiO2", "thickness_nm": 90.0, "enabled": True},
    ]
    result = simulate_custom_stack(_design(layers=layers))
    assert [row["id"] for row in result["design"]["layers"]] == ["high", "low"]
    assert result["summary"]["layer_count"] == 1
    assert result["summary"]["total_thickness_nm"] == pytest.approx(90.0)


@pytest.mark.parametrize(
    "change, match",
    [
        ({"layers": []}, "At least one layer"),
        ({"polarization": "x"}, "polarization"),
        ({"angle_deg": 90}, "angle_deg"),
        ({"layers": [{"id": "bad", "material_id": "MgF2", "thickness_nm": 0}]}, "thickness_nm"),
        ({"layers": [{"id": "bad", "material_id": "Unobtainium", "thickness_nm": 1}]}, "Unknown material"),
    ],
)
def test_invalid_design_is_rejected(change, match):
    with pytest.raises(ValueError, match=match):
        simulate_custom_stack(_design(**change))


def test_clip_policy_reports_material_range_warning():
    result = simulate_custom_stack(
        _design(
            layers=[{"id": "metal", "material_id": "Ag", "thickness_nm": 20.0}],
            spectrum={"start_nm": 200.0, "stop_nm": 1000.0, "points": 21},
            out_of_range_policy="clip",
        )
    )
    assert result["warnings"]
    assert np.all(np.isfinite(result["R"]))


def test_spectral_metrics_report_high_reflection_band_and_linewidth_status():
    layers = []
    for index in range(5):
        layers.extend(
            [
                {"id": f"h-{index}", "material_id": "TiO2", "thickness_nm": 63.95},
                {"id": f"l-{index}", "material_id": "SiO2", "thickness_nm": 94.1},
            ]
        )
    result = simulate_custom_stack(
        _design(layers=layers, spectrum={"start_nm": 450.0, "stop_nm": 800.0, "points": 351})
    )
    band = result["metrics"]["high_reflection_band"]
    assert band is not None
    assert band["width_nm"] > 0
    assert result["metrics"]["transmission_peak_linewidth"]["status"] in {"available", "not_available"}


@pytest.mark.parametrize("polarization, angle_deg", [("p", 0.0), ("p", 30.0), ("s", 30.0)])
def test_v2_field_and_phase_evidence_match_probe_spectrum(polarization, angle_deg):
    result = simulate_custom_stack(
        _design(probe_wavelength_nm=550.0, polarization=polarization, angle_deg=angle_deg)
    )
    probe_index = int(np.argmin(np.abs(result["wavelength_nm"] - 550.0)))
    assert result["field"]["wavelength_nm"] == pytest.approx(550.0)
    assert result["field"]["R"] == pytest.approx(result["R"][probe_index], abs=1e-10)
    assert len(result["field"]["z_nm"]) == len(result["field"]["E2"])
    assert result["field"]["peak_E2"] > 0
    assert len(result["phase"]["reflection_phase_deg"]) == 101
    assert len(result["phase"]["layer_phase"]) == 1


@pytest.mark.parametrize("task_id", ["single-layer-ar", "bragg-reflector", "fp-cavity"])
def test_v2_guided_tasks_return_transparent_evaluation(task_id):
    result = simulate_custom_stack(_design(experiment_task_id=task_id, probe_wavelength_nm=550.0))
    evaluation = result["evaluation"]
    assert evaluation["status"] == "available"
    assert 0 <= evaluation["score"] <= 100
    assert evaluation["criteria"]
    assert all({"label", "value", "target", "score", "passed"} <= set(item) for item in evaluation["criteria"])


def test_probe_wavelength_must_be_inside_scan():
    with pytest.raises(ValueError, match="probe_wavelength_nm"):
        simulate_custom_stack(_design(probe_wavelength_nm=700.0))
