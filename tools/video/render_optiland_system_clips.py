"""Render three Optiland system comparisons from actual ray-trace outputs."""

from __future__ import annotations

import argparse
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.optiland_ar_comparison import _trace_snapshot  # noqa: E402
from experiments.optiland_engineering_nsq import trace_branches, trace_matched_ghost  # noqa: E402
from experiments.optiland_poc import _save_3d_png  # noqa: E402
from thinfilm.optiland_integration import (  # noqa: E402
    CoatingLayerInput, CoatingStackInput, OptilandBridge, make_teaching_system_input,
)
from tools.video.render_simulation_clips import BG, CORAL, FONT, GOLD, INK, MUTED, TEAL  # noqa: E402

FPS = 20
FRAMES = 240
NM = 550.0
ANGLE = 45.0
GHOST_RAYS = 10000
BRANCH_RAYS = 4096


def setup(title: str, subtitle: str) -> tuple[plt.Figure, FigureCanvasAgg]:
    plt.rcParams.update({"font.family": FONT, "font.size": 12, "text.color": INK,
                         "axes.edgecolor": "#b4c4c7", "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.unicode_minus": False})
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BG)
    fig.text(0.055, 0.917, title, fontsize=23, weight="bold")
    fig.text(0.055, 0.862, subtitle, fontsize=11, color=MUTED)
    fig.text(0.055, 0.038, "Optiland 教学系统  ·  550 nm  ·  膜系材料来自 PyThinFilm", fontsize=9, color=MUTED)
    return fig, FigureCanvasAgg(fig)


