r"""Minimal PyThinFilm-to-Optiland integration proof of concept.

This script deliberately lives outside the production ``thinfilm`` package.  It
converts a small, JSON-like layer-stack description into an Optiland
``ThinFilmCoating``, attaches it to a simple imaging lens, traces rays and
exports numerical results that a Web/Three.js client can consume.

Run with the Python environment created in the sibling Optiland checkout::

    ..\optiland\.venv\Scripts\python.exe experiments\optiland_poc.py
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


DEFAULT_STACK: dict[str, Any] = {
    "name": "PyThinFilm-style Air/(H/L)^2/BK7 demo",
    "incident": {"kind": "ideal", "name": "Air", "n": 1.0, "k": 0.0},
    "substrate": {"kind": "ideal", "name": "BK7-demo", "n": 1.52, "k": 0.0},
    "layers": [
        {"name": "H1", "kind": "ideal", "n": 2.30, "k": 0.0, "thickness_nm": 59.78},
        {"name": "L1", "kind": "ideal", "n": 1.46, "k": 0.0, "thickness_nm": 94.18},
        {"name": "H2", "kind": "ideal", "n": 2.30, "k": 0.0, "thickness_nm": 59.78},
        {"name": "L2", "kind": "ideal", "n": 1.46, "k": 0.0, "thickness_nm": 94.18},
    ],
}


def _json_ready(value: Any) -> Any:
    """Convert arrays, numpy scalars and complex values to JSON-safe data."""
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _load_optiland(optiland_root: Path) -> dict[str, Any]:
    """Import the small Optiland API surface used by the PoC."""
    root = optiland_root.resolve()
    if not (root / "optiland" / "__init__.py").is_file():
        raise FileNotFoundError(f"Optiland source checkout not found: {root}")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import optiland.backend as be
    from optiland.analysis import RayFan, SpotDiagram
    from optiland.coatings import ThinFilmCoating
    from optiland.materials import IdealMaterial, Material
    from optiland.optic import Optic
    from optiland.rays import PolarizationState

    return {
        "be": be,
        "IdealMaterial": IdealMaterial,
        "Material": Material,
        "Optic": Optic,
        "PolarizationState": PolarizationState,
        "RayFan": RayFan,
        "SpotDiagram": SpotDiagram,
        "ThinFilmCoating": ThinFilmCoating,
    }


def _material_from_spec(spec: dict[str, Any], api: dict[str, Any]) -> Any:
    """Translate a PyThinFilm-style material record to an Optiland material."""
    kind = spec.get("kind", "ideal")
    if kind == "ideal":
        return api["IdealMaterial"](n=float(spec["n"]), k=float(spec.get("k", 0.0)))
    if kind == "catalog":
        return api["Material"](
            spec["name"],
            reference=spec.get("reference"),
            catalog=spec.get("catalog"),
        )
    raise ValueError(f"Unsupported material kind: {kind!r}")


def build_coating(
    stack_spec: dict[str, Any], api: dict[str, Any]
) -> tuple[Any, Any, Any]:
    """Build an Optiland ThinFilmCoating from a serializable stack spec."""
    incident = _material_from_spec(stack_spec["incident"], api)
    substrate = _material_from_spec(stack_spec["substrate"], api)
    layers = []
    for layer in stack_spec["layers"]:
        layers.append(
            (
                _material_from_spec(layer, api),
                float(layer["thickness_nm"]),
                layer.get("name"),
            )
        )
    coating = api["ThinFilmCoating"](incident, substrate, layers)
    return incident, substrate, coating


def build_minimal_system(
    stack_spec: dict[str, Any], api: dict[str, Any]
) -> tuple[Any, Any]:
    """Create Object -> coated singlet -> Image Plane."""
    incident, substrate, coating = build_coating(stack_spec, api)
    optic = api["Optic"](name="PyThinFilm Optiland PoC")
    optic.surfaces.add(index=0, radius=np.inf, thickness=np.inf, material=incident)
    optic.surfaces.add(
        index=1,
        radius=40.0,
        thickness=4.0,
        material=substrate,
        is_stop=True,
        coating=coating,
    )
    optic.surfaces.add(index=2, radius=-40.0, thickness=40.0, material=incident)
    optic.surfaces.add(index=3, material=incident)
    optic.set_aperture(aperture_type="EPD", value=10.0)
    optic.fields.set_type(field_type="angle")
    optic.fields.add(y=0.0)
    optic.wavelengths.add(value=0.55, is_primary=True)
    optic.updater.set_polarization(api["PolarizationState"](is_polarized=False))
    return optic, coating


def _surface_payload(optic: Any, api: dict[str, Any]) -> list[dict[str, Any]]:
    """Export the optical surfaces without coupling to Optiland's renderer."""
    be = api["be"]
    vertices = be.to_numpy(optic.surfaces.vertices_gcs)
    payload = []
    for index, surface in enumerate(optic.surfaces):
        geometry = surface.geometry
        payload.append(
            {
                "index": index,
                "type": surface.__class__.__name__,
                "surface_type": surface.surface_type,
                "vertex_mm": vertices[index].tolist(),
                "radius_mm": float(be.to_numpy(geometry.radius)),
                "thickness_to_next_mm": _json_ready(float(surface.thickness)),
                "is_stop": bool(surface.is_stop),
                "material_post": surface.material_post.to_dict(),
                "geometry": geometry.to_dict(),
            }
        )
    return payload


