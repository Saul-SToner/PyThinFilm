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
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np

from .paths import PROJECT_DIR, output_file
from .plotting import BLUE, GREEN, INK, MUTED, RED, apply_plot_style, save_publication_figure, style_axis
from .figure_audit import audit_source_files, build_figure_audit, write_figure_audit


REAL_NK_DIR = PROJECT_DIR / "data" / "real_nk"
REAL_NK_MANIFEST = REAL_NK_DIR / "manifest.json"

_MATERIAL_CACHE: dict[tuple[str, str | None], "MaterialDataset"] = {}


def _make_readonly(arr: np.ndarray) -> np.ndarray:
    """Make a numpy array read-only to prevent accidental mutation."""
    arr.flags.writeable = False
    return arr


def clear_material_cache() -> None:
    """Clear all material caches. Useful for testing."""
    _MATERIAL_CACHE.clear()
    _load_manifest.cache_clear()

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


@lru_cache(maxsize=1)
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
    """Load one material n/k table by material name and optional source filter.
    
    Results are cached: repeated calls with the same arguments return the
    same MaterialDataset instance without re-reading from disk.
    """
    cache_key = (canonical_material_name(material), source_contains)
    cached = _MATERIAL_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if canonical_material_name(material) == "Air":
        lambda_um = _make_readonly(np.asarray([0.1, 100.0], dtype=float))
        ds = MaterialDataset(
            material="Air",
            source="constant vacuum/air approximation",
            file=Path(""),
            lambda_um=lambda_um,
            n=_make_readonly(np.ones_like(lambda_um)),
            k=_make_readonly(np.zeros_like(lambda_um)),
            metadata={
                "material": "Air",
                "source": "constant vacuum/air approximation",
                "lambda_min_um": float(lambda_um[0]),
                "lambda_max_um": float(lambda_um[-1]),
                "type": "constant",
            },
        )
        _MATERIAL_CACHE[cache_key] = ds
        return ds

    entry = _find_manifest_entry(material, source_contains=source_contains)
    path = PROJECT_DIR / str(entry["file"])
    if not path.exists():
        raise FileNotFoundError(f"material CSV not found: {path}")

    data = np.genfromtxt(path, delimiter=",", names=True, dtype=None, encoding="utf-8")
    lambda_um = np.asarray(data["lambda_um"], dtype=float)
    n_vals = np.asarray(data["n"], dtype=float)
    k_vals = np.asarray(data["k"], dtype=float)
    order = np.argsort(lambda_um)

    ds = MaterialDataset(
        material=str(entry["material"]),
        source=str(entry["source"]),
        file=path,
        lambda_um=_make_readonly(lambda_um[order]),
        n=_make_readonly(n_vals[order]),
        k=_make_readonly(k_vals[order]),
        metadata=dict(entry),
    )
    _MATERIAL_CACHE[cache_key] = ds
    return ds


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
    source_files = [str(item["file"]) for item in catalog]
    audit = build_figure_audit(
        figure_id=f"{prefix}_overview",
        title="真实材料 n/k 光学常数库",
        evidence_level="real_material_theory",
        checks=[audit_source_files(source_files)],
        source_files=source_files,
    )
    audit_path = output_file(f"{prefix}_figure_audit.json")

    return {
        "catalog_json": str(catalog_json),
        "sampled_csv": str(sample_csv),
        "summary_txt": str(summary_txt),
        "overview_png": str(plot_path),
        "audit_json": write_figure_audit(audit_path, audit),
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
    ax.text(0.34, -0.52, "太阳波段", color=GREEN, fontsize=7, ha="left", va="center")
    ax.text(8.1, -0.52, "大气窗口", color=RED, fontsize=7, ha="left", va="center")

    ax = axes[1]
    sample_wl = np.linspace(0.45, 1.5, 180)
    ax_k = ax.twinx()
    for material, color in [
        ("SiO2", BLUE),
        ("TiO2", RED),
        ("MgF2", GREEN),
        ("Au", MUTED),
    ]:
        try:
            n_vals, k_vals = material_nk_at(material, sample_wl)
        except ValueError:
            dataset = load_real_material(material)
            wl = sample_wl[(sample_wl >= dataset.lambda_min_um) & (sample_wl <= dataset.lambda_max_um)]
            if wl.size == 0:
                continue
            n_vals, k_vals = material_nk_at(material, wl)
            ax.plot(wl, n_vals, color=color, lw=2.0, label=material)
            ax_k.plot(wl, k_vals, color=color, lw=1.25, alpha=0.65, linestyle="--")
            continue
        ax.plot(sample_wl, n_vals, color=color, lw=2.0, label=material)
        ax_k.plot(sample_wl, k_vals, color=color, lw=1.25, alpha=0.65, linestyle="--")
    style_axis(ax)
    ax.set_title("代表材料色散：n 实线，k 虚线", loc="left")
    ax.set_xlabel("波长 (μm)")
    ax.set_ylabel("折射率 n")
    ax_k.set_ylabel("消光系数 k", color=MUTED)
    ax_k.tick_params(axis="y", colors=MUTED, labelsize=8)
    ax_k.set_yscale("symlog", linthresh=1e-4)
    ax.legend(loc="best")

    fig.suptitle("真实材料 n/k 光学常数库", fontsize=10, fontweight="semibold", color=INK, x=0.02, ha="left")
    save_publication_figure(fig, path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# APP-facing material metadata helpers
# ---------------------------------------------------------------------------

#: Static metadata for every real material in the library.
#: ``suitable_roles`` lists the layer-role keys this material can fill.
_MATERIAL_DISPLAY_META: dict[str, dict[str, Any]] = {
    "Air": {
        "display_name": "Air（空气/真空）",
        "display_name_en": "Air / Vacuum",
        "suitable_roles": ["n_incident"],
        "locked_roles": ["n_incident"],   # always locked: air is the only incidence medium
        "category": "气体",
    },
    "SiO2": {
        "display_name": "SiO₂（二氧化硅 / 熔融石英）",
        "display_name_en": "SiO₂ (Fused Silica)",
        "suitable_roles": ["n_low", "n_substrate"],
        "locked_roles": [],
        "category": "介质",
    },
    "MgF2": {
        "display_name": "MgF₂（氟化镁，最低折射率增透层）",
        "display_name_en": "MgF₂ (Magnesium Fluoride)",
        "suitable_roles": ["n_low"],
        "locked_roles": [],
        "category": "介质",
    },
    "Al2O3": {
        "display_name": "Al₂O₃（氧化铝）",
        "display_name_en": "Al₂O₃ (Alumina)",
        "suitable_roles": ["n_low", "n_mid"],
        "locked_roles": [],
        "category": "介质",
    },
    "TiO2": {
        "display_name": "TiO₂（二氧化钛，高折射率层）",
        "display_name_en": "TiO₂ (Titanium Dioxide)",
        "suitable_roles": ["n_high", "n_high_2"],
        "locked_roles": [],
        "category": "介质",
    },
    "Si": {
        "display_name": "Si（硅，近红外高折射率半导体）",
        "display_name_en": "Si (Silicon)",
        "suitable_roles": ["n_high", "n_high_2"],
        "locked_roles": [],
        "category": "半导体",
    },
    "Ag": {
        "display_name": "Ag（银，金属宽带高反衬底）",
        "display_name_en": "Ag (Silver)",
        "suitable_roles": ["n_substrate"],
        "locked_roles": [],
        "category": "金属",
    },
    "Au": {
        "display_name": "Au（金，金属宽带高反衬底）",
        "display_name_en": "Au (Gold)",
        "suitable_roles": ["n_substrate"],
        "locked_roles": [],
        "category": "金属",
    },
}

#: Role-level human-readable labels (Chinese).
ROLE_LABELS_CN: dict[str, str] = {
    "n_incident":  "入射侧介质",
    "n_substrate": "衬底材料",
    "n_low":       "低折射率膜层",
    "n_mid":       "中折射率膜层",
    "n_high":      "高折射率膜层",
    "n_high_2":    "第二高折射率膜层",
    "n_porous":    "多孔等效层",
}

#: Roles used by each design type (ordered; only roles that matter for the design).
_DESIGN_ROLE_MAP: dict[str, list[str]] = {
    "single_ar":                    ["n_incident", "n_low", "n_substrate"],
    "double_ar":                    ["n_incident", "n_low", "n_mid", "n_substrate"],
    "triple_ar":                    ["n_incident", "n_low", "n_mid", "n_high", "n_substrate"],
    "high_reflector":               ["n_incident", "n_low", "n_high", "n_substrate"],
    "bragg_reflector":              ["n_incident", "n_low", "n_high", "n_substrate"],
    "quarter_wave_stack":           ["n_incident", "n_low", "n_high", "n_substrate"],
    "quarter_wave_single_layer":    ["n_incident", "n_low", "n_substrate"],
    "quarter_wave_double_layer":    ["n_incident", "n_low", "n_high", "n_substrate"],
    "half_wave_single_layer":       ["n_incident", "n_mid", "n_substrate"],
    "fp_filter":                    ["n_incident", "n_low", "n_high", "n_substrate"],
    "fp_single_halfwave":           ["n_incident", "n_low", "n_high", "n_substrate"],
    "fp_double_halfwave":           ["n_incident", "n_low", "n_high", "n_substrate"],
    "narrowband_filter":            ["n_incident", "n_low", "n_high", "n_substrate"],
    "neutral_beamsplitter":         ["n_incident", "n_low", "n_high", "n_substrate"],
    "rugate_filter":                ["n_incident", "n_low", "n_high", "n_substrate"],
    "porous_sio2_layer":            ["n_incident", "n_porous", "n_substrate"],
    "porous_double_ar":             ["n_incident", "n_porous", "n_low", "n_substrate"],
    "moth_eye_effective_gradient":  ["n_incident", "n_low", "n_high", "n_substrate"],
}

#: Roles that are always locked for standard teaching cases (user cannot change them).
_LOCKED_ROLES: frozenset[str] = frozenset(["n_incident", "n_porous"])


def material_display_info() -> list[dict[str, Any]]:
    """Return APP-friendly metadata for every material in the library.

    Each entry includes display names, suitable layer roles, wavelength range,
    and the n/k values sampled at 550 nm (for UI preview).  Air is included as
    a synthetic entry even though it has no CSV file.
    """
    rows: list[dict[str, Any]] = []
    manifest = _load_manifest()
    manifest_by_id: dict[str, dict[str, Any]] = {
        canonical_material_name(str(m["material"])): m for m in manifest
    }

    ordered_ids = ["Air", "SiO2", "MgF2", "Al2O3", "TiO2", "Si", "Ag", "Au"]

    for mat_id in ordered_ids:
        meta = _MATERIAL_DISPLAY_META.get(mat_id, {})
        canon = canonical_material_name(mat_id)

        # Wavelength range
        if canon == "Air":
            lmin_nm, lmax_nm = 100.0, 100_000.0
            n_550, k_550 = 1.0, 0.0
        else:
            mf = manifest_by_id.get(canon, {})
            lmin_nm = float(mf.get("lambda_min_um", 0.0)) * 1000.0
            lmax_nm = float(mf.get("lambda_max_um", 0.0)) * 1000.0
            # Sample n/k at 550 nm; fall back gracefully if out of range
            try:
                n_arr, k_arr = material_nk_at(mat_id, 0.550, allow_extrapolate=True)
                n_550 = float(np.asarray(n_arr).flat[0])
                k_550 = float(np.asarray(k_arr).flat[0])
            except Exception:
                n_550, k_550 = float("nan"), float("nan")

        rows.append({
            "id": mat_id,
            "display_name": meta.get("display_name", mat_id),
            "display_name_en": meta.get("display_name_en", mat_id),
            "category": meta.get("category", "未知"),
            "suitable_roles": meta.get("suitable_roles", []),
            "locked_roles": meta.get("locked_roles", []),
            "lambda_min_nm": round(lmin_nm, 1),
            "lambda_max_nm": round(lmax_nm, 1),
            "n_at_550nm": round(n_550, 4),
            "k_at_550nm": round(k_550, 6),
        })
    return rows


def get_material_roles_for_design(design_type: str) -> dict[str, Any]:
    """Return the role picker schema for one design type.

    The returned dict describes which material roles are active for this design,
    what options are available for each role, which roles are locked, and the
    recommended default material.

    This is the primary entry point for building the APP material-selection UI.
    """
    key = str(design_type).strip().lower()
    role_list = _DESIGN_ROLE_MAP.get(key, ["n_incident", "n_low", "n_high", "n_substrate"])

    # Build role → eligible material list
    all_info = {row["id"]: row for row in material_display_info()}

    # Default material choices per role
    role_defaults: dict[str, str] = {
        "n_incident":  "Air",
        "n_substrate": "SiO2",
        "n_low":       "MgF2",
        "n_mid":       "Al2O3",
        "n_high":      "TiO2",
        "n_high_2":    "Si",
        "n_porous":    "Air",   # porous layer handled internally
    }

    roles_out: dict[str, Any] = {}
    for role in role_list:
        eligible = [
            mid for mid, info in all_info.items()
            if role in info["suitable_roles"]
        ]
        locked = role in _LOCKED_ROLES
        default = role_defaults.get(role, eligible[0] if eligible else "")
        roles_out[role] = {
            "label": ROLE_LABELS_CN.get(role, role),
            "options": eligible,
            "default": default,
            "locked": locked,
        }

    return {
        "design_type": key,
        "roles": roles_out,
    }

