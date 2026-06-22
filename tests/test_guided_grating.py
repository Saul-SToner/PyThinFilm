"""Tests for the guided_grating module: comsol_io, spectra, solver, models."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import numpy as np
import pytest

from guided_grating.comsol_io import (
    _clean_header_name,
    _leading_float,
    _normalize_sweep_name,
    _sweep_scale_and_unit,
    load_comsol_grating_csv,
    load_comsol_two_param_sweep,
)
from guided_grating.models import GratingSweepConfig, GuidedGratingSpec
from guided_grating.solver import (
    _default_wavelength_grid_nm,
    simulate_guided_grating_placeholder,
    validate_guided_grating_spec,
)
from guided_grating.spectra import (
    summarize_guided_grating_spectrum,
    summarize_lambda_period_sweep,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def _make_grating_csv(path: Path) -> None:
    """Standard COMSOL grating global-table CSV."""
    rows = [
        ["% Model", "test_grating"],
        ["% Type", "global_table"],
        ["% Date", "2025-01-01"],
        ["% Param", "period=980nm"],
        ["% wavelength (m)", "unused1", "unused2", "unused3", "unused4", "unused5", "R(1)", "T(1)", "unused8", "A(1)", "R+T"],
        ["1.500e-6", "", "", "", "", "", "0.05", "0.93", "", "0.02", "0.98"],
        ["1.520e-6", "", "", "", "", "", "0.08", "0.90", "", "0.02", "0.98"],
        ["1.550e-6", "", "", "", "", "", "0.15", "0.83", "", "0.02", "0.98"],
        ["1.580e-6", "", "", "", "", "", "0.08", "0.90", "", "0.02", "0.98"],
        ["1.600e-6", "", "", "", "", "", "0.05", "0.93", "", "0.02", "0.98"],
    ]
    _write_csv(path, rows)


def _make_sweep_csv(path: Path) -> None:
    """COMSOL wavelength + period sweep CSV."""
    rows = [
        ["% Model: sweep"],
        ["% Type: sweep_table"],
        ["% Date: 2025-01-01"],
        ["% Param: sweep"],
        ["% lambda (m)", "period (m)", "unused2", "unused3", "unused4", "unused5", "unused6", "R(1)", "T(1)", "unused9", "A(1)", "R+T"],
    ]
    # Two period values, 3 wavelengths each
    for period_m in ["960e-9", "980e-9"]:
        for wl_m in ["1.500e-6", "1.550e-6", "1.600e-6"]:
            rows.append([wl_m, period_m, "", "", "", "", "", "0.10", "0.88", "", "0.02", "0.98"])
    _write_csv(path, rows)


# ---------------------------------------------------------------------------
# 1. _leading_float
# ---------------------------------------------------------------------------

class TestLeadingFloat:
    def test_simple_integer(self):
        assert _leading_float("42") == 42.0

    def test_simple_float(self):
        assert _leading_float("3.14") == 3.14

    def test_with_suffix(self):
        assert _leading_float("0.95 + 0.01i") == 0.95

    def test_negative(self):
        assert _leading_float("-2.5e-3") == -2.5e-3

    def test_scientific(self):
        assert _leading_float("1.5e-6") == 1.5e-6

    def test_invalid(self):
        with pytest.raises(ValueError):
            _leading_float("abc")


# ---------------------------------------------------------------------------
# 2. _clean_header_name
# ---------------------------------------------------------------------------

class TestCleanHeaderName:
    def test_strip_percent(self):
        assert _clean_header_name("% wavelength (m)") == "wavelength"

    def test_strip_unit(self):
        assert _clean_header_name("R(1)") == "R"

    def test_no_parens(self):
        assert _clean_header_name("period") == "period"


# ---------------------------------------------------------------------------
# 3. _normalize_sweep_name
# ---------------------------------------------------------------------------

class TestNormalizeSweepName:
    def test_basic(self):
        assert _normalize_sweep_name("Period") == "period"

    def test_spaces(self):
        assert _normalize_sweep_name("fill factor") == "fill_factor"


# ---------------------------------------------------------------------------
# 4. _sweep_scale_and_unit
# ---------------------------------------------------------------------------

class TestSweepScaleAndUnit:
    def test_fill_factor(self):
        scale, unit = _sweep_scale_and_unit("fill_factor")
        assert scale == 1.0
        assert unit == "value"

    def test_ff(self):
        scale, unit = _sweep_scale_and_unit("ff")
        assert scale == 1.0

    def test_period(self):
        scale, unit = _sweep_scale_and_unit("period")
        assert scale == 1e9
        assert unit == "nm"


# ---------------------------------------------------------------------------
# 5. load_comsol_grating_csv
# ---------------------------------------------------------------------------

class TestLoadComsolGratingCSV:
    def test_load(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        _make_grating_csv(csv_path)
        result = load_comsol_grating_csv(csv_path)
        assert result["backend"] == "comsol_csv"
        assert not result["is_placeholder"]
        assert len(result["wavelength_nm"]) == 5
        assert result["R"].shape == (5,)

    def test_wavelengths_in_nm(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        _make_grating_csv(csv_path)
        result = load_comsol_grating_csv(csv_path)
        np.testing.assert_allclose(result["wavelength_nm"], [1500, 1520, 1550, 1580, 1600])

    def test_r_values(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        _make_grating_csv(csv_path)
        result = load_comsol_grating_csv(csv_path)
        np.testing.assert_allclose(result["R"], [0.05, 0.08, 0.15, 0.08, 0.05])

    def test_too_short(self, tmp_path):
        csv_path = tmp_path / "short.csv"
        _write_csv(csv_path, [["a"], ["b"]])
        with pytest.raises(ValueError, match="too short"):
            load_comsol_grating_csv(csv_path)

    def test_no_data_rows(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        rows = [
            ["% m1"], ["% m2"], ["% m3"], ["% m4"],
            ["% wl", "R", "T"],
            # row 5 is the only data row, but it's text, not numeric
            ["abc", "def", "ghi"],
        ]
        _write_csv(csv_path, rows)
        # Function tries float(row[0]) on non-numeric data -> ValueError
        with pytest.raises(ValueError):
            load_comsol_grating_csv(csv_path)

    def test_meta_extracted(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        _make_grating_csv(csv_path)
        result = load_comsol_grating_csv(csv_path)
        # Meta keys are stripped of "% " prefix
        assert len(result["meta"]) > 0


# ---------------------------------------------------------------------------
# 6. load_comsol_two_param_sweep
# ---------------------------------------------------------------------------

class TestLoadComsolTwoParamSweep:
    def test_load(self, tmp_path):
        csv_path = tmp_path / "sweep.csv"
        _make_sweep_csv(csv_path)
        result = load_comsol_two_param_sweep(csv_path)
        assert result["backend"] == "comsol_csv_sweep"
        assert len(result["sweep_groups"]) == 2

    def test_group_wavelengths(self, tmp_path):
        csv_path = tmp_path / "sweep.csv"
        _make_sweep_csv(csv_path)
        result = load_comsol_two_param_sweep(csv_path)
        for key, group in result["sweep_groups"].items():
            assert len(group["wavelength_nm"]) == 3

    def test_sweep_name_detected(self, tmp_path):
        csv_path = tmp_path / "sweep.csv"
        _make_sweep_csv(csv_path)
        result = load_comsol_two_param_sweep(csv_path)
        assert result["sweep_name"] == "period"

    def test_override_sweep_name(self, tmp_path):
        csv_path = tmp_path / "sweep.csv"
        _make_sweep_csv(csv_path)
        result = load_comsol_two_param_sweep(csv_path, sweep_name="t_wg")
        assert result["sweep_name"] == "t_wg"

    def test_too_short(self, tmp_path):
        csv_path = tmp_path / "short.csv"
        _write_csv(csv_path, [["a"], ["b"]])
        with pytest.raises(ValueError, match="too short"):
            load_comsol_two_param_sweep(csv_path)

    def test_header_too_short(self, tmp_path):
        csv_path = tmp_path / "bad_header.csv"
        rows = [
            ["% m1"], ["% m2"], ["% m3"], ["% m4"],
            ["% wl", "param", "R"],
            ["1.5e-6", "0.5", "0.1"],
        ]
        _write_csv(csv_path, rows)
        with pytest.raises(ValueError, match="header is too short"):
            load_comsol_two_param_sweep(csv_path)


# ---------------------------------------------------------------------------
# 7. GuidedGratingSpec
# ---------------------------------------------------------------------------

class TestGuidedGratingSpec:
    def test_creation(self):
        spec = GuidedGratingSpec(
            sample_id="test",
            period_nm=980,
            waveguide_thickness_nm=220,
            grating_thickness_nm=50,
            fill_factor=0.55,
            n_incident=1.0,
            n_waveguide=3.4,
            n_grating=1.5,
            n_substrate=1.45,
        )
        assert spec.period_nm == 980
        assert spec.pol == "TE"

    def test_to_dict(self):
        spec = GuidedGratingSpec(
            sample_id="test", period_nm=980, waveguide_thickness_nm=220,
            grating_thickness_nm=50, fill_factor=0.55, n_incident=1.0,
            n_waveguide=3.4, n_grating=1.5, n_substrate=1.45,
        )
        d = spec.to_dict()
        assert d["period_nm"] == 980
        assert isinstance(d, dict)

    def test_frozen(self):
        spec = GuidedGratingSpec(
            sample_id="test", period_nm=980, waveguide_thickness_nm=220,
            grating_thickness_nm=50, fill_factor=0.55, n_incident=1.0,
            n_waveguide=3.4, n_grating=1.5, n_substrate=1.45,
        )
        with pytest.raises(AttributeError):
            spec.period_nm = 1000


# ---------------------------------------------------------------------------
# 8. validate_guided_grating_spec
# ---------------------------------------------------------------------------

class TestValidateGuidedGratingSpec:
    def _valid_spec(self, **overrides):
        defaults = dict(
            sample_id="test", period_nm=980, waveguide_thickness_nm=220,
            grating_thickness_nm=50, fill_factor=0.55, n_incident=1.0,
            n_waveguide=3.4, n_grating=1.5, n_substrate=1.45,
        )
        defaults.update(overrides)
        return GuidedGratingSpec(**defaults)

    def test_valid(self):
        validate_guided_grating_spec(self._valid_spec())

    def test_zero_period(self):
        with pytest.raises(ValueError, match="period_nm"):
            validate_guided_grating_spec(self._valid_spec(period_nm=0))

    def test_negative_waveguide(self):
        with pytest.raises(ValueError, match="waveguide_thickness"):
            validate_guided_grating_spec(self._valid_spec(waveguide_thickness_nm=-1))

    def test_fill_factor_zero(self):
        with pytest.raises(ValueError, match="fill_factor"):
            validate_guided_grating_spec(self._valid_spec(fill_factor=0.0))

    def test_fill_factor_one(self):
        with pytest.raises(ValueError, match="fill_factor"):
            validate_guided_grating_spec(self._valid_spec(fill_factor=1.0))

    def test_negative_index(self):
        with pytest.raises(ValueError, match="refractive indices"):
            validate_guided_grating_spec(self._valid_spec(n_waveguide=-1.0))

    def test_invalid_pol(self):
        with pytest.raises(ValueError, match="pol"):
            validate_guided_grating_spec(self._valid_spec(pol="invalid"))


# ---------------------------------------------------------------------------
# 9. simulate_guided_grating_placeholder
# ---------------------------------------------------------------------------

class TestSimulateGuidedGratingPlaceholder:
    def _valid_spec(self, **overrides):
        defaults = dict(
            sample_id="test", period_nm=980, waveguide_thickness_nm=220,
            grating_thickness_nm=50, fill_factor=0.55, n_incident=1.0,
            n_waveguide=3.4, n_grating=1.5, n_substrate=1.45, pol="TE",
        )
        defaults.update(overrides)
        return GuidedGratingSpec(**defaults)

    def test_returns_all_keys(self):
        result = simulate_guided_grating_placeholder(self._valid_spec())
        assert "wavelength_nm" in result
        assert "R" in result
        assert "T" in result
        assert "A" in result
        assert result["is_placeholder"] is True

    def test_energy_conservation(self):
        result = simulate_guided_grating_placeholder(self._valid_spec())
        total = result["R"] + result["T"] + result["A"]
        np.testing.assert_array_less(total, 1.0 + 1e-10)

    def test_custom_wavelengths(self):
        wl = np.linspace(1500, 1600, 50)
        result = simulate_guided_grating_placeholder(self._valid_spec(), wavelengths_nm=wl)
        assert len(result["wavelength_nm"]) == 50

    def test_with_sweep_config(self):
        sweep = GratingSweepConfig(1450, 1650, 1.0)
        result = simulate_guided_grating_placeholder(self._valid_spec(), sweep=sweep)
        assert len(result["wavelength_nm"]) > 100

    def test_tm_pol_shift(self):
        spec_te = self._valid_spec(pol="TE")
        spec_tm = self._valid_spec(pol="TM")
        r_te = simulate_guided_grating_placeholder(spec_te)
        r_tm = simulate_guided_grating_placeholder(spec_tm)
        # TM should have a different resonance center
        assert abs(r_te["resonance_center_estimate_nm"] - r_tm["resonance_center_estimate_nm"]) > 1.0


# ---------------------------------------------------------------------------
# 10. _default_wavelength_grid_nm
# ---------------------------------------------------------------------------

class TestDefaultWavelengthGrid:
    def test_default(self):
        spec = GuidedGratingSpec(
            sample_id="test", period_nm=980, waveguide_thickness_nm=220,
            grating_thickness_nm=50, fill_factor=0.55, n_incident=1.0,
            n_waveguide=3.4, n_grating=1.5, n_substrate=1.45,
        )
        wl = _default_wavelength_grid_nm(spec)
        assert len(wl) > 100
        assert wl[0] < spec.lambda0_nm
        assert wl[-1] > spec.lambda0_nm

    def test_with_sweep(self):
        spec = GuidedGratingSpec(
            sample_id="test", period_nm=980, waveguide_thickness_nm=220,
            grating_thickness_nm=50, fill_factor=0.55, n_incident=1.0,
            n_waveguide=3.4, n_grating=1.5, n_substrate=1.45,
        )
        sweep = GratingSweepConfig(1400, 1700, 0.5)
        wl = _default_wavelength_grid_nm(spec, sweep)
        assert len(wl) == 601


# ---------------------------------------------------------------------------
# 11. summarize_guided_grating_spectrum
# ---------------------------------------------------------------------------

class TestSummarizeGratingSpectrum:
    def _mock_result(self):
        wl = np.linspace(1500, 1600, 201)
        # Gaussian peak at 1550 nm
        r = 0.8 * np.exp(-((wl - 1550) / 5) ** 2) + 0.05
        t = 1.0 - r - 0.02
        a = np.full_like(wl, 0.02)
        return {
            "wavelength_nm": wl,
            "R": r,
            "T": t,
            "A": a,
            "backend": "test",
            "is_placeholder": False,
        }

    def test_peak_wavelength(self):
        s = summarize_guided_grating_spectrum(self._mock_result())
        assert abs(s["peak_wavelength_nm"] - 1550) < 1.0

    def test_peak_reflectance(self):
        s = summarize_guided_grating_spectrum(self._mock_result())
        assert s["peak_reflectance"] > 0.8

    def test_fwhm_positive(self):
        s = summarize_guided_grating_spectrum(self._mock_result())
        assert s["fwhm_nm"] > 0

    def test_num_points(self):
        s = summarize_guided_grating_spectrum(self._mock_result())
        assert s["num_points"] == 201


# ---------------------------------------------------------------------------
# 12. summarize_lambda_period_sweep
# ---------------------------------------------------------------------------

class TestSummarizeLambdaPeriodSweep:
    def _mock_bundle(self):
        groups = {}
        for i, period in enumerate([960, 980, 1000]):
            wl = np.linspace(1500, 1600, 101)
            peak_wl = 1540 + i * 10  # peaks shift with period
            r = 0.7 * np.exp(-((wl - peak_wl) / 8) ** 2) + 0.05
            t = 1.0 - r - 0.02
            a = np.full_like(wl, 0.02)
            key = f"{period:.6f}"
            groups[key] = {
                "spec": {
                    "period_nm": period,
                    "period_nm_nm": float(period),
                },
                "wavelength_nm": wl,
                "R": r,
                "T": t,
                "A": a,
            }
        return {
            "sample_id": "test_sweep",
            "source_csv": "test.csv",
            "backend": "test",
            "sweep_name": "period",
            "sweep_display_unit": "nm",
            "sweep_groups": groups,
        }

    def test_best_candidate(self):
        result = summarize_lambda_period_sweep(self._mock_bundle(), target_wavelength_nm=1550)
        assert "best_candidate" in result
        assert result["num_periods"] == 3

    def test_sorted_by_target_error(self):
        result = summarize_lambda_period_sweep(self._mock_bundle(), target_wavelength_nm=1550)
        errors = [row["target_error_nm"] for row in result["period_summaries"]]
        assert errors == sorted(errors)
