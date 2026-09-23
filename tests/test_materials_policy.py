# -*- coding: utf-8 -*-
"""Tests for materials out-of-range extrapolation policy and physical sign convention."""

from __future__ import annotations

import numpy as np
import pytest

from thinfilm.materials import load_real_material, material_nk_at, material_complex_index
from thinfilm.education import LayerSpec, multilayer_rt_spectrum


class TestMaterialsPolicy:
    def test_out_of_range_policy_error(self):
        # SiO2 valid range is 0.21 - 50.0 um. Requesting 0.15 um should fail with "error" policy
        with pytest.raises(ValueError, match="valid range"):
            material_nk_at("SiO2", 0.15, out_of_range_policy="error")

    def test_out_of_range_policy_clip(self):
        # With "clip", it should clamp to the nearest data point (0.21 um) and succeed
        n_clip, k_clip = material_nk_at("SiO2", 0.15, out_of_range_policy="clip")
        n_edge, k_edge = material_nk_at("SiO2", 0.21, out_of_range_policy="error")
        np.testing.assert_allclose(n_clip, n_edge)
        np.testing.assert_allclose(k_clip, k_edge)

    def test_default_policy_is_error(self):
        # The default policy should be "error" (exception raised for 0.15 um)
        with pytest.raises(ValueError, match="valid range"):
            material_nk_at("SiO2", 0.15)

    def test_mutual_exclusion(self):
        # Specifying both should raise ValueError
        with pytest.raises(ValueError, match="Cannot specify both"):
            material_nk_at("SiO2", 0.15, out_of_range_policy="clip", allow_extrapolate=True)

    def test_deprecation_warning(self):
        # Specifying only legacy allow_extrapolate should issue warning and work
        with pytest.deprecated_call():
            n, k = material_nk_at("SiO2", 0.15, allow_extrapolate=True)
        n_edge, k_edge = material_nk_at("SiO2", 0.21, out_of_range_policy="error")
        np.testing.assert_allclose(n, n_edge)

    def test_metadata_clip_record(self):
        # Clip should record the event and wavelengths in dataset metadata
        from thinfilm.materials import load_real_material
        dataset = load_real_material("SiO2")
        # clear any previous metadata flags
        dataset.metadata.pop("clipped_occurred", None)
        dataset.metadata.pop("clipped_wavelengths", None)
        
        # Query with clip
        material_nk_at("SiO2", 0.15, out_of_range_policy="clip")
        assert dataset.metadata.get("clipped_occurred") is True
        assert 0.15 in dataset.metadata.get("clipped_wavelengths", [])


