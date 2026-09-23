"""Tests for reflection phase calculation (Tamm analysis support)."""

from __future__ import annotations

import numpy as np
import pytest

from thinfilm.education import (
    LayerSpec,
    multilayer_rt_spectrum,
    phase_difference,
    reflection_phase_degrees,
    reflection_phase_radians,
    quarter_wave_thickness_nm,
)


LAMBDAS_NM = np.linspace(400, 800, 600)


def _single_layer_result():
    n = 1.38
    layers = [LayerSpec("L", n, quarter_wave_thickness_nm(550.0, n))]
    return multilayer_rt_spectrum(LAMBDAS_NM, layers, n_incident=1.0, n_substrate=1.52)


def _bragg_result():
    from thinfilm.education import build_high_reflector_layers
    layers = build_high_reflector_layers(550.0, n_high=2.30, n_low=1.46, periods=3)
    return multilayer_rt_spectrum(LAMBDAS_NM, layers, n_incident=1.0, n_substrate=1.52)


# ---------------------------------------------------------------------------
# 1. reflection_phase_radians
# ---------------------------------------------------------------------------

class TestReflectionPhaseRadians:
    def test_shape(self):
        result = _single_layer_result()
        phase = reflection_phase_radians(result)
        assert phase.shape == (600,)

    def test_dtype(self):
        result = _single_layer_result()
        phase = reflection_phase_radians(result)
        assert phase.dtype == np.float64

    def test_range_wrapped(self):
        result = _single_layer_result()
        phase = reflection_phase_radians(result, unwrap=False)
        assert np.all(phase >= -np.pi)
        assert np.all(phase <= np.pi)

    def test_unwrapped_continuous(self):
        result = _bragg_result()
        phase = reflection_phase_radians(result, unwrap=True)
        # Unwrapped phase should be monotonically varying (no jumps)
        dphase = np.diff(phase)
        # Max jump should be less than π (no wrapping)
        assert np.max(np.abs(dphase)) < np.pi

    def test_matches_angle(self):
        result = _single_layer_result()
        phase = reflection_phase_radians(result, unwrap=False)
        expected = np.angle(result["r_complex"])
        np.testing.assert_allclose(phase, expected, atol=1e-12)


# ---------------------------------------------------------------------------
# 2. reflection_phase_degrees
# ---------------------------------------------------------------------------

class TestReflectionPhaseDegrees:
    def test_shape(self):
        result = _single_layer_result()
        phase = reflection_phase_degrees(result)
        assert phase.shape == (600,)

    def test_conversion(self):
        result = _single_layer_result()
        rad = reflection_phase_radians(result, unwrap=False)
        deg = reflection_phase_degrees(result, unwrap=False)
        np.testing.assert_allclose(deg, np.degrees(rad), atol=1e-10)


# ---------------------------------------------------------------------------
# 3. phase_difference
# ---------------------------------------------------------------------------

class TestPhaseDifference:
    def test_same_structure_zero(self):
        result = _single_layer_result()
        delta = phase_difference(result, result)
        np.testing.assert_allclose(delta, 0.0, atol=1e-12)

    def test_different_structures(self):
        n1, n2 = 1.38, 1.46
        r1 = multilayer_rt_spectrum(
            LAMBDAS_NM,
            [LayerSpec("L", n1, quarter_wave_thickness_nm(550.0, n1))],
            n_incident=1.0, n_substrate=1.52,
        )
        r2 = multilayer_rt_spectrum(
            LAMBDAS_NM,
            [LayerSpec("L", n2, quarter_wave_thickness_nm(550.0, n2))],
            n_incident=1.0, n_substrate=1.52,
        )
        delta = phase_difference(r1, r2)
        assert delta.shape == (600,)
        # Different structures should give nonzero phase difference
        assert np.max(np.abs(delta)) > 0.01

    def test_wrapped_range(self):
        r1 = _single_layer_result()
        r2 = _bragg_result()
        delta = phase_difference(r1, r2, unwrap=False)
        assert np.all(delta >= -np.pi)
        assert np.all(delta <= np.pi)

    def test_unwrapped_smaller_magnitude(self):
        r1 = _single_layer_result()
        r2 = _bragg_result()
        delta_wrapped = np.abs(phase_difference(r1, r2, unwrap=False))
        delta_unwrapped = np.abs(phase_difference(r1, r2, unwrap=True))
        # Unwrapped difference should generally have smaller magnitude
        assert np.mean(delta_unwrapped) <= np.mean(delta_wrapped) + 0.1


