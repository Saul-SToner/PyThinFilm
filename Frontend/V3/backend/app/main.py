from __future__ import annotations

import math
import os
import sys
import csv
import json
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


APP_ROOT = Path(os.environ.get("THINFILM_APP_ROOT", Path(__file__).resolve().parents[2]))


def _default_pythinfilm_root() -> Path:
    """Prefer the outer source tree; packaged builds provide a resource copy."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    source_root = APP_ROOT.parents[1] if len(APP_ROOT.parents) > 1 else APP_ROOT
    if (source_root / "thinfilm" / "api.py").exists():
        return source_root
    return APP_ROOT / "PyThinFilm"


PYTHINFILM_ROOT = Path(os.environ.get("THINFILM_PYTHINFILM_ROOT", _default_pythinfilm_root()))
OUTPUTS_DIR = Path(os.environ.get("THINFILM_OUTPUT_DIR", APP_ROOT / "backend" / "outputs"))
MATERIALS_METADATA_FILENAME = "app_materials_metadata.csv"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
os.environ["THINFILM_OUTPUT_DIR"] = str(OUTPUTS_DIR)
os.environ.setdefault("MPLBACKEND", "Agg")

OPTILAND_OUTPUT_DIR = OUTPUTS_DIR / "optiland_real_material_ar_comparison"
OPTILAND_RESULT_PATH = OPTILAND_OUTPUT_DIR / "comparison_result.json"
_OPTILAND_LOCK = threading.Lock()
OPTILAND_LIVE_OUTPUT_DIR = OUTPUTS_DIR / "optiland_live_draft"
_OPTILAND_LIVE_LOCK = threading.Lock()

if str(PYTHINFILM_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHINFILM_ROOT))

from thinfilm import api as thinfilm_api  # noqa: E402
from thinfilm import education as thinfilm_education  # noqa: E402
from thinfilm.plotting import add_panel_labels  # noqa: E402

from .design_service import simulate_design  # noqa: E402
from .ai_qa import AskResultRequest, prepare_result_request, stream_result_answer  # noqa: E402
from .schemas import DesignSimulationRequest  # noqa: E402
from .case_catalog_service import build_case_catalog, load_case_detail  # noqa: E402
from .case_release import app_catalog  # noqa: E402
from .case_acceptance_service import build_case_acceptance_matrix  # noqa: E402
from .external_evidence_service import import_template, validate_comsol_csv  # noqa: E402
from .tmmcore_service import tmmcore_runtime_status, simulate_teaching_case_with_tmmcore  # noqa: E402
from thinfilm.solvers import specialist_solver_status  # noqa: E402
from thinfilm.solvers.rcwa_adapter import sweep_periodic_stack  # noqa: E402
from thinfilm.solvers.generaltmm_adapter import (  # noqa: E402
    multilayer_field_comparison as native_field_comparison,
    sweep_interface as native_sweep_interface,
    sweep_multilayer as native_sweep_multilayer,
)
from . import packaged_tamm  # noqa: E402
from thinfilm.solvers.wptherml_adapter import spectrum as wptherml_spectrum  # noqa: E402


class SimulationRequest(BaseModel):
    case_id: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    export_files: bool = True


class OptilandDraftRequest(BaseModel):
    draft: dict[str, Any] = Field(...)


class RcwaSweepRequest(BaseModel):
    wavelength_start_um: float = Field(0.4, gt=0)
    wavelength_stop_um: float = Field(0.8, gt=0)
    wavelength_points: int = Field(81, ge=2, le=2001)
    period_um: float = Field(0.7, gt=0)
    thickness_um: float = Field(0.2, gt=0)
    n_grating: float = Field(2.0, gt=0)
    n_void: float = Field(1.0, gt=0)
    harmonics: int = Field(11, ge=3, le=101)


class GeneralTmmSweepRequest(BaseModel):
    case_id: str | None = None
    wavelength_start_nm: float = Field(450, gt=0)
    wavelength_stop_nm: float = Field(750, gt=0)
    wavelength_points: int = Field(81, ge=2, le=1001)
    n_incident: float = Field(1.5, gt=0)
    n_layer: float = Field(2.0, gt=0)
    n_substrate: float = Field(1.0, gt=0)
    thickness_nm: float = Field(100, gt=0)
    beta: float = Field(0.0, ge=0, le=0.99)
    polarization: str = Field("p", pattern="^(p|s)$")
    ag_thickness_nm: float = Field(30.0, ge=5.0, le=150.0)
    dbr_periods: int = Field(3, ge=1, le=8)


class WPThermlSweepRequest(BaseModel):
    case_id: str | None = None
    wavelength_start_nm: float = Field(400, gt=0)
    wavelength_stop_nm: float = Field(20000, gt=0)
    wavelength_points: int = Field(121, ge=2, le=2001)
    thickness_nm: float = Field(100, gt=0)
    temperature_k: float = Field(300, gt=0)


class ExternalEvidenceCsvRequest(BaseModel):
    case_id: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    csv_text: str = Field(..., min_length=1)


class MaterialIndexRequest(BaseModel):
    material_id: str = Field(..., min_length=1)
    wavelength_nm: float = Field(..., gt=0)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    port: int
    outputs_dir: str


app = FastAPI(title="Thin-Film Simulation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")


HIDDEN_OUTPUT_FILE_KEYS = {"analysis_png"}


def _save_app_png_figure(
    fig: Any,
    png_path: str | Path,
    *,
    dpi: int = 300,
    max_width_in: float | None = 7.2,
    add_labels: bool = True,
    close: bool = False,
) -> dict[str, str]:
    """Save only the PNG images consumed by the desktop app."""
    import matplotlib.pyplot as plt

    path = Path(png_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if max_width_in is not None:
        width, height = fig.get_size_inches()
        if width > max_width_in:
            scale = max_width_in / width
            fig.set_size_inches(max_width_in, min(height * scale, 7.8), forward=True)
    if add_labels:
        add_panel_labels(fig)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    if close:
        plt.close(fig)
    return {"png": str(path)}


thinfilm_education.save_publication_figure = _save_app_png_figure


def _cleanup_hidden_output_file(path: str | Path) -> None:
    output_path = Path(path)
    for suffix in (".png", ".svg", ".pdf"):
        candidate = output_path.with_suffix(suffix)
        try:
            candidate.unlink(missing_ok=True)
        except OSError:
            pass


def _visible_exported_files(exported: dict[str, str]) -> dict[str, str]:
    visible: dict[str, str] = {}
    for key, value in exported.items():
        if key in HIDDEN_OUTPUT_FILE_KEYS:
            _cleanup_hidden_output_file(value)
            continue
        visible[key] = value
    return visible


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return _jsonable(value.tolist())
    if hasattr(value, "item"):
        return _jsonable(value.item())
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return str(value)


def _cases_by_id() -> dict[str, dict[str, Any]]:
    return {case["case_id"]: case for case in thinfilm_api.list_teaching_cases()}


def _split_roles(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def _candidate_materials_metadata_paths() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("THINFILM_MATERIALS_METADATA_CSV")
    if env_path:
        candidates.append(Path(env_path))

    candidates.extend(
        [
            APP_ROOT / "materials" / MATERIALS_METADATA_FILENAME,
            APP_ROOT / "resources" / "materials" / MATERIALS_METADATA_FILENAME,
            APP_ROOT / "frontend" / "src" / "assets" / "materials" / MATERIALS_METADATA_FILENAME,
            Path.cwd() / "materials" / MATERIALS_METADATA_FILENAME,
            Path.cwd().parent / "materials" / MATERIALS_METADATA_FILENAME,
            Path(sys.executable).resolve().parent / "materials" / MATERIALS_METADATA_FILENAME,
            Path(sys.executable).resolve().parent.parent / "materials" / MATERIALS_METADATA_FILENAME,
        ]
    )

    pyinstaller_root = getattr(sys, "_MEIPASS", None)
    if pyinstaller_root:
        candidates.append(Path(pyinstaller_root) / "materials" / MATERIALS_METADATA_FILENAME)

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate)
        if normalized not in seen:
            unique.append(candidate)
            seen.add(normalized)
    return unique


def _materials_metadata_csv() -> Path:
    candidates = _candidate_materials_metadata_paths()
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = "; ".join(str(candidate) for candidate in candidates)
    raise HTTPException(status_code=500, detail=f"Material metadata file not found. Searched: {searched}")


def _material_rows() -> list[dict[str, Any]]:
    materials_metadata_csv = _materials_metadata_csv()

    rows: list[dict[str, Any]] = []
    with open(materials_metadata_csv, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "material_id": str(row["material_id"]),
                    "display_name_zh": str(row["display_name_zh"]),
                    "display_name_en": str(row["display_name_en"]),
                    "category": str(row["category"]),
                    "suitable_roles": _split_roles(str(row.get("suitable_roles", ""))),
                    "locked_roles": _split_roles(str(row.get("locked_roles", ""))),
                    "lambda_min_nm": float(row["lambda_min_nm"]),
                    "lambda_max_nm": float(row["lambda_max_nm"]),
                    "n_at_550nm": float(row["n_at_550nm"]),
                    "k_at_550nm": float(row["k_at_550nm"]),
                }
            )
    return rows


def _material_by_id(material_id: str) -> dict[str, Any]:
    for row in _material_rows():
        if row["material_id"] == material_id:
            return row
    raise HTTPException(status_code=404, detail=f"Unsupported material_id: {material_id}")


def _sellmeier_n(wavelength_nm: float, terms: list[tuple[float, float]]) -> float:
    wavelength_um = float(wavelength_nm) / 1000.0
    lambda_sq = wavelength_um * wavelength_um
    n_sq = 1.0
    for b_i, c_i in terms:
        denominator = lambda_sq - c_i
        if abs(denominator) < 1e-15:
            raise ValueError("wavelength is too close to a Sellmeier resonance.")
        n_sq += b_i * lambda_sq / denominator
    if n_sq <= 0:
        raise ValueError("Sellmeier formula produced non-positive n^2.")
    return math.sqrt(n_sq)


def _calculate_material_index(material: dict[str, Any], wavelength_nm: float) -> dict[str, Any]:
    material_id = str(material["material_id"])
    min_nm = float(material["lambda_min_nm"])
    max_nm = float(material["lambda_max_nm"])
    in_range = min_nm <= float(wavelength_nm) <= max_nm

    try:
        if material_id == "N-BK7":
            n_val = _sellmeier_n(
                wavelength_nm,
                [
                    (1.03961212, 0.00600069867),
                    (0.231792344, 0.0200179144),
                    (1.01046945, 103.560653),
                ],
            )
            return {"n": n_val, "k": 0.0, "method": "Sellmeier 解析公式", "in_range": in_range}
        if material_id == "Ta2O5":
            n_val = _sellmeier_n(wavelength_nm, [(3.109, 0.033)])
            return {"n": n_val, "k": 0.0, "method": "Sellmeier 解析公式", "in_range": in_range}
        if material_id == "ZrO2":
            n_val = _sellmeier_n(wavelength_nm, [(2.92, 0.026)])
            return {"n": n_val, "k": 0.0, "method": "Sellmeier 解析公式", "in_range": in_range}

        try:
            n_vals, k_vals = thinfilm_api.material_nk_at(
                material_id,
                float(wavelength_nm) / 1000.0,
                allow_extrapolate=False,
            )
            return {
                "n": float(n_vals),
                "k": float(k_vals),
                "method": "离散 nk 数据线性插值",
                "in_range": True,
            }
        except Exception:
            return {
                "n": float(material["n_at_550nm"]),
                "k": float(material["k_at_550nm"]),
                "method": "550 nm 参考值（未提供可插值 nk 数据）",
                "in_range": in_range,
            }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _coerce_param(name: str, raw_value: Any, default_value: Any) -> Any:
    if isinstance(default_value, bool):
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, str):
            normalized = raw_value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        raise ValueError(f"Parameter '{name}' must be a boolean.")

    if isinstance(default_value, int) and not isinstance(default_value, bool):
        if isinstance(raw_value, bool):
            raise ValueError(f"Parameter '{name}' must be an integer.")
        try:
            return int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Parameter '{name}' must be an integer.") from exc

    if isinstance(default_value, float):
        if isinstance(raw_value, bool):
            raise ValueError(f"Parameter '{name}' must be a number.")
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Parameter '{name}' must be a number.") from exc
        if not math.isfinite(value):
            raise ValueError(f"Parameter '{name}' must be finite.")
        return value

    if isinstance(default_value, str):
        value = str(raw_value)
        if name == "pol" and value not in {"s", "p"}:
            raise ValueError("Parameter 'pol' must be 's' or 'p'.")
        return value

    return raw_value


def _validated_params(case: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    defaults = case.get("default_params", {})
    unknown = sorted(set(params) - set(defaults))
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown parameter(s) for case '{case['case_id']}': {', '.join(unknown)}",
        )

    converted: dict[str, Any] = {}
    for key, value in params.items():
        try:
            converted[key] = _coerce_param(key, value, defaults[key])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return converted


def _output_url(path_value: str) -> str:
    path = Path(path_value).resolve()
    try:
        relative_path = path.relative_to(OUTPUTS_DIR.resolve())
    except ValueError:
        return path_value
    return "/outputs/" + relative_path.as_posix()


def _optiland_configuration() -> tuple[Path, Path, Path]:
    """Resolve the optional Optiland checkout, Python runtime and experiment."""
    project_checkout = PYTHINFILM_ROOT / "optiland"
    local_checkout = (project_checkout / "optiland" / "__init__.py").is_file()
    default_root = project_checkout if local_checkout else PYTHINFILM_ROOT.parent / "optiland"
    optiland_root = Path(
        os.environ.get("THINFILM_OPTILAND_ROOT", str(default_root))
    ).resolve()
    python_value = os.environ.get(
        "THINFILM_OPTILAND_PYTHON",
        sys.executable if local_checkout and optiland_root == project_checkout.resolve()
        else str(optiland_root / ".venv" / "Scripts" / "python.exe"),
    )
    python_path = Path(python_value).resolve()
    script_path = PYTHINFILM_ROOT / "experiments" / "optiland_real_material_ar_comparison.py"
    return optiland_root, python_path, script_path


def _optiland_public_result() -> dict[str, Any]:
    """Generate once, then expose only the compact data needed by the renderer."""
    optiland_root, python_path, script_path = _optiland_configuration()
    if not script_path.is_file():
        return {
            "available": False,
            "ready": False,
            "error": f"Optiland 实验脚本不存在：{script_path}",
        }
    if not optiland_root.joinpath("optiland", "__init__.py").is_file():
        return {
            "available": False,
            "ready": False,
            "error": f"未找到 Optiland 源码目录：{optiland_root}",
        }
    if not python_path.is_file():
        return {
            "available": False,
            "ready": False,
            "error": f"未找到 Optiland Python 环境：{python_path}",
        }

    with _OPTILAND_LOCK:
        if not OPTILAND_RESULT_PATH.is_file():
            OPTILAND_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            command = [
                str(python_path),
                *(["--optiland-comparison"] if getattr(sys, "frozen", False) else [str(script_path)]),
                "--optiland-root",
                str(optiland_root),
                "--output-dir",
                str(OPTILAND_OUTPUT_DIR),
            ]
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(PYTHINFILM_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=180,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return {
                    "available": False,
                    "ready": False,
                    "error": f"Optiland 结果生成失败：{type(exc).__name__}: {exc}",
                }
            if completed.returncode != 0 or not OPTILAND_RESULT_PATH.is_file():
                detail = (completed.stderr or completed.stdout or "无额外输出").strip()[-1200:]
                return {
                    "available": False,
                    "ready": False,
                    "error": f"Optiland 结果生成失败（退出码 {completed.returncode}）：{detail}",
                }

        try:
            payload = json.loads(OPTILAND_RESULT_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "available": False,
                "ready": False,
                "error": f"Optiland 结果读取失败：{type(exc).__name__}: {exc}",
            }

    artifacts = {
        key: _output_url(str(path))
        for key, path in (payload.get("artifacts") or {}).items()
        if path and Path(str(path)).is_file()
    }
    return {
        "available": True,
        "ready": True,
        "schema_version": payload.get("schema_version"),
        "scope": payload.get("scope", {}),
        "design": payload.get("design", {}),
        "metrics": payload.get("metrics", {}),
        "checks": payload.get("checks", {}),
        "interpretation": payload.get("interpretation", ""),
        "artifacts": artifacts,
    }


def _optiland_live_draft_result(draft: dict[str, Any]) -> dict[str, Any]:
    """Render the current editor draft through the optional Optiland process."""
    if draft.get("system_template") in {"folded_reflector", "laser_expander", "dbr_laser_cavity", "dual_path_beamsplitter"}:
        try:
            angle = float(draft.get("angle_deg", 45))
        except (TypeError, ValueError):
            angle = float("nan")
        if not math.isfinite(angle) or not 0 <= angle <= 60:
            return {"available": False, "ready": False, "error": "反射/分光基线支持 0–60° 入射，请调整入射角后重试。"}
    optiland_root, python_path, script_path = _optiland_configuration()
    live_script = PYTHINFILM_ROOT / "experiments" / "optiland_draft_render.py"
    if not live_script.is_file():
        return {"available": False, "ready": False, "error": f"Optiland 实时脚本不存在：{live_script}"}
    if not optiland_root.joinpath("optiland", "__init__.py").is_file():
        return {"available": False, "ready": False, "error": f"未找到 Optiland 源码目录：{optiland_root}"}
    if not python_path.is_file():
        return {"available": False, "ready": False, "error": f"未找到 Optiland Python 环境：{python_path}"}

    with _OPTILAND_LIVE_LOCK:
        render_dir = OPTILAND_LIVE_OUTPUT_DIR / uuid.uuid4().hex
        render_dir.mkdir(parents=True, exist_ok=True)
        result_path = render_dir / 'comparison_result.json'
        draft_path = render_dir / 'draft.json'
        draft_path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
        command = [
            str(python_path),
            *(["--optiland-render"] if getattr(sys, "frozen", False) else [str(live_script)]),
            "--optiland-root",
            str(optiland_root),
            "--output-dir",
            str(render_dir),
            "--draft-json",
            str(draft_path),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(PYTHINFILM_ROOT),
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"available": False, "ready": False, "error": f"Optiland 实时更新失败：{type(exc).__name__}: {exc}"}
        finally:
            draft_path.unlink(missing_ok=True)
        if completed.returncode != 0 or not result_path.is_file():
            diagnostic = (completed.stderr or completed.stdout or "无额外输出").strip()
            (render_dir / "error.log").write_text(diagnostic, encoding="utf-8")
            detail = diagnostic.splitlines()[-1][:400]
            if detail.startswith("ValueError: "):
                detail = detail[len("ValueError: "):]
            return {"available": False, "ready": False, "error": f"Optiland 实时更新失败（退出码 {completed.returncode}）：{detail}"}
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {"available": False, "ready": False, "error": f"Optiland 实时结果读取失败：{type(exc).__name__}: {exc}"}

    # Every request owns immutable image URLs; later drafts cannot overwrite
    # files while the browser is still fetching an earlier result.
    artifacts = {
        key: _output_url(str(path))
        for key, path in (payload.get("artifacts") or {}).items()
        if path and Path(str(path)).is_file()
    }
    return {
        "available": True,
        "ready": True,
        "draft": payload.get("draft", draft),
        "system_template": payload.get("system_template", draft.get("system_template", "single_lens_imaging")),
        "system_family": payload.get("system_family", "baseline"),
        "branch_analysis": payload.get("branch_analysis"),
        "sampling": payload.get("sampling", {}),
        "analysis_conditions": payload.get("analysis_conditions", {}),
        "metrics": payload.get("metrics", {}),
        "analysis_groups": payload.get("analysis_groups", {}),
        "ghost_stray": payload.get("ghost_stray", {}),
        "spectrum_color": payload.get("spectrum_color", {}),
        "artifacts": artifacts,
        "material_sources": payload.get("material_sources", []),
        "interpretation": payload.get("interpretation", ""),
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", port=8122, outputs_dir=str(OUTPUTS_DIR))


@app.get("/api/diagnostics")
def diagnostics() -> dict[str, Any]:
    materials_candidates = _candidate_materials_metadata_paths()
    return _jsonable(
        {
            "app_root": APP_ROOT,
            "pythinfilm_root": PYTHINFILM_ROOT,
            "outputs_dir": OUTPUTS_DIR,
            "materials_metadata_csv": next((path for path in materials_candidates if path.exists()), None),
            "materials_candidates": [
                {"path": path, "exists": path.exists()}
                for path in materials_candidates
            ],
            "tmmcore": tmmcore_runtime_status(APP_ROOT),
            "specialist_solvers": specialist_solver_status(),
        }
    )


@app.get("/api/optiland/comparison")
def get_optiland_comparison() -> dict[str, Any]:
    """Return the cached/generated native Optiland comparison for the workspace."""
    return _jsonable(_optiland_public_result())


@app.post("/api/optiland/system")
def render_optiland_system(request: OptilandDraftRequest) -> dict[str, Any]:
    """Rebuild the Optiland system from the current free-design draft."""
    return _jsonable(_optiland_live_draft_result(request.draft))


@app.post("/api/specialist/rcwa")
def run_rcwa_sweep(request: RcwaSweepRequest) -> dict[str, Any]:
    """Run the optional real RCWA backend for a 1D rectangular grating."""
    if request.wavelength_stop_um <= request.wavelength_start_um:
        raise HTTPException(status_code=422, detail="wavelength_stop_um must exceed wavelength_start_um")
    import numpy as np

    wavelengths = np.linspace(request.wavelength_start_um, request.wavelength_stop_um, request.wavelength_points).tolist()
    try:
        return _jsonable(sweep_periodic_stack(
            wavelengths_um=wavelengths,
            period_um=request.period_um,
            thickness_um=request.thickness_um,
            n_grating=request.n_grating,
            n_void=request.n_void,
            harmonics=request.harmonics,
        ))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _generaltmm_call(method: str, **arguments: Any) -> dict[str, Any]:
    if getattr(sys, "frozen", False):
        return getattr(packaged_tamm, method)(**arguments)
    native_methods = {
        "sweep_multilayer": native_sweep_multilayer,
        "multilayer_field_comparison": native_field_comparison,
        "sweep_interface": native_sweep_interface,
    }
    return native_methods[method](**arguments)


@app.post("/api/specialist/generaltmm")
def run_generaltmm_sweep(request: GeneralTmmSweepRequest) -> dict[str, Any]:
    if request.wavelength_stop_nm <= request.wavelength_start_nm:
        raise HTTPException(status_code=422, detail="wavelength_stop_nm must exceed wavelength_start_nm")
    import numpy as np

    try:
        wavelengths = np.linspace(request.wavelength_start_nm, request.wavelength_stop_nm, request.wavelength_points).tolist()
        if request.case_id and request.case_id.startswith("tamm_"):
            source = json.loads((PYTHINFILM_ROOT / "web3d" / "public" / "results" / "tamm_phase_bundle.json").read_text(encoding="utf-8-sig"))
            source_layers = source["layers"]
            metal = {**source_layers[0], "thickness_nm": request.ag_thickness_nm}
            high = source_layers[1]
            low = source_layers[2]
            layers = [metal, *[layer for _ in range(request.dbr_periods) for layer in (high, low)], high]
            layer_indices = [complex(float(layer["n_real"]), float(layer.get("n_imag", 0.0))) for layer in layers]
            layer_thicknesses = [float(layer["thickness_nm"]) for layer in layers]
            result = _generaltmm_call("sweep_multilayer",
                wavelengths_nm=wavelengths,
                n_incident=complex(float(source["ambient"]["n"])),
                layer_indices=layer_indices,
                layer_thickness_nm=layer_thicknesses,
                n_substrate=complex(float(source["substrate"]["n"])),
                beta=request.beta,
            )
            result["case_id"] = request.case_id
            result["materials"] = [str(layer["type"]) for layer in layers]
            result["experiment_params"] = {
                "ag_thickness_nm": request.ag_thickness_nm,
                "dbr_periods": request.dbr_periods,
                "beta": request.beta,
                "polarization": request.polarization,
            }
            result["field_comparison"] = _generaltmm_call("multilayer_field_comparison",
                spectrum=result,
                n_incident=complex(float(source["ambient"]["n"])),
                layer_indices=layer_indices,
                layer_thickness_nm=layer_thicknesses,
                n_substrate=complex(float(source["substrate"]["n"])),
                beta=request.beta,
                polarization=request.polarization,
            )
            if request.case_id == "tamm_interface_priority":
                result["curves"] = [
                    {"label": "p 偏振反射率", "x": wavelengths, "y": result["R"]},
                    {"label": "s 偏振反射率", "x": wavelengths, "y": result["R_s"]},
                ]
                result["x_label"], result["y_label"] = "波长 (nm)", "反射率"
            elif request.case_id == "tamm_phase_bundle":
                result["curves"] = [
                    {"label": "p 偏振反射相位", "x": wavelengths, "y": result["phase_p_deg"]},
                    {"label": "s 偏振反射相位", "x": wavelengths, "y": result["phase_s_deg"]},
                ]
                result["x_label"], result["y_label"] = "波长 (nm)", "反射相位 (°)"
            elif request.case_id == "tamm_phase_candidates":
                suffix = "" if request.polarization == "p" else "_s"
                result["curves"] = [
                    {"label": f"{request.polarization} 偏振反射率", "x": wavelengths, "y": result[f"R{suffix}"]},
                    {"label": f"{request.polarization} 偏振吸收率", "x": wavelengths, "y": result[f"A{suffix}"]},
                ]
                result["x_label"], result["y_label"] = "候选波长 (nm)", "功率"
            elif request.case_id == "tamm_phase_focus":
                suffix = "" if request.polarization == "p" else "_s"
                result["curves"] = [{"label": f"{request.polarization} 偏振吸收率", "x": wavelengths, "y": result[f"A{suffix}"]}]
                result["x_label"], result["y_label"] = "波长 (nm)", "吸收率"
            elif request.case_id == "tamm_reflection_phase_screen":
                result["curves"] = [
                    {"label": "p 偏振相位", "x": wavelengths, "y": result["phase_p_deg"]},
                    {"label": "s 偏振相位", "x": wavelengths, "y": result["phase_s_deg"]},
                ]
                result["x_label"], result["y_label"] = "波长 (nm)", "反射相位 (°)"
            elif request.case_id == "tamm_interface_window_bundle":
                result["curves"] = [
                    {"label": "p 偏振界面窗口", "x": wavelengths, "y": result["R"]},
                    {"label": "s 偏振界面窗口", "x": wavelengths, "y": result["R_s"]},
                ]
                result["x_label"], result["y_label"] = "波长 (nm)", "反射率"
            elif request.case_id == "tamm_interface_window_scan":
                betas = np.linspace(0.0, 0.95, 41).tolist()
                center_nm = float((request.wavelength_start_nm + request.wavelength_stop_nm) / 2.0)
                channel = "R" if request.polarization == "p" else "R_s"
                scan_r = [_generaltmm_call("sweep_multilayer", wavelengths_nm=[center_nm], n_incident=complex(float(source["ambient"]["n"])), layer_indices=layer_indices, layer_thickness_nm=layer_thicknesses, n_substrate=complex(float(source["substrate"]["n"])), beta=beta)[channel][0] for beta in betas]
                result["curves"] = [{"label": f"{request.polarization} 偏振 {center_nm:.0f} nm 角度窗口", "x": betas, "y": scan_r}]
                result["x_label"], result["y_label"] = "归一化切向波矢 β", "反射率"
            suffix = "" if request.polarization == "p" else "_s"
            if request.case_id in {"tamm_phase_bundle", "tamm_reflection_phase_screen"}:
                comparison_y = result[f"phase_{request.polarization}_deg"]
                comparison_label = f"{request.polarization} 偏振反射相位"
            elif request.case_id in {"tamm_phase_candidates", "tamm_phase_focus"}:
                comparison_y = result[f"A{suffix}"]
                comparison_label = f"{request.polarization} 偏振吸收率"
            elif request.case_id == "tamm_interface_window_scan":
                result["comparison_curve"] = result["curves"][0]
                comparison_y = None
                comparison_label = ""
            else:
                comparison_y = result[f"R{suffix}"]
                comparison_label = f"{request.polarization} 偏振反射率"
            if comparison_y is not None:
                result["comparison_curve"] = {"label": comparison_label, "x": wavelengths, "y": comparison_y}
            return _jsonable(result)
        return _jsonable(_generaltmm_call("sweep_interface", wavelengths_nm=wavelengths, n_incident=request.n_incident, n_layer=request.n_layer, n_substrate=request.n_substrate, thickness_nm=request.thickness_nm, beta=request.beta))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/specialist/wptherml")
def run_wptherml_sweep(request: WPThermlSweepRequest) -> dict[str, Any]:
    if request.wavelength_stop_nm <= request.wavelength_start_nm:
        raise HTTPException(status_code=422, detail="wavelength_stop_nm must exceed wavelength_start_nm")
    import numpy as np

    try:
        materials = ["Air", "SiO2", "Air"]
        thickness_m = [0.0, request.thickness_nm * 1e-9, 0.0]
        if request.case_id == "pdrc_cooling_bundle":
            source = json.loads((PYTHINFILM_ROOT / "web3d" / "public" / "results" / "pdrc_cooling_bundle.json").read_text(encoding="utf-8-sig"))
            materials = ["Air", *[str(layer["material"]) for layer in source["layers"]], "Air"]
            thickness_m = [0.0, *[float(layer["thickness_nm"]) * 1e-9 for layer in source["layers"]], 0.0]
        result = wptherml_spectrum(
            materials=materials,
            thickness_m=thickness_m,
            wavelength_range_m=(request.wavelength_start_nm * 1e-9, request.wavelength_stop_nm * 1e-9, request.wavelength_points),
            temperature_k=request.temperature_k,
        )
        result["wavelength_nm"] = (np.asarray(result.pop("wavelength_m")) * 1e9).tolist()
        result["case_id"] = request.case_id
        result["materials"] = materials
        return _jsonable(result)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/cases")
def get_cases() -> list[dict[str, Any]]:
    return _jsonable(thinfilm_api.list_teaching_cases())


@app.get("/api/case-library")
def get_case_library(include_archived: bool = False) -> dict[str, Any]:
    try:
        catalog = build_case_catalog(PYTHINFILM_ROOT, APP_ROOT, thinfilm_api.list_teaching_cases())
        return _jsonable(catalog if include_archived else app_catalog(catalog))
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/case-acceptance")
def get_case_acceptance() -> dict[str, Any]:
    """Return the reproducible end-to-end acceptance matrix for all 40 cases."""
    try:
        return _jsonable(build_case_acceptance_matrix(PYTHINFILM_ROOT, APP_ROOT, thinfilm_api.list_teaching_cases()))
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/evidence/comsol-template/{case_id}")
def get_comsol_import_template(case_id: str) -> dict[str, Any]:
    try:
        return _jsonable(import_template(case_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/evidence/validate-comsol-csv")
def validate_external_comsol_csv(request: ExternalEvidenceCsvRequest) -> dict[str, Any]:
    try:
        return _jsonable(validate_comsol_csv(request.case_id, request.role, request.csv_text))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/case-library/{case_id}")
def get_case_library_detail(case_id: str) -> dict[str, Any]:
    try:
        return _jsonable(load_case_detail(PYTHINFILM_ROOT, APP_ROOT, thinfilm_api.list_teaching_cases(), case_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unsupported case_id: {case_id}") from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/catalog")
def get_catalog() -> dict[str, Any]:
    return _jsonable(thinfilm_api.get_teaching_main_branch_catalog())


@app.get("/api/materials")
def get_materials() -> list[dict[str, Any]]:
    return _jsonable(_material_rows())


@app.post("/api/material-index")
def get_material_index(request: MaterialIndexRequest) -> dict[str, Any]:
    material = _material_by_id(request.material_id)
    calculated = _calculate_material_index(material, request.wavelength_nm)
    return _jsonable(
        {
            **material,
            "wavelength_nm": float(request.wavelength_nm),
            **calculated,
        }
    )


@app.post("/api/simulations")
def run_simulation(request: SimulationRequest) -> dict[str, Any]:
    cases = _cases_by_id()
    case = cases.get(request.case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Unsupported case_id: {request.case_id}")

    params = _validated_params(case, request.params)
    try:
        core_cases = {
            "quarter_wave_single_layer", "half_wave_single_layer", "single_ar",
            "porous_sio2_layer", "double_ar", "quarter_wave_double_layer", "porous_double_ar",
            "triple_ar", "high_reflector", "quarter_wave_stack", "bragg_reflector", "fp_filter",
            "fp_double_halfwave", "narrowband_filter", "neutral_beamsplitter",
            "rugate_filter", "moth_eye_effective_gradient",
        }
        if request.case_id in core_cases:
            result = simulate_teaching_case_with_tmmcore(request.case_id, params, APP_ROOT)
        else:
            result = thinfilm_api.simulate_teaching_case(request.case_id, **params)
        files: dict[str, str] = {}
        if request.export_files:
            prefix = f"app_teaching_case_{request.case_id}"
            exported = thinfilm_education.export_report_case_outputs(
                result=result,
                prefix=prefix,
                save_plot=True,
                save_csv=True,
                save_json=True,
                save_txt=True,
            )
            files = {key: _output_url(value) for key, value in _visible_exported_files(exported).items()}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - keeps desktop UI errors readable.
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}") from exc

    return _jsonable(
        {
            "case_id": result.get("case_id"),
            "title_cn": result.get("title_cn"),
            "title_en": result.get("title_en"),
            "design_type": result.get("design_type"),
            "solver": result.get("solver", {"spectral_engine": "pythinfilm", "teaching_insights_engine": "pythinfilm"}),
            "summary": result.get("summary", {}),
            "layers": result.get("layers", []),
            "series": {
                "wavelength_nm": result.get("wavelength_nm", []),
                "R": result.get("R", []),
                "T": result.get("T", []),
                "A": result.get("A", []),
            },
            "figure_explanations": result.get("figure_explanations", result.get("figure_explanation", {})),
            "files": files,
        }
    )


@app.post("/api/designs/simulate")
def run_design_simulation(request: DesignSimulationRequest) -> dict[str, Any]:
    """Simulate an editor-defined stack using the root real-material engine."""
    try:
        return _jsonable(simulate_design(request, thinfilm_api, APP_ROOT))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - keeps desktop UI errors readable.
        raise HTTPException(status_code=500, detail=f"Design simulation failed: {exc}") from exc


@app.post("/api/ai/ask-result")
def run_ai_ask_result(request: AskResultRequest) -> StreamingResponse:
    outgoing = prepare_result_request(request)
    return StreamingResponse(stream_result_answer(outgoing), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
