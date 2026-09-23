from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DesignLayerRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    material_id: str = Field(..., min_length=1, max_length=100)
    thickness_nm: float = Field(..., gt=0, le=1_000_000)
    enabled: bool = True


class SpectrumRequest(BaseModel):
    start_nm: float = Field(400.0, gt=0)
    stop_nm: float = Field(800.0, gt=0)
    points: int = Field(401, ge=2, le=5000)


class DesignSimulationRequest(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: str = Field(..., min_length=1, max_length=100)
    incident_material_id: str = Field("Air", min_length=1)
    substrate_material_id: str = Field("N-BK7", min_length=1)
    layers: list[DesignLayerRequest] = Field(..., min_length=1, max_length=200)
    spectrum: SpectrumRequest = Field(default_factory=SpectrumRequest)
    angle_deg: float = Field(0.0, ge=0, lt=90)
    polarization: Literal["s", "p"] = "p"
    out_of_range_policy: Literal["error", "clip"] = "error"
    probe_wavelength_nm: float | None = Field(None, gt=0)
    experiment_task_id: str | None = Field(None, max_length=100)
    solver: Literal["pythinfilm", "tmmcore"] = "tmmcore"
