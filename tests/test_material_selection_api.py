"""Tests for the material-selection APP API module."""
from __future__ import annotations
import math
import pytest
from thinfilm.api import (
    get_material_roles_for_design,
    list_materials_for_app,
    simulate_with_material_selection,
    simulate_teaching_design_real_materials,
)

class TestListMaterialsForApp:
    def setup_method(self):
        self.catalog = list_materials_for_app()
    def test_returns_list(self):
        assert isinstance(self.catalog, list)
        assert len(self.catalog) >= 7
    def test_required_keys(self):
        required = {"id","display_name","display_name_en","category","suitable_roles","locked_roles","lambda_min_nm","lambda_max_nm","n_at_550nm","k_at_550nm"}
        for entry in self.catalog:
            assert required <= entry.keys()
    def test_known_materials_present(self):
        ids = {m["id"] for m in self.catalog}
        for expected in ("Air","SiO2","MgF2","Al2O3","TiO2","Si","Ag","Au"):
            assert expected in ids
    def test_n_at_550nm_physical(self):
        for m in self.catalog:
            n = m["n_at_550nm"]
            assert math.isfinite(n)
            # Metals (Ag, Au) have n < 1 in the visible range due to plasma
            # effects - that is physically correct, so only check dielectrics.
            if m["category"] != "金属":
                assert n >= 1.0, f'{m["id"]}: n={n}'
    def test_k_at_550nm_nonnegative(self):
        for m in self.catalog:
            assert m["k_at_550nm"] >= 0.0
    def test_sio2_n_range(self):
        sio2 = next(m for m in self.catalog if m["id"] == "SiO2")
        assert 1.44 <= sio2["n_at_550nm"] <= 1.48
    def test_tio2_n_range(self):
        tio2 = next(m for m in self.catalog if m["id"] == "TiO2")
        assert 2.3 <= tio2["n_at_550nm"] <= 2.8
    def test_mgf2_suitable_for_n_low(self):
        mgf2 = next(m for m in self.catalog if m["id"] == "MgF2")
        assert "n_low" in mgf2["suitable_roles"]
    def test_metals_suitable_for_substrate(self):
        for mat_id in ("Ag","Au"):
            m = next(x for x in self.catalog if x["id"] == mat_id)
            assert "n_substrate" in m["suitable_roles"]
    def test_json_serialisable(self):
        import json
        json.dumps(self.catalog)

class TestGetMaterialRolesForDesign:
    @pytest.mark.parametrize("design_type", ["single_ar","double_ar","high_reflector","fp_filter","neutral_beamsplitter"])
    def test_schema_structure(self, design_type):
        schema = get_material_roles_for_design(design_type)
        assert schema["design_type"] == design_type
        roles = schema["roles"]
        assert len(roles) >= 2
        for role_key, role_info in roles.items():
            assert "label" in role_info
            assert len(role_info["options"]) >= 1
            assert role_info["default"] in role_info["options"]
            assert isinstance(role_info["locked"], bool)
    def test_n_incident_is_locked(self):
        schema = get_material_roles_for_design("single_ar")
        assert schema["roles"]["n_incident"]["locked"] is True
    def test_n_low_not_locked(self):
        schema = get_material_roles_for_design("high_reflector")
        assert schema["roles"]["n_low"]["locked"] is False
    def test_mgf2_sio2_in_n_low_options(self):
        schema = get_material_roles_for_design("single_ar")
        opts = schema["roles"]["n_low"]["options"]
        assert "MgF2" in opts
        assert "SiO2" in opts
    def test_normalises_case(self):
        schema = get_material_roles_for_design("Single_AR")
        assert schema["design_type"] == "single_ar"
    def test_json_serialisable(self):
        import json
        json.dumps(get_material_roles_for_design("high_reflector"))

class TestSimulateWithMaterialSelection:
    def test_single_ar_mgf2_runs(self):
        result = simulate_with_material_selection("single_ar",{"n_low":"MgF2"},lambda0_nm=550.0,warn_range=False)
        assert result["material_model"] == "real_nk"
        assert "R_at_lambda0" in result["summary"]
    def test_energy_conservation(self):
        import numpy as np
        result = simulate_with_material_selection("single_ar",{"n_low":"MgF2"},lambda0_nm=550.0,warn_range=False)
        total = np.asarray(result["R"]) + np.asarray(result["T"]) + np.asarray(result["A"])
        assert float(max(abs(total - 1.0))) < 1e-6
    def test_matches_real_materials_engine(self):
        import numpy as np
        wl = list(range(430,751,5))
        r_new = np.asarray(simulate_with_material_selection("single_ar",{"n_low":"MgF2"},lambda0_nm=550.0,wavelengths_nm=wl,warn_range=False)["R"])
        r_old = np.asarray(simulate_teaching_design_real_materials("single_ar",material_map={"n_low":"MgF2"},wavelengths_nm=wl,lambda0_nm=550.0)["R"])
        assert float(max(abs(r_new - r_old))) < 1e-10
    def test_high_reflector_peak(self):
        result = simulate_with_material_selection("high_reflector",{"n_low":"SiO2","n_high":"TiO2"},lambda0_nm=550.0,warn_range=False)
        assert result["summary"]["R_max"] > 0.95
    def test_material_map_recorded(self):
        result = simulate_with_material_selection("single_ar",{"n_low":"SiO2"},lambda0_nm=550.0,warn_range=False)
        assert result["material_map"].get("n_low") == "SiO2"
    def test_warn_range_fires(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # allow_extrapolate=True so the engine does not raise before we
            # get a chance to capture the UserWarning emitted by our API layer.
            simulate_with_material_selection(
                "single_ar", {"n_low": "TiO2"}, lambda0_nm=380.0,
                warn_range=True, allow_extrapolate=True,
            )
        assert any(issubclass(x.category, UserWarning) for x in w)
    def test_empty_selection_uses_defaults(self):
        result = simulate_with_material_selection("single_ar",{},lambda0_nm=550.0,warn_range=False)
        assert "R" in result and "T" in result
