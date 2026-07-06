"""Tests for data-driven R/T/A visual hierarchy."""

import numpy as np
import pytest

from thinfilm.plot_logic import focused_power_limits, infer_rta_focus, padded_numeric_limits, rta_trace_styles


def test_context_prefers_reflectance_for_high_reflector():
    x = np.linspace(0.0, 1.0, 50)
    assert infer_rta_focus(0.95 + 0.04 * x, 0.05 - 0.04 * x, 0.0 * x, context="laser mirror DBR") == "R"


def test_context_prefers_transmittance_for_fp_filter():
    x = np.linspace(0.0, 1.0, 50)
    assert infer_rta_focus(1.0 - x, x, 0.0 * x, context="fp_filter") == "T"


def test_data_fallback_selects_largest_variation():
    x = np.linspace(0.0, 1.0, 50)
    assert infer_rta_focus(0.50 + 0.02 * x, 0.40 + 0.30 * x, 0.10 - 0.01 * x) == "T"


def test_focused_limits_reveal_variation_near_one():
    y0, y1 = focused_power_limits([0.965, 0.992, 0.999])
    assert 0.90 < y0 < 0.965
    assert 0.999 < y1 <= 1.02
    assert y1 - y0 == pytest.approx(0.08)


def test_focused_limits_keep_zero_boundary():
    y0, y1 = focused_power_limits([0.0, 0.002, 0.006])
    assert y0 == 0.0
    assert y1 == pytest.approx(0.08)


def test_negligible_absorption_is_visually_muted():
    curves = {
        "R": np.array([0.96, 0.99, 1.0]),
        "T": np.array([0.04, 0.01, 0.0]),
        "A": np.array([0.0, 0.0002, 0.0001]),
    }
    styles = rta_trace_styles("R", curves)
    assert styles["R"]["linewidth"] > styles["T"]["linewidth"] > styles["A"]["linewidth"]
    assert styles["A"]["alpha"] < 0.3


def test_invalid_preference_rejected():
    with pytest.raises(ValueError):
        infer_rta_focus([1], [0], [0], preferred="X")


def test_dimensional_limits_compare_nearby_wavelengths_without_zero_baseline():
    y0, y1 = padded_numeric_limits([550.0, 553.0], min_span=20.0)
    assert y0 > 500.0
    assert y0 < 550.0 < 553.0 < y1


def test_angle_wavelength_plot_defaults_to_quantitative_heatmap():
    from thinfilm.plotly_charts import plot_angle_wavelength_surface

    fig = plot_angle_wavelength_surface(
        np.array([500.0, 600.0]), np.array([0.0, 30.0]), np.array([[0.2, 0.3], [0.4, 0.5]])
    )
    assert fig.data[0].type == "heatmap"


def test_angle_wavelength_plot_retains_optional_surface_view():
    from thinfilm.plotly_charts import plot_angle_wavelength_surface

    fig = plot_angle_wavelength_surface(
        np.array([500.0, 600.0]), np.array([0.0, 30.0]), np.array([[0.2, 0.3], [0.4, 0.5]]),
        render_mode="surface",
    )
    assert fig.data[0].type == "surface"
