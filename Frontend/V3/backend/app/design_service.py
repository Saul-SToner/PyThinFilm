from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import DesignSimulationRequest


def simulate_design(request: DesignSimulationRequest, thinfilm_api: Any, app_root: Path | None = None) -> dict[str, Any]:
    payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
    request_id = payload.pop("request_id")
    schema_version = payload.pop("schema_version")
    solver = payload.pop("solver", "pythinfilm")
    if solver == "tmmcore":
        if app_root is None:
            raise ValueError("app_root is required for the tmmcore solver.")
        from .tmmcore_service import simulate_design_with_tmmcore

        result = simulate_design_with_tmmcore(payload, app_root, thinfilm_api)
    else:
        result = thinfilm_api.simulate_custom_stack(payload)
    return {
        "schema_version": schema_version,
        "request_id": request_id,
        "design": result["design"],
        "series": {
            "wavelength_nm": result["wavelength_nm"],
            "R": result["R"],
            "T": result["T"],
            "A": result["A"],
        },
        "summary": result["summary"],
        "metrics": result["metrics"],
        "field": result["field"],
        "phase": result["phase"],
        "evaluation": result["evaluation"],
        "warnings": result["warnings"],
        "solver": result.get(
            "solver",
            {"spectral_engine": "pythinfilm", "teaching_insights_engine": "pythinfilm"},
        ),
    }