class TestPhysicalSignConvention:
    def test_absorption_decay_with_thickness(self):
        """Verify that positive extinction coefficient k > 0 leads to Beer-Lambert energy decay.

        In a complex matched setup (no boundary reflections), the transmission T
        should match the analytical Beer-Lambert law: T = exp(-4 * pi * k * d / lambda)
        and R should be exactly 0.
        """
        # Define an absorbing layer with n = 2.0, k = 0.5
        n_absorbing = 2.0 + 0.5j
        wl = [500.0]
        
        # Test thicknesses of 50 nm, 150 nm, 250 nm, 500 nm
        thicknesses = [50.0, 150.0, 250.0, 500.0]
        
        for d in thicknesses:
            layers = [LayerSpec(name="Absorber", thickness_nm=d, n=n_absorbing)]
            # Match incident and substrate to n_absorbing to eliminate reflections
            res = multilayer_rt_spectrum(
                wavelengths_nm=wl,
                layers=layers,
                n_incident=n_absorbing,
                n_substrate=n_absorbing,
                pol="p"
            )
            R = res["R"][0]
            T = res["T"][0]
            A = res["A"][0]
            
            # Since index is matched complex-wise, R should be extremely close to 0
            np.testing.assert_allclose(R, 0.0, atol=1e-12)
            
            # Analytical Beer-Lambert transmission
            k = 0.5
            T_analytic = np.exp(-4.0 * np.pi * k * d / 500.0)
            np.testing.assert_allclose(T, T_analytic, rtol=1e-10)
            
            # Energy conservation: R + T + A = 1.0
            np.testing.assert_allclose(R + T + A, 1.0, atol=1e-12)

    def test_energy_residue_returned_and_warnings(self):
        from thinfilm.education import LayerSpec, multilayer_rt_spectrum
        wl = [500.0]
        # Test lossless case: residue should be near 0
        res = multilayer_rt_spectrum(
            wavelengths_nm=wl,
            layers=[LayerSpec(name="Glass", thickness_nm=100.0, n=1.5)],
            n_incident=1.0,
            n_substrate=1.5,
            pol="p"
        )
        assert "energy_residue" in res
        assert res["energy_residue"][0] < 1e-12
        
        # Test warning behavior when active medium (gain) is introduced
        # (Since TMM conjugates inputs, passing n = 2.0 - 0.5j results in 2.0 + 0.5j, which acts as gain)
        with pytest.warns(UserWarning, match="exceeds limit of 1e-5"):
            multilayer_rt_spectrum(
                wavelengths_nm=wl,
                layers=[LayerSpec(name="Active", thickness_nm=200.0, n=2.0 - 0.5j)],
                n_incident=1.0,
                n_substrate=1.5,
                pol="p"
            )

    def test_boundary_poynting_flux_consistency(self):
        """Verify boundary Poynting flux consistency in the characteristic matrix relations.
        
        We compare the net power difference at boundaries:
            A_poynting = (Re(E_in * H_in*) - Re(E_out * H_out*)) / Re(q0)
        against the standard algebraic form:
            A_standard = 1.0 - R - T
        This checks that the characteristic matrix relates boundary fields
        exactly, verifying numerical consistency of field relations.
        """
        from thinfilm.education import LayerSpec, _cos_theta_in_layer, _q_admittance, _layer_matrix
        
        # Multilayer stack: 100 nm Ag, 50 nm TiO2, 100 nm SiO2 (lossy and dispersive-like index)
        n_incident = 1.0
        n_substrate = 1.52
        layers = [
            LayerSpec(name="Ag", thickness_nm=100.0, n=0.05 + 3.13j),
            LayerSpec(name="TiO2", thickness_nm=50.0, n=2.5 + 0.01j),
            LayerSpec(name="SiO2", thickness_nm=100.0, n=1.45 + 0.001j)
        ]
        wl = 500.0
        lam_m = wl * 1e-9
        pol = "p"
        
        # standard TMM
        res = multilayer_rt_spectrum([wl], layers, n_incident=n_incident, n_substrate=n_substrate, theta0_deg=0.0, pol=pol)
        R = res["R"][0]
        T = res["T"][0]
        T_complex = res["t_complex"][0]
        
        # Conjugated indices for physical time convention inside solver
        n0 = np.conj(complex(n_incident))
        ns = np.conj(complex(n_substrate))
        
        cos_theta0 = _cos_theta_in_layer(n0, n0, 0.0)
        cos_thetas = _cos_theta_in_layer(n0, ns, 0.0)
        q0 = _q_admittance(n0, cos_theta0, pol)
        qs = _q_admittance(ns, cos_thetas, pol)
        
        # Calculate matrix product M
        m_total = np.eye(2, dtype=complex)
        for layer in layers:
            n_layer = np.conj(complex(layer.n))
            d_m = float(layer.thickness_nm) * 1e-9
            cos_theta_layer = _cos_theta_in_layer(n0, n_layer, 0.0)
            q_layer = _q_admittance(n_layer, cos_theta_layer, pol)
            delta = 2.0 * np.pi * n_layer * d_m * cos_theta_layer / lam_m
            m_total = m_total @ _layer_matrix(delta, q_layer)
            
        # Exit fields: E_out = t_complex, H_out = qs * t_complex
        # Note: the returned t_complex was conjugated back, so inside TMM it is np.conj(T_complex)
        t = np.conj(T_complex)
        E_out = t
        H_out = qs * t
        
        # Boundary 1 fields via matrix multiplication
        fields_in = m_total @ np.array([E_out, H_out], dtype=complex)
        E_in = fields_in[0]
        H_in = fields_in[1]
        
        # Poynting fluxes
        P_in = np.real(E_in * np.conj(H_in))
        P_out = np.real(E_out * np.conj(H_out))
        
        # Normalized Poynting absorption
        A_poynting = (P_in - P_out) / np.real(q0)
        
        # Verify Poynting absorption matches 1.0 - R - T
        A_standard = 1.0 - R - T
        np.testing.assert_allclose(A_poynting, A_standard, atol=1e-12)


class TestAnalyticalValidation:
    def test_analytical_validations(self):
        from thinfilm.validation import run_all_analytical_validations
        res = run_all_analytical_validations()
        assert res["all_valid"]
        assert res["fresnel"]["max_diff_s"] < 1e-12
        assert res["fresnel"]["max_diff_p"] < 1e-12
        assert res["brewster"]["R_p_at_brewster"] < 1e-12
        assert res["quarter_wave_ar"]["R_matched"] < 1e-12
        assert res["quarter_wave_ar"]["difference"] < 1e-12
        assert res["dbr_analytical"]["max_difference"] < 1e-12
        assert res["single_layer_airy"]["max_diff_r"] < 1e-12
        assert res["single_layer_airy"]["max_diff_t"] < 1e-12
        assert res["single_layer_airy"]["max_phase_diff_r"] < 1e-12
        assert res["single_layer_airy"]["max_phase_diff_t"] < 1e-12
        assert res["multilayer_recursive_fresnel"]["max_diff_r"] < 1e-12
        assert res["multilayer_recursive_fresnel"]["max_diff_t"] < 1e-12
        assert res["multilayer_recursive_fresnel"]["max_diff_A"] < 1e-12
        assert res["multilayer_recursive_fresnel"]["max_phase_diff_r"] < 1e-12
        assert res["multilayer_recursive_fresnel"]["max_phase_diff_t"] < 1e-12

