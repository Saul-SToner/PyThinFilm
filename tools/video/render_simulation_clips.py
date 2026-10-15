"""Render reproducible teaching-simulation footage from PyThinFilm results."""

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
from matplotlib.patches import Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thinfilm.custom_stack import simulate_custom_stack  # noqa: E402
from thinfilm.materials import material_complex_index  # noqa: E402

FPS = 20
SECONDS = 10
FRAMES = FPS * SECONDS
WAVELENGTHS = np.linspace(430, 760, 331)
DESIGN_INDEX = int(np.argmin(abs(WAVELENGTHS - 550)))
BG = "#f7f9fa"
INK = "#19323a"
MUTED = "#536a73"
TEAL = "#087f8c"
CORAL = "#c34a45"
GOLD = "#bd821f"
FONT = "Microsoft YaHei"


def design(layers: list[dict], probe: float = 550.0) -> dict:
    return {
        "incident_material_id": "Air",
        "substrate_material_id": "N-BK7",
        "layers": layers,
        "spectrum": {"start_nm": 430, "stop_nm": 760, "points": len(WAVELENGTHS)},
        "angle_deg": 0,
        "polarization": "s",
        "out_of_range_policy": "error",
        "probe_wavelength_nm": probe,
    }


def single_layer(thickness: float) -> list[dict]:
    return [{"id": "mgf2", "material_id": "MgF2", "thickness_nm": float(thickness), "enabled": True}]


def bragg_layers(periods: int) -> list[dict]:
    layers = []
    for index in range(periods):
        layers.extend([
            {"id": f"h{index}", "material_id": "TiO2", "thickness_nm": 63.95, "enabled": True},
            {"id": f"l{index}", "material_id": "SiO2", "thickness_nm": 94.1, "enabled": True},
        ])
    return layers


def fp_layers(cavity_nm: float) -> list[dict]:
    left = bragg_layers(3)
    return [
        *left,
        {"id": "cavity", "material_id": "SiO2", "thickness_nm": float(cavity_nm), "enabled": True},
        *[{**layer, "id": f"right-{layer['id']}"} for layer in reversed(left)],
    ]


def setup_figure(title: str, subtitle: str) -> tuple[plt.Figure, FigureCanvasAgg]:
    plt.rcParams.update({
        "font.family": FONT, "font.size": 12, "axes.edgecolor": "#b5c3c8",
        "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "text.color": INK, "axes.unicode_minus": False,
    })
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BG)
    fig.text(0.055, 0.915, title, fontsize=24, weight="bold", color=INK)
    fig.text(0.055, 0.86, subtitle, fontsize=11, color=MUTED)
    fig.text(0.055, 0.035, "PyThinFilm  ·  正入射 / 实测 n(λ), k(λ) / 一维平面膜 TMM", fontsize=9, color=MUTED)
    canvas = FigureCanvasAgg(fig)
    return fig, canvas


def style_plot(ax: plt.Axes, x_label: str, y_label: str) -> None:
    ax.set_facecolor("#ffffff")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, color="#e2eaed", linewidth=0.8, zorder=0)
    ax.set_xlabel(x_label, labelpad=9)
    ax.set_ylabel(y_label, labelpad=9)


def video_writer(path: Path, ffmpeg: str, canvas: FigureCanvasAgg) -> subprocess.Popen:
    width, height = canvas.get_width_height()
    return subprocess.Popen(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
         "-video_size", f"{width}x{height}", "-framerate", str(FPS), "-i", "-", "-an",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
        stdin=subprocess.PIPE,
    )


def encode(path: Path, ffmpeg: str, fig: plt.Figure, canvas: FigureCanvasAgg, draw_frame) -> None:
    process = video_writer(path, ffmpeg, canvas)
    try:
        assert process.stdin is not None
        for frame in range(FRAMES):
            draw_frame(frame / (FRAMES - 1))
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


