"""Automated scientific-evidence audits for exported figures.

The auditor checks the arrays and provenance behind a figure.  It does not
attempt to judge aesthetics from pixels; instead it catches mistakes that can
make an attractive figure scientifically misleading.
"""

from __future__ import annotations

import hashlib
import json
import csv
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


EVIDENCE_LEVELS = {
    "theory": "理论计算",
    "real_material_theory": "真实材料理论计算",
    "external_validation": "外部数据验证",
    "approximation": "近似模型",
    "placeholder": "占位演示",
}


def _issue(code: str, severity: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def _array(values: Sequence[float]) -> np.ndarray:
    return np.asarray(values, dtype=float).reshape(-1)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_rta_data(
    wavelength: Sequence[float],
    R: Sequence[float],
    T: Sequence[float],
    A: Sequence[float],
    *,
    focus: str | None = None,
    feature_kind: str | None = None,
    feature_wavelength: float | None = None,
    conservation_tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Audit bounded R/T/A data, conservation, and a declared feature."""
    wl = _array(wavelength)
    curves = {"R": _array(R), "T": _array(T), "A": _array(A)}
    issues: list[dict[str, str]] = []
    lengths = {wl.size, *(arr.size for arr in curves.values())}
    if len(lengths) != 1 or wl.size == 0:
        issues.append(_issue("shape_mismatch", "error", "波长与 R/T/A 数组长度不一致或为空。"))
        return _result("rta", issues, {})
    if not np.all(np.isfinite(wl)) or any(not np.all(np.isfinite(arr)) for arr in curves.values()):
        issues.append(_issue("non_finite", "error", "光谱包含 NaN 或无穷值。"))
    if np.any(np.diff(wl) <= 0):
        issues.append(_issue("wavelength_order", "error", "波长轴必须严格递增。"))
    for name, arr in curves.items():
        if np.any(arr < -1e-9) or np.any(arr > 1.0 + 1e-9):
            issues.append(_issue("response_out_of_bounds", "error", f"{name} 超出物理范围 [0, 1]。"))
    conservation = curves["R"] + curves["T"] + curves["A"] - 1.0
    max_conservation_error = float(np.nanmax(np.abs(conservation)))
    if max_conservation_error > conservation_tolerance:
        issues.append(_issue("energy_conservation", "warning", f"max|R+T+A-1|={max_conservation_error:.3e}。"))
    if focus is not None and str(focus).upper() not in curves:
        issues.append(_issue("invalid_focus", "error", f"未知主变量 {focus!r}。"))
    if feature_kind is not None:
        kind = str(feature_kind).strip().lower()
        if focus is None or str(focus).upper() not in curves:
            issues.append(_issue("feature_without_focus", "error", "声明峰谷前必须声明 R/T/A 主变量。"))
        elif kind not in {"peak", "valley"}:
            issues.append(_issue("invalid_feature", "error", "feature_kind 必须是 peak 或 valley。"))
        elif feature_wavelength is not None:
            arr = curves[str(focus).upper()]
            idx = int(np.argmax(arr) if kind == "peak" else np.argmin(arr))
            grid_step = float(np.median(np.diff(wl))) if wl.size > 1 else 0.0
            if abs(float(feature_wavelength) - float(wl[idx])) > max(grid_step * 0.51, 1e-9):
                issues.append(_issue("feature_mismatch", "error", f"声明特征波长与 {focus} 的实际{('峰' if kind == 'peak' else '谷')}不一致。"))
    metrics = {
        "num_points": int(wl.size),
        "wavelength_min": float(np.nanmin(wl)),
        "wavelength_max": float(np.nanmax(wl)),
        "max_energy_conservation_error": max_conservation_error,
    }
    return _result("rta", issues, metrics)


def audit_external_comparison(
    theory: Sequence[float],
    reference: Sequence[float],
    *,
    reference_label: str,
    reference_file: str | Path | None,
    residual: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Audit external-reference provenance and residual definition."""
    theory_arr, reference_arr = _array(theory), _array(reference)
    issues: list[dict[str, str]] = []
    if theory_arr.size == 0 or theory_arr.size != reference_arr.size:
        issues.append(_issue("comparison_shape", "error", "理论与参考数组长度不一致或为空。"))
    source_path = None if reference_file is None else Path(reference_file).expanduser()
    label_key = str(reference_label).lower()
    claims_external = any(term in label_key for term in ("comsol", "external", "外部", "实验", "测量"))
    if source_path is None or not source_path.is_file():
        severity = "error" if claims_external else "warning"
        issues.append(_issue("missing_reference_source", severity, "外部验证缺少可追溯的原始数据文件。"))
    if residual is not None and theory_arr.size == reference_arr.size:
        residual_arr = _array(residual)
        if residual_arr.size != theory_arr.size or not np.allclose(residual_arr, theory_arr - reference_arr, atol=1e-10, rtol=1e-8):
            issues.append(_issue("residual_definition", "error", "残差必须明确等于 theory - reference。"))
    metrics: dict[str, Any] = {}
    if theory_arr.size and theory_arr.size == reference_arr.size:
        diff = theory_arr - reference_arr
        metrics.update({"mae": float(np.mean(np.abs(diff))), "rmse": float(np.sqrt(np.mean(diff ** 2)))})
    if source_path is not None and source_path.is_file():
        metrics.update({"reference_file": str(source_path.resolve()), "reference_sha256": _sha256(source_path)})
    return _result("external_comparison", issues, metrics)


def audit_missing_values(values: Sequence[float | None], *, zero_is_valid: bool = True) -> dict[str, Any]:
    """Report missing values so renderers do not silently convert them to zero."""
    missing = sum(value is None or (isinstance(value, float) and not np.isfinite(value)) for value in values)
    issues = []
    if missing:
        issues.append(_issue("missing_values", "warning", f"存在 {missing} 个缺失结果；图中必须用 NA/叉号表示，不能替换成零。"))
    return _result("missing_values", issues, {"missing_count": int(missing), "zero_is_valid": bool(zero_is_valid)})


def audit_source_files(paths: Sequence[str | Path], *, required: bool = True) -> dict[str, Any]:
    """Verify provenance files and record immutable hashes."""
    issues: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    for value in paths:
        path = Path(value).expanduser()
        if not path.is_file():
            issues.append(_issue("missing_source_file", "error" if required else "warning", f"源文件不存在：{path}"))
            continue
        records.append({"path": str(path.resolve()), "size_bytes": path.stat().st_size, "sha256": _sha256(path)})
    if required and not paths:
        issues.append(_issue("empty_source_list", "error", "该证据等级要求至少一个可追溯源文件。"))
    return _result("source_files", issues, {"files": records})


def build_figure_audit(
    *,
    figure_id: str,
    title: str,
    evidence_level: str,
    checks: Sequence[Mapping[str, Any]],
    source_files: Sequence[str | Path] = (),
) -> dict[str, Any]:
    """Combine checks into one serializable audit record."""
    issues = [dict(issue) for check in checks for issue in check.get("issues", [])]
    if evidence_level not in EVIDENCE_LEVELS:
        issues.append(_issue("evidence_level", "error", f"未知证据等级 {evidence_level!r}。"))
    elif evidence_level == "placeholder":
        issues.append(_issue("placeholder_evidence", "warning", "占位演示只能用于界面或流程说明，不能作为物理验证证据。"))
    severity_rank = {"info": 0, "warning": 1, "error": 2}
    worst = max((severity_rank.get(str(item.get("severity")), 2) for item in issues), default=0)
    status = "fail" if worst >= 2 else "warn" if worst == 1 else "pass"
    return {
        "schema_version": 1,
        "figure_id": str(figure_id),
        "title": str(title),
        "evidence_level": str(evidence_level),
        "evidence_label_cn": EVIDENCE_LEVELS.get(evidence_level, "未知"),
        "status": status,
        "issues": issues,
        "checks": [dict(check) for check in checks],
        "source_files": [str(Path(path)) for path in source_files],
    }


def write_figure_audit(path: str | Path, audit: Mapping[str, Any]) -> str:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(audit), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output)


def publication_scope(audit: Mapping[str, Any]) -> str:
    """Classify whether an audited figure may enter the report body."""
    if audit.get("status") == "fail":
        return "excluded"
    level = str(audit.get("evidence_level", ""))
    if level == "placeholder":
        return "excluded"
    if level == "approximation":
        return "appendix"
    return "main_text"


def collect_figure_audits(paths: Sequence[str | Path]) -> dict[str, Any]:
    """Collect audit JSON files into one delivery-gate manifest."""
    files: list[Path] = []
    for value in paths:
        path = Path(value).expanduser()
        if path.is_dir():
            files.extend(sorted(path.rglob("*_figure_audit.json")))
        elif path.is_file():
            files.append(path)
    records: list[dict[str, Any]] = []
    malformed: list[dict[str, str]] = []
    for path in dict.fromkeys(files):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "status" not in data or "figure_id" not in data:
                raise ValueError("missing figure_id/status")
            records.append({**data, "audit_file": str(path.resolve()), "publication_scope": publication_scope(data)})
        except Exception as exc:
            malformed.append({"path": str(path), "error": str(exc)})
    counts = {
        "total": len(records),
        "pass": sum(row.get("status") == "pass" for row in records),
        "warn": sum(row.get("status") == "warn" for row in records),
        "fail": sum(row.get("status") == "fail" for row in records),
        "main_text": sum(row["publication_scope"] == "main_text" for row in records),
        "appendix": sum(row["publication_scope"] == "appendix" for row in records),
        "excluded": sum(row["publication_scope"] == "excluded" for row in records),
        "malformed": len(malformed),
    }
    return {
        "schema_version": 1,
        "gate_status": "fail" if counts["fail"] or counts["malformed"] else "warn" if counts["warn"] else "pass",
        "counts": counts,
        "records": records,
        "malformed": malformed,
    }


def write_audit_manifest(output_dir: str | Path, manifest: Mapping[str, Any]) -> dict[str, str]:
    """Write machine-readable, tabular, and report-ready audit summaries."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "figure_audit_manifest.json"
    csv_path = output / "figure_audit_manifest.csv"
    md_path = output / "figure_audit_manifest.md"
    json_path.write_text(json.dumps(dict(manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    records = list(manifest.get("records", []))
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["figure_id", "title", "evidence_level", "status", "publication_scope", "audit_file"])
        writer.writeheader()
        for row in records:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
    counts = dict(manifest.get("counts", {}))
    lines = [
        "# 图表证据审计清单",
        "",
        f"交付门禁：**{manifest.get('gate_status', 'unknown')}**",
        "",
        f"总计 {counts.get('total', 0)}；正文可用 {counts.get('main_text', 0)}；仅附录 {counts.get('appendix', 0)}；排除 {counts.get('excluded', 0)}。",
        "",
        "| 图号/ID | 证据等级 | 审计状态 | 文档范围 |",
        "|---|---|---|---|",
    ]
    for row in records:
        lines.append(f"| {row.get('figure_id', '')} | {row.get('evidence_label_cn', row.get('evidence_level', ''))} | {row.get('status', '')} | {row.get('publication_scope', '')} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path)}


def _result(name: str, issues: Sequence[Mapping[str, str]], metrics: Mapping[str, Any]) -> dict[str, Any]:
    return {"check": name, "passed": not any(item.get("severity") == "error" for item in issues), "issues": list(issues), "metrics": dict(metrics)}
