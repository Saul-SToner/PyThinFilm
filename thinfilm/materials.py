"""Unified real-material optical constants library.

The CSV files under ``data/real_nk`` are normalized snapshots from
RefractiveIndex.INFO.  This module provides a small, stable API for loading
those files, interpolating n/k values, and exporting material-library summary
artifacts for the teaching and research modules.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np

from .paths import PROJECT_DIR, output_file
from .plotting import BLUE, GREEN, INK, MUTED, RED, apply_plot_style, style_axis


REAL_NK_DIR = PROJECT_DIR / "data" / "real_nk"
REAL_NK_MANIFEST = REAL_NK_DIR / "manifest.json"

MATERIAL_ALIASES = {
    "silica": "SiO2",
    "sio2": "SiO2",
    "quartz": "SiO2",
    "tio2": "TiO2",
    "titania": "TiO2",
    "mgf2": "MgF2",
    "al2o3": "Al2O3",
    "alumina": "Al2O3",
    "au": "Au",
    "gold": "Au",
    "ag": "Ag",
    "silver": "Ag",
    "si": "Si",
    "silicon": "Si",
    "air": "Air",
}


@dataclass(frozen=True)
class MaterialDataset:
    """Loaded n/k table for one material source."""

    material: str
    source: str
    file: Path
    lambda_um: np.ndarray
    n: np.ndarray
    k: np.ndarray
    metadata: dict[str, Any]

    @property
    def lambda_min_um(self) -> float:
        return float(np.min(self.lambda_um))

    @property
    def lambda_max_um(self) -> float:
        return float(np.max(self.lambda_um))


def canonical_material_name(material: str) -> str:
    """Normalize common material aliases used across COMSOL and Python code."""
    key = str(material).strip()
    if not key:
        raise ValueError("material name must not be empty")
    return MATERIAL_ALIASES.get(key.lower(), key)


def _load_manifest() -> list[dict[str, Any]]:
    if not REAL_NK_MANIFEST.exists():
        raise FileNotFoundError(f"real material manifest not found: {REAL_NK_MANIFEST}")
    return json.loads(REAL_NK_MANIFEST.read_text(encoding="utf-8"))


def list_real_materials() -> list[dict[str, Any]]:
    """Return available real-material n/k datasets from ``data/real_nk``."""
    rows: list[dict[str, Any]] = []
    for item in _load_manifest():
        row = dict(item)
        row["file"] = str(PROJECT_DIR / str(item["file"]))
        rows.append(row)
    return rows


def _find_manifest_entry(material: str, source_contains: str | None = None) -> dict[str, Any]:
    target = canonical_material_name(material)
    matches = [
        item
        for item in _load_manifest()
        if canonical_material_name(str(item.get("material", ""))) == target
    ]
    if source_contains:
        source_key = str(source_contains).lower()
        matches = [item for item in matches if source_key in str(item.get("source", "")).lower()]
    if not matches:
        available = ", ".join(sorted({str(item.get("material")) for item in _load_manifest()}))
        raise KeyError(f"material dataset not found: {material}. Available: {available}")
    return matches[0]


def load_real_material(material: str, source_contains: str | None = None) -> MaterialDataset:
    """Load one material n/k table by material name and optional source filter."""
    if canonical_material_name(material) == "Air":
        lambda_um = np.asarray([0.1, 100.0], dtype=float)
        return MaterialDataset(
            material="Air",
            source="constant vacuum/air approximation",
            file=Path(""),
            lambda_um=lambda_um,
            n=np.ones_like(lambda_um),
            k=np.zeros_like(lambda_um),
            metadata={
                "material": "Air",
                "source": "constant vacuum/air approximation",
                "lambda_min_um": float(lambda_um[0]),
                "lambda_max_um": float(lambda_um[-1]),
                "type": "constant",
            },
        )

    entry = _find_manifest_entry(material, source_contains=source_contains)
    path = PROJECT_DIR / str(entry["file"])
    if not path.exists():
        raise FileNotFoundError(f"material CSV not found: {path}")

    data = np.genfromtxt(path, delimiter=",", names=True, dtype=None, encoding="utf-8")
    lambda_um = np.asarray(data["lambda_um"], dtype=float)
    n_vals = np.asarray(data["n"], dtype=float)
    k_vals = np.asarray(data["k"], dtype=float)
    order = np.argsort(lambda_um)

    return MaterialDataset(
        material=str(entry["material"]),
        source=str(entry["source"]),
        file=path,
        lambda_um=lambda_um[order],
        n=n_vals[order],
        k=k_vals[order],
        metadata=dict(entry),
    )


def material_nk_at(
    material: str,
    wavelength_um: float | Sequence[float],
    *,
    source_contains: str | None = None,
    allow_extrapolate: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Interpolate real-material n/k values at one or more wavelengths in um."""
    dataset = load_real_material(material, source_contains=source_contains)
    wl = np.asarray(wavelength_um, dtype=float)
    wl_min = dataset.lambda_min_um
    wl_max = dataset.lambda_max_um
    if not allow_extrapolate and (np.any(wl < wl_min) or np.any(wl > wl_max)):
        raise ValueError(
            f"{dataset.material} ({dataset.source}) valid range is "
            f"{wl_min:.4g}-{wl_max:.4g} um, requested "
            f"{float(np.min(wl)):.4g}-{float(np.max(wl)):.4g} um."
        )
    n_vals = np.interp(wl, dataset.lambda_um, dataset.n)
    k_vals = np.interp(wl, dataset.lambda_um, dataset.k)
    return n_vals, k_vals


