from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


def summarize_guided_grating_spectrum(result: Dict[str, Any]) -> Dict[str, Any]:
    wl = np.asarray(result["wavelength_nm"], dtype=float)
    r_vals = np.asarray(result["R"], dtype=float)
    t_vals = np.asarray(result["T"], dtype=float)
    a_vals = np.asarray(result["A"], dtype=float)

    peak_idx = int(np.argmax(r_vals))
    peak_r = float(r_vals[peak_idx])
    peak_wl = float(wl[peak_idx])
    half_level = 0.5 * peak_r
    above = np.where(r_vals >= half_level)[0]
    fwhm_nm = float(wl[above[-1]] - wl[above[0]]) if len(above) >= 2 else 0.0

    return {
        "peak_reflectance": peak_r,
        "peak_wavelength_nm": peak_wl,
        "fwhm_nm": fwhm_nm,
        "min_reflectance": float(np.min(r_vals)),
        "min_reflectance_wavelength_nm": float(wl[int(np.argmin(r_vals))]),
        "max_transmittance": float(np.max(t_vals)),
        "max_absorptance": float(np.max(a_vals)),
        "wavelength_start_nm": float(wl[0]),
        "wavelength_stop_nm": float(wl[-1]),
        "num_points": int(wl.size),
        "backend": result.get("backend"),
        "is_placeholder": bool(result.get("is_placeholder", False)),
    }


def summarize_lambda_period_sweep(
    bundle: Dict[str, Any],
    target_wavelength_nm: float = 1550.0,
) -> Dict[str, Any]:
    period_summaries: List[Dict[str, Any]] = []
    groups = bundle.get("sweep_groups", {})
    sweep_name = str(bundle.get("sweep_name") or "period")
    sweep_display_unit = str(bundle.get("sweep_display_unit") or "nm")
    sweep_value_key = f"{sweep_name}_{sweep_display_unit}"

    for period_key, result in groups.items():
        spec = result.get("spec", {})
        period_nm = float(spec.get(sweep_value_key, float(period_key)))
        summary = summarize_guided_grating_spectrum(result)
        row = {
            "period_key": str(period_key),
            "period_nm": period_nm,
            "sweep_name": sweep_name,
            "sweep_display_unit": sweep_display_unit,
            **summary,
            "target_error_nm": abs(
                float(summary["peak_wavelength_nm"]) - float(target_wavelength_nm)
            ),
        }
        period_summaries.append(row)

    period_summaries.sort(
        key=lambda row: (
            float(row["target_error_nm"]),
            -float(row["peak_reflectance"]),
            float(row["fwhm_nm"]),
        )
    )
    best = period_summaries[0] if period_summaries else {}

    return {
        "sample_id": bundle.get("sample_id", ""),
        "source_csv": bundle.get("source_csv", ""),
        "backend": bundle.get("backend"),
        "has_duplicate_block": bool(bundle.get("has_duplicate_block", False)),
        "sweep_name": sweep_name,
        "sweep_display_unit": sweep_display_unit,
        "target_wavelength_nm": float(target_wavelength_nm),
        "num_periods": len(period_summaries),
        "best_candidate": best,
        "period_summaries": period_summaries,
    }