def _ray_payload(optic: Any, api: dict[str, Any]) -> list[dict[str, Any]]:
    """Export one polyline per sequential ray using recorded surface snapshots."""
    be = api["be"]
    coords = np.stack(
        [
            be.to_numpy(optic.surfaces.x),
            be.to_numpy(optic.surfaces.y),
            be.to_numpy(optic.surfaces.z),
        ],
        axis=-1,
    )
    directions = np.stack(
        [
            be.to_numpy(optic.surfaces.L),
            be.to_numpy(optic.surfaces.M),
            be.to_numpy(optic.surfaces.N),
        ],
        axis=-1,
    )
    intensities = be.to_numpy(optic.surfaces.intensity)
    paths = []
    for ray_index in range(coords.shape[1]):
        paths.append(
            {
                "ray_index": ray_index,
                "points_mm": coords[:, ray_index, :].tolist(),
                "directions": directions[:, ray_index, :].tolist(),
                "intensity_by_surface": intensities[:, ray_index].tolist(),
            }
        )
    return paths


def _save_3d_png(optic: Any, output_path: Path) -> None:
    """Render the Optiland VTK scene off-screen without starting a GUI loop."""
    import vtk
    from optiland.visualization import OpticViewer3D

    viewer = OpticViewer3D(optic)
    renderer = viewer._make_renderer(dark_mode=False)
    viewer.ren_win.SetOffScreenRendering(1)
    viewer.ren_win.AddRenderer(renderer)
    viewer.rays.plot(
        renderer,
        fields="all",
        wavelengths="primary",
        num_rays=12,
        distribution="ring",
    )
    viewer.system.plot(renderer)
    viewer.ren_win.SetSize(1000, 650)
    renderer.GetActiveCamera().SetPosition(1, 0, 0)
    renderer.GetActiveCamera().SetFocalPoint(0, 0, 0)
    renderer.GetActiveCamera().SetViewUp(0, 1, 0)
    renderer.ResetCamera()
    renderer.GetActiveCamera().Azimuth(150)
    viewer.ren_win.Render()

    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(viewer.ren_win)
    capture.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(output_path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    viewer.ren_win.Finalize()


def run_poc(optiland_root: Path, output_dir: Path) -> Path:
    """Run the minimal integration and return the generated JSON path."""
    api = _load_optiland(optiland_root)
    be = api["be"]
    output_dir.mkdir(parents=True, exist_ok=True)
    optic, coating = build_minimal_system(DEFAULT_STACK, api)

    wavelength_um = 0.55
    traced = optic.trace(
        Hx=0.0,
        Hy=0.0,
        wavelength=wavelength_um,
        num_rays=5,
        distribution="hexapolar",
    )
    mean_exit_ray_intensity = float(np.mean(be.to_numpy(traced.i)))
    rays = _ray_payload(optic, api)

    spot = api["SpotDiagram"](
        optic,
        fields=[(0.0, 0.0)],
        wavelengths=[wavelength_um],
        num_rings=5,
    )
    spot_data = spot.data[0][0]
    spot_payload = {
        "x_mm": be.to_numpy(spot_data.x),
        "y_mm": be.to_numpy(spot_data.y),
        "intensity": be.to_numpy(spot_data.intensity),
    }

    ray_fan = api["RayFan"](
        optic,
        fields=[(0.0, 0.0)],
        wavelengths=[wavelength_um],
        num_points=33,
    )

    wavelengths_nm = np.linspace(450.0, 700.0, 101)
    spectrum_s = coating.stack.compute_rtRAT_nm_deg(wavelengths_nm, 0.0, "s")
    spectrum_p = coating.stack.compute_rtRAT_nm_deg(wavelengths_nm, 0.0, "p")
    center_s = coating.stack.compute_rtRAT_nm_deg([550.0], [0.0], "s")
    center_p = coating.stack.compute_rtRAT_nm_deg([550.0], [0.0], "p")
    coating_power_transmission = 0.5 * (
        float(be.to_numpy(center_s["T"])[0, 0])
        + float(be.to_numpy(center_p["T"])[0, 0])
    )

    layout_path = output_dir / "minimal_system_2d.png"
    layout_svg_path = output_dir / "minimal_system_2d.svg"
    fig, _ = optic.draw(num_rays=5, show=False, figsize=(10, 4))
    fig.savefig(layout_path, dpi=160, bbox_inches="tight")
    fig.savefig(layout_svg_path, bbox_inches="tight")

    spot_path = output_dir / "spot_diagram.png"
    spot_fig, _ = spot.view(show=False)
    spot_fig.savefig(spot_path, dpi=160, bbox_inches="tight")

    layout_3d_path = output_dir / "minimal_system_3d.png"
    three_d_error = None
    try:
        _save_3d_png(optic, layout_3d_path)
    except Exception as exc:  # VTK support is platform/driver dependent.
        three_d_error = f"{type(exc).__name__}: {exc}"

    result = {
        "schema_version": "0.1.0-poc",
        "source": {
            "pythinfilm_project": str(Path(__file__).resolve().parents[1]),
            "optiland_project": str(optiland_root.resolve()),
            "optiland_commit": "17610805",
        },
        "units": {"length": "mm", "wavelength": "um", "spectrum_wavelength": "nm"},
        "input_layer_stack": DEFAULT_STACK,
        "system": {
            "name": optic.name,
            "wavelength_um": wavelength_um,
            "surfaces": _surface_payload(optic, api),
        },
        "system_transmission": {
            "coating_power_transmittance_at_550nm_normal_incidence": (
                coating_power_transmission
            ),
            "mean_exit_ray_field_intensity": mean_exit_ray_intensity,
            "definition": (
                "Power T comes from ThinFilmStack and includes optical-admittance "
                "normalization. The traced ray value is the final Jones-field norm "
                "and must not be presented as power throughput without normalization."
            ),
        },
        "ray_paths": rays,
        "spot": spot_payload,
        "ray_fan": ray_fan.data,
        "coating_spectrum": {
            "wavelength_nm": wavelengths_nm,
            "s": spectrum_s,
            "p": spectrum_p,
        },
        "polarization": {
            "final_ray_jones_transform": getattr(traced, "p", None),
            "note": "Optiland exposes the final per-ray 3x3 polarization transform; per-surface Jones snapshots are not recorded.",
        },
        "artifacts": {
            "layout_2d_png": str(layout_path),
            "layout_2d_svg": str(layout_svg_path),
            "spot_png": str(spot_path),
            "layout_3d_png": str(layout_3d_path) if layout_3d_path.exists() else None,
            "layout_3d_error": three_d_error,
        },
    }

    result_path = output_dir / "optiland_poc_result.json"
    result_path.write_text(
        json.dumps(_json_ready(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result_path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--optiland-root",
        type=Path,
        default=project_root.parent / "optiland",
        help="Path to the local Optiland source checkout.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "thinfilm_outputs" / "optiland_poc",
        help="Directory for JSON and PNG artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    result_path = run_poc(args.optiland_root, args.output_dir)
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