def output_video(path: Path, ffmpeg: str, fig: plt.Figure, canvas: FigureCanvasAgg, draw) -> None:
    process = subprocess.Popen(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
         "-pixel_format", "rgb24", "-video_size", "1280x720", "-framerate", str(FPS),
         "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
        stdin=subprocess.PIPE,
    )
    try:
        assert process.stdin is not None
        for frame in range(FRAMES):
            draw(min(len(draw.states) - 1, int(frame * len(draw.states) / FRAMES)))
            canvas.draw()
            process.stdin.write(np.asarray(canvas.buffer_rgba())[:, :, :3].tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError(f"ffmpeg failed for {path}")
    except Exception:
        process.kill()
        process.wait()
        raise
    finally:
        plt.close(fig)


def make_stack(layers: list[tuple[str, float]]) -> CoatingStackInput:
    return CoatingStackInput("Air", "N-BK7", tuple(CoatingLayerInput(material, thickness) for material, thickness in layers))


def lens_states(bridge: OptilandBridge, output: Path) -> tuple[list[dict], Path, Path]:
    states = []
    geometry_fingerprint = None
    bare = None
    layout_path = output / "single_lens_layout.png"
    layout_3d_path = output / "single_lens_3d.png"
    for thickness in (0, 80, 90, 99.6, 110, 120, 130):
        stack = make_stack([] if thickness == 0 else [("MgF2", thickness)])
        spec = make_teaching_system_input(
            template="single_lens_imaging", name="AR teaching singlet", glass_material_id="N-BK7",
            front_coating=stack, wavelength_um=NM / 1000,
        )
        optic = bridge.build_system(spec)
        optic.updater.image_solve()
        if thickness == 0:
            figure, _ = optic.draw(num_rays=7, show=False, figsize=(8, 4))
            figure.savefig(layout_path, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close(figure)
            _save_3d_png(optic, layout_3d_path)
        trace = _trace_snapshot(optic, bridge.api, NM, (0.0, 0.0))
        geometry = tuple((round(float(surface.radius_mm), 6) if surface.radius_mm is not None else None,
                          surface.material_id, surface.thickness_mm) for surface in spec.surfaces)
        if geometry_fingerprint is None:
            geometry_fingerprint = geometry
        elif geometry != geometry_fingerprint:
            raise RuntimeError("Lens geometry changed during coating-only scan")
        ghost = trace_matched_ghost(bridge, spec, optic, NM, count=GHOST_RAYS)
        row = {"thickness_nm": thickness,
               "exit_weight": float(np.mean(np.asarray(trace["exit_intensity"], dtype=float))),
               "ghost_fraction": float(ghost["ghost_fraction"]),
               "ghost_flux": float(ghost["ghost_flux"]),
               "ghost_flux_standard_error": float(ghost["ghost_flux_standard_error"]),
               "detected_ghost_paths": int(ghost["detected_ghost_paths"]),
               "ray_count": GHOST_RAYS, "seed": 2026,
               "geometry_surface_count": len(ghost["geometry"]["surfaces"])}
        states.append(row)
        if thickness == 0:
            bare = row
    assert bare is not None
    for row in states:
        difference = bare["ghost_flux"] - row["ghost_flux"]
        combined_se = np.hypot(bare["ghost_flux_standard_error"], row["ghost_flux_standard_error"])
        row["ghost_difference_significant_3se"] = bool(difference > 3 * combined_se)
    return states, layout_path, layout_3d_path


def lens_clip(path: Path, ffmpeg: str, states: list[dict], layout_path: Path, layout_3d_path: Path) -> None:
    fig, canvas = setup("01  镜片镀膜：能量到达像面之后", "单透镜几何与焦面保持相同  ·  裸表面 vs MgF2 前表面膜")
    layout = plt.imread(layout_path)
    layout_3d = plt.imread(layout_3d_path)
    ax_layout = fig.add_axes((0.055, 0.39, 0.43, 0.37))
    layout_artist = ax_layout.imshow(layout)
    ax_layout.axis("off")
    layout_caption = fig.text(0.07, 0.345, "Optiland 原生 2D 镜头布局（几何不随镀膜变化）", fontsize=10, color=MUTED)
    ax = fig.add_axes((0.56, 0.39, 0.38, 0.36))
    ax.set(facecolor="white", ylim=(0, 1.02), ylabel="相对出射光线权重")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e2eaed", zorder=0)
    bars = ax.bar(["裸表面", "当前膜厚"], [states[0]["exit_weight"], states[0]["exit_weight"]],
                  color=["#84949a", TEAL], width=.52, zorder=2)
    ax_ghost = fig.add_axes((0.14, 0.13, 0.71, 0.16))
    ax_ghost.set(facecolor="white", xlim=(0, 0.12), ylim=(0, 1), xlabel="匹配几何鬼像接收占比 (%)")
    ax_ghost.spines[["top", "right", "left"]].set_visible(False)
    ax_ghost.set_yticks([])
    ax_ghost.grid(axis="x", color="#e2eaed")
    base_marker, = ax_ghost.plot([states[0]["ghost_fraction"] * 100], [.72], "o", ms=10, color="#84949a", label="裸表面")
    coated_marker, = ax_ghost.plot([states[0]["ghost_fraction"] * 100], [.34], "o", ms=10, color=CORAL, label="当前膜厚")
    ax_ghost.legend(loc="upper right", fontsize=9, frameon=False)
    thickness_text = fig.text(0.07, 0.79, "", fontsize=16, color=TEAL, weight="bold")
    metric_text = fig.text(0.56, 0.315, "", fontsize=11, color=INK)
    fig.text(0.055, 0.076, "鬼像：10,000 射线 / 固定种子 / 同一调焦几何；仅单镜透明玻璃教学基线。", fontsize=9, color=MUTED)

    frame_number = 0

    def draw(index: int) -> None:
        nonlocal frame_number
        row = states[index]
        if frame_number == FRAMES // 2:
            layout_artist.set_data(layout_3d)
            layout_caption.set_text("Optiland 原生 3D 系统视角（同一固定几何）")
        frame_number += 1
        thickness_text.set_text("裸界面" if index == 0 else f"MgF2 厚度  {row['thickness_nm']:.1f} nm")
        bars[1].set_height(row["exit_weight"])
        coated_marker.set_data([row["ghost_fraction"] * 100], [.34])
        result = "鬼像功率差异 > 3 倍合并标准误" if row["ghost_difference_significant_3se"] else "鬼像功率差异不足 3 倍合并标准误"
        metric_text.set_text(f"像面权重  {row['exit_weight']:.4f}   ·   鬼像  {row['ghost_fraction'] * 100:.4f}%\n{result}")

    draw.states = states
    output_video(path, ffmpeg, fig, canvas, draw)


def branch_states(bridge: OptilandBridge, mirror: bool) -> list[dict]:
    samples = list(range(1, 7)) if mirror else [30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130]
    states = []
    direction = None
    for parameter in samples:
        if mirror:
            layers = [(material, thickness) for _ in range(parameter)
                      for material, thickness in (("TiO2", 63.95), ("SiO2", 94.1))]
        else:
            layers = [("MgF2", 99.6), ("TiO2", parameter), ("MgF2", 99.6), ("TiO2", parameter)]
        result = trace_branches(bridge, make_stack(layers), NM, ANGLE, mirror, count=BRANCH_RAYS)
        if result["direction_error"] is None or result["direction_error"] > 1e-8:
            raise RuntimeError("NSQ reflected direction failed geometric check")
        if result["ledger"]["accounted_residual"] > 1e-8:
            raise RuntimeError("NSQ branch power budget did not close")
        if abs(result["reflected_flux"] - result["expected_R"]) > 1e-8:
            raise RuntimeError("Reflected detector power differs from coating R")
        if not mirror and abs(result["transmitted_flux"] - result["expected_T"]) > 1e-8:
            raise RuntimeError("Transmitted detector power differs from coating T")
        current_direction = np.asarray(result["reflection_direction"])
        if direction is None:
            direction = current_direction
        elif not np.allclose(current_direction, direction):
            raise RuntimeError("Branch geometry changed during coating-only scan")
        states.append({"parameter": parameter, "R": result["expected_R"], "T": result["expected_T"],
                       "reflected_flux_w": result["reflected_flux"],
                       "transmitted_flux_w": result["transmitted_flux"],
                       "unreflected_loss_w": 1 - result["expected_R"] if mirror else None,
                       "accounted_residual": result["ledger"]["accounted_residual"],
                       "direction_error": result["direction_error"],
                       "paths": result["paths"] if parameter == samples[0] else [],
                       "ray_count": BRANCH_RAYS, "seed": 2026})
    return states


def branch_clip(path: Path, ffmpeg: str, states: list[dict], *, mirror: bool) -> None:
    title = "02  高反膜：折返路径的接收功率" if mirror else "03  分光膜：两支路的真实功率分配"
    subtitle = "45° 原生 NSQ 不透明单镜  ·  TiO2 / SiO2 周期数扫描" if mirror else "45° 原生 NSQ 零厚度等效分光面  ·  TiO2 层厚扫描"
    fig, canvas = setup(title, subtitle)
    ax = fig.add_axes((0.07, 0.27, 0.48, 0.50))
    ax.set(facecolor="white", xlim=(-13, 23), ylim=(-25, 25), xlabel="Z (mm)", ylabel="X (mm)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(color="#e2eaed")
    ax.plot([0], [0], "s", ms=14, color=INK, label="膜面")
    for path_data in states[0]["paths"]:
        xyz = np.asarray(path_data["xyz"], dtype=float)
        if xyz.shape != (3, 3):
            continue
        color = CORAL if path_data["branch"] == "reflected" else TEAL
        ax.plot(xyz[:, 2], xyz[:, 0], color=color, lw=1.5, alpha=.3)
    ax.text(-11, 4, "入射", fontsize=10, color=MUTED)
    fig.text(0.07, 0.20, "Optiland NSQ 实际追迹路径；光路方向与几何固定。", fontsize=10, color=MUTED)
    ax_bar = fig.add_axes((0.64, 0.35, 0.29, 0.37))
    ax_bar.set(facecolor="white", ylim=(0, 1.05), ylabel="接收功率 (W)，入射 1 W")
    ax_bar.spines[["top", "right"]].set_visible(False)
    ax_bar.grid(axis="y", color="#e2eaed", zorder=0)
    labels = ["反射探测器", "未反射损失"] if mirror else ["反射探测器", "透射探测器"]
    values = [states[0]["R"], 1 - states[0]["R"] if mirror else states[0]["T"]]
    bars = ax_bar.bar(labels, values, color=[CORAL, "#94a4aa" if mirror else TEAL], width=.55, zorder=2)
    parameter_text = fig.text(0.64, 0.77, "", fontsize=16, color=TEAL, weight="bold")
    metric_text = fig.text(0.64, 0.25, "", fontsize=12, color=INK)
    fig.text(0.07, 0.105, "单镜不代表激光腔反馈；分光面无基片厚度与背面反射。", fontsize=10, color=MUTED)
    fig.text(0.07, 0.071, "无偏振单波长；同一次追迹的两支路探测功率与膜系 R/T 对照。", fontsize=9, color=MUTED)

    def draw(index: int) -> None:
        row = states[index]
        parameter_text.set_text(f"{row['parameter']} 周期 / {row['parameter'] * 2} 层" if mirror
                                else f"TiO2 层厚  {row['parameter']} nm")
        bars[0].set_height(row["reflected_flux_w"])
        bars[1].set_height(row["unreflected_loss_w"] if mirror else row["transmitted_flux_w"])
        metric_text.set_text(f"反射接收  {row['reflected_flux_w']:.3f} W\n"
                             + (f"未反射损失  {row['unreflected_loss_w']:.3f} W" if mirror
                                else f"透射接收  {row['transmitted_flux_w']:.3f} W"))

    draw.states = states
    output_video(path, ffmpeg, fig, canvas, draw)


def join(output: Path, ffmpeg: str) -> None:
    names = ("01_lens_energy_ghost", "02_mirror_reflection", "03_splitter_two_branches")
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    *[arg for name in names for arg in ("-i", str(output / f"{name}.mp4"))],
                    "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0,fps=20[v]",
                    "-map", "[v]", "-an", "-r", "20", "-c:v", "libx264", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(output / "Optiland_system_preview_36s.mp4")], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--optiland-root", type=Path, default=ROOT.parent / "optiland")
    parser.add_argument("--output", type=Path, default=ROOT / "video_materials" / "optiland_system_v1")
    args = parser.parse_args()
    if not args.ffmpeg or not Path(args.ffmpeg).is_file():
        parser.error("Pass --ffmpeg <path-to-full-ffmpeg.exe>")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bridge = OptilandBridge(args.optiland_root)
    print("Tracing lens and geometry-matched ghost states", flush=True)
    lens, layout, layout_3d = lens_states(bridge, output)
    print("Tracing native mirror branches", flush=True)
    mirror = branch_states(bridge, True)
    print("Tracing native splitter branches", flush=True)
    splitter = branch_states(bridge, False)
    for name, render in (("01_lens_energy_ghost", lambda path: lens_clip(path, args.ffmpeg, lens, layout, layout_3d)),
                         ("02_mirror_reflection", lambda path: branch_clip(path, args.ffmpeg, mirror, mirror=True)),
                         ("03_splitter_two_branches", lambda path: branch_clip(path, args.ffmpeg, splitter, mirror=False))):
        print(f"Rendering {name}", flush=True)
        render(output / f"{name}.mp4")
    join(output, args.ffmpeg)
    (output / "optiland_system_manifest.json").write_text(json.dumps({
        "fps": FPS, "seconds_per_clip": FRAMES / FPS, "resolution": [1280, 720],
        "optiland_root": str(args.optiland_root.resolve()),
        "lens_layouts": [layout.name, layout_3d.name],
        "lens": lens, "mirror": mirror, "splitter": splitter,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Optiland system videos complete", flush=True)


if __name__ == "__main__":
    main()
