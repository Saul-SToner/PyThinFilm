import json
from pathlib import Path

import numpy as np
import pytest

from thinfilm.education import simulate_report_case
from tools.export_visualization_cases import (
    ADDITIONAL_TEACHING_CASES,
    compute_hash,
    compute_physics_hashes,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "web3d" / "public" / "results"


@pytest.mark.parametrize("case_id", list(ADDITIONAL_TEACHING_CASES))
def test_visualization_export_matches_python_te_tm(case_id: str) -> None:
    exported = json.loads((RESULTS / f"{case_id}.json").read_text(encoding="utf-8"))
    assert exported["case_id"] == case_id
    assert exported["calculation_source"] == "python_export"

    for polarization, python_pol in (("TE", "s"), ("TM", "p")):
        calculated = simulate_report_case(case_id, theta_deg=45.0, pol=python_pol)
        np.testing.assert_allclose(exported["wavelength_nm"], calculated["wavelength_nm"], atol=5.1e-3, rtol=0)
        for quantity in ("R", "T", "A"):
            np.testing.assert_allclose(exported[polarization][quantity], calculated[quantity], atol=5.1e-7, rtol=0)
        np.testing.assert_allclose(
            np.asarray(exported[polarization]["R"])
            + np.asarray(exported[polarization]["T"])
            + np.asarray(exported[polarization]["A"]),
            1.0,
            atol=1.1e-6,
            rtol=0,
        )

    calculated_layers = simulate_report_case(case_id, theta_deg=45.0, pol="s")["layers"]
    assert [layer["type"] for layer in exported["layers"]] == [layer["name"] for layer in calculated_layers]
    assert [layer["thickness_nm"] for layer in exported["layers"]] == [
        round(layer["thickness_nm"], 4) for layer in calculated_layers
    ]

    physics_input_hash, physics_result_hash = compute_physics_hashes(exported)
    assert exported["physics_input_hash"] == physics_input_hash
    assert exported["physics_result_hash"] == physics_result_hash
    result_hash = exported.pop("result_hash")
    assert result_hash == compute_hash(exported)
