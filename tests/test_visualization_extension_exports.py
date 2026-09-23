import json
from pathlib import Path

import numpy as np
import pytest

from tools.export_visualization_cases import compute_hash, compute_physics_hashes
from tools.export_visualization_extension_cases import (
    EXTENSION_VISUALIZATION_CASES,
    export_guided_grating_emt,
    export_material_library_demo,
    export_pdrc,
    export_rugate_table,
    export_smart_window,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "web3d" / "public" / "results"
EXPORTERS = {
    "app_smart_window": export_smart_window,
    "guided_grating_emt": export_guided_grating_emt,
    "mat_library_demo": export_material_library_demo,
    "pdrc_cooling_bundle": export_pdrc,
    "rugate_80layer_table": export_rugate_table,
}


@pytest.mark.parametrize("case_id", list(EXTENSION_VISUALIZATION_CASES))
def test_extension_contract_recomputes_from_python(case_id: str) -> None:
    exported = json.loads((RESULTS / f"{case_id}.json").read_text(encoding="utf-8"))
    recomputed = EXPORTERS[case_id]()

    assert exported["case_id"] == case_id
    assert exported["calculation_source"] == "python_export"
    assert len(exported["layers"]) == EXTENSION_VISUALIZATION_CASES[case_id]
    assert exported["wavelength_nm"] == recomputed["wavelength_nm"]
    assert exported["layers"] == recomputed["layers"]
    for polarization in ("TE", "TM"):
        for quantity in ("R", "T", "A"):
            np.testing.assert_allclose(
                exported[polarization][quantity], recomputed[polarization][quantity], atol=5.1e-7, rtol=0
            )
        np.testing.assert_allclose(
            np.asarray(exported[polarization]["R"])
            + np.asarray(exported[polarization]["T"])
            + np.asarray(exported[polarization]["A"]),
            1.0,
            atol=1.1e-6,
            rtol=0,
        )

    input_hash, result_hash = compute_physics_hashes(exported)
    assert exported["physics_input_hash"] == input_hash
    assert exported["physics_result_hash"] == result_hash
    final_hash = exported.pop("result_hash")
    assert final_hash == compute_hash(exported)


def test_emt_contract_exposes_invalidity_boundary() -> None:
    exported = json.loads((RESULTS / "guided_grating_emt.json").read_text(encoding="utf-8"))
    assert exported["emt_applicability"]["rho"] >= 1.0
    assert exported["emt_applicability"]["status"] == "rejected"
    assert exported["emt_applicability"]["is_valid"] is False


def test_smart_window_contract_is_not_presented_as_switching_simulation() -> None:
    exported = json.loads((RESULTS / "app_smart_window.json").read_text(encoding="utf-8"))
    assert exported["model_scope"] == "static_spectral_selectivity_state"
    assert "does not simulate electrochromic switching" in exported["semantic_limit"]
