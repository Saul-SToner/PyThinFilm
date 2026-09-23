# -*- coding: utf-8 -*-
"""Export reproducible standalone visualization contracts for extension cases.

This adapter only calls existing public Python calculation functions.  It does
not modify the TMM/EMT implementations or import external COMSOL CSV data.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.applications.smart_window import (
    N_AIR,
    N_SUBSTRATE,
    build_smart_window_layers,
)
from guided_grating.emt import GratingLayer, check_emt_applicability, emt_layer_spectrum
from thinfilm import simulate_pdrc_cooling, simulate_teaching_design_real_materials
from thinfilm.education import multilayer_rt_spectrum, simulate_report_case
from tools.export_visualization_cases import (
    compute_hash,
    compute_physics_hashes,
    get_git_commit_hash,
)


EXTENSION_VISUALIZATION_CASES = {
    "app_smart_window": 3,
    "guided_grating_emt": 1,
    "mat_library_demo": 1,
    "pdrc_cooling_bundle": 6,
    "rugate_80layer_table": 80,
}


def _rounded(values, digits: int = 6) -> list[float]:
    return [round(float(value), digits) for value in values]


def _finalize(data: dict) -> dict:
    data["physics_input_hash"], data["physics_result_hash"] = compute_physics_hashes(data)
    data["result_hash"] = compute_hash(data)
    return data


def _base_contract(*, case_id: str, title: str, source_file: str, source_symbol: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "title": title,
        "source_commit": get_git_commit_hash(),
        "source_file": source_file,
        "source_symbol": source_symbol,
        "generated_at": datetime.datetime.now().isoformat(),
        "calculation_source": "python_export",
        "incidence_angle_deg": 45.0,
        "polarization_support": ["TE", "TM"],
    }


def _energy_status(te: dict, tm: dict) -> dict:
    residual = max(
        float(np.max(np.abs(np.asarray(te["R"]) + np.asarray(te["T"]) + np.asarray(te["A"]) - 1.0))),
        float(np.max(np.abs(np.asarray(tm["R"]) + np.asarray(tm["T"]) + np.asarray(tm["A"]) - 1.0))),
    )
    return {"max_residual": round(residual, 12), "status": "PASSED" if residual <= 1e-6 else "FAILED"}


def _spectrum_block(result: dict) -> dict:
    # Eight decimals keep the serialized R+T+A residual below the frontend's
    # formal-contract tolerance without changing the underlying calculation.
    return {key: _rounded(result[key], 8) for key in ("R", "T", "A")}


def export_smart_window() -> dict:
    wavelengths = np.linspace(300.0, 2500.0, 500)
    layers = build_smart_window_layers()
    calculated = {
        label: multilayer_rt_spectrum(
            wavelengths, layers, n_incident=N_AIR, n_substrate=N_SUBSTRATE,
            theta0_deg=45.0, pol=pol,
        )
        for label, pol in (("TE", "s"), ("TM", "p"))
    }
    data = _base_contract(
        case_id="app_smart_window", title="智能调温窗 Low-E 膜",
        source_file="examples/applications/smart_window.py", source_symbol="build_smart_window_layers",
    )
    data.update({
        "model_scope": "static_spectral_selectivity_state",
        "ambient": {"name": "Air", "n": N_AIR},
        "layers": [
            {"layer_index": index, "type": layer.name, "material": layer.name,
             "n_real": round(float(np.real(layer.n)), 6), "n_imag": round(float(np.imag(layer.n)), 6),
             "thickness_nm": round(float(layer.thickness_nm), 4)}
            for index, layer in enumerate(layers, 1)
        ],
        "substrate": {"name": "Glass", "n": N_SUBSTRATE},
        "wavelength_nm": _rounded(wavelengths, 2),
        "TE": _spectrum_block(calculated["TE"]),
        "TM": _spectrum_block(calculated["TM"]),
        "semantic_limit": "This contract is one fixed WO3/NiO/Ag state; it does not simulate electrochromic switching.",
    })
    data["energy_conservation"] = _energy_status(data["TE"], data["TM"])
    return _finalize(data)


def export_guided_grating_emt() -> dict:
    wavelengths = np.linspace(1450.0, 1650.0, 201)
    grating = GratingLayer(period_nm=980.0, thickness_nm=200.0, n_low=1.45, n_high=3.4, fill_factor=0.55)
    calculated = {
        label: emt_layer_spectrum(
            wavelengths, grating, n_incident=1.0, n_substrate=1.45, theta_deg=45.0, pol=label,
        )
        for label in ("TE", "TM")
    }
    data = _base_contract(
        case_id="guided_grating_emt", title="一维亚波长光栅 EMT 零级近似",
        source_file="guided_grating/emt.py", source_symbol="emt_layer_spectrum",
    )
    applicability = check_emt_applicability(grating.period_nm, grating.n_low, grating.n_high, 1550.0)
    data.update({
        "model_scope": "zero_order_effective_medium_approximation",
        "design_wavelength_nm": 1550.0,
        "ambient": {"name": "Air", "n": 1.0},
        "layers": [{
            "layer_index": 1, "type": "EMT", "material": "Si grating EMT",
            "n_TE": round(float(np.real(calculated["TE"]["n_eff"])), 6),
            "n_TM": round(float(np.real(calculated["TM"]["n_eff"])), 6),
            "thickness_nm": grating.thickness_nm,
        }],
        "substrate": {"name": "Substrate", "n": 1.45},
        "wavelength_nm": _rounded(wavelengths, 2),
        "TE": _spectrum_block(calculated["TE"]),
        "TM": _spectrum_block(calculated["TM"]),
        "grating_parameters": {
            "period_nm": grating.period_nm, "fill_factor": grating.fill_factor,
            "n_low": grating.n_low, "n_high": grating.n_high,
        },
        "emt_applicability": applicability,
        "semantic_limit": "The displayed slab is the anisotropic EMT equivalent layer, not literal grating teeth or full-wave diffraction.",
    })
    data["energy_conservation"] = _energy_status(data["TE"], data["TM"])
    return _finalize(data)


def _real_material_single_ar(pol: str) -> dict:
    return simulate_teaching_design_real_materials(
        "single_ar",
        material_map={"n_incident": "Air", "n_low": "MgF2", "n_substrate": "SiO2"},
        lambda0_nm=550.0, wavelengths_nm=list(range(430, 751, 2)), theta_deg=45.0, pol=pol,
    )


def export_material_library_demo() -> dict:
    calculated = {"TE": _real_material_single_ar("s"), "TM": _real_material_single_ar("p")}
    wavelengths = calculated["TE"]["wavelength_nm"]
    layer = calculated["TE"]["layers"][0]
    data = _base_contract(
        case_id="mat_library_demo", title="真实材料库与色散插值演示",
        source_file="cases/materials/run_material_library_demo.py", source_symbol="simulate_teaching_design_real_materials",
    )
    data.update({
        "model_scope": "real_nk_single_ar_representative",
        "design_wavelength_nm": 550.0,
        "ambient": {"name": "Air"},
        "layers": [{
            "layer_index": 1, "type": "MgF2", "material": "MgF2 (real n,k)",
            "n_real_at_design": round(float(layer["n_real"]), 8),
            "n_imag_at_design": round(float(layer["n_imag"]), 8),
            "thickness_nm": round(float(layer["thickness_nm"]), 4),
        }],
        "substrate": {"name": "SiO2 (real n,k)"},
        "wavelength_nm": _rounded(wavelengths, 2),
        "TE": _spectrum_block(calculated["TE"]),
        "TM": _spectrum_block(calculated["TM"]),
        "material_map": calculated["TE"]["material_map"],
        "semantic_limit": "This standalone scene shows the MgF2-on-SiO2 representative from the library demo, not all catalog materials simultaneously.",
    })
    data["energy_conservation"] = _energy_status(data["TE"], data["TM"])
    return _finalize(data)


def export_pdrc() -> dict:
    wavelength_grid_um = np.linspace(0.3, 13.0, 636)
    calculated = {
        "TE": simulate_pdrc_cooling(wavelengths_um=wavelength_grid_um, theta_deg=45.0, pol="s"),
        "TM": simulate_pdrc_cooling(wavelengths_um=wavelength_grid_um, theta_deg=45.0, pol="p"),
    }
    data = _base_contract(
        case_id="pdrc_cooling_bundle", title="PDRC 被动辐射制冷评估束",
        source_file="thinfilm/education.py", source_symbol="simulate_pdrc_multilayer_cooling",
    )
    data.update({
        "model_scope": "wideband_surrogate_screening",
        "ambient": {"name": "Air", "n": 1.0},
        "layers": [
            {"layer_index": index, "type": layer["name"], "material": layer["material"],
             "thickness_nm": round(float(layer["thickness_nm"]), 4)}
            for index, layer in enumerate(calculated["TE"]["layers"], 1)
        ],
        "substrate": {"name": "Substrate"},
        "wavelength_nm": _rounded(calculated["TE"]["wavelength_nm"], 2),
        "TE": _spectrum_block(calculated["TE"]),
        "TM": _spectrum_block(calculated["TM"]),
        "metrics": {"TE": calculated["TE"]["metrics"], "TM": calculated["TM"]["metrics"]},
        "semantic_limit": calculated["TE"]["optical_constant_note_cn"],
    })
    data["energy_conservation"] = _energy_status(data["TE"], data["TM"])
    return _finalize(data)


def export_rugate_table() -> dict:
    calculated = {
        "TE": simulate_report_case("rugate_filter", theta_deg=45.0, pol="s"),
        "TM": simulate_report_case("rugate_filter", theta_deg=45.0, pol="p"),
    }
    layers = calculated["TE"]["layers"]
    data = _base_contract(
        case_id="rugate_80layer_table", title="80 层 Rugate 褶皱滤光片列表",
        source_file="thinfilm/education.py", source_symbol="build_rugate_filter_layers",
    )
    data.update({
        "model_scope": "rugate_discrete_layer_table_and_tmm",
        "design_wavelength_nm": 550.0,
        "ambient": {"name": "Air", "n": float(np.real(calculated["TE"]["n_incident"]))},
        "layers": [
            {"layer_index": index, "type": layer["name"], "material": layer["name"],
             "n_real": round(float(layer["n_real"]), 8), "n_imag": round(float(layer["n_imag"]), 8),
             "thickness_nm": round(float(layer["thickness_nm"]), 4)}
            for index, layer in enumerate(layers, 1)
        ],
        "substrate": {"name": "Glass", "n": float(np.real(calculated["TE"]["n_substrate"]))},
        "wavelength_nm": _rounded(calculated["TE"]["wavelength_nm"], 2),
        "TE": _spectrum_block(calculated["TE"]),
        "TM": _spectrum_block(calculated["TM"]),
        "table_metadata": {"periods": 8, "total_layers": 80, "slices_per_period": 10},
        "semantic_limit": "The scene preserves the same 80 sliced layers exported for the COMSOL-friendly table.",
    })
    data["energy_conservation"] = _energy_status(data["TE"], data["TM"])
    return _finalize(data)


def export_all() -> None:
    output_dir = ROOT / "web3d" / "public" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    exporters = {
        "app_smart_window": export_smart_window,
        "guided_grating_emt": export_guided_grating_emt,
        "mat_library_demo": export_material_library_demo,
        "pdrc_cooling_bundle": export_pdrc,
        "rugate_80layer_table": export_rugate_table,
    }
    for case_id, exporter in exporters.items():
        output = output_dir / f"{case_id}.json"
        output.write_text(json.dumps(exporter(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[export] {case_id} -> {output}")


if __name__ == "__main__":
    export_all()
