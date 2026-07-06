import numpy as np

from thinfilm.decision import (
    build_decision_record,
    compute_device_metrics,
    normalize_metric,
    pareto_front_indices,
    pass_probability,
    robust_interval,
    score_device_metrics,
)


def test_device_classes_use_different_physical_metrics():
    wl = np.linspace(500.0, 600.0, 101)
    r_ar = 0.01 + 0.04 * ((wl - 550.0) / 50.0) ** 2
    ar = compute_device_metrics("single_ar", wl, r_ar, 1 - r_ar, np.zeros_like(wl), design_wavelength=550.0)
    assert ar["device_class"] == "ar"
    assert set(ar["metrics"]) == {"R_design", "R_band_mean", "R_band_max"}

    r_hr = np.full_like(wl, 0.995)
    hr = compute_device_metrics("high_reflector", wl, r_hr, 1 - r_hr, np.zeros_like(wl), design_wavelength=550.0)
    assert hr["device_class"] == "reflector"
    assert hr["metrics"]["high_R_fraction"] == 1.0


def test_normalization_respects_metric_direction():
    assert normalize_metric(0.01, direction="min", good=0.01, bad=0.1) == 1.0
    assert normalize_metric(0.1, direction="min", good=0.01, bad=0.1) == 0.0
    assert normalize_metric(0.99, direction="max", good=0.99, bad=0.8) == 1.0


def test_geometric_score_exposes_weakest_component():
    result = score_device_metrics("ar", {"R_design": 0.01, "R_band_mean": 0.03, "R_band_max": 0.25})
    assert result["weakest_metric"] == "R_band_max"
    assert result["score"] < 0.1


def test_robust_interval_and_pass_probability():
    summary = robust_interval([0.4, 0.5, 0.6, 0.7], confidence=0.5)
    assert summary["lower"] < summary["median"] < summary["upper"]
    assert pass_probability([0.4, 0.5, 0.6, 0.7], direction="max", threshold=0.6) == 0.5


def test_pareto_front_handles_mixed_directions():
    rows = [
        {"performance": 0.9, "cost": 0.5},
        {"performance": 0.8, "cost": 0.4},
        {"performance": 0.7, "cost": 0.7},
    ]
    assert pareto_front_indices(rows, {"performance": "max", "cost": "min"}) == [0, 1]


def test_decision_record_keeps_interval_not_only_best_value():
    wl = np.linspace(500.0, 600.0, 101)
    r = np.full_like(wl, 0.02)
    record = build_decision_record(
        case_id="single_ar", title="AR", wavelength=wl, R=r, T=1-r, A=np.zeros_like(wl),
        design_wavelength=550.0, score_samples=[0.7, 0.8, 0.9],
    )
    assert record["robustness_score"] < record["score_interval"]["median"]
