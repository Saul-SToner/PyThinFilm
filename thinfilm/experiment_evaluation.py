"""Transparent physics criteria for guided undergraduate experiments."""

from __future__ import annotations

from typing import Any

import numpy as np

from .design_models import StackDesign
from .materials import material_complex_index


def _criterion(label: str, value: float | None, target: str, score: float, passed: bool) -> dict[str, Any]:
    return {"label": label, "value": value, "target": target, "score": float(np.clip(score, 0.0, 1.0)), "passed": bool(passed)}


def evaluate_experiment(
    task_id: str | None,
    design: StackDesign,
    wavelengths: np.ndarray,
    reflectance: np.ndarray,
    transmittance: np.ndarray,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    if not task_id:
        return {"status": "not_applicable", "task_id": None, "score": None, "level": None, "criteria": [], "feedback": "自由探索模式不进行任务评分。"}

    target_index = int(np.argmin(np.abs(wavelengths - 550.0)))
    r550, t550 = float(reflectance[target_index]), float(transmittance[target_index])
    enabled = [layer for layer in design.layers if layer.enabled]
    criteria: list[dict[str, Any]] = []
    if task_id == "single-layer-ar":
        minimum = metrics["R"]["minimum"]
        minimum_wavelength = metrics["R"]["minimum_wavelength_nm"]
        phase_error = None
        if enabled:
            resolved_n = float(
                np.real(
                    np.asarray(
                        material_complex_index(
                            enabled[0].material_id,
                            550.0,
                            out_of_range_policy=design.out_of_range_policy,
                        )
                    ).item()
                )
            )
            if resolved_n > 0:
                expected = 550.0 / (4.0 * resolved_n)
                phase_error = abs(enabled[0].thickness_nm - expected) / expected
        criteria = [
            _criterion("550 nm反射率", r550, "≤ 3%", 1.0 - r550 / 0.10, r550 <= 0.03),
            _criterion("反射谷与550 nm偏差", abs(minimum_wavelength - 550.0), "≤ 25 nm", 1.0 - abs(minimum_wavelength - 550.0) / 100.0, abs(minimum_wavelength - 550.0) <= 25.0),
            _criterion("最低反射率", minimum, "≤ 3%", 1.0 - minimum / 0.10, minimum <= 0.03),
        ]
        if phase_error is not None:
            criteria.append(_criterion("四分之一波长厚度相对误差", phase_error, "≤ 15%", 1.0 - phase_error / 0.5, phase_error <= 0.15))
    elif task_id == "bragg-reflector":
        band = metrics["high_reflection_band"]
        width = None if band is None else float(band["width_nm"])
        criteria = [
            _criterion("550 nm反射率", r550, "≥ 90%", (r550 - 0.5) / 0.5, r550 >= 0.9),
            _criterion("R≥90%高反带宽", width, "≥ 50 nm", 0.0 if width is None else width / 100.0, width is not None and width >= 50.0),
            _criterion("启用膜层数", float(len(enabled)), "≥ 6层", len(enabled) / 10.0, len(enabled) >= 6),
        ]
    elif task_id == "fp-cavity":
        linewidth = metrics["transmission_peak_linewidth"]
        width = linewidth["fwhm_nm"]
        q_factor = linewidth["q_factor"]
        criteria = [
            _criterion("最高透射率", metrics["T"]["maximum"], "≥ 80%", metrics["T"]["maximum"], metrics["T"]["maximum"] >= 0.8),
            _criterion("透射峰FWHM", width, "≤ 25 nm", 0.0 if width is None else 1.0 - width / 60.0, width is not None and width <= 25.0),
            _criterion("品质因子Q", q_factor, "≥ 20", 0.0 if q_factor is None else q_factor / 40.0, q_factor is not None and q_factor >= 20.0),
            _criterion("550 nm透射率", t550, "观察量", t550, True),
        ]
    else:
        return {"status": "not_applicable", "task_id": task_id, "score": None, "level": None, "criteria": [], "feedback": "当前任务尚未配置自动评价规则。"}

    score = round(100.0 * float(np.mean([item["score"] for item in criteria])), 1)
    passed_count = sum(bool(item["passed"]) for item in criteria)
    level = "excellent" if score >= 85 and passed_count == len(criteria) else "qualified" if score >= 60 else "developing"
    feedback = {
        "excellent": "主要物理指标均已达到任务目标，请结合场分布和相位证据完成结论。",
        "qualified": "设计已接近任务目标，可优先改进未通过的指标并保存对比记录。",
        "developing": "当前设计仍处于探索阶段，请一次只改变一个变量并观察指标变化。",
    }[level]
    return {"status": "available", "task_id": task_id, "score": score, "level": level, "criteria": criteria, "feedback": feedback}
