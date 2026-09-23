"""Tests for real-material spectrum calculations.

These tests verify the material loading and dispersive TMM pipeline.
They use data from data/real_nk/ which is part of the repository.
"""

from __future__ import annotations

import numpy as np
import pytest

from thinfilm.education import (
    LayerSpec,
    multilayer_rt_spectrum,
    multilayer_rt_spectrum_real_materials,
    quarter_wave_thickness_nm,
)
from thinfilm.materials import (
    common_wavelength_window_um,
    list_real_materials,
    load_real_material,
    material_complex_index,
    material_nk_at,
)


# ---------------------------------------------------------------------------
# 1. Material loading
# ---------------------------------------------------------------------------

class TestMaterialLoading:
    """Verify manifest and CSV loading."""

    def test_manifest_has_entries(self):
        materials = list_real_materials()
        assert len(materials) >= 5

    def test_load_sio2(self):
        ds = load_real_material("SiO2")
        assert ds.material == "SiO2"
        assert len(ds.lambda_um) > 100
        assert ds.lambda_min_um < 1.0
        assert ds.lambda_max_um > 5.0

    def test_load_mgf2(self):
        ds = load_real_material("MgF2")
        assert ds.material == "MgF2"
        assert len(ds.lambda_um) > 100

    def test_load_gold(self):
        ds = load_real_material("Au")
        assert ds.material == "Au"
        assert np.any(ds.k > 0)  # Au is metallic, should have k > 0

    def test_load_air(self):
        ds = load_real_material("Air")
        assert ds.material == "Air"
        np.testing.assert_array_equal(ds.n, np.ones_like(ds.n))
        np.testing.assert_array_equal(ds.k, np.zeros_like(ds.k))


# ---------------------------------------------------------------------------
# 2. Material n/k interpolation
# ---------------------------------------------------------------------------

class TestMaterialInterpolation:
    """Verify n/k interpolation at specific wavelengths."""

    def test_sio2_n_at_550nm(self):
        n, k = material_nk_at("SiO2", 0.55)
        # SiO2 at 550nm: n ≈ 1.46, k ≈ 0
        assert 1.40 < n < 1.50
        assert abs(k) < 0.01

    def test_mgf2_n_at_550nm(self):
        n, k = material_nk_at("MgF2", 0.55)
        # MgF2 at 550nm: n ≈ 1.38
        assert 1.35 < n < 1.42

    def test_extrapolation_rejected(self):
        with pytest.raises(ValueError):
            material_nk_at("SiO2", 10.0, out_of_range_policy="error")  # Outside range

    def test_extrapolation_allowed(self):
        n, k = material_nk_at("SiO2", 10.0, allow_extrapolate=True)
        assert np.isfinite(n)


# ---------------------------------------------------------------------------
# 3. Complex refractive index
# ---------------------------------------------------------------------------

class TestComplexIndex:
    """Verify complex index computation."""

    def test_complex_index_shape(self):
        n_complex = material_complex_index("SiO2", [400, 550, 800])
        assert n_complex.shape == (3,)

    def test_imaginary_part_zero_for_dielectric(self):
        n_complex = material_complex_index("SiO2", [550])
        assert abs(np.imag(n_complex[0])) < 0.01

    def test_imaginary_part_nonzero_for_metal(self):
        n_complex = material_complex_index("Au", [550])
        assert np.abs(np.imag(n_complex[0])) > 0.1


# ---------------------------------------------------------------------------
# 4. Common wavelength window
# ---------------------------------------------------------------------------

class TestWavelengthWindow:
    """Verify overlapping wavelength window calculation."""

    def test_sio2_mgf2_overlap(self):
        lo, hi = common_wavelength_window_um(["SiO2", "MgF2"])
        assert lo < hi
        assert lo > 0.2
        assert hi > 5.0

    def test_single_material_window(self):
        lo, hi = common_wavelength_window_um(["SiO2"])
        assert lo < hi