def interference_clip(output: Path, ffmpeg: str) -> dict:
    thickness = 99.6
    result = simulate_custom_stack(design(single_layer(thickness)))
    reflectance = np.asarray(result["R"])
    probes = np.linspace(440, 740, FRAMES)
    n0 = 1.0
    n1 = np.asarray(material_complex_index("MgF2", probes), dtype=complex)
    ns = np.asarray(material_complex_index("N-BK7", probes), dtype=complex)
    r01 = (n0 - n1) / (n0 + n1)
    r12 = (n1 - ns) / (n1 + ns)
    t01 = 2 * n0 / (n0 + n1)
    t10 = 2 * n1 / (n0 + n1)
    roundtrip = 4 * np.pi * n1 * thickness / probes
    second = t01 * t10 * r12 * np.exp(1j * roundtrip)

    fig, canvas = setup_figure("01  两个界面，为什么能减反？", "固定空气 / MgF2 99.6 nm / N-BK7  ·  扫描波长")
    fig.text(0.065, 0.79, "前两束反射振幅（物理示意）", fontsize=16, weight="bold", color=INK)
    ax = fig.add_axes((0.085, 0.24, 0.30, 0.47))
    ax.set(aspect="equal", xlim=(-0.34, 0.34), ylim=(-0.34, 0.34))
    ax.set_facecolor("#ffffff")
    ax.axhline(0, color="#d7e2e4", lw=1)
    ax.axvline(0, color="#d7e2e4", lw=1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines[:].set_visible(False)
    first_arrow = ax.annotate("", xy=(r01[0].real, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", lw=3, color=CORAL))
    second_arrow = ax.annotate("", xy=(second[0].real, second[0].imag), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", lw=3, color=TEAL))
    sum_arrow = ax.annotate("", xy=(0, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", lw=2, color=GOLD))
    ax.text(-0.29, 0.285, "红：上界面", color=CORAL, fontsize=10)
    ax.text(-0.29, 0.245, "绿：下界面返回", color=TEAL, fontsize=10)
    ax.text(-0.29, 0.205, "金：两束之和", color=GOLD, fontsize=10)
    phase_text = fig.text(0.065, 0.15, "", fontsize=11, color=INK)
    fig.text(0.065, 0.095, "仅显示前两束；其余多次反射由 TMM 计入。", fontsize=10, color=MUTED)

    spectrum_ax = fig.add_axes((0.49, 0.27, 0.45, 0.48))
    style_plot(spectrum_ax, "波长 (nm)", "完整 TMM 反射率 R")
    spectrum_ax.set(xlim=(430, 760), ylim=(0, 0.055))
    spectrum_ax.plot(WAVELENGTHS, reflectance, color=TEAL, lw=2.8)
    spectrum_ax.axvline(550, color="#b5c5c9", ls="--", lw=1)
    cursor = spectrum_ax.axvline(probes[0], color=CORAL, lw=1.3)
    marker, = spectrum_ax.plot([probes[0]], [np.interp(probes[0], WAVELENGTHS, reflectance)], "o", color=CORAL, ms=8)
    metric_text = fig.text(0.49, 0.14, "", fontsize=12, color=INK)
    fig.text(0.49, 0.09, "右图为完整多光束 TMM，不等于金色两束示意箭头。", fontsize=10, color=MUTED)

    def draw(t: float) -> None:
        i = min(FRAMES - 1, int(round(t * (FRAMES - 1))))
        wavelength = float(probes[i])
        a = complex(r01[i])
        b = complex(second[i])
        first_arrow.xy = (a.real, a.imag)
        second_arrow.xy = (b.real, b.imag)
        sum_arrow.xy = ((a + b).real, (a + b).imag)
        cursor.set_xdata([wavelength, wavelength])
        value = float(np.interp(wavelength, WAVELENGTHS, reflectance))
        marker.set_data([wavelength], [value])
        phase_text.set_text(f"{wavelength:.0f} nm：膜内往返传播相位 {np.degrees(roundtrip[i].real):.0f}°")
        metric_text.set_text(f"真实膜系反射率  R = {100 * value:.2f}%")

    encode(output, ffmpeg, fig, canvas, draw)
    return {"film_thickness_nm": thickness, "probe_wavelength_nm": [440, 740],
            "R_550": float(reflectance[DESIGN_INDEX]), "phasors": "first_two_reflected_fields_only"}


def thickness_clip(output: Path, ffmpeg: str) -> dict:
    thicknesses = np.linspace(80, 135, FRAMES)
    results = [simulate_custom_stack(design(single_layer(d))) for d in thicknesses]
    spectra = [np.asarray(row["R"]) for row in results]
    indices = [float(np.argmin(row)) for row in spectra]
    n0 = float(np.real(material_complex_index("Air", 550)))
    n1 = float(np.real(material_complex_index("MgF2", 550)))
    ns = float(np.real(material_complex_index("N-BK7", 550)))
    bare = np.abs((n0 - np.asarray(material_complex_index("N-BK7", WAVELENGTHS))) /
                  (n0 + np.asarray(material_complex_index("N-BK7", WAVELENGTHS)))) ** 2

    fig, canvas = setup_figure("02  厚度改变，反射谷如何移动？", "空气 / MgF2 / N-BK7  ·  固定材料，只改变膜厚")
    stack = fig.add_axes((0.06, 0.38, 0.29, 0.36))
    stack.set(xlim=(0, 1), ylim=(-18, 165))
    stack.axis("off")
    stack.add_patch(Rectangle((0.06, -17), 0.88, 17, color="#aebdc2"))
    film = Rectangle((0.06, 0), 0.88, 80, color="#75c5be")
    stack.add_patch(film)
    stack.text(0.5, -10, "N-BK7 玻璃", ha="center", va="center", fontsize=11)
    stack.text(0.5, 151, "空气", ha="center", va="center", fontsize=11)
    layer_label = stack.text(0.5, 72, "MgF2", ha="center", va="center", fontsize=12)
    thickness_text = fig.text(0.07, 0.79, "", fontsize=19, weight="bold", color=TEAL)

    phasors = fig.add_axes((0.085, 0.115, 0.22, 0.22))
    phasors.set(aspect="equal", xlim=(-0.48, 0.48), ylim=(-0.48, 0.48))
    phasors.axis("off")
    phasors.plot([-0.5, 0.5], [0, 0], color="#d6e0e2", lw=1)
    phasors.plot([0, 0], [-0.5, 0.5], color="#d6e0e2", lw=1)
    first = (n0 - n1) / (n0 + n1)
    second_base = (2 * n0 / (n0 + n1)) * (2 * n1 / (n0 + n1)) * ((n1 - ns) / (n1 + ns))
    first_arrow, = phasors.plot([0, first], [0, 0], color=CORAL, lw=3, marker="o", markevery=[-1])
    second_arrow, = phasors.plot([0, 0], [0, 0], color=TEAL, lw=3, marker="o", markevery=[-1])
    fig.text(0.07, 0.34, "前两束反射振幅（示意）", fontsize=11, color=MUTED)
    phase_text = fig.text(0.07, 0.085, "", fontsize=10, color=MUTED)

    ax = fig.add_axes((0.43, 0.26, 0.51, 0.49))
    style_plot(ax, "波长 (nm)", "反射率 R")
    ax.set(xlim=(430, 760), ylim=(0, 0.13))
    ax.plot(WAVELENGTHS, bare, color="#84949b", ls="--", lw=1.7, label="未镀膜基底")
    line, = ax.plot(WAVELENGTHS, spectra[0], color=TEAL, lw=3, label="MgF2 单层膜")
    marker, = ax.plot([550], [spectra[0][DESIGN_INDEX]], "o", color=CORAL, ms=8)
    ax.axvline(550, color="#d5dee0", lw=1)
    ax.legend(loc="upper right", frameon=False, fontsize=10)
    metric_text = fig.text(0.43, 0.14, "", fontsize=13, color=INK)
    fig.text(0.43, 0.09, "光谱由完整 TMM 求解；振幅箭头仅用于相位直观解释。", fontsize=10, color=MUTED)

    def draw(t: float) -> None:
        index = min(len(thicknesses) - 1, int(round(t * (len(thicknesses) - 1))))
        d = float(thicknesses[index])
        curve = spectra[index]
        film.set_height(d)
        layer_label.set_y(d / 2)
        thickness_text.set_text(f"膜厚  {d:.1f} nm")
        line.set_ydata(curve)
        marker.set_data([550], [float(np.interp(550, WAVELENGTHS, curve))])
        phase = 4 * np.pi * n1 * d / 550
        second = second_base * np.exp(1j * phase)
        second_arrow.set_data([0, second.real], [0, second.imag])
        first_arrow.set_data([0, first], [0, 0])
        phase_text.set_text(f"膜内往返传播相位  {np.degrees(phase):.0f}°  (550 nm)")
        metric_text.set_text(f"550 nm: R = {100 * np.interp(550, WAVELENGTHS, curve):.2f}%    反射谷 ≈ {WAVELENGTHS[int(np.argmin(curve))]:.0f} nm")

    encode(output, ffmpeg, fig, canvas, draw)
    return {"thickness_nm": [80, 135], "minima_nm_at_endpoints": [float(WAVELENGTHS[int(v)]) for v in (indices[0], indices[-1])],
            "R_550_at_endpoints": [float(row[DESIGN_INDEX]) for row in (spectra[0], spectra[-1])]}


def bragg_clip(output: Path, ffmpeg: str) -> dict:
    results = [simulate_custom_stack(design(bragg_layers(periods))) for periods in range(1, 11)]
    spectra = [np.asarray(row["R"]) for row in results]
    fig, canvas = setup_figure("03  周期数增加，高反射带如何形成？", "TiO2 / SiO2 交替堆叠  ·  每层设计厚度固定")
    ax_layers = fig.add_axes((0.07, 0.19, 0.22, 0.59))
    ax_layers.set(xlim=(0, 1), ylim=(-1, 21))
    ax_layers.axis("off")
    patches = []
    for i in range(20):
        patch = Rectangle((0.15, 19 - i + 0.08), 0.7, 0.82, facecolor="#bddbd9" if i % 2 else "#ebada0", visible=i < 2)
        ax_layers.add_patch(patch)
        patches.append(patch)
    ax_layers.text(0.5, 20.5, "空气", ha="center", fontsize=10)
    ax_layers.text(0.5, -0.8, "N-BK7", ha="center", fontsize=10)
    fig.text(0.075, 0.12, "红：TiO2 高折射率层\n绿：SiO2 低折射率层", fontsize=10, color=MUTED)
    count_text = fig.text(0.36, 0.77, "", fontsize=18, weight="bold", color=TEAL)

    ax = fig.add_axes((0.36, 0.22, 0.58, 0.50))
    style_plot(ax, "波长 (nm)", "反射率 R")
    ax.set(xlim=(430, 760), ylim=(0, 1.03))
    ax.axvline(550, color="#d5dee0", lw=1)
    ax.axhline(0.9, color="#a9b9be", lw=1, ls="--")
    line, = ax.plot(WAVELENGTHS, spectra[0], color=CORAL, lw=3)
    metric_text = fig.text(0.36, 0.105, "", fontsize=12, color=INK)

    def draw(t: float) -> None:
        periods = min(10, 1 + int(t * 10))
        for i, patch in enumerate(patches):
            patch.set_visible(i < 2 * periods)
        line.set_ydata(spectra[periods - 1])
        count_text.set_text(f"{periods} 周期  /  {2 * periods} 层")
        metric_text.set_text(f"550 nm 反射率  {100 * spectra[periods - 1][DESIGN_INDEX]:.1f}%  ·  虚线表示 R = 90%")

    encode(output, ffmpeg, fig, canvas, draw)
    return {"periods": [1, 10], "R_550_at_endpoints": [float(spectra[0][DESIGN_INDEX]), float(spectra[-1][DESIGN_INDEX])]}


def fp_clip(output: Path, ffmpeg: str) -> dict:
    wavelengths = np.linspace(500, 650, 601)
    cavities = np.linspace(300, 400, FRAMES)
    results = []
    for thickness in cavities:
        payload = design(fp_layers(float(thickness)))
        payload["spectrum"] = {"start_nm": 500, "stop_nm": 650, "points": len(wavelengths)}
        results.append(simulate_custom_stack(payload))
    transmissions = [np.asarray(row["T"]) for row in results]
    peaks = [int(np.argmax(curve)) for curve in transmissions]
    if any(index <= 0 or index >= len(wavelengths) - 1 for index in peaks):
        raise RuntimeError("F-P transmission peak left the plotted wavelength range")

    fig, canvas = setup_figure("04  腔长改变，选通波长如何移动？", "空气 / (HL)3 / SiO2 腔 / (LH)3 / N-BK7  ·  仅改变腔层厚度")
    cavity_text = fig.text(0.07, 0.77, "", fontsize=19, color=TEAL, weight="bold")
    ax_stack = fig.add_axes((0.07, 0.23, 0.26, 0.47))
    ax_stack.set(xlim=(0, 1), ylim=(0, 1))
    ax_stack.axis("off")
    mirror_colors = ["#d9aaa0", "#a8d5d3"] * 3
    for index, color in enumerate(mirror_colors):
        ax_stack.add_patch(Rectangle((0.12, 0.89 - index * 0.055), 0.76, 0.047, color=color))
        ax_stack.add_patch(Rectangle((0.12, 0.07 + index * 0.055), 0.76, 0.047, color=color))
    cavity = Rectangle((0.12, 0.425), 0.76, 0.13, color="#f1cf87")
    ax_stack.add_patch(cavity)
    ax_stack.text(0.5, 0.495, "SiO2 腔", ha="center", va="center", fontsize=10)
    ax_stack.text(0.5, 0.94, "入射", ha="center", fontsize=10, color=MUTED)
    fig.text(0.07, 0.15, "上下镜堆保持不变\n黄色腔层厚度按比例示意", fontsize=10, color=MUTED)

    ax = fig.add_axes((0.43, 0.26, 0.51, 0.49))
    style_plot(ax, "波长 (nm)", "透射率 T")
    ax.set(xlim=(500, 650), ylim=(0, 1.04))
    line, = ax.plot(wavelengths, transmissions[0], color=TEAL, lw=3)
    marker, = ax.plot([wavelengths[peaks[0]]], [transmissions[0][peaks[0]]], "o", color=CORAL, ms=8)
    center_line = ax.axvline(wavelengths[peaks[0]], color=CORAL, lw=1, alpha=0.7)
    metric_text = fig.text(0.43, 0.14, "", fontsize=12, color=INK)
    fig.text(0.43, 0.09, "完整 TMM 光谱；峰位为当前扫描范围内的最大透射点。", fontsize=10, color=MUTED)

    def draw(t: float) -> None:
        i = min(FRAMES - 1, int(round(t * (FRAMES - 1))))
        thickness = float(cavities[i])
        peak = peaks[i]
        curve = transmissions[i]
        cavity_text.set_text(f"腔层厚度  {thickness:.1f} nm")
        cavity.set_height(0.11 + (thickness - 300) / 100 * 0.045)
        line.set_ydata(curve)
        marker.set_data([wavelengths[peak]], [curve[peak]])
        center_line.set_xdata([wavelengths[peak], wavelengths[peak]])
        metric_text.set_text(f"透射峰  {wavelengths[peak]:.1f} nm    峰值 T = {100 * curve[peak]:.1f}%")

    encode(output, ffmpeg, fig, canvas, draw)
    return {"cavity_thickness_nm": [300, 400],
            "peak_wavelength_nm_at_endpoints": [float(wavelengths[peaks[0]]), float(wavelengths[peaks[-1]])],
            "peak_T_at_endpoints": [float(transmissions[0][peaks[0]]), float(transmissions[-1][peaks[-1]])]}


def field_clip(output: Path, ffmpeg: str) -> dict:
    probes = np.linspace(440, 740, 41)
    results = [simulate_custom_stack(design(single_layer(99.6), float(w))) for w in probes]
    spectrum = np.asarray(results[0]["R"])
    depths = [np.asarray(row["field"]["z_nm"]) for row in results]
    intensities = [np.asarray(row["field"]["E2"]) for row in results]
    field_ceiling = max(float(np.max(values)) for values in intensities) * 1.12
    fig, canvas = setup_figure("05  波长选择改变层内场强分布", "固定 MgF2 99.6 nm  ·  扫描探针波长，不改变膜结构")
    left = fig.add_axes((0.07, 0.26, 0.37, 0.49))
    style_plot(left, "波长 (nm)", "反射率 R")
    left.set(xlim=(430, 760), ylim=(0, max(0.13, float(np.max(spectrum)) * 1.08)))
    left.plot(WAVELENGTHS, spectrum, color=TEAL, lw=2.7)
    marker, = left.plot([probes[0]], [float(np.interp(probes[0], WAVELENGTHS, spectrum))], "o", color=CORAL, ms=9)
    cursor = left.axvline(probes[0], color=CORAL, lw=1.3)
    right = fig.add_axes((0.54, 0.26, 0.41, 0.49))
    style_plot(right, "相对膜表面深度 z (nm)", "|E(z)|² / |E入射|²")
    right.set(xlim=(-40, 140), ylim=(0, field_ceiling))
    right.axvspan(0, 99.6, facecolor="#dcefeb", zorder=0)
    right.axvline(0, color="#92b7b2", lw=1)
    right.axvline(99.6, color="#92b7b2", lw=1)
    right.text(49, field_ceiling * 0.92, "MgF2", ha="center", fontsize=10, color=MUTED)
    line, = right.plot(depths[0], intensities[0], color=GOLD, lw=2.6)
    wavelength_text = fig.text(0.07, 0.79, "", fontsize=17, weight="bold", color=TEAL)
    metric_text = fig.text(0.54, 0.14, "", fontsize=12, color=INK)
    fig.text(0.54, 0.09, "空间场强来自一维 TMM；不是几何光线追踪。", fontsize=10, color=MUTED)

    def draw(t: float) -> None:
        i = min(len(probes) - 1, int(t * len(probes)))
        wavelength = float(probes[i])
        marker.set_data([wavelength], [float(np.interp(wavelength, WAVELENGTHS, spectrum))])
        cursor.set_xdata([wavelength, wavelength])
        line.set_data(depths[i], intensities[i])
        wavelength_text.set_text(f"探针波长  {wavelength:.0f} nm")
        metric_text.set_text(f"峰值相对场强  {np.max(intensities[i]):.2f}    ·    R = {100 * np.interp(wavelength, WAVELENGTHS, spectrum):.2f}%")

    encode(output, ffmpeg, fig, canvas, draw)
    return {"film_thickness_nm": 99.6, "probe_wavelength_nm": [440, 740],
            "field_peak_range": [float(min(np.max(row) for row in intensities)), float(max(np.max(row) for row in intensities))]}


def combine_clips(output: Path, ffmpeg: str, names: tuple[str, ...]) -> None:
    clips = [output / f"{name}.mp4" for name in names]
    streams = "".join(f"[{i}:v]" for i in range(len(clips)))
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
         *[item for clip in clips for item in ("-i", str(clip))],
         "-filter_complex", f"{streams}concat=n={len(clips)}:v=1:a=0[v]",
         "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         str(output / "PyThinFilm_simulation_preview_50s.mp4")],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "video_materials" / "simulation_v1")
    parser.add_argument("--ffmpeg", default=None)
    args = parser.parse_args()
    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg or not Path(ffmpeg).is_file():
        parser.error("ffmpeg unavailable; pass --ffmpeg <path-to-ffmpeg.exe>")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scenes = {}
    clips = (
        ("00_interference_mechanism", interference_clip),
        ("01_mgf2_thickness", thickness_clip),
        ("02_bragg_periods", bragg_clip),
        ("04_fp_cavity", fp_clip),
        ("03_field_vs_wavelength", field_clip),
    )
    for name, render in clips:
        path = output / f"{name}.mp4"
        print(f"Rendering {path}", flush=True)
        scenes[name] = render(path, ffmpeg)
    combine_clips(output, ffmpeg, tuple(name for name, _ in clips))
    (output / "simulation_manifest.json").write_text(json.dumps({
        "fps": FPS, "seconds_per_clip": SECONDS, "resolution": [1280, 720],
        "engine": "thinfilm.custom_stack.simulate_custom_stack", "scenes": scenes,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("All clips rendered", flush=True)


if __name__ == "__main__":
    main()