def material_complex_index(
    material: str,
    wavelength_nm: float | Sequence[float],
    *,
    source_contains: str | None = None,
    allow_extrapolate: bool = False,
) -> np.ndarray:
    """Return complex refractive index ``n + i k`` at wavelength(s) in nm."""
    wl_um = np.asarray(wavelength_nm, dtype=float) / 1000.0
    n_vals, k_vals = material_nk_at(
        material,
        wl_um,
        source_contains=source_contains,
        allow_extrapolate=allow_extrapolate,
    )
    return np.asarray(n_vals, dtype=float) + 1j * np.asarray(k_vals, dtype=float)


def common_wavelength_window_um(materials: Iterable[str]) -> tuple[float, float]:
    """Return the common valid wavelength window for a set of materials."""
    datasets = [load_real_material(material) for material in materials if canonical_material_name(material) != "Air"]
    if not datasets:
        return (0.1, 100.0)
    lower = max(dataset.lambda_min_um for dataset in datasets)
    upper = min(dataset.lambda_max_um for dataset in datasets)
    if lower >= upper:
        names = ", ".join(f"{d.material}({d.lambda_min_um:.3g}-{d.lambda_max_um:.3g}um)" for d in datasets)
        raise ValueError(f"no overlapping wavelength window for materials: {names}")
    return (float(lower), float(upper))


def sample_real_materials(
    materials: Sequence[str] | None = None,
    wavelengths_um: Sequence[float] | None = None,
    *,
    allow_extrapolate: bool = False,
) -> list[dict[str, Any]]:
    """Sample the material library into row dictionaries for CSV/JSON export."""
    if materials is None:
        materials = [str(item["material"]) for item in list_real_materials()]
    if wavelengths_um is None:
        wavelengths_um = [0.45, 0.55, 0.65, 1.0, 1.55]

    rows: list[dict[str, Any]] = []
    for material in materials:
        dataset = load_real_material(material)
        for wl_um in wavelengths_um:
            try:
                n_vals, k_vals = material_nk_at(material, float(wl_um), allow_extrapolate=allow_extrapolate)
                in_range = dataset.lambda_min_um <= float(wl_um) <= dataset.lambda_max_um
                rows.append(
                    {
                        "material": dataset.material,
                        "source": dataset.source,
                        "lambda_um": float(wl_um),
                        "n": float(np.asarray(n_vals)),
                        "k": float(np.asarray(k_vals)),
                        "in_source_range": bool(in_range),
                        "lambda_min_um": dataset.lambda_min_um,
                        "lambda_max_um": dataset.lambda_max_um,
                    }
                )
            except ValueError:
                rows.append(
                    {
                        "material": dataset.material,
                        "source": dataset.source,
                        "lambda_um": float(wl_um),
                        "n": "",
                        "k": "",
                        "in_source_range": False,
                        "lambda_min_um": dataset.lambda_min_um,
                        "lambda_max_um": dataset.lambda_max_um,
                    }
                )
    return rows


