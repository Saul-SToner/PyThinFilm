from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from typing import Any


COMSOL_IMPORT_TEMPLATES: dict[str, dict[str, Any]] = {
    "absorbing_surface_gain": {
        "description": "分别导入粗糙表面与平面基准的光谱文件。",
        "roles": ["rough_surface", "planar_baseline"],
        "required_quantities": ["wavelength_nm", "one_of:R,T,A"],
        "canonical_header": "wavelength_nm,R,T,A",
    },
    "absorbing_surface_gain_trend": {
        "description": "为平面基准和每个粗糙度因子分别导入光谱文件。",
        "roles": ["planar_baseline", "roughness_<factor>"],
        "required_quantities": ["wavelength_nm", "one_of:R,T,A"],
        "canonical_header": "wavelength_nm,R,T,A",
    },
    "advanced_ar_bundle": {
        "description": "为每个增透子案例导入 COMSOL 参考反射光谱。",
        "roles": ["single_ar", "porous", "porous_double", "moth_eye_effective", "moth_eye_2d"],
        "required_quantities": ["wavelength_nm", "R"],
        "canonical_header": "wavelength_nm,R",
    },
    "porous_double_ar_topic_bundle": {
        "description": "导入多孔双层增透的验证、参数或角度扫描数据。",
        "roles": ["validation", "n_porous", "d_porous", "d_high", "theta"],
        "required_quantities": ["wavelength_nm", "R"],
        "canonical_header": "wavelength_nm,R,theta_deg",
    },
}


def import_template(case_id: str) -> dict[str, Any]:
    try:
        return {"case_id": case_id, **COMSOL_IMPORT_TEMPLATES[case_id]}
    except KeyError as exc:
        raise KeyError(f"Unsupported external-evidence case_id: {case_id}") from exc


def _normalized_column(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower().lstrip("%").strip())


def _quantity_for_column(name: str) -> str | None:
    normalized = _normalized_column(name)
    if normalized in {"wavelength", "wavelengthnm", "lambdanm", "lambda", "lam1nm1", "lamnm"} or "wavelength" in normalized or normalized.startswith("lam"):
        return "wavelength_nm"
    if normalized in {"r", "reflectance", "reflection"} or "s11" in normalized:
        return "R"
    if normalized in {"t", "transmittance", "transmission"} or "s21" in normalized:
        return "T"
    if normalized in {"a", "absorptance", "absorption"}:
        return "A"
    if normalized in {"theta", "thetadeg", "thetarad"} or normalized.startswith("theta"):
        return "theta"
    if normalized in {"factor", "roughnessfactor"}:
        return "factor"
    return None


def _parse_number(value: str) -> float:
    text = str(value).strip()
    if "∠" in text:
        text = text.split("∠", 1)[0]
    number = float(text)
    if not math.isfinite(number):
        raise ValueError("non-finite numeric value")
    return number


def validate_comsol_csv(case_id: str, role: str, csv_text: str) -> dict[str, Any]:
    template = import_template(case_id)
    if not role or not any(role == allowed or ("<factor>" in allowed and role.startswith(allowed.split("<", 1)[0])) for allowed in template["roles"]):
        raise ValueError(f"Unsupported role '{role}' for {case_id}")
    lines = [line for line in csv_text.splitlines() if line.strip()]
    header_index = next((index for index, line in enumerate(lines) if "," in line and any(_quantity_for_column(column) for column in line.lstrip("% ").split(","))), None)
    if header_index is None:
        raise ValueError("No recognizable CSV header was found")
    reader = csv.DictReader(io.StringIO("\n".join([lines[header_index].lstrip("% "), *[line for line in lines[header_index + 1 :] if not line.lstrip().startswith("%")]])))
    columns = reader.fieldnames or []
    mapping = {quantity: column for column in columns if (quantity := _quantity_for_column(column))}
    required = {"wavelength_nm"}
    if case_id in {"advanced_ar_bundle", "porous_double_ar_topic_bundle"}:
        required.add("R")
    elif not {"R", "T", "A"}.intersection(mapping):
        raise ValueError("At least one of R, T, or A is required")
    missing = sorted(required - set(mapping))
    if missing:
        raise ValueError(f"Missing required quantity: {', '.join(missing)}")

    row_count = 0
    minima: dict[str, float] = {}
    maxima: dict[str, float] = {}
    for row in reader:
        if not any(str(value or "").strip() for value in row.values()):
            continue
        for quantity, column in mapping.items():
            value = _parse_number(row.get(column, ""))
            minima[quantity] = min(minima.get(quantity, value), value)
            maxima[quantity] = max(maxima.get(quantity, value), value)
        row_count += 1
    if row_count < 2:
        raise ValueError("At least two numeric data rows are required")
    for quantity in ("R", "T", "A"):
        if quantity in minima and (minima[quantity] < -1e-6 or maxima[quantity] > 1.0 + 1e-6):
            raise ValueError(f"{quantity} must stay within [0, 1]")
    return {
        "valid": True,
        "case_id": case_id,
        "role": role,
        "row_count": row_count,
        "columns": columns,
        "quantity_mapping": mapping,
        "ranges": {quantity: {"min": minima[quantity], "max": maxima[quantity]} for quantity in mapping},
        "sha256": hashlib.sha256(csv_text.encode("utf-8")).hexdigest(),
    }