# ---------------------------------------------------------------------------
# 5. Dispersive TMM spectrum
# ---------------------------------------------------------------------------

class TestDispersiveSpectrum:
    """Verify multilayer_rt_spectrum_real_materials with dispersive materials."""

    def test_single_layer_real_material(self):
        """Single-layer AR using real SiO2 n/k data."""
        n_sio2_550 = float(np.real(material_complex_index("SiO2", 550)))
        layers = [LayerSpec("SiO2", n_sio2_550, quarter_wave_thickness_nm(550, n_sio2_550))]
        wavelengths = np.linspace(400, 800, 100)

        # Constant-index version
        result_const = multilayer_rt_spectrum(
            wavelengths, layers, n_incident=1.0, n_substrate=1.52,
        )

        # Real-material version
        result_real = multilayer_rt_spectrum_real_materials(
            wavelengths, layers,
            design_type="single_ar",
            material_map={"n_low": "SiO2"},
            role_fallback_indices={"n_incident": 1.0, "n_substrate": 1.52},
            allow_extrapolate=True,
        )

        # Both should have valid outputs
        assert result_const["R"].shape == (100,)
        assert result_real["R"].shape == (100,)
        assert np.all(np.isfinite(result_const["R"]))
        assert np.all(np.isfinite(result_real["R"]))

    def test_energy_conservation_real_materials(self):
        """Energy conservation should hold for real-material dispersive TMM."""
        n_sio2_550 = float(np.real(material_complex_index("SiO2", 550)))
        layers = [LayerSpec("SiO2", n_sio2_550, quarter_wave_thickness_nm(550, n_sio2_550))]
        wavelengths = np.linspace(400, 800, 100)

        result = multilayer_rt_spectrum_real_materials(
            wavelengths, layers,
            design_type="single_ar",
            material_map={"n_low": "SiO2"},
            role_fallback_indices={"n_incident": 1.0, "n_substrate": 1.52},
            allow_extrapolate=True,
        )
        total = result["R"] + result["T"] + result["A"]
        np.testing.assert_allclose(total, 1.0, atol=1e-10)


# ---------------------------------------------------------------------------
# 6. Performance-relevant: multiple materials, wide spectrum
# ---------------------------------------------------------------------------

class TestMultiMaterialSpectrum:
    """Test with multiple dispersive materials across wide spectrum."""

    def test_bragg_with_real_materials(self):
        """Bragg reflector using real MgF2 and TiO2."""
        n_mgf2_550 = float(np.real(material_complex_index("MgF2", 550)))
        n_tio2_550 = float(np.real(material_complex_index("TiO2", 550)))

        d_l = quarter_wave_thickness_nm(550, n_mgf2_550)
        d_h = quarter_wave_thickness_nm(550, n_tio2_550)

        layers = [
            LayerSpec("H", n_tio2_550, d_h),
            LayerSpec("L", n_mgf2_550, d_l),
            LayerSpec("H", n_tio2_550, d_h),
        ]

        wavelengths = np.linspace(400, 800, 600)

        # Constant-index baseline
        result_const = multilayer_rt_spectrum(
            wavelengths, layers, n_incident=1.0, n_substrate=1.52,
        )

        # Real-material version
        result_real = multilayer_rt_spectrum_real_materials(
            wavelengths, layers,
            design_type="bragg_reflector",
            material_map={"n_high": "TiO2", "n_low": "MgF2"},
            role_fallback_indices={"n_incident": 1.0, "n_substrate": 1.52},
            allow_extrapolate=True,
        )

        assert result_const["R"].shape == (600,)
        assert result_real["R"].shape == (600,)
        np.testing.assert_allclose(result_const["R"] + result_const["T"], 1.0, atol=1e-10)
        np.testing.assert_allclose(result_real["R"] + result_real["T"], 1.0, atol=1e-10)