def export_real_material_library(
    *,
    prefix: str = "real_material_library",
    materials: Sequence[str] | None = None,
    wavelengths_um: Sequence[float] | None = None,
) -> dict[str, str]:
    """Export material catalog, sampled n/k table, and overview plot."""
    catalog = list_real_materials()
    sample_rows = sample_real_materials(materials=materials, wavelengths_um=wavelengths_um)

    catalog_json = output_file(f"{prefix}_catalog.json")
    catalog_json.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    sample_csv = output_file(f"{prefix}_sampled_nk.csv")
    fieldnames = [
        "material",
        "source",
        "lambda_um",
        "n",
        "k",
        "in_source_range",
        "lambda_min_um",
        "lambda_max_um",
    ]
    with sample_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_rows)

    summary_txt = output_file(f"{prefix}_summary.txt")
    lines = [
        "真实材料 n/k 光学常数库",
        f"data_dir = {REAL_NK_DIR}",
        f"materials = {', '.join(str(item['material']) for item in catalog)}",
        "",
        "覆盖范围:",
    ]
    for item in catalog:
        lines.append(
            f"- {item['material']}: {item['lambda_min_um']:.4g}-{item['lambda_max_um']:.4g} um | "
            f"{item['source']}"
        )
    summary_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    plot_path = output_file(f"{prefix}_overview.png")
    _plot_material_library_overview(plot_path, catalog)

    return {
        "catalog_json": str(catalog_json),
        "sampled_csv": str(sample_csv),
        "summary_txt": str(summary_txt),
        "overview_png": str(plot_path),
    }


def _plot_material_library_overview(path: Path, catalog: Sequence[dict[str, Any]]) -> None:
    apply_plot_style()
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)

    ax = axes[0]
    names = [str(item["material"]) for item in catalog]
    starts = [float(item["lambda_min_um"]) for item in catalog]
    widths = [float(item["lambda_max_um"]) - float(item["lambda_min_um"]) for item in catalog]
    y = np.arange(len(catalog))
    ax.barh(y, widths, left=starts, color=BLUE, alpha=0.82)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xscale("log")
    style_axis(ax)
    ax.set_title("材料光学常数覆盖范围", loc="left")
    ax.set_xlabel("波长 (μm，对数坐标)")
    ax.axvspan(0.3, 2.5, color=GREEN, alpha=0.10, label="太阳波段 0.3-2.5 μm")
    ax.axvspan(8.0, 13.0, color=RED, alpha=0.08, label="大气窗口 8-13 μm")
    ax.legend(loc="lower right")

    ax = axes[1]
    sample_wl = np.linspace(0.45, 1.5, 180)
    for material, color in [
        ("SiO2", BLUE),
        ("TiO2", RED),
        ("MgF2", GREEN),
        ("Al2O3", MUTED),
    ]:
        try:
            n_vals, _ = material_nk_at(material, sample_wl)
        except ValueError:
            dataset = load_real_material(material)
            wl = sample_wl[(sample_wl >= dataset.lambda_min_um) & (sample_wl <= dataset.lambda_max_um)]
            if wl.size == 0:
                continue
            n_vals, _ = material_nk_at(material, wl)
            ax.plot(wl, n_vals, color=color, lw=2.0, label=material)
            continue
        ax.plot(sample_wl, n_vals, color=color, lw=2.0, label=material)
    style_axis(ax)
    ax.set_title("可见/近红外折射率色散", loc="left")
    ax.set_xlabel("波长 (μm)")
    ax.set_ylabel("折射率 n")
    ax.legend(loc="best")

    fig.suptitle("真实材料 n/k 光学常数库", fontsize=15, fontweight="bold", color=INK, x=0.02, ha="left")
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)
