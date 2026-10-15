"""Build one provenance-labeled video per catalog case without inventing physics."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "Frontend" / "V3" / "backend"
for folder in (str(ROOT), str(BACKEND)):
    if folder not in sys.path:
        sys.path.insert(0, folder)

from app.main import (  # noqa: E402
    APP_ROOT, GeneralTmmSweepRequest, RcwaSweepRequest, get_case_library,
    get_case_library_detail, run_generaltmm_sweep, run_rcwa_sweep,
)
from app.tmmcore_service import simulate_teaching_case_with_tmmcore  # noqa: E402
from thinfilm.api import simulate_teaching_case  # noqa: E402
from tools.video.render_simulation_clips import BG, CORAL, FONT, GOLD, INK, MUTED, TEAL, style_plot  # noqa: E402

FPS = 15
FRAMES = 90
CATEGORY = {
    "teaching_thinfilm": "薄膜物理教学",
    "teaching_emt": "光栅虚拟实验",
    "engineering_applications": "工程应用（归档）",
    "research_extension": "研究拓展",
}
FP_CASES = {"fp_single_halfwave", "fp_filter", "fp_double_halfwave", "narrowband_filter", "app_wdm_filter"}
ABS_CASES = {"pdrc_cooling_bundle", "tamm_phase_focus", "tamm_phase_candidates", "absorbing_surface_bundle", "absorbing_baseline_template"}
COMPARE_CASES = {"neutral_beamsplitter", "absorbing_surface_gain", "porous_double_ar_topic_bundle"}
PUBLIC_SPECIALISTS = {"guided_grating_emt", "tamm_interface_priority", "tamm_phase_bundle", "tamm_phase_focus"}
EVIDENCE_LABELS = {
    "READY_EXTERNAL": "外部证据已保存",
    "READY_EXTERNAL_BOUND": "已绑定外部基线",
    "READY_EXTERNAL_WITH_LIMITS": "外部证据（有限制）",
    "DEGRADED_PARTIAL_INPUT": "输入不完整（归档）",
    "SAVED_RESULT": "保存的计算结果",
}


def clean_label(label: str, *, fallback: str) -> str:
    return fallback if "\ufffd" in label or not label.strip() else label


def select_saved_traces(case_id: str, detail: dict) -> list[dict]:
    traces = detail["series"]
    preferred = "T" if case_id in FP_CASES else "A" if case_id in ABS_CASES else "R"
    matching = [row for row in traces if row["label"] in (f"TE {preferred}", preferred)]
    selected = matching[:1] or traces[:1]
    if case_id == "neutral_beamsplitter":
        selected = [row for row in traces if row["label"] in ("TE R", "TE T")][:2]
    elif case_id in COMPARE_CASES - {"neutral_beamsplitter"}:
        selected = traces[:2]
    return selected


def current_specialist(case_id: str) -> tuple[list[dict], str, dict]:
    if case_id == "guided_grating_emt":
        params = {"wavelength_start_um": 1.45, "wavelength_stop_um": 1.65,
                  "wavelength_points": 41, "harmonics": 3}
        result = run_rcwa_sweep(RcwaSweepRequest(**params))
        return [{"label": "RCWA R", "x": np.asarray(result["wavelength_um"]) * 1000,
                 "y": result["R"], "x_label": "波长", "x_unit": "nm"}], "RCWA 本次计算", params

    params = {"case_id": case_id, "wavelength_start_nm": 500,
              "wavelength_stop_nm": 750, "wavelength_points": 101}
    if case_id == "tamm_interface_priority":
        params["beta"] = 0.3
    result = run_generaltmm_sweep(GeneralTmmSweepRequest(**params))
    if case_id == "tamm_phase_bundle":
        channels = (("p 相位", "phase_p_deg"), ("s 相位", "phase_s_deg"))
        quantity = "反射相位 (°)"
    elif case_id == "tamm_phase_focus":
        channels = (("p 吸收", "A"),)
        quantity = "吸收率 A"
    else:
        channels = (("p 反射", "R"), ("s 反射", "R_s"))
        quantity = "反射率 R"
    return ([{"label": label, "x": result["wavelength_nm"], "y": result[key],
              "x_label": "波长", "x_unit": "nm", "quantity": quantity} for label, key in channels],
            "GeneralTmm 本次计算", params)


def case_data(case: dict, detail: dict, is_public: bool) -> tuple[list[dict], str, dict]:
    case_id = case["case_id"]
    if case.get("has_live_simulation") and is_public:
        if case_id == "fp_single_halfwave":
            result = simulate_teaching_case(case_id)
            source = "PyThinFilm 本次基线计算"
        else:
            result = simulate_teaching_case_with_tmmcore(case_id, {}, APP_ROOT)
            source = "tmmcore 本次基线计算"
        quantities = ("R", "T") if case_id == "neutral_beamsplitter" else ("T",) if case_id in FP_CASES else ("R",)
        return ([{"label": quantity, "x": result["wavelength_nm"], "y": result[quantity],
                  "x_label": "波长", "x_unit": "nm"} for quantity in quantities], source, {"default_parameters": True})
    if is_public and case_id in PUBLIC_SPECIALISTS:
        return current_specialist(case_id)
    status = detail.get("evidence_status") or "SAVED_RESULT"
    return select_saved_traces(case_id, detail), f"结果回放 · {EVIDENCE_LABELS.get(status, status)}", {"data_kind": detail["data_kind"]}


def prepare(traces: list[dict]) -> tuple[list[dict], str, str, bool, bool]:
    prepared = []
    for trace in traces:
        x = np.asarray(trace["x"], dtype=float)
        y = np.asarray(trace["y"], dtype=float)
        if x.size < 2 or x.shape != y.shape or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
            raise ValueError(f"Invalid numeric series: {trace.get('label')}")
        prepared.append({**trace, "x": x, "y": y})
    reference = prepared[0]
    same_x = all(np.array_equal(row["x"], reference["x"]) for row in prepared)
    if not same_x:
        prepared = prepared[:1]
    x = prepared[0]["x"]
    constant_x = bool(np.isclose(np.max(x), np.min(x)))
    discrete = constant_x or len(x) <= 10 or bool(np.any(np.diff(x) < 0))
    unit = reference.get("x_unit", "")
    is_wavelength = unit == "nm" or ("波长" in reference.get("x_label", "") and not constant_x)
    if is_wavelength and np.max(x) > 5000:
        for row in prepared:
            row["x"] = row["x"] / 1000
        x_label = "波长 (µm)"
    elif is_wavelength:
        x_label = "波长 (nm)" if unit == "nm" else clean_label(str(reference.get("x_label", "")), fallback="波长")
    else:
        x_label = clean_label(str(reference.get("x_label", "")), fallback="参数 / 序号")
    label = str(reference.get("quantity") or reference["label"])
    if label in ("R", "TE R", "RCWA R"):
        y_label = "反射率 R"
    elif label in ("T", "TE T"):
        y_label = "透射率 T"
    elif label in ("A", "TE A"):
        y_label = "吸收率 A"
    else:
        y_label = clean_label(label, fallback="数值")
    if len(prepared) > 1:
        names = [str(row["label"]) for row in prepared]
        if set(names) == {"R", "T"}:
            y_label = "反射率 R / 透射率 T"
        elif all(name.endswith(" R") for name in names):
            y_label = "反射率 R"
        elif all(name.endswith(" A") for name in names):
            y_label = "吸收率 A"
    return prepared, x_label, y_label, discrete, constant_x


def render_case(path: Path, case: dict, detail: dict, traces: list[dict], source: str, is_public: bool,
                ffmpeg: str) -> dict:
    traces, x_label, y_label, discrete, constant_x = prepare(traces)
    x = traces[0]["x"]
    y_values = np.concatenate([trace["y"] for trace in traces])
    y_min, y_max = float(np.min(y_values)), float(np.max(y_values))
    range_y = y_max - y_min
    axis_min = min(0.0, y_min - 0.12 * range_y) if y_min >= 0 and y_max <= 1 else y_min - max(0.12 * range_y, abs(y_min) * 0.05, 1e-6)
    axis_max = y_max + max(0.15 * range_y, abs(y_max) * 0.05, 1e-6)
    if y_min >= 0 and y_max <= 1 and y_max > 0.8:
        axis_max = max(axis_max, 1.02)
    if constant_x:
        axis_min, axis_max = 0, 1

    plt.rcParams.update({"font.family": FONT, "font.size": 12, "axes.edgecolor": "#b5c3c8",
                         "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                         "text.color": INK, "axes.unicode_minus": False})
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BG)
    public_label = "公开教学案例" if is_public else "归档案例 / 不在 App 默认列表"
    fig.text(0.055, 0.928, f"{case['order']:02d}  {CATEGORY[case['category']]}   ·   {public_label}", fontsize=11, color=TEAL)
    title = case["title_cn"]
    fig.text(0.055, 0.85, title, fontsize=21 if len(title) <= 20 else 17, weight="bold", color=INK)
    fig.text(0.055, 0.795, case["case_id"], fontsize=10, color=MUTED)

    goal = str(case.get("learning_goal") or "观察该案例的数值结果")
    function = str(case.get("coating_function") or "")
    fig.text(0.055, 0.70, "物理问题", fontsize=11, color=MUTED)
    fig.text(0.055, 0.65, goal[:20] + ("…" if len(goal) > 20 else ""), fontsize=13, color=INK)
    fig.text(0.055, 0.54, "膜系功能", fontsize=11, color=MUTED)
    fig.text(0.055, 0.49, function[:20] + ("…" if len(function) > 20 else ""), fontsize=13, color=INK)
    fig.text(0.055, 0.34, "数据来源", fontsize=11, color=MUTED)
    fig.text(0.055, 0.29, source, fontsize=11, color=CORAL if not is_public else TEAL)
    if not is_public:
        fig.text(0.055, 0.22, "仅回放保存数据；不代表本次重新求解。", fontsize=9, color=MUTED)
    elif case["case_id"].startswith("tamm_"):
        fig.text(0.055, 0.22, "当前平面 Ag/DBR 教学模型，非历史 COMSOL 复现。", fontsize=9, color=MUTED)
    elif case["case_id"] == "guided_grating_emt":
        fig.text(0.055, 0.22, "当前参数未显示尖锐共振；不推断导模耦合。", fontsize=9, color=MUTED)
    fig.text(0.055, 0.055, "PyThinFilm  ·  案例数值资料 / 标注来源与模型边界", fontsize=9, color=MUTED)

    plot = fig.add_axes((0.40, 0.24, 0.55, 0.49))
    if constant_x:
        plot.axis("off")
        plot.text(0.04, 0.93, "固定横坐标的离散记录", fontsize=16, color=INK, transform=plot.transAxes)
        plot.text(0.04, 0.82, "不能由这些点推断参数趋势或连续光谱。", fontsize=11, color=MUTED, transform=plot.transAxes)
        columns = detail.get("table", {}).get("columns", [])
        rows = detail.get("table", {}).get("rows", [])
        values = []
        if columns and rows and "source" in columns:
            source_at = columns.index("source")
            numeric = [name for name in ("lambda_um", "G_if", "eta_if") if name in columns]
            for row in rows:
                if len(row) <= source_at:
                    continue
                metrics = "   ".join(f"{name}={float(row[columns.index(name)]):.4g}" for name in numeric)
                values.append(f"{row[source_at]}    {metrics}")
        if not values:
            values = [f"{trace['label']}: {float(value):.4g}" for trace in traces for value in trace["y"]]
        texts = [plot.text(0.06, 0.69 - i * 0.085, "", fontsize=11, color=TEAL, transform=plot.transAxes)
                 for i in range(min(len(values), 7))]

        def draw(progress: float) -> None:
            count = min(len(texts), 1 + int(progress * len(texts)))
            for i, artist in enumerate(texts):
                artist.set_text(values[i] if i < count else "")
    else:
        style_plot(plot, x_label, y_label)
        padding_x = max(float(np.ptp(x)) * 0.035, 1e-5)
        plot.set(xlim=(float(np.min(x)) - padding_x, float(np.max(x)) + padding_x), ylim=(axis_min, axis_max))
        artists = []
        colors = (TEAL, GOLD)
        for i, trace in enumerate(traces):
            color = colors[i]
            if discrete:
                artist, = plot.plot([], [], "o", color=color, ms=7, label=clean_label(str(trace["label"]), fallback=y_label))
            else:
                artist, = plot.plot([], [], color=color, lw=2.8, label=clean_label(str(trace["label"]), fallback=y_label))
            artists.append(artist)
        if len(artists) > 1:
            plot.legend(loc="upper right", frameon=False, fontsize=10)

        def draw(progress: float) -> None:
            for trace, artist in zip(traces, artists):
                count = max(1, int(round(progress * (len(trace["x"]) - 1))) + 1)
                shown_x = trace["x"][:count]
                shown_y = trace["y"][:count].copy()
                if not discrete and len(shown_x) > 2:
                    gaps = np.diff(shown_x)
                    positive = gaps[gaps > 0]
                    if positive.size:
                        shown_y[1:][gaps > 10 * np.median(positive)] = np.nan
                artist.set_data(shown_x, shown_y)

    note = "逐项呈现保存数据" if discrete else "沿横坐标逐点揭示数值结果；不是参数随时间演化"
    if case["case_id"] == "tamm_interface_priority" and is_public:
        note = "β = 0.30；p/s 在非零切向波矢下比较"
    fig.text(0.40, 0.13, note, fontsize=11, color=MUTED)
    fig.text(0.40, 0.09, f"{len(x)} 个原始数据点  ·  {x_label}  ·  {y_label}", fontsize=10, color=MUTED)
    canvas = FigureCanvasAgg(fig)
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pixel_format", "rgb24", "-video_size", "1280x720", "-framerate", str(FPS),
               "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        assert process.stdin is not None
        for frame in range(FRAMES):
            draw(frame / (FRAMES - 1))
            canvas.draw()
            process.stdin.write(np.asarray(canvas.buffer_rgba())[:, :, :3].tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError(f"ffmpeg failed: {case['case_id']}")
    except Exception:
        process.kill()
        process.wait()
        raise
    finally:
        plt.close(fig)

    canonical = [{"label": str(row["label"]), "x": row["x"].tolist(), "y": row["y"].tolist()} for row in traces]
    return {"case_id": case["case_id"], "title_cn": case["title_cn"], "public": is_public,
            "category": case["category"], "source": source, "data_kind": detail["data_kind"],
            "evidence_status": detail.get("evidence_status", ""), "stored_result_hash": detail.get("result_hash", ""),
            "displayed_trace_sha256": hashlib.sha256(json.dumps(canonical, ensure_ascii=False).encode()).hexdigest(),
            "traces": [str(row["label"]) for row in traces], "points": len(x),
            "chart_mode": "fixed_parameter_record" if constant_x else "discrete_points" if discrete else "series_reveal"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "video_materials" / "all_cases_v1")
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--case-id", action="append", help="Render selected IDs for QA; omit to render all 40")
    parser.add_argument("--resume", action="store_true", help="Reuse verified outputs listed in the existing manifest")
    parser.add_argument("--refresh-case-id", action="append", help="Recalculate selected IDs while resuming other cases")
    args = parser.parse_args()
    if not args.ffmpeg or not Path(args.ffmpeg).is_file():
        parser.error("Pass --ffmpeg <path-to-full-ffmpeg.exe>")
    catalog = get_case_library(include_archived=True)["cases"]
    if len(catalog) != 40 or len({case["case_id"] for case in catalog}) != 40:
        raise RuntimeError("Expected exactly 40 unique catalog cases")
    public_catalog = {case["case_id"]: case for case in get_case_library()["cases"]}
    if len(public_catalog) != 22:
        raise RuntimeError("Expected exactly 22 public cases")
    wanted = set(args.case_id or [case["case_id"] for case in catalog])
    if wanted - {case["case_id"] for case in catalog}:
        raise ValueError(f"Unknown case IDs: {sorted(wanted - {case['case_id'] for case in catalog})}")
    output = args.output.resolve()
    manifest = []
    manifest_path = output / "case_video_manifest.json"
    refresh = set(args.refresh_case_id or [])
    if refresh and not args.resume:
        parser.error("--refresh-case-id requires --resume")
    if refresh - wanted:
        parser.error("Refresh IDs must belong to the selected case set")
    completed = {}
    if args.resume and manifest_path.is_file():
        completed = {row["case_id"]: row for row in json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]}
    for case in catalog:
        case_id = case["case_id"]
        if case_id not in wanted:
            continue
        if case_id in completed and case_id not in refresh:
            prior = completed[case_id]
            prior_file = output / prior["relative_video"]
            if not prior_file.is_file() or prior_file.stat().st_size < 1000:
                raise RuntimeError(f"Resume file missing/incomplete: {prior_file}")
            manifest.append(prior)
            print(f"Reusing {case_id} ({len(manifest)}/{len(wanted)})", flush=True)
            continue
        is_public = case_id in public_catalog
        if is_public:
            case = {**case, **public_catalog[case_id]}
        detail = get_case_library_detail(case_id)
        traces, source, parameters = case_data(case, detail, is_public)
        path = output / ("public" if is_public else "archive") / f"{case['order']:02d}_{case_id}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Rendering {case_id} ({len(manifest) + 1}/{len(wanted)})", flush=True)
        entry = render_case(path, case, detail, traces, source, is_public, args.ffmpeg)
        manifest.append({**entry, "parameters": parameters, "relative_video": path.relative_to(output).as_posix()})
        manifest_path.write_text(json.dumps({
            "schema_version": "1.0", "fps": FPS, "seconds_per_case": FRAMES / FPS,
            "resolution": [1280, 720], "total": len(manifest), "public": sum(row["public"] for row in manifest),
            "archive": sum(not row["public"] for row in manifest), "cases": manifest,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.case_id:
        concat_list = output / "review_order.txt"
        concat_list.write_text("".join(f"file '{entry['relative_video']}'\n" for entry in manifest), encoding="utf-8")
        subprocess.run([args.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy",
                        str(output / "40_cases_review_240s.mp4")], check=True)
    print(f"Completed {len(manifest)} case videos in {output}", flush=True)


if __name__ == "__main__":
    main()