# ---------------------------------------------------------------------------
# 4. Edge cases
# ---------------------------------------------------------------------------

class TestPhaseEdgeCases:
    def test_bare_interface(self):
        result = multilayer_rt_spectrum(
            LAMBDAS_NM, [], n_incident=1.0, n_substrate=1.52,
        )
        phase = reflection_phase_radians(result)
        # Bare interface: phase should be ~0 or ~π (real r)
        assert phase.shape == (600,)

    def test_single_wavelength(self):
        result = multilayer_rt_spectrum(
            [550.0], [], n_incident=1.0, n_substrate=1.52,
        )
        phase = reflection_phase_radians(result)
        assert phase.shape == (1,)

    def test_oblique_incidence(self):
        n = 1.38
        layers = [LayerSpec("L", n, quarter_wave_thickness_nm(550.0, n))]
        result = multilayer_rt_spectrum(
            LAMBDAS_NM, layers, n_incident=1.0, n_substrate=1.52,
            theta0_deg=45.0, pol="s",
        )
        phase = reflection_phase_radians(result)
        assert phase.shape == (600,)


class TestTammPhaseRegression:
    def test_tamm_phase_condition_near_reflection_dip(self):
        """Verify the Tamm phase matching condition near the resonance reflection dip.
        
        Conventions & Reference Planes:
        1. Reference Plane: The interface between the 30 nm Ag metal layer and the first DBR layer.
        2. DBR Phase (phi_dbr): Phase of amplitude reflection coefficient looking from the interface
           into the DBR, with the incident medium set to the interface medium (n_H = 2.5).
        3. Metal Phase (phi_metal): Phase of amplitude reflection coefficient looking from the interface
           into the metal layer (and leaking into Air), with the incident medium set to n_H = 2.5
           and substrate set to Air (1.0).
        4. Matching Condition: Since both coefficients are defined at the same interface reference plane,
           the round-trip phase condition for the Tamm interface mode is simply phi_dbr + phi_metal = 2*m*pi.
           At the resonance wavelength, the phase matching sum (wrapped to [-pi, pi]) should be close to 0.
        """
        # 1. Setup DBR (quarter wave at 600 nm, 8 periods)
        lambda0 = 600.0
        n_H = 2.5
        n_L = 1.45
        d_H = quarter_wave_thickness_nm(lambda0, n_H)
        d_L = quarter_wave_thickness_nm(lambda0, n_L)

        dbr_layers = []
        for _ in range(8):
            dbr_layers.append(LayerSpec("H", n_H, d_H))
            dbr_layers.append(LayerSpec("L", n_L, d_L))

        # 30 nm Ag
        n_metal = 0.05 + 3.9j
        combined_layers = [LayerSpec("Ag", n_metal, 30.0)] + dbr_layers

        # Wavelength range containing the Tamm state dip
        wavelengths = np.linspace(680.0, 740.0, 100)
        res_combined = multilayer_rt_spectrum(wavelengths, combined_layers, n_incident=1.0, n_substrate=1.52)
        R_vals = res_combined["R"]

        # Find resonance dip wavelength
        dip_idx = np.argmin(R_vals)
        dip_wl = wavelengths[dip_idx]
        
        # Dip must be close to 711 nm
        assert abs(dip_wl - 711.0) < 5.0

        # Calculate DBR phase at the dip
        res_dbr = multilayer_rt_spectrum([dip_wl], dbr_layers, n_incident=n_H, n_substrate=1.52)
        phi_dbr = np.angle(res_dbr["r_complex"][0])

        # Calculate Metal phase at the dip
        metal_layers = [LayerSpec("Ag", n_metal, 30.0)]
        res_metal = multilayer_rt_spectrum([dip_wl], metal_layers, n_incident=n_H, n_substrate=1.0)
        phi_metal = np.angle(res_metal["r_complex"][0])

        # Phase sum: should be close to 0 mod 2*pi
        total_phase = phi_dbr + phi_metal
        total_phase_wrapped = (total_phase + np.pi) % (2.0 * np.pi) - np.pi

        # The phase matching error at resonance dip must be small (within 10 degrees or ~0.17 rad)
        assert abs(total_phase_wrapped) < 0.15

