from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import atexit
from pathlib import Path
from typing import Any, Mapping

import numpy as np


class TmmcoreUnavailableError(RuntimeError):
    """Raised when the optional Node/tmmcore backend is not installed."""


def _bridge_candidates(app_root: Path) -> list[Path]:
    configured = os.environ.get("THINFILM_TMMCORE_BRIDGE")
    candidates = [Path(configured)] if configured else []
    candidates.extend(
        [
            app_root / "frontend" / "tools" / "tmmcore_bridge.mjs",
            app_root / "tmmcore" / "tmmcore_bridge.mjs",
            Path(__file__).resolve().parents[2] / "frontend" / "tools" / "tmmcore_bridge.mjs",
        ]
    )
    return candidates


def tmmcore_runtime_status(app_root: Path) -> dict[str, Any]:
    bridge = next((path for path in _bridge_candidates(app_root) if path.exists()), None)
    configured_node = os.environ.get("THINFILM_NODE_EXECUTABLE")
    node = configured_node or shutil.which("node")
    return {
        "available": bool(bridge and node),
        "node_executable": node,
        "bridge": str(bridge) if bridge else None,
        "version": "0.4.0",
    }


class _TmmcoreWorker:
    def __init__(self, node_executable: str, bridge: str) -> None:
        self.node_executable = node_executable
        self.bridge = bridge
        self.process: subprocess.Popen[str] | None = None
        self.responses: queue.Queue[str] = queue.Queue()
        self.lock = threading.Lock()

    def _start(self) -> None:
        child_env = os.environ.copy()
        if os.environ.get("THINFILM_NODE_EXECUTABLE"):
            child_env["ELECTRON_RUN_AS_NODE"] = "1"
        self.process = subprocess.Popen(
            [self.node_executable, self.bridge],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=child_env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()

    def _read_stdout(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            self.responses.put(line)

    def stop(self) -> None:
        process, self.process = self.process, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

    def request(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self.stop()
                self._start()
            assert self.process is not None and self.process.stdin is not None
            try:
                self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self.process.stdin.flush()
                raw = self.responses.get(timeout=45)
                message = json.loads(raw)
            except (BrokenPipeError, queue.Empty, json.JSONDecodeError) as exc:
                self.stop()
                raise RuntimeError(f"tmmcore worker communication failed: {exc}") from exc
            if not message.get("ok"):
                raise RuntimeError(f"tmmcore failed: {message.get('error', 'unknown error')}")
            return message["result"]


_WORKERS: dict[tuple[str, str], _TmmcoreWorker] = {}
_WORKERS_LOCK = threading.Lock()


def _shutdown_workers() -> None:
    for worker in list(_WORKERS.values()):
        worker.stop()


atexit.register(_shutdown_workers)


def run_tmmcore_resolved(payload: Mapping[str, Any], app_root: Path) -> dict[str, Any]:
    status = tmmcore_runtime_status(app_root)
    if not status["available"]:
        raise TmmcoreUnavailableError("tmmcore requires its bridge script and a Node-compatible runtime.")
    key = (str(status["node_executable"]), str(status["bridge"]))
    with _WORKERS_LOCK:
        worker = _WORKERS.setdefault(key, _TmmcoreWorker(*key))
    result = worker.request(payload)
    for key in ("R", "T", "A"):
        result[key] = np.asarray(result[key], dtype=float)
    return result


def _nk_pairs(material_complex_index: Any, material_id: str, wavelengths: np.ndarray, policy: str) -> list[list[float]]:
    values = np.asarray(
        material_complex_index(material_id, wavelengths, out_of_range_policy=policy),
        dtype=complex,
    )
    return [[float(value.real), float(value.imag)] for value in values]


def build_resolved_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    from thinfilm.materials import canonical_material_name, material_complex_index

    spectrum = payload["spectrum"]
    wavelengths = np.linspace(
        float(spectrum["start_nm"]),
        float(spectrum["stop_nm"]),
        int(spectrum["points"]),
        dtype=float,
    )
    policy = str(payload.get("out_of_range_policy", "error"))
    layers = []
    for layer in payload["layers"]:
        if not layer.get("enabled", True):
            continue
        material_id = canonical_material_name(str(layer["material_id"]))
        layers.append(
            {
                "material_id": material_id,
                "thickness_nm": float(layer["thickness_nm"]),
                "nk": _nk_pairs(material_complex_index, material_id, wavelengths, policy),
            }
        )
    incident_id = canonical_material_name(str(payload["incident_material_id"]))
    substrate_id = canonical_material_name(str(payload["substrate_material_id"]))
    return {
        "wavelength_nm": wavelengths.tolist(),
        "angle_deg": float(payload.get("angle_deg", 0.0)),
        "polarization": str(payload.get("polarization", "p")),
        "incident_nk": _nk_pairs(material_complex_index, incident_id, wavelengths, policy),
        "substrate_nk": _nk_pairs(material_complex_index, substrate_id, wavelengths, policy),
        "layers": layers,
    }


def simulate_design_with_tmmcore(
    payload: Mapping[str, Any],
    app_root: Path,
    thinfilm_api: Any,
) -> dict[str, Any]:
    """Use tmmcore for the full spectrum without a duplicate Python TMM pass."""
    import math

    from thinfilm.custom_stack import _index, _validate_design, analyze_spectrum
    from thinfilm.design_models import StackDesign
    from thinfilm.experiment_evaluation import evaluate_experiment
    from thinfilm.materials import canonical_material_name
    from thinfilm.stack_insights import compute_field_profile

    experiment_task_id = str(payload.get("experiment_task_id") or "") or None
    design, warning_messages = _validate_design(StackDesign.from_mapping(payload))
    raw_probe = payload.get("probe_wavelength_nm")
    probe_wavelength_nm = float(raw_probe) if raw_probe is not None else 0.5 * (design.spectrum.start_nm + design.spectrum.stop_nm)
    if not math.isfinite(probe_wavelength_nm) or not design.spectrum.start_nm <= probe_wavelength_nm <= design.spectrum.stop_nm:
        raise ValueError("probe_wavelength_nm must be finite and inside the spectrum range.")

    resolved = build_resolved_payload(payload)
    result = run_tmmcore_resolved(resolved, app_root)
    wavelengths = np.asarray(resolved["wavelength_nm"], dtype=float)
    reflectance, transmittance, absorption = result["R"], result["T"], result["A"]
    metrics = analyze_spectrum(wavelengths, reflectance, transmittance, np.maximum(0.0, absorption))
    enabled_layers = [layer for layer in design.layers if layer.enabled]
    field = compute_field_profile(design, probe_wavelength_nm)
    reflection_phase = np.asarray(result.get("reflection_phase_deg", []), dtype=float)
    transmission_phase = np.asarray(result.get("transmission_phase_deg", []), dtype=float)
    probe_index = int(np.argmin(np.abs(wavelengths - probe_wavelength_nm)))
    if reflectance[probe_index] <= 0.1:
        interpretation = "该波长处整体反射较弱，多个界面反射分量主要表现为相消叠加。"
    elif reflectance[probe_index] >= 0.9:
        interpretation = "该波长处整体反射很强，多个界面反射分量主要表现为相长叠加。"
    else:
        interpretation = "该波长处反射分量仅部分抵消，需要结合层内场强和各层相位厚度判断。"
    phase = {
        "wavelength_nm": wavelengths,
        "reflection_phase_deg": reflection_phase,
        "reflection_phase_unwrapped_deg": np.degrees(np.unwrap(np.radians(reflection_phase))),
        "transmission_phase_deg": transmission_phase,
        "probe": {
            "wavelength_nm": float(wavelengths[probe_index]),
            "reflection_phase_deg": float(reflection_phase[probe_index]),
            "transmission_phase_deg": float(transmission_phase[probe_index]),
        },
        "layer_phase": field["layer_phase"],
        "explanations": [
            interpretation,
            "单层相位厚度表示光在该层单程传播积累的相位；约90°对应四分之一波长光学厚度。",
            f"场强峰值 |E|²={field['peak_E2']:.3f}，位置 z={field['peak_z_nm']:.2f} nm。",
        ],
    }
    evaluation = evaluate_experiment(
        experiment_task_id,
        design,
        wavelengths,
        reflectance,
        transmittance,
        metrics,
    )
    resolved_layers = []
    center_nm = 0.5 * (design.spectrum.start_nm + design.spectrum.stop_nm)
    for layer in design.layers:
        center_index = _index(layer.material_id, np.asarray([center_nm]), design.out_of_range_policy)[0]
        resolved_layers.append(
            {
                "id": layer.id,
                "material_id": canonical_material_name(layer.material_id),
                "thickness_nm": float(layer.thickness_nm),
                "enabled": layer.enabled,
                "n_center": float(np.real(center_index)),
                "k_center": float(np.imag(center_index)),
            }
        )
    return {
            "design": {
                "incident_material_id": canonical_material_name(design.incident_material_id),
                "substrate_material_id": canonical_material_name(design.substrate_material_id),
                "layers": resolved_layers,
                "spectrum": {
                    "start_nm": design.spectrum.start_nm,
                    "stop_nm": design.spectrum.stop_nm,
                    "points": design.spectrum.points,
                },
                "angle_deg": design.angle_deg,
                "polarization": design.polarization,
                "out_of_range_policy": design.out_of_range_policy,
                "probe_wavelength_nm": probe_wavelength_nm,
                "experiment_task_id": experiment_task_id,
            },
            "wavelength_nm": wavelengths,
            "R": reflectance,
            "T": transmittance,
            "A": absorption,
            "metrics": metrics,
            "summary": {
                "layer_count": len(enabled_layers),
                "total_thickness_nm": float(sum(layer.thickness_nm for layer in enabled_layers)),
                "max_energy_residue": float(np.max(np.abs(reflectance + transmittance + absorption - 1.0))),
                "mean_R": float(np.mean(reflectance)),
                "mean_T": float(np.mean(transmittance)),
                "mean_A": float(np.mean(np.maximum(0.0, absorption))),
            },
            "solver": {
                "spectral_engine": "tmmcore",
                "spectral_engine_version": result.get("version", "0.4.0"),
                "teaching_insights_engine": "pythinfilm",
            },
            "field": field,
            "phase": phase,
            "evaluation": evaluation,
            "warnings": warning_messages,
    }


def simulate_teaching_case_with_tmmcore(
    case_id: str,
    params: Mapping[str, Any],
    app_root: Path,
) -> dict[str, Any]:
    """Run one of the audited teaching baseline cases with tmmcore.

    The layer builders and post-processing remain sourced from PyThinFilm;
    only the wavelength sweep is delegated to tmmcore.  Keeping this adapter
    limited to the three reference cases makes the migration explicit while
    the remaining teaching cases are audited.
    """
    from thinfilm.education import (
        REPORT_CHAPTER2_CASES,
        _default_wavelength_grid_for_design,
        build_fp_single_halfwave_layers,
        build_fp_double_halfwave_layers,
        build_narrowband_filter_layers,
        build_neutral_beamsplitter_layers,
        build_rugate_filter_layers,
        build_moth_eye_effective_gradient_layers,
        build_high_reflector_layers,
        build_single_ar_layers,
        build_double_ar_layers,
        build_porous_double_ar_layers,
        build_triple_ar_layers,
        build_uniform_single_layer_layers,
        describe_layers,
        generate_case_figure_explanations,
    )

    key = str(case_id).strip()
    item = REPORT_CHAPTER2_CASES.get(key)
    if item is None:
        raise ValueError(f"Unsupported report case_id: {case_id}")
    if key not in {
        "quarter_wave_single_layer", "half_wave_single_layer", "single_ar",
        "porous_sio2_layer", "double_ar", "quarter_wave_double_layer", "porous_double_ar",
        "triple_ar", "high_reflector", "quarter_wave_stack", "bragg_reflector", "fp_filter",
        "fp_double_halfwave", "narrowband_filter", "neutral_beamsplitter",
        "rugate_filter", "moth_eye_effective_gradient",
    }:
        raise ValueError(f"tmmcore teaching adapter does not cover case_id: {case_id}")

    merged = dict(item.get("default_params", {}))
    merged.update(dict(params))
    design_type = str(item["design_type"])
    lambda0_nm = float(merged.get("lambda0_nm", 550.0))
    n0 = complex(float(merged.get("n_incident", 1.0)), float(merged.get("k_incident", 0.0)))
    ns = complex(float(merged.get("n_substrate", 1.52)), float(merged.get("k_substrate", 0.0)))
    nl = complex(float(merged.get("n_low", 1.38)), float(merged.get("k_low", 0.0)))
    nh2 = complex(float(merged.get("n_high_2", 2.15)), float(merged.get("k_high_2", 0.0)))
    periods = int(merged.get("periods", 3))
    if key == "quarter_wave_single_layer":
        layers = build_uniform_single_layer_layers(lambda0_nm, nl, optical_kind="quarter")
    elif key == "half_wave_single_layer":
        layers = build_uniform_single_layer_layers(lambda0_nm, nl, optical_kind="half")
    elif key == "single_ar":
        layers = build_single_ar_layers(lambda0_nm, nl)
    elif key == "porous_sio2_layer":
        layers = build_uniform_single_layer_layers(
            lambda0_nm,
            complex(float(merged.get("n_porous", 1.18)), 0.0),
            optical_kind="quarter",
        )
    elif key in {"double_ar", "quarter_wave_double_layer"}:
        layers = build_double_ar_layers(lambda0_nm, nl, complex(float(merged.get("n_high", 2.0)), float(merged.get("k_high", 0.0))))
    elif key == "porous_double_ar":
        layers = build_porous_double_ar_layers(
            lambda0_nm,
            complex(float(merged.get("n_porous", 1.18)), 0.0),
            complex(float(merged.get("n_high", 2.0)), float(merged.get("k_high", 0.0))),
        )
    elif key == "triple_ar":
        layers = build_triple_ar_layers(
            lambda0_nm,
            complex(float(merged.get("n_mid", 1.60)), float(merged.get("k_mid", 0.0))),
            nh2,
            nl,
        )
    elif key in {"high_reflector", "quarter_wave_stack", "bragg_reflector"}:
        layers = build_high_reflector_layers(lambda0_nm, nh2, nl, periods)
    elif key == "fp_double_halfwave":
        layers = build_fp_double_halfwave_layers(lambda0_nm, nh2, nl, periods)
    elif key == "narrowband_filter":
        layers = build_narrowband_filter_layers(
            lambda0_nm, nh2, nl, periods,
            spacer_kind=str(merged.get("fp_spacer_kind", "L")),
        )
    elif key == "neutral_beamsplitter":
        layers = build_neutral_beamsplitter_layers(
            lambda0_nm, nh2, nl,
            use_front_halfwave_low=bool(merged.get("beamsplitter_front_halfwave_low", False)),
        )
    elif key == "rugate_filter":
        slices = merged.get("slices_per_period")
        if slices is None and merged.get("total_layers") is not None:
            total_layers = max(int(merged["total_layers"]), periods)
            if total_layers % max(periods, 1) != 0:
                raise ValueError("For rugate_filter, total_layers must be divisible by periods.")
            slices = total_layers // max(periods, 1)
        layers = build_rugate_filter_layers(
            lambda0_nm, nl, nh2, periods,
            slices_per_period=int(slices if slices is not None else 24),
        )
    elif key == "moth_eye_effective_gradient":
        layers = build_moth_eye_effective_gradient_layers(
            complex(float(merged.get("n_top", 1.10)), 0.0),
            complex(float(merged.get("n_bottom", 1.50)), 0.0),
            d_total_nm=float(merged.get("d_total_nm", 300.0)),
            num_gradient_layers=int(merged.get("num_gradient_layers", 5)),
            gradient_type=str(merged.get("gradient_type", "linear")),
            layer_indices=merged.get("layer_indices"),
            layer_thickness_nm=merged.get("layer_thickness_nm"),
        )
    else:
        layers = build_fp_single_halfwave_layers(
            lambda0_nm, nh2, nl, periods,
            spacer_kind=str(merged.get("fp_spacer_kind", "L")),
        )

    wavelengths = np.asarray(
        merged.get("wavelengths_nm")
        if merged.get("wavelengths_nm") is not None
        else _default_wavelength_grid_for_design(design_type, lambda0_nm),
        dtype=float,
    )
    if wavelengths.ndim != 1 or wavelengths.size < 2 or not np.all(np.isfinite(wavelengths)):
        raise ValueError("wavelengths_nm must contain at least two finite values.")
    def pairs(value: complex) -> list[list[float]]:
        return [[float(value.real), float(value.imag)] for _ in wavelengths]

    resolved = {
        "wavelength_nm": wavelengths.tolist(),
        "angle_deg": float(merged.get("theta_deg", 0.0)),
        "polarization": str(merged.get("pol", "p")),
        "incident_nk": pairs(n0),
        "substrate_nk": pairs(ns),
        "layers": [
            {"material_id": layer.name, "thickness_nm": float(layer.thickness_nm), "nk": pairs(layer.n)}
            for layer in layers
        ],
    }
    spectrum = run_tmmcore_resolved(resolved, app_root)
    r_vals = np.asarray(spectrum["R"], dtype=float)
    t_vals = np.asarray(spectrum["T"], dtype=float)
    a_vals = np.asarray(spectrum["A"], dtype=float)
    peak_r_idx = int(np.argmax(r_vals))
    valley_r_idx = int(np.argmin(r_vals))
    peak_t_idx = int(np.argmax(t_vals))
    summary = {
        "R_at_lambda0": float(np.interp(lambda0_nm, wavelengths, r_vals)),
        "T_at_lambda0": float(np.interp(lambda0_nm, wavelengths, t_vals)),
        "A_at_lambda0": float(np.interp(lambda0_nm, wavelengths, a_vals)),
        "R_min": float(np.min(r_vals)), "R_min_wavelength_nm": float(wavelengths[valley_r_idx]),
        "R_max": float(np.max(r_vals)), "R_max_wavelength_nm": float(wavelengths[peak_r_idx]),
        "T_max": float(np.max(t_vals)), "T_max_wavelength_nm": float(wavelengths[peak_t_idx]),
    }
    result: dict[str, Any] = {
        "case_id": key, "title_cn": item["title_cn"], "title_en": item["title_en"],
        "design_type": design_type, "theta_deg": float(merged.get("theta_deg", 0.0)),
        "pol": str(merged.get("pol", "p")), "lambda0_nm": lambda0_nm,
        "n_incident": n0, "n_substrate": ns, "layers": describe_layers(layers),
        "wavelength_nm": wavelengths, "R": r_vals, "T": t_vals, "A": a_vals,
        "A_display": np.maximum(0.0, a_vals),
        "energy_residue": np.abs(r_vals + t_vals + a_vals - 1.0),
        "energy_excess": np.maximum(0.0, r_vals + t_vals - 1.0),
        "summary": summary,
        "solver": {
            "spectral_engine": "tmmcore",
            "spectral_engine_version": spectrum.get("version", "0.4.0"),
            "teaching_insights_engine": "pythinfilm",
            "discretization": "layer_sliced_approximation" if key in {"rugate_filter", "moth_eye_effective_gradient"} else None,
        },
    }
    result["figure_explanations"] = generate_case_figure_explanations(result)
    return result
