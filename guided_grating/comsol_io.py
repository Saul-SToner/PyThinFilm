from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


def _leading_float(text: str) -> float:
    s = str(text).strip()
    match = re.match(r"^[+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?", s)
    if match is None:
        raise ValueError(f"Cannot parse numeric prefix from value: {text!r}")
    return float(match.group(0))


def load_comsol_grating_csv(csv_path: Path | str) -> Dict[str, Any]:
    """Load a COMSOL global-table CSV exported for grating spectra."""

    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    if len(rows) < 6:
        raise ValueError(f"COMSOL CSV looks too short: {path}")

    header = rows[4]
    data_rows = rows[5:]
    if not data_rows:
        raise ValueError(f"COMSOL CSV has no numeric rows: {path}")

    meta_rows = rows[:4]
    meta: Dict[str, str] = {}
    for row in meta_rows:
        if len(row) >= 2:
            meta[str(row[0]).lstrip("% ").strip()] = str(row[1]).strip()

    wavelength_nm: List[float] = []
    r_vals: List[float] = []
    t_vals: List[float] = []
    a_vals: List[float] = []
    sum_vals: List[float] = []

    for row in data_rows:
        wavelength_nm.append(float(row[0]) * 1e9)
        r_vals.append(_leading_float(row[6]))
        t_vals.append(_leading_float(row[7]))
        if len(row) > 9:
            a_vals.append(abs(_leading_float(row[9])))
        else:
            a_vals.append(max(0.0, 1.0 - r_vals[-1] - t_vals[-1]))
        if len(row) > 10:
            sum_vals.append(_leading_float(row[10]))
        else:
            sum_vals.append(r_vals[-1] + t_vals[-1])

    wl = np.asarray(wavelength_nm, dtype=float)
    r = np.asarray(r_vals, dtype=float)
    t = np.asarray(t_vals, dtype=float)
    a = np.asarray(a_vals, dtype=float)
    rt_sum = np.asarray(sum_vals, dtype=float)

    return {
        "sample_id": path.stem,
        "model_type": "comsol_grating_global_table",
        "is_placeholder": False,
        "backend": "comsol_csv",
        "warning": "",
        "source_csv": str(path),
        "meta": meta,
        "header": header,
        "spec": {
            "sample_id": path.stem,
            "source_csv": str(path),
            "notes": "Loaded from COMSOL grating global table export.",
        },
        "wavelength_nm": wl,
        "R": r,
        "T": t,
        "A": a,
        "energy_sum": rt_sum,
    }


def _period_key(period_nm: float) -> str:
    return f"{period_nm:.6f}"


def _clean_header_name(text: str) -> str:
    s = str(text).strip().lstrip("% ").strip()
    if "(" in s:
        s = s.split("(", 1)[0].strip()
    return s


def _normalize_sweep_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_")


def _sweep_scale_and_unit(sweep_name: str) -> tuple[float, str]:
    normalized = _normalize_sweep_name(sweep_name)
    if normalized in {"ff", "fill", "fill_factor", "duty_cycle"}:
        return 1.0, "value"
    return 1e9, "nm"


def load_comsol_two_param_sweep(
    csv_path: Path | str,
    sweep_name: str | None = None,
) -> Dict[str, Any]:
    """Load a COMSOL wavelength + one-parameter sweep table.

    This function intentionally uses only the first result block
    (columns 0-11). Some COMSOL exports may append a second repeated result
    block (columns 12+) when the table layout is widened; that duplicate
    block is ignored here.
    """

    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    if len(rows) < 6:
        raise ValueError(f"COMSOL CSV looks too short: {path}")

    header = rows[4]
    data_rows = rows[5:]
    if len(header) < 12:
        raise ValueError(f"COMSOL sweep CSV header is too short: {path}")

    detected_sweep_name = _clean_header_name(header[1]) or "sweep_param"
    active_sweep_name = str(sweep_name or detected_sweep_name)
    active_label = active_sweep_name.replace(" ", "_")
    value_scale, display_unit = _sweep_scale_and_unit(active_sweep_name)

    groups: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "param_value_raw": 0.0,
            "param_value_display": 0.0,
            "wavelength_nm": [],
            "R": [],
            "T": [],
            "A": [],
            "sum": [],
        }
    )

    for row in data_rows:
        param_value_raw = float(row[1])
        param_value_display = param_value_raw * value_scale
        key = _period_key(param_value_display)
        groups[key]["param_value_raw"] = param_value_raw
        groups[key]["param_value_display"] = param_value_display
        groups[key]["wavelength_nm"].append(float(row[0]) * 1e9)
        groups[key]["R"].append(_leading_float(row[7]))
        groups[key]["T"].append(_leading_float(row[8]))
        groups[key]["A"].append(abs(_leading_float(row[10])))
        groups[key]["sum"].append(_leading_float(row[11]))

    result_groups: Dict[str, Dict[str, Any]] = {}
    for key, series in sorted(groups.items(), key=lambda item: item[1]["param_value_display"]):
        param_value_display = float(series["param_value_display"])
        param_label = f"{param_value_display:.6f}".rstrip("0").rstrip(".")
        result_groups[key] = {
            "sample_id": f"{path.stem}_{active_label}_{param_label}{display_unit}",
            "model_type": "comsol_two_param_sweep_member",
            "is_placeholder": False,
            "backend": "comsol_csv_sweep",
            "warning": "",
            "source_csv": str(path),
            "spec": {
                "sample_id": f"{path.stem}_{active_label}_{param_label}{display_unit}",
                active_sweep_name: param_value_raw,
                f"{active_sweep_name}_{display_unit}": param_value_display,
                "sweep_display_unit": display_unit,
                "source_csv": str(path),
                "notes": "Split from COMSOL wavelength + parameter sweep table.",
            },
            "wavelength_nm": np.asarray(series["wavelength_nm"], dtype=float),
            "R": np.asarray(series["R"], dtype=float),
            "T": np.asarray(series["T"], dtype=float),
            "A": np.asarray(series["A"], dtype=float),
            "energy_sum": np.asarray(series["sum"], dtype=float),
        }

    has_duplicate_block = len(header) > 12
    return {
        "sample_id": path.stem,
        "model_type": "comsol_two_param_sweep_bundle",
        "backend": "comsol_csv_sweep",
        "source_csv": str(path),
        "has_duplicate_block": has_duplicate_block,
        "header": header,
        "sweep_name": active_sweep_name,
        "sweep_display_name": detected_sweep_name,
        "sweep_display_unit": display_unit,
        "sweep_groups": result_groups,
    }

