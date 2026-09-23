from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .case_catalog_service import build_case_catalog, load_case_detail


SPECIALIST_SOLVERS: dict[str, tuple[str, str]] = {
    "guided_grating_emt": ("RCWA", "/api/specialist/rcwa"),
    "tamm_interface_priority": ("GeneralTmm", "/api/specialist/generaltmm"),
    "tamm_phase_bundle": ("GeneralTmm", "/api/specialist/generaltmm"),
    "tamm_phase_candidates": ("GeneralTmm", "/api/specialist/generaltmm"),
    "tamm_phase_focus": ("GeneralTmm", "/api/specialist/generaltmm"),
    "tamm_reflection_phase_screen": ("GeneralTmm", "/api/specialist/generaltmm"),
    "tamm_interface_window_bundle": ("GeneralTmm", "/api/specialist/generaltmm"),
    "tamm_interface_window_scan": ("GeneralTmm", "/api/specialist/generaltmm"),
    "pdrc_cooling_bundle": ("WPTherml", "/api/specialist/wptherml"),
}

def _series_checks(series: list[dict[str, Any]]) -> dict[str, Any]:
    plot_ready = bool(series)
    finite_values = True
    point_count = 0
    for trace in series:
        x_values = trace.get("x")
        y_values = trace.get("y")
        if not isinstance(x_values, list) or not isinstance(y_values, list) or len(x_values) != len(y_values) or len(x_values) < 2:
            plot_ready = False
            finite_values = False
            continue
        point_count += len(x_values)
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) for value in [*x_values, *y_values]):
            finite_values = False
    return {"plot_ready": plot_ready, "finite_values": finite_values, "point_count": point_count}


def _energy_check(series: list[dict[str, Any]], tolerance: float = 2e-2) -> dict[str, Any]:
    by_label = {str(trace.get("label", "")).strip().upper(): trace for trace in series}
    deviations: list[float] = []
    for prefix in ("TE ", "TM ", ""):
        traces = [by_label.get(f"{prefix}{quantity}") for quantity in ("R", "T", "A")]
        if not all(traces):
            continue
        y_values = [trace.get("y", []) for trace in traces if trace]
        if len({len(values) for values in y_values}) != 1:
            continue
        deviations.extend(abs(float(r) + float(t) + float(a) - 1.0) for r, t, a in zip(*y_values))
    if not deviations:
        return {"status": "not_applicable", "max_deviation": None, "tolerance": tolerance}
    maximum = max(deviations)
    return {"status": "passed" if maximum <= tolerance else "failed", "max_deviation": maximum, "tolerance": tolerance}


def _external_provenance_ready(detail: dict[str, Any]) -> bool:
    provenance = detail.get("external_data_provenance")
    return bool(provenance) and all(
        isinstance(item, dict)
        and item.get("status") == "AVAILABLE"
        and bool(item.get("sha256"))
        for item in provenance
    )


def _classification(case: dict[str, Any], detail: dict[str, Any]) -> tuple[str, str, str]:
    case_id = str(case["case_id"])
    if case.get("has_live_simulation"):
        return "complete_interactive", "TMMCore / Python thin-film model", "/api/simulations"
    if case_id in SPECIALIST_SOLVERS:
        solver, endpoint = SPECIALIST_SOLVERS[case_id]
        return "specialist_solver", solver, endpoint
    if case.get("physics_data_status") == "EXTERNAL_DATA_REQUIRED" and not _external_provenance_ready(detail):
        return "pending_physics", "Formal evidence only", f"/api/case-library/{case_id}"
    return "formal_evidence", "Formal result/evidence", f"/api/case-library/{case_id}"


def build_case_acceptance_matrix(project_root: Path, app_root: Path, dynamic_cases: list[dict[str, Any]]) -> dict[str, Any]:
    catalog = build_case_catalog(project_root, app_root, dynamic_cases)
    rows: list[dict[str, Any]] = []
    for case in catalog["cases"]:
        case_id = str(case["case_id"])
        detail = load_case_detail(project_root, app_root, dynamic_cases, case_id)
        classification, solver, endpoint = _classification(case, detail)
        series_check = _series_checks(detail.get("series", []))
        energy = _energy_check(detail.get("series", []))
        teaching_route_ready = all(case.get(key) for key in ("learning_goal", "coating_function", "application_scene", "design_task"))
        system_binding_ready = bool(case.get("system_experiment"))
        blocking_failures = [
            name
            for name, passed in (
                ("plot_ready", series_check["plot_ready"]),
                ("finite_values", series_check["finite_values"]),
                ("teaching_route", teaching_route_ready),
                ("system_binding", system_binding_ready),
                ("energy_conservation", energy["status"] != "failed"),
            )
            if not passed
        ]
        acceptance_status = "failed" if blocking_failures else ("attention" if classification == "pending_physics" else "passed")
        rows.append(
            {
                "order": case["order"],
                "case_id": case_id,
                "title_cn": case["title_cn"],
                "classification": classification,
                "acceptance_status": acceptance_status,
                "solver": solver,
                "endpoint": endpoint,
                "plot_ready": series_check["plot_ready"],
                "finite_values": series_check["finite_values"],
                "point_count": series_check["point_count"],
                "energy_conservation": energy,
                "teaching_route_ready": teaching_route_ready,
                "system_binding_ready": system_binding_ready,
                "external_provenance_ready": _external_provenance_ready(detail),
                "physics_data_status": case.get("physics_data_status", ""),
                "blocking_failures": blocking_failures,
                "attention_reason": "缺少可重建物理输入或正式外部扫描数据" if classification == "pending_physics" else "",
            }
        )

    classifications = ("complete_interactive", "specialist_solver", "formal_evidence", "pending_physics")
    statuses = ("passed", "attention", "failed")
    return {
        "schema_version": "1.0",
        "total_cases": len(rows),
        "classification_counts": {name: sum(row["classification"] == name for row in rows) for name in classifications},
        "status_counts": {name: sum(row["acceptance_status"] == name for row in rows) for name in statuses},
        "all_plot_ready": all(row["plot_ready"] for row in rows),
        "all_finite": all(row["finite_values"] for row in rows),
        "all_teaching_routes_ready": all(row["teaching_route_ready"] for row in rows),
        "all_system_bindings_ready": all(row["system_binding_ready"] for row in rows),
        "rows": rows,
    }
