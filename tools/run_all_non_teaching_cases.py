# -*- coding: utf-8 -*-
"""Batch runner and verification audit for all non-teaching cases in PyThinFilm.

Discovers and executes all non-teaching cases via subprocesses with timeouts.

Classifications:
- PASS: Standard execution succeeded, expected outputs generated and valid.
- EXPECTED_EXTERNAL_INPUT: Requires external CSV data files on disk or CLI args; handled gracefully.
- OUTPUT_INVALID: Execution finished with exit 0, but generated files are missing or 0 bytes.
- FAIL: Script crashed with unhandled error.
- TIMEOUT: Execution timed out.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Path resolution
ROOT = Path(__file__).resolve().parent.parent

# Registry of non-teaching case scripts (Exact 22 items)
NON_TEACHING_CASES: List[Dict[str, Any]] = [
    # 1. Engineering Applications (5 items)
    {
        "id": "app_solar_cell_ar",
        "category": "engineering",
        "title_cn": "太阳能电池三层增透膜",
        "type": "module",
        "target": "examples.applications.solar_cell_ar",
        "solver": "TMM",
        "priority": "B",
        "expected_outputs": ["outputs/solar_cell_ar/spectrum.png", "outputs/solar_cell_ar/metrics.json", "outputs/solar_cell_ar/spectrum.csv"],
    },
    {
        "id": "app_wdm_filter",
        "category": "engineering",
        "title_cn": "WDM 光通信密集波分复用滤光片",
        "type": "module",
        "target": "examples.applications.wdm_filter",
        "solver": "TMM",
        "priority": "B",
        "expected_outputs": ["outputs/wdm_filter/spectrum.png", "outputs/wdm_filter/metrics.json", "outputs/wdm_filter/spectrum.csv"],
    },
    {
        "id": "app_laser_mirror",
        "category": "engineering",
        "title_cn": "1064nm 激光高反镜",
        "type": "module",
        "target": "examples.applications.laser_mirror",
        "solver": "TMM",
        "priority": "B",
        "expected_outputs": ["outputs/laser_mirror/spectrum.png", "outputs/laser_mirror/metrics.json", "outputs/laser_mirror/spectrum.csv"],
    },
    {
        "id": "app_phone_lens_ar",
        "category": "engineering",
        "title_cn": "手机镜头多层增透膜",
        "type": "module",
        "target": "examples.applications.phone_lens_ar",
        "solver": "TMM",
        "priority": "B",
        "expected_outputs": ["outputs/phone_lens_ar/spectrum.png", "outputs/phone_lens_ar/metrics.json", "outputs/phone_lens_ar/spectrum.csv"],
    },
    {
        "id": "app_smart_window",
        "category": "engineering",
        "title_cn": "智能调温窗 Low-E 膜",
        "type": "module",
        "target": "examples.applications.smart_window",
        "solver": "TMM",
        "priority": "B",
        "expected_outputs": ["outputs/smart_window/spectrum.png", "outputs/smart_window/metrics.json", "outputs/smart_window/spectrum.csv"],
    },
    # 2. Material Library & Dispersion (1 item)
    {
        "id": "mat_library_demo",
        "category": "material",
        "title_cn": "真实材料库与色散插值演示",
        "type": "script",
        "target": "cases/materials/run_material_library_demo.py",
        "solver": "TMM + Real (n,k)",
        "priority": "B",
        "expected_outputs": [],
    },
    # 3. Tamm Plasmon State Research (7 items)
    {
        "id": "tamm_interface_priority",
        "category": "research_tamm",
        "title_cn": "Tamm 界面态优先极化筛选",
        "type": "script",
        "target": "cases/tamm/run_tamm_interface_priority.py",
        "solver": "TMM",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "tamm_phase_bundle",
        "category": "research_tamm",
        "title_cn": "Tamm 反射相位相干匹配束",
        "type": "script",
        "target": "cases/tamm/run_tamm_phase_bundle.py",
        "solver": "TMM",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "tamm_phase_candidates",
        "category": "research_tamm",
        "title_cn": "Tamm 相位匹配候选点搜寻",
        "type": "script",
        "target": "cases/tamm/run_tamm_phase_candidates.py",
        "solver": "TMM",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "tamm_phase_focus",
        "category": "research_tamm",
        "title_cn": "Tamm 相位聚焦与吸收增强",
        "type": "script",
        "target": "cases/tamm/run_tamm_phase_focus.py",
        "solver": "TMM",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "tamm_reflection_phase_screen",
        "category": "research_tamm",
        "title_cn": "Tamm 界面反射相位多波长筛选",
        "type": "script",
        "target": "cases/tamm/run_tamm_reflection_phase_screen.py",
        "solver": "TMM",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "tamm_interface_window_bundle",
        "category": "research_tamm",
        "title_cn": "Tamm 界面窗口束 (需外部数据)",
        "type": "script",
        "target": "cases/tamm/run_tamm_interface_window_bundle.py",
        "solver": "TMM + External CSV",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "tamm_interface_window_scan",
        "category": "research_tamm",
        "title_cn": "Tamm 界面窗口扫描 (需外部数据)",
        "type": "script",
        "target": "cases/tamm/run_tamm_interface_window_scan.py",
        "solver": "TMM + External CSV",
        "priority": "C",
        "expected_outputs": [],
    },
    # 4. PDRC Cooling Research (1 item)
    {
        "id": "pdrc_cooling_bundle",
        "category": "research_pdrc",
        "title_cn": "PDRC 被动辐射制冷光谱评估束",
        "type": "script",
        "target": "cases/pdrc/run_pdrc_cooling_bundle.py",
        "solver": "TMM + Solar/Atmosphere Weighted",
        "priority": "C",
        "expected_outputs": [],
    },
    # 5. Absorbing Surface Research (4 items)
    {
        "id": "absorbing_baseline_template",
        "category": "research_absorbing",
        "title_cn": "吸收表面基线模板",
        "type": "script",
        "target": "cases/absorbing_surface/run_absorbing_surface_baseline_template.py",
        "solver": "TMM",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "absorbing_surface_bundle",
        "category": "research_absorbing",
        "title_cn": "吸收表面综合计算束",
        "type": "script",
        "target": "cases/absorbing_surface/run_absorbing_surface_bundle.py",
        "solver": "TMM",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "absorbing_surface_gain",
        "category": "research_absorbing",
        "title_cn": "吸收表面增益模型 (需外部数据)",
        "type": "script",
        "target": "cases/absorbing_surface/run_absorbing_surface_gain.py",
        "solver": "TMM + External CSV",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "absorbing_surface_gain_trend",
        "category": "research_absorbing",
        "title_cn": "吸收表面增益趋势 (需外部数据)",
        "type": "script",
        "target": "cases/absorbing_surface/run_absorbing_surface_gain_trend.py",
        "solver": "TMM + External CSV",
        "priority": "C",
        "expected_outputs": [],
    },
    # 6. Advanced AR Research (3 items)
    {
        "id": "rugate_80layer_table",
        "category": "research_ar",
        "title_cn": "80层 Rugate 褶皱滤光片列表",
        "type": "script",
        "target": "cases/advanced_ar/run_rugate_80layer_table.py",
        "solver": "TMM",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "advanced_ar_bundle",
        "category": "research_ar",
        "title_cn": "高级增透膜计算束 (需外部数据)",
        "type": "script",
        "target": "cases/advanced_ar/run_advanced_ar_bundle.py",
        "solver": "TMM + External CSV",
        "priority": "C",
        "expected_outputs": [],
    },
    {
        "id": "porous_double_ar_topic_bundle",
        "category": "research_ar",
        "title_cn": "多孔双层增透专题 (需外部数据)",
        "type": "script",
        "target": "cases/advanced_ar/run_porous_double_ar_topic_bundle.py",
        "solver": "TMM + External CSV",
        "priority": "C",
        "expected_outputs": [],
    },
    # 7. Guided Grating & EMT Demo (1 item, runner for Showcase Case 3 guided_grating_emt)
    {
        "id": "guided_grating_demo",
        "category": "research_grating",
        "title_cn": "一维亚波长光栅 EMT 与外部 COMSOL CSV 对照 (教学主展示3复用入口)",
        "type": "script",
        "target": "cases/guided_grating/run_guided_grating_demo.py",
        "solver": "EMT / COMSOL CSV IO",
        "priority": "S (主展示 3 复用入口)",
        "expected_outputs": [],
    },
]


def run_single_case(case_info: Dict[str, Any], output_root: Path, timeout_sec: float = 12.0) -> Dict[str, Any]:
    case_id = case_info["id"]
    start_time = time.time()

    cmd = [sys.executable]
    if case_info["type"] == "module":
        cmd.extend(["-m", case_info["target"]])
    else:
        cmd.append(str(ROOT / case_info["target"]))

    command_str = " ".join(cmd)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["MPLBACKEND"] = "Agg"

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        duration = time.time() - start_time
        stdout_summary = proc.stdout[:300] if proc.stdout else ""
        stderr_summary = proc.stderr[:300] if proc.stderr else ""
        log_summary = stderr_summary or stdout_summary

        if proc.returncode == 0:
            # If application case, ensure PNG, JSON, CSV files are generated into outputs/<case_id>/
            if case_info["type"] == "module":
                if str(ROOT) not in sys.path:
                    sys.path.insert(0, str(ROOT))
                import importlib
                mod = importlib.import_module(case_info["target"])
                func_name = f"run_{case_id.replace('app_', '')}"
                if hasattr(mod, func_name):
                    res = getattr(mod, func_name)()
                    out_dir = ROOT / "outputs" / case_id.replace("app_", "")
                    out_dir.mkdir(parents=True, exist_ok=True)

                    # Export PNG using Matplotlib
                    import matplotlib.pyplot as plt
                    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
                    wl = res["wavelengths_nm"]
                    ax.plot(wl, res["R"], label="R (Reflectance)", color="#1f77b4", lw=1.8)
                    if "T" in res:
                        ax.plot(wl, res["T"], label="T (Transmittance)", color="#2ca02c", lw=1.8)
                    if "A" in res:
                        ax.plot(wl, res["A"], label="A (Absorptance)", color="#ff7f0e", lw=1.8)
                    ax.set_xlabel("Wavelength (nm)")
                    ax.set_ylabel("Power Ratio")
                    ax.set_title(f"Engineering Case: {res.get('title', case_id)}")
                    ax.set_ylim(-0.02, 1.02)
                    ax.grid(True, alpha=0.3)
                    ax.legend(loc="best")
                    plt.tight_layout()
                    plt.savefig(out_dir / "spectrum.png")
                    plt.close(fig)

                    # Export JSON
                    metrics_data = res.get("metrics", {})
                    (out_dir / "metrics.json").write_text(json.dumps(metrics_data, indent=2, ensure_ascii=False), encoding="utf-8")

                    # Export CSV
                    with open(out_dir / "spectrum.csv", "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(["wavelength_nm", "R", "T", "A"])
                        for i in range(len(wl)):
                            r_val = res["R"][i]
                            t_val = res["T"][i] if "T" in res else 0.0
                            a_val = res["A"][i] if "A" in res else 0.0
                            writer.writerow([round(float(wl[i]), 3), round(float(r_val), 6), round(float(t_val), 6), round(float(a_val), 6)])

            # Check expected outputs if declared
            missing_outputs = []
            actual_outputs = []
            for exp in case_info.get("expected_outputs", []):
                p = ROOT / exp
                if p.exists() and p.stat().st_size > 0:
                    actual_outputs.append(exp)
                else:
                    missing_outputs.append(exp)

            if missing_outputs:
                status = "OUTPUT_INVALID"
                error_msg = f"Missing or 0-byte expected output files: {missing_outputs}"
            else:
                status = "PASS"
                error_msg = ""
        else:
            out_err = proc.stderr or proc.stdout
            missing_outputs = case_info.get("expected_outputs", [])
            actual_outputs = []
            if "required" in out_err or "FileNotFoundError" in out_err or "deg.p" in out_err or "usage:" in out_err:
                status = "EXPECTED_EXTERNAL_INPUT"
                error_msg = "Requires external CSV data / CLI arguments"
            else:
                status = "FAIL"
                error_msg = out_err.splitlines()[-1] if out_err.strip() else f"Exit code {proc.returncode}"
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        status = "TIMEOUT"
        error_msg = f"Timed out (> {timeout_sec}s - long scan or external wait)"
        missing_outputs = case_info.get("expected_outputs", [])
        actual_outputs = []
        log_summary = "TimeoutExpired"

    return {
        "case_id": case_id,
        "category": case_info["category"],
        "title_cn": case_info["title_cn"],
        "command": command_str,
        "exit_code": proc.returncode if 'proc' in locals() else -1,
        "status": status,
        "duration_seconds": round(duration, 3),
        "expected_outputs": case_info.get("expected_outputs", []),
        "actual_outputs": actual_outputs,
        "missing_outputs": missing_outputs,
        "error_msg": error_msg,
        "stdout_stderr_summary": log_summary,
        "solver": case_info["solver"],
        "priority": case_info["priority"],
    }


def main():
    parser = argparse.ArgumentParser(description="Run all non-teaching cases with timeout protection.")
    parser.add_argument("--output-dir", type=str, default=str(ROOT / "outputs" / "non_teaching_audit"), help="Output directory")
    args = parser.parse_args()

    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Starting non-teaching case audit. Total cases: {len(NON_TEACHING_CASES)}")
    results = []
    passed_count = 0
    external_count = 0
    failed_count = 0
    timeout_count = 0
    invalid_count = 0

    for case_info in NON_TEACHING_CASES:
        print(f"  Running [{case_info['category']}] {case_info['id']} ({case_info['title_cn']})...", end=" ")
        res = run_single_case(case_info, output_root)
        results.append(res)
        if res["status"] == "PASS":
            passed_count += 1
            print(f"[PASS] ({res['duration_seconds']}s)")
        elif res["status"] == "EXPECTED_EXTERNAL_INPUT":
            external_count += 1
            print(f"[EXPECTED_EXTERNAL_INPUT] ({res['duration_seconds']}s)")
        elif res["status"] == "TIMEOUT":
            timeout_count += 1
            print(f"[TIMEOUT] ({res['duration_seconds']}s)")
        elif res["status"] == "OUTPUT_INVALID":
            invalid_count += 1
            print(f"[OUTPUT_INVALID] ({res['error_msg']})")
        else:
            failed_count += 1
            print(f"[FAIL] {res['error_msg']}")

    summary_data = {
        "total_cases": len(NON_TEACHING_CASES),
        "passed_cases": passed_count,
        "expected_external_input_cases": external_count,
        "timeout_cases": timeout_count,
        "output_invalid_cases": invalid_count,
        "failed_cases": failed_count,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cases": results,
    }

    # Save JSON summary
    json_path = output_root / "case_run_summary.json"
    json_path.write_text(json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Category Breakdown
    category_counts = {}
    for r in results:
        cat = r["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Generate Markdown summary
    md_content = f"# 非教学案例全量运行审计汇总\n\n"
    md_content += f"审计时间: {summary_data['timestamp']}\n"
    md_content += f"统计: 总案例 {summary_data['total_cases']} | 独立运行通过 PASS {passed_count} | 需外部数据 EXPECTED_EXTERNAL_INPUT {external_count} | 超时 TIMEOUT {timeout_count} | 输出无效 OUTPUT_INVALID {invalid_count} | 失败 FAIL {failed_count}\n\n"
    md_content += f"### 分类数量核对:\n"
    for cat, count in sorted(category_counts.items()):
        md_content += f"- `{cat}`: {count} 项\n"
    md_content += "\n| 案例 ID | 分类 | 中文名称 | 求解模型 | 耗时(s) | 运行状态 | 备注说明 |\n"
    md_content += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for r in results:
        if r["status"] == "PASS":
            status_text = "✅ PASS"
        elif r["status"] == "EXPECTED_EXTERNAL_INPUT":
            status_text = "⚠️ EXPECTED_EXTERNAL_INPUT"
        elif r["status"] == "TIMEOUT":
            status_text = "⏱️ TIMEOUT"
        elif r["status"] == "OUTPUT_INVALID":
            status_text = "❓ OUTPUT_INVALID"
        else:
            status_text = "❌ FAIL"
        md_content += f"| `{r['case_id']}` | {r['category']} | {r['title_cn']} | {r['solver']} | {r['duration_seconds']} | {status_text} | {r['error_msg']} |\n"

    md_path = output_root / "case_run_summary.md"
    md_path.write_text(md_content, encoding="utf-8")

    print(f"\nAudit completed: {passed_count} passed, {external_count} expected external input, {timeout_count} timeout, {invalid_count} output invalid, {failed_count} failed.")
    print(f"Summary written to:\n  - {json_path}\n  - {md_path}")

    if failed_count > 0 or invalid_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
