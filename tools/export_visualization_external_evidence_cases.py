# -*- coding: utf-8 -*-
"""Build standalone external-evidence contracts for research visualization apps.

The contracts intentionally describe analysis outputs rather than inventing a
planar Three.js stack for COMSOL scans, rough surfaces, or validation bundles.
Only basenames and file hashes are exported; private absolute paths are not.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thinfilm.validation import (
    analyze_absorbing_surface_gain_against_baseline,
    analyze_quasi_random_absorbing_surface,
    analyze_tamm_dw_phase_scan,
    analyze_tamm_interface_2d_window_csv,
    analyze_tamm_reflection_phase_screen,
    build_advanced_ar_validation_cases,
    compare_teaching_case_to_reference,
    run_teaching_validation_suite,
    summarize_absorbing_surface_gain_trend,
)
from tools.export_visualization_cases import compute_hash, get_git_commit_hash


EXTERNAL_DATA_DIR = Path(r"C:\Users\L2791\OneDrive\Desktop\deg.p")
OUTPUT_DIR = ROOT / "web3d" / "public" / "evidence"

EXTERNAL_EVIDENCE_CASES = {
    "tamm_interface_priority": "tamm-interface-priority",
    "tamm_phase_candidates": "tamm-phase-candidates",
    "tamm_phase_focus": "tamm-phase-focus",
    "tamm_reflection_phase_screen": "tamm-reflection-phase-screen",
    "tamm_interface_window_bundle": "tamm-interface-window-bundle",
    "tamm_interface_window_scan": "tamm-interface-window-scan",
    "absorbing_baseline_template": "absorbing-baseline-template",
    "absorbing_surface_bundle": "absorbing-surface-bundle",
    "absorbing_surface_gain": "absorbing-surface-gain",
    "absorbing_surface_gain_trend": "absorbing-surface-gain-trend",
    "advanced_ar_bundle": "advanced-ar-bundle",
    "porous_double_ar_topic_bundle": "porous-double-ar-topic",
}


def _json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.name
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _sha256(path: Path) -> str | None:
    if not path.is_file() or path.stat().st_size <= 0:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _provenance(role: str, filename: str) -> dict[str, Any]:
    path = EXTERNAL_DATA_DIR / filename
    available = path.is_file() and path.stat().st_size > 0
    return {
        "role": role,
        "file_name": filename,
        "status": "AVAILABLE" if available else "MISSING",
        "size_bytes": path.stat().st_size if available else 0,
        "sha256": _sha256(path),
    }


def _base(case_id: str, title: str, source_file: str, source_symbol: str, *, status: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "title": title,
        "source_commit": get_git_commit_hash(),
        "source_file": source_file,
        "source_symbol": source_symbol,
        "generated_at": datetime.datetime.now().isoformat(),
        "calculation_source": "python_external_csv_analysis",
        "evidence_status": status,
        "summary_cards": [],
        "series": [],
        "table": {"columns": [], "rows": []},
        "limitations": [],
    }


def _finish(contract: dict[str, Any]) -> dict[str, Any]:
    clean = _json_value(contract)
    hash_payload = {
        "case_id": clean["case_id"],
        "calculation_source": clean["calculation_source"],
        "evidence_status": clean["evidence_status"],
        "external_data_provenance": clean.get("external_data_provenance", []),
        "summary_cards": clean.get("summary_cards", []),
        "series": clean.get("series", []),
        "table": clean.get("table", {}),
        "limitations": clean.get("limitations", []),
    }
    clean["evidence_hash"] = compute_hash(hash_payload)
    clean["result_hash"] = compute_hash(clean)
    return clean


def _card(label: str, value: Any, unit: str = "", note: str = "") -> dict[str, Any]:
    return {"label": label, "value": _json_value(value), "unit": unit, "note": note}


def _downsample(x: Any, y: Any, maximum: int = 260) -> tuple[list[float], list[float]]:
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if len(x_arr) <= maximum:
        indices = np.arange(len(x_arr))
    else:
        indices = np.unique(np.linspace(0, len(x_arr) - 1, maximum).round().astype(int))
    return [round(float(x_arr[i]), 8) for i in indices], [round(float(y_arr[i]), 10) for i in indices]


def _series(label: str, x: Any, y: Any, *, x_label: str, y_label: str, color: str) -> dict[str, Any]:
    xs, ys = _downsample(x, y)
    return {"label": label, "x": xs, "y": ys, "x_label": x_label, "y_label": y_label, "color": color}


TAMM_SCAN_FILE = "tamm_spectrum_dW_scan(4).csv"


def _tamm_scan() -> dict[str, Any]:
    return analyze_tamm_dw_phase_scan(EXTERNAL_DATA_DIR / TAMM_SCAN_FILE)


def export_tamm_interface_priority() -> dict[str, Any]:
    result = _tamm_scan()
    screen = analyze_tamm_reflection_phase_screen(EXTERNAL_DATA_DIR / TAMM_SCAN_FILE)
    best = screen["summary"]["best_pair"]
    contract = _base(
        "tamm_interface_priority", "Tamm 界面态优先极化筛选",
        "cases/tamm/run_tamm_interface_priority.py", "export_tamm_interface_priority",
        status="READY_EXTERNAL",
    )
    contract["external_data_provenance"] = [_provenance("phase_scan", TAMM_SCAN_FILE)]
    contract["summary_cards"] = [
        _card("最佳吸收层厚", result["summary"]["best_dW_nm"], "nm"),
        _card("峰值吸收", result["summary"]["best_A_max"]),
        _card("端结构候选", f"{best['dW_left_nm']:.0f}/{best['dW_right_nm']:.0f}", "nm"),
        _card("通过严格判据", screen["summary"]["num_passing_pairs"], "组"),
    ]
    contract["table"] = {
        "columns": ["dW_nm", "A_max", "peak_um", "phase_at_peak_rad"],
        "rows": [[g["dW_nm"], g["summary"]["A_max"], g["summary"]["peak_wavelength_um"], g["summary"]["phase_at_peak_rad"]] for g in result["groups"]],
    }
    contract["limitations"] = [
        "当前严格高反射与 π 相位差联合判据没有通过项；页面显示候选优先级，不宣称已经发现界面本征态。",
        "数据来自单个 COMSOL dW 扫描文件，不能外推到未扫描参数。",
    ]
    return _finish(contract)


def export_tamm_phase_candidates() -> dict[str, Any]:
    screen = analyze_tamm_reflection_phase_screen(EXTERNAL_DATA_DIR / TAMM_SCAN_FILE)
    contract = _base(
        "tamm_phase_candidates", "Tamm 相位匹配候选点搜寻",
        "cases/tamm/run_tamm_phase_candidates.py", "analyze_tamm_reflection_phase_screen",
        status="READY_EXTERNAL",
    )
    contract["external_data_provenance"] = [_provenance("phase_scan", TAMM_SCAN_FILE)]
    best = screen["summary"]["best_pair"]
    contract["summary_cards"] = [
        _card("候选对总数", screen["summary"]["num_pairs"]),
        _card("通过数", screen["summary"]["num_passing_pairs"]),
        _card("最小反射率", best["min_R"]),
        _card("相位误差", best["phase_error_to_pi_rad"], "rad"),
    ]
    contract["series"] = [_series(
        "候选对：相位误差 vs 最小反射率",
        [row["phase_error_to_pi_rad"] for row in screen["rows"]],
        [row["min_R"] for row in screen["rows"]],
        x_label="|π-Δφ| (rad)", y_label="min(R_left,R_right)", color="#5f7891",
    )]
    contract["table"] = {
        "columns": ["left_nm", "right_nm", "lambda_um", "min_R", "phase_error", "passes"],
        "rows": [[r["dW_left_nm"], r["dW_right_nm"], r["wavelength_um"], r["min_R"], r["phase_error_to_pi_rad"], r["passes"]] for r in screen["rows"][:16]],
    }
    contract["limitations"] = [screen["interpretation_cn"]]
    return _finish(contract)


def export_tamm_phase_focus() -> dict[str, Any]:
    result = _tamm_scan()
    selected = [min(result["groups"], key=lambda group: abs(float(group["dW_nm"]) - target)) for target in (100.0, 110.0, 120.0)]
    contract = _base(
        "tamm_phase_focus", "Tamm 相位聚焦与吸收增强",
        "cases/tamm/run_tamm_phase_focus.py", "analyze_tamm_dw_phase_scan",
        status="READY_EXTERNAL",
    )
    contract["external_data_provenance"] = [_provenance("phase_scan", TAMM_SCAN_FILE)]
    contract["summary_cards"] = [
        _card("聚焦厚度", "100 / 110 / 120", "nm"),
        _card("全局最佳 A", result["summary"]["best_A_max"]),
        _card("最佳峰位", result["summary"]["best_peak_wavelength_um"], "μm"),
        _card("相位阶段就绪", result["phase_ready"]),
    ]
    colors = ("#758ca3", "#9a8495", "#7f937e")
    contract["series"] = [
        _series(f"dW={g['dW_nm']:.0f} nm · A", g["wavelength_um"], g["A"], x_label="波长 (μm)", y_label="A", color=color)
        for g, color in zip(selected, colors)
    ]
    contract["table"] = {
        "columns": ["dW_nm", "A_max", "peak_um", "phase_span_rad"],
        "rows": [[g["dW_nm"], g["summary"]["A_max"], g["summary"]["peak_wavelength_um"], g["summary"]["phase_unwrapped_span_rad"]] for g in selected],
    }
    contract["limitations"] = ["聚焦页比较三个已有扫描组；它不是连续厚度优化器。"]
    return _finish(contract)


def export_tamm_reflection_screen() -> dict[str, Any]:
    result = analyze_tamm_reflection_phase_screen(EXTERNAL_DATA_DIR / TAMM_SCAN_FILE)
    contract = _base(
        "tamm_reflection_phase_screen", "Tamm 界面反射相位多波长筛选",
        "cases/tamm/run_tamm_reflection_phase_screen.py", "analyze_tamm_reflection_phase_screen",
        status="READY_EXTERNAL",
    )
    contract["external_data_provenance"] = [_provenance("phase_scan", TAMM_SCAN_FILE)]
    best = result["summary"]["best_pair"]
    contract["summary_cards"] = [
        _card("候选对", result["summary"]["num_pairs"]),
        _card("严格通过", result["summary"]["num_passing_pairs"]),
        _card("最佳波长", best["wavelength_um"], "μm"),
        _card("最佳评分", best["score"]),
    ]
    contract["series"] = [_series(
        "相位误差—反射率筛选",
        [row["phase_error_to_pi_rad"] for row in result["rows"]],
        [row["min_R"] for row in result["rows"]],
        x_label="相位误差 (rad)", y_label="最小反射率", color="#667f98",
    )]
    contract["table"] = {
        "columns": ["left_nm", "right_nm", "lambda_um", "min_R", "phase_diff_rad", "score", "passes"],
        "rows": [[r["dW_left_nm"], r["dW_right_nm"], r["wavelength_um"], r["min_R"], r["phase_diff_rad"], r["score"], r["passes"]] for r in result["rows"][:20]],
    }
    contract["limitations"] = [result["interpretation_cn"]]
    return _finish(contract)


WINDOW_FILES = {
    "yplus5": "tamm_interface_110to120_yplus5nm.csv",
    "yplus2": "tamm_interface_110to120_yplus2nm.csv",
    "yplus10": "tamm_interface_110to120_yplus10nm.csv",
}
WINDOW_MISSING = {
    "E3": "E3.csv",
    "E4": "E4.csv",
    "test111": "tamm_interface_test_111nm_455um.csv",
}


def _window_results(**kwargs: Any) -> dict[str, dict[str, Any]]:
    return {
        label: analyze_tamm_interface_2d_window_csv(EXTERNAL_DATA_DIR / filename, **kwargs)
        for label, filename in WINDOW_FILES.items()
    }


def export_tamm_window_bundle() -> dict[str, Any]:
    results = _window_results()
    contract = _base(
        "tamm_interface_window_bundle", "Tamm 界面窗口束",
        "cases/tamm/run_tamm_interface_window_bundle.py", "analyze_tamm_interface_2d_window_csv",
        status="DEGRADED_PARTIAL_INPUT",
    )
    contract["external_data_provenance"] = [
        *[_provenance(label, filename) for label, filename in WINDOW_FILES.items()],
        *[_provenance(label, filename) for label, filename in WINDOW_MISSING.items()],
    ]
    best = max((item["best_interface_gain"] for item in results.values()), key=lambda row: float(row["G_interface"]))
    contract["summary_cards"] = [
        _card("可用来源", len(results), "份"),
        _card("缺失来源", len(WINDOW_MISSING), "份"),
        _card("最佳 G_interface", best["G_interface"]),
        _card("最佳 dW", best["dW_left_nm"], "nm"),
    ]
    rows = []
    for label, item in results.items():
        row = item["best_interface_gain"]
        rows.append([label, item["source_is_true_2d"], row["dW_left_nm"], row["wavelength_um"], row["G_interface"], row["eta_interface"], row["wx_um"]])
    contract["table"] = {"columns": ["source", "true_2d", "dW_nm", "lambda_um", "G_if", "eta_if", "wx_um"], "rows": rows}
    contract["limitations"] = [
        "原 Runner 声明的 E3.csv、E4.csv 和 test111 文件缺失；本页只分析三份现存 y+ 线切数据。",
        "现存文件 unique_y=1，因此不能称为完整二维场热力图。",
    ]
    return _finish(contract)


def export_tamm_window_scan() -> dict[str, Any]:
    configurations = [
        ((8.8, 10.4), 0.3), ((8.8, 10.4), 0.5), ((8.8, 10.4), 0.8),
        ((9.0, 9.8), 0.3), ((9.0, 9.8), 0.5), ((9.0, 9.8), 0.8),
        ((9.2, 10.0), 0.3), ((9.2, 10.0), 0.5), ((9.2, 10.0), 0.8),
    ]
    scan_rows = []
    for y_window, half_width in configurations:
        config_results = {}
        for label, filename in WINDOW_FILES.items():
            try:
                config_results[label] = analyze_tamm_interface_2d_window_csv(
                    EXTERNAL_DATA_DIR / filename,
                    y_window_um=y_window,
                    interface_half_width_um=half_width,
                )
            except ValueError:
                continue
        for label, item in config_results.items():
            best = item["best_interface_gain"]
            scan_rows.append({
                "source": label, "y_window": list(y_window), "half_width": half_width,
                "dW_nm": best["dW_left_nm"], "lambda_um": best["wavelength_um"],
                "G_interface": best["G_interface"], "eta_interface": best["eta_interface"], "wx_um": best["wx_um"],
            })
    best = max(scan_rows, key=lambda row: float(row["G_interface"]))
    contract = _base(
        "tamm_interface_window_scan", "Tamm 界面窗口扫描",
        "cases/tamm/run_tamm_interface_window_scan.py", "analyze_tamm_interface_2d_window_csv",
        status="DEGRADED_PARTIAL_INPUT",
    )
    contract["external_data_provenance"] = [
        *[_provenance(label, filename) for label, filename in WINDOW_FILES.items()],
        *[_provenance(label, filename) for label, filename in WINDOW_MISSING.items()],
    ]
    contract["summary_cards"] = [
        _card("窗口配置", len(configurations)), _card("有效组合", len(scan_rows)),
        _card("最佳 G_interface", best["G_interface"]), _card("最佳半宽", best["half_width"], "μm"),
    ]
    contract["series"] = [_series(
        "窗口配置序号—G_interface",
        list(range(1, len(scan_rows) + 1)), [row["G_interface"] for row in scan_rows],
        x_label="配置序号", y_label="G_interface", color="#758ca3",
    )]
    contract["table"] = {
        "columns": ["source", "y_window", "half_width", "dW_nm", "lambda_um", "G_if"],
        "rows": [[r["source"], r["y_window"], r["half_width"], r["dW_nm"], r["lambda_um"], r["G_interface"]] for r in sorted(scan_rows, key=lambda row: row["G_interface"], reverse=True)[:24]],
    }
    contract["limitations"] = [
        "三份声明来源缺失，扫描结果为降级子集。",
        "现存数据是单 y 截面；窗口扫描评价局域统计稳健性，不是二维热力图。",
    ]
    return _finish(contract)


ROUGH_FILE = "2D periodic quasi-random rough absorbing surface.csv"
BASELINE_FILE = "2D periodic quasi-random rough absorbing surface(basic).csv"


def export_absorbing_baseline_template() -> dict[str, Any]:
    contract = _base(
        "absorbing_baseline_template", "吸收表面基线模板",
        "cases/absorbing_surface/run_absorbing_surface_baseline_template.py", "export_absorbing_surface_baseline_reference_template",
        status="TEMPLATE_ONLY",
    )
    contract["calculation_source"] = "python_template_export"
    contract["external_data_provenance"] = [_provenance("available_baseline_example", BASELINE_FILE)]
    contract["summary_cards"] = [
        _card("中心波长", 550, "nm"), _card("模板状态", "等待用户绑定"),
        _card("建议量", "R / T / A"), _card("几何要求", "同材料同厚度平面基准"),
    ]
    contract["table"] = {
        "columns": ["required_column", "meaning"],
        "rows": [["lam/1[nm] (1)", "波长"], ["abs(ewfd.S11)^2 (1)", "R"], ["abs(ewfd.S21)^2 (1)", "T"], ["1-R-T", "A"]],
    }
    contract["limitations"] = ["这是输入模板而不是一个独立物理仿真结果；页面不会绘制虚构光谱。"]
    return _finish(contract)


def export_absorbing_bundle() -> dict[str, Any]:
    result = analyze_quasi_random_absorbing_surface(EXTERNAL_DATA_DIR / ROUGH_FILE)
    contract = _base(
        "absorbing_surface_bundle", "吸收表面综合计算束",
        "cases/absorbing_surface/run_absorbing_surface_bundle.py", "analyze_quasi_random_absorbing_surface",
        status="READY_EXTERNAL",
    )
    contract["external_data_provenance"] = [_provenance("rough_surface", ROUGH_FILE)]
    summary = result["summary"]
    contract["summary_cards"] = [
        _card("平均吸收率", summary["A_mean"]), _card("550 nm 吸收率", summary["A_at_lambda0"]),
        _card("峰值吸收率", summary["A_max"]), _card("能量残差", summary["energy_balance_max_error"]),
    ]
    contract["series"] = [
        _series("R", result["wavelength_nm"], result["R"], x_label="波长 (nm)", y_label="功率", color="#6c8298"),
        _series("T", result["wavelength_nm"], result["T"], x_label="波长 (nm)", y_label="功率", color="#869b91"),
        _series("A", result["wavelength_nm"], result["A"], x_label="波长 (nm)", y_label="功率", color="#a58a72"),
    ]
    contract["limitations"] = ["光谱来自 COMSOL 粗糙表面结果；没有可审计的逐层平面结构，因此不绘制 Three.js 膜层。"]
    return _finish(contract)


def export_absorbing_gain() -> dict[str, Any]:
    result = analyze_absorbing_surface_gain_against_baseline(
        EXTERNAL_DATA_DIR / ROUGH_FILE, EXTERNAL_DATA_DIR / BASELINE_FILE,
    )
    contract = _base(
        "absorbing_surface_gain", "吸收表面增益模型",
        "cases/absorbing_surface/run_absorbing_surface_gain.py", "analyze_absorbing_surface_gain_against_baseline",
        status="READY_EXTERNAL",
    )
    contract["external_data_provenance"] = [_provenance("rough_surface", ROUGH_FILE), _provenance("planar_baseline", BASELINE_FILE)]
    delta = result["delta_summary"]
    contract["summary_cards"] = [
        _card("平均吸收增益", delta["delta_A_mean"]), _card("550 nm 吸收增益", delta["delta_A_at_lambda0"]),
        _card("平均吸收倍率", delta["rough_to_baseline_A_mean_ratio"]), _card("550 nm 倍率", delta["rough_to_baseline_A_at_lambda0_ratio"]),
    ]
    contract["series"] = [
        _series("粗糙表面 A", result["rough"]["wavelength_nm"], result["rough"]["A"], x_label="波长 (nm)", y_label="A", color="#a27f68"),
        _series("平面基准 A", result["baseline"]["wavelength_nm"], result["baseline"]["A"], x_label="波长 (nm)", y_label="A", color="#70879b"),
    ]
    contract["limitations"] = [result["interpretation_cn"], "增益只对这两个输入文件成立。"]
    return _finish(contract)


ROUGHNESS_FILES = {
    0.25: "2D periodic quasi-random rough absorbing surface(0.25).csv",
    0.5: "2D periodic quasi-random rough absorbing surface(0.5).csv",
    0.75: "2D periodic quasi-random rough absorbing surface(0.75).csv",
    1.0: ROUGH_FILE,
    1.1: "2D periodic quasi-random rough absorbing surface(1.1).csv",
    1.15: "2D periodic quasi-random rough absorbing surface(1.15).csv",
}


def export_absorbing_gain_trend() -> dict[str, Any]:
    result = summarize_absorbing_surface_gain_trend(
        {factor: EXTERNAL_DATA_DIR / filename for factor, filename in ROUGHNESS_FILES.items()},
        EXTERNAL_DATA_DIR / BASELINE_FILE,
    )
    contract = _base(
        "absorbing_surface_gain_trend", "吸收表面增益趋势",
        "cases/absorbing_surface/run_absorbing_surface_gain_trend.py", "summarize_absorbing_surface_gain_trend",
        status="READY_EXTERNAL",
    )
    contract["external_data_provenance"] = [
        _provenance("planar_baseline", BASELINE_FILE),
        *[_provenance(f"roughness_{factor}", filename) for factor, filename in ROUGHNESS_FILES.items()],
    ]
    best = result["best_by_delta_amean"]
    contract["summary_cards"] = [
        _card("扫描点", len(result["rows"])), _card("最佳粗糙度因子", best["roughness_factor"]),
        _card("最佳平均增益", best["delta_A_mean"]), _card("严格单调", result["monotonic_delta_amean"]),
    ]
    factors = [row["roughness_factor"] for row in result["rows"]]
    contract["series"] = [
        _series("ΔA_mean", factors, [row["delta_A_mean"] for row in result["rows"]], x_label="粗糙度因子", y_label="吸收增益", color="#7f927d"),
        _series("ΔA@550", factors, [row["delta_A_at_lambda0"] for row in result["rows"]], x_label="粗糙度因子", y_label="吸收增益", color="#9b826e"),
    ]
    contract["table"] = {
        "columns": ["factor", "A_mean", "A_550", "delta_A_mean", "delta_A_550"],
        "rows": [[r["roughness_factor"], r["A_mean"], r["A_at_lambda0"], r["delta_A_mean"], r["delta_A_at_lambda0"]] for r in result["rows"]],
    }
    contract["limitations"] = [result["interpretation_cn"]]
    return _finish(contract)


ADVANCED_AR_FILES = {
    "single_ar": "AR_MgF2_BK7G18_550nm_theta0.csv",
    "porous": "porous.csv",
    "porous_double": "New.csv",
    "moth_eye_effective": "Rugate2.csv",
    "moth_eye_2d": "moth_eye_2D_trapezoid_P200_H300_Wtop40_Wbottom180_Glass_550nm_theta0_comsol.csv",
}


def export_advanced_ar() -> dict[str, Any]:
    cases = build_advanced_ar_validation_cases(
        *(EXTERNAL_DATA_DIR / ADVANCED_AR_FILES[key] for key in ("single_ar", "porous", "porous_double", "moth_eye_effective", "moth_eye_2d"))
    )
    results = run_teaching_validation_suite(cases)
    contract = _base(
        "advanced_ar_bundle", "高级增透膜计算束",
        "cases/advanced_ar/run_advanced_ar_bundle.py", "build_advanced_ar_validation_cases",
        status="READY_EXTERNAL",
    )
    contract["external_data_provenance"] = [_provenance(role, filename) for role, filename in ADVANCED_AR_FILES.items()]
    maes = [item["summary"]["mae"] for item in results]
    contract["summary_cards"] = [
        _card("验证子案例", len(results)), _card("最小 MAE", min(maes)),
        _card("最大 MAE", max(maes)), _card("参考来源", "COMSOL"),
    ]
    contract["series"] = [_series(
        "子案例 MAE", list(range(1, len(results) + 1)), maes,
        x_label="子案例序号", y_label="MAE", color="#6f879b",
    )]
    contract["table"] = {
        "columns": ["case_id", "reference", "points", "mae", "rmse", "lambda0_error"],
        "rows": [[item["case_id"], Path(item["reference_csv"]).name, item["summary"]["num_points"], item["summary"]["mae"], item["summary"]["rmse"], item["summary"]["lambda0_error"]] for item in results],
    }
    contract["limitations"] = ["该入口是五项 Python—COMSOL 验证总览，不把不同结构拼接成一个 Three.js 膜堆。"]
    return _finish(contract)


POROUS_TOPIC_FILES = {
    "validation": "New.csv", "n_porous": "n_porous.csv", "d_porous": "err_d_porous.csv",
    "d_high": "err_d_high.csv", "theta": "theta.csv",
}


def export_porous_topic() -> dict[str, Any]:
    result = compare_teaching_case_to_reference(
        "porous_double_ar", EXTERNAL_DATA_DIR / POROUS_TOPIC_FILES["validation"],
        y_selector="abs(ewfd.S11)^2 (1)", quantity="R", reference_label="COMSOL",
        theta_deg=0.0, pol="p", lambda0_nm=550.0, n_incident=1.0, n_substrate=1.5215,
        n_porous=1.18, n_high=1.45,
    )
    comparison = result["comparison"]
    contract = _base(
        "porous_double_ar_topic_bundle", "多孔双层增透专题",
        "cases/advanced_ar/run_porous_double_ar_topic_bundle.py", "compare_teaching_case_to_reference",
        status="READY_EXTERNAL_WITH_LIMITS",
    )
    contract["external_data_provenance"] = [_provenance(role, filename) for role, filename in POROUS_TOPIC_FILES.items()]
    summary = result["summary"]
    contract["summary_cards"] = [
        _card("验证 MAE", summary["mae"]), _card("验证 RMSE", summary["rmse"]),
        _card("550 nm 误差", summary["lambda0_error"]), _card("验证点", summary["num_points"]),
    ]
    contract["series"] = [
        _series("Python R", comparison["wavelength_nm"], comparison["theory"], x_label="波长 (nm)", y_label="R", color="#6d8599"),
        _series("COMSOL R", comparison["wavelength_nm"], comparison["reference"], x_label="波长 (nm)", y_label="R", color="#a48770"),
    ]
    contract["table"] = {
        "columns": ["input", "status", "sha256_prefix"],
        "rows": [[item["role"], item["status"], (item["sha256"] or "")[:16]] for item in contract["external_data_provenance"]],
    }
    contract["limitations"] = [
        "光谱验证可直接复算；灵敏度和角度 CSV 在本入口记录来源哈希，但不在前端重新解释多参数列。",
        "结论仍以 Python topic bundle 的正式分析为准。",
    ]
    return _finish(contract)


EXPORTERS: dict[str, Callable[[], dict[str, Any]]] = {
    "tamm_interface_priority": export_tamm_interface_priority,
    "tamm_phase_candidates": export_tamm_phase_candidates,
    "tamm_phase_focus": export_tamm_phase_focus,
    "tamm_reflection_phase_screen": export_tamm_reflection_screen,
    "tamm_interface_window_bundle": export_tamm_window_bundle,
    "tamm_interface_window_scan": export_tamm_window_scan,
    "absorbing_baseline_template": export_absorbing_baseline_template,
    "absorbing_surface_bundle": export_absorbing_bundle,
    "absorbing_surface_gain": export_absorbing_gain,
    "absorbing_surface_gain_trend": export_absorbing_gain_trend,
    "advanced_ar_bundle": export_advanced_ar,
    "porous_double_ar_topic_bundle": export_porous_topic,
}


def export_all() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for case_id, exporter in EXPORTERS.items():
        output = OUTPUT_DIR / f"{case_id}.json"
        output.write_text(json.dumps(exporter(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[evidence] {case_id} -> {output}")


if __name__ == "__main__":
    export_all()
