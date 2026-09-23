import json

import numpy as np
import pytest

from app import main, packaged_tamm
from thinfilm.solvers.generaltmm_adapter import (
    multilayer_field_comparison as native_field_comparison,
    sweep_multilayer as native_sweep_multilayer,
)


def test_packaged_tamm_routes_away_from_native_extension(monkeypatch):
    monkeypatch.setattr(main.sys, "frozen", True, raising=False)
    result = main._generaltmm_call(
        "sweep_multilayer", wavelengths_nm=[500, 510], n_incident=1 + 0j,
        layer_indices=[2 + 0j], layer_thickness_nm=[100], n_substrate=1.5 + 0j,
    )
    assert result["solver"] == "pythinfilm-isotropic-tmm"
    assert len(result["R"]) == 2


@pytest.mark.parametrize("beta", [0.0, 0.35])
@pytest.mark.parametrize("polarization", ["p", "s"])
def test_isotropic_packaged_tamm_matches_native_spectrum_and_field(beta, polarization):
    source = json.loads((main.PYTHINFILM_ROOT / "web3d/public/results/tamm_phase_bundle.json").read_text(encoding="utf-8-sig"))
    metal, high, low = source["layers"][:3]
    layers = [metal, *[layer for _ in range(3) for layer in (high, low)], high]
    arguments = {
        "wavelengths_nm": [500.0, 510.0],
        "n_incident": complex(source["ambient"]["n"]),
        "layer_indices": [complex(layer["n_real"], layer.get("n_imag", 0)) for layer in layers],
        "layer_thickness_nm": [layer["thickness_nm"] for layer in layers],
        "n_substrate": complex(source["substrate"]["n"]),
        "beta": beta,
    }
    packaged = packaged_tamm.sweep_multilayer(**arguments)
    native = native_sweep_multilayer(**arguments)
    for key in ("R", "T", "A", "R_s", "T_s", "A_s", "phase_p_deg", "phase_s_deg"):
        np.testing.assert_allclose(packaged[key], native[key], rtol=1e-8, atol=1e-8)

    field_args = {key: value for key, value in arguments.items() if key != "wavelengths_nm"}
    field_args["polarization"] = polarization
    packaged_field = packaged_tamm.multilayer_field_comparison(spectrum=packaged, **field_args)
    native_field = native_field_comparison(spectrum=native, **field_args)
    for p_profile, n_profile in zip(packaged_field["profiles"], native_field["profiles"]):
        np.testing.assert_allclose(p_profile["electric_intensity"], n_profile["electric_intensity"], rtol=1e-7, atol=1e-7)
    assert packaged_field["validation"]["tangential_e_continuity_passed"]
