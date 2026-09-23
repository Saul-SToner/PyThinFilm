"""Data models shared by arbitrary thin-film stack simulations.

These models deliberately contain no UI or HTTP concerns.  They are the
stable boundary between an editor payload and the numerical solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DesignLayer:
    id: str
    material_id: str
    thickness_nm: float
    enabled: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], index: int) -> "DesignLayer":
        return cls(
            id=str(value.get("id") or f"layer-{index + 1}"),
            material_id=str(value.get("material_id") or ""),
            thickness_nm=float(value.get("thickness_nm", 0.0)),
            enabled=bool(value.get("enabled", True)),
        )

@dataclass(frozen=True)
class SpectrumSpec:
    start_nm: float = 400.0
    stop_nm: float = 800.0
    points: int = 401

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "SpectrumSpec":
        value = value or {}
        return cls(
            start_nm=float(value.get("start_nm", 400.0)),
            stop_nm=float(value.get("stop_nm", 800.0)),
            points=int(value.get("points", 401)),
        )


@dataclass(frozen=True)
class StackDesign:
    incident_material_id: str
    substrate_material_id: str
    layers: tuple[DesignLayer, ...]
    spectrum: SpectrumSpec
    angle_deg: float = 0.0
    polarization: str = "p"
    out_of_range_policy: str = "error"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "StackDesign":
        raw_layers: Sequence[Mapping[str, Any]] = value.get("layers", ())
        return cls(
            incident_material_id=str(value.get("incident_material_id") or "Air"),
            substrate_material_id=str(value.get("substrate_material_id") or "N-BK7"),
            layers=tuple(DesignLayer.from_mapping(layer, i) for i, layer in enumerate(raw_layers)),
            spectrum=SpectrumSpec.from_mapping(value.get("spectrum")),
            angle_deg=float(value.get("angle_deg", 0.0)),
            polarization=str(value.get("polarization", "p")).lower(),
            out_of_range_policy=str(value.get("out_of_range_policy", "error")).lower(),
        )
