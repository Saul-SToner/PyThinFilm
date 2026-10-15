"""Fail closed on missing release dependencies and exercise an unpacked build."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((Path(__file__).with_name("release-dependencies.json")).read_text(encoding="utf-8"))


def checkout_path() -> Path:
    return Path(os.environ.get("THINFILM_OPTILAND_CHECKOUT", PROJECT.parent / "optiland")).resolve()


def preflight() -> None:
    checkout = checkout_path()
    if not (checkout / "optiland" / "__init__.py").is_file():
        raise RuntimeError(f"Optiland checkout is missing: {checkout}")
    commit = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if commit != MANIFEST["optiland"]["commit"]:
        raise RuntimeError(f"Optiland commit mismatch: {commit}")
    origin = subprocess.check_output(["git", "-C", str(checkout), "remote", "get-url", "origin"], text=True).strip()
    if origin.rstrip("/") != MANIFEST["optiland"]["repository"]:
        raise RuntimeError(f"Unexpected Optiland origin: {origin}")
    for package in ("optiland", "rcwa", "GeneralTmm", "wptherml", "numpy", "eigency"):
        expected = MANIFEST["optiland"]["version"] if package == "optiland" else MANIFEST[package]
        actual = importlib.metadata.version(package)
        if actual != expected:
            raise RuntimeError(f"{package}: expected {expected}, found {actual}")
    for package, resource in (("rcwa", "nkData/library.yml"), ("wptherml", "data/SiO2_ir.txt")):
        distribution = importlib.metadata.distribution(package)
        if not Path(distribution.locate_file(f"{package}/{resource}")).is_file():
            raise RuntimeError(f"Missing {package} resource: {resource}")
    import optiland

    if not Path(optiland.__file__).resolve().is_relative_to(checkout):
        raise RuntimeError(f"Optiland import does not use pinned checkout: {optiland.__file__}")
    frontend = PROJECT / "Frontend" / "V3" / "frontend"
    installed = json.loads((frontend / "node_modules" / "tmmcore" / "package.json").read_text(encoding="utf-8"))
    declared = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    if installed["version"] != MANIFEST["tmmcore"] or declared["dependencies"]["tmmcore"] != MANIFEST["tmmcore"]:
        raise RuntimeError("tmmcore version mismatch")
    print(f"Release dependencies verified: Optiland {commit}, tmmcore {installed['version']}, specialist solvers")


def request(base: str, endpoint: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    try:
        with urlopen(Request(base + endpoint, data=data, headers={"Content-Type": "application/json"}), timeout=180) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"{endpoint}: HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:1000]}") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected response from {endpoint}: {type(result).__name__}")
    return result


def smoke(unpacked: Path) -> None:
    unpacked = unpacked.resolve()
    resources = unpacked / "resources"
    backend = resources / "backend"
    exe = backend / "thinfilm-backend.exe"
    electron = unpacked / "PythonFilm.exe"
    bridge = resources / "tmmcore" / "tmmcore_bridge.mjs"
    package = resources / "tmmcore" / "node_modules" / "tmmcore" / "package.json"
    general_runtime = resources / "generaltmm-python"
    for required in (
        exe, electron, bridge, package, backend / "optiland" / "__init__.py",
        backend / "rcwa" / "nkData" / "library.yml", backend / "wptherml" / "data" / "SiO2_ir.txt",
        general_runtime / "python.exe", general_runtime / "worker.py",
        general_runtime / "GeneralTmm" / "_GeneralTmmCppExt.cp313-win_amd64.pyd",
    ):
        if not required.is_file():
            raise RuntimeError(f"Missing packaged runtime: {required}")
    if json.loads(package.read_text(encoding="utf-8"))["version"] != MANIFEST["tmmcore"]:
        raise RuntimeError("Packaged tmmcore version mismatch")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="pythonfilm-release-smoke-") as output:
        env = os.environ.copy()
        env.update({
            "THINFILM_APP_ROOT": str(resources),
            "THINFILM_PYTHINFILM_ROOT": str(backend),
            "THINFILM_OUTPUT_DIR": output,
            "THINFILM_MATERIALS_METADATA_CSV": str(resources / "materials" / "app_materials_metadata.csv"),
            "THINFILM_NODE_EXECUTABLE": str(electron),
            "THINFILM_TMMCORE_BRIDGE": str(bridge),
            "THINFILM_OPTILAND_ROOT": str(backend),
            "THINFILM_OPTILAND_PYTHON": str(exe),
            "THINFILM_GENERALTMM_PYTHON": str(general_runtime / "python.exe"),
            "THINFILM_GENERALTMM_WORKER": str(general_runtime / "worker.py"),
            "THINFILM_PORT": str(port),
            "PYTHONFAULTHANDLER": "1",
        })
        log_path = Path(output) / "backend.log"
        log = log_path.open("wb")
        proc = subprocess.Popen([str(exe)], cwd=backend, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(90):
                if proc.poll() is not None:
                    raise RuntimeError(f"Packaged backend exited with code {proc.returncode}")
                try:
                    request(base, "/health")
                    break
                except (URLError, OSError):
                    time.sleep(0.5)
            else:
                raise RuntimeError("Packaged backend did not become healthy")
            diagnostics = request(base, "/api/diagnostics")
            if not diagnostics["tmmcore"]["available"]:
                raise RuntimeError("Packaged tmmcore is unavailable")
            for solver in ("rcwa", "generaltmm", "wptherml"):
                if not diagnostics["specialist_solvers"][solver]["available"]:
                    raise RuntimeError(f"Packaged {solver} is unavailable")
            design = {
                "schema_version": "1.0", "request_id": "release-smoke", "solver": "tmmcore", "incident_material_id": "Air",
                "substrate_material_id": "N-BK7", "layers": [{"id": "ar", "material_id": "MgF2", "thickness_nm": 100, "enabled": True}],
                "spectrum": {"start_nm": 500, "stop_nm": 600, "points": 3},
            }
            result = request(base, "/api/designs/simulate", design)
            if result["solver"]["spectral_engine"] != "tmmcore" or len(result["series"]["R"]) != 3:
                raise RuntimeError("Packaged tmmcore calculation failed")
            checks = (
                ("rcwa", {"wavelength_start_um": 0.5, "wavelength_stop_um": 0.52, "wavelength_points": 2, "harmonics": 3}),
                ("wptherml", {"wavelength_start_nm": 500, "wavelength_stop_nm": 510, "wavelength_points": 2}),
            )
            for solver, payload in checks:
                print(f"Checking packaged {solver}", flush=True)
                result = request(base, f"/api/specialist/{solver}", payload)
                wavelengths = result.get("wavelength_nm" if solver == "wptherml" else "wavelength_um", [])
                if result["solver"].lower() != solver or len(result["R"]) < 2 or len(result["R"]) != len(wavelengths):
                    raise RuntimeError(f"Packaged {solver} calculation failed: solver={result.get('solver')}, R points={len(result.get('R', []))}")
                print(f"PASS {solver}")
            draft = json.loads((PROJECT / "Frontend" / "V3" / "backend" / "tests" / "fixtures" / "optiland_packaged_smoke.json").read_text(encoding="utf-8"))
            optiland = request(base, "/api/optiland/system", {"draft": draft})
            if not optiland.get("ready") or not optiland.get("artifacts"):
                raise RuntimeError(f"Packaged Optiland rendering failed: {optiland.get('error', optiland)}")
            print("PASS tmmcore; PASS Optiland system rendering")
            result = request(base, "/api/specialist/generaltmm", {"wavelength_start_nm": 500, "wavelength_stop_nm": 510, "wavelength_points": 2})
            if result["solver"] != "generaltmm" or len(result["R"]) != 2:
                raise RuntimeError("Packaged GeneralTmm calculation failed")
            print("PASS generaltmm")
            tamm = request(base, "/api/specialist/generaltmm", {
                "case_id": "tamm_phase_focus", "wavelength_start_nm": 500,
                "wavelength_stop_nm": 510, "wavelength_points": 2,
            })
            profiles = tamm.get("field_comparison", {}).get("profiles", [])
            if tamm.get("solver") != "generaltmm" or len(profiles) != 2 or len(profiles[0]["depth_nm"]) != 601:
                raise RuntimeError("Packaged Tamm multilayer/field calculation failed")
            print("PASS Tamm multilayer and field profile")
        except Exception as exc:
            time.sleep(0.5)
            log.flush()
            detail = log_path.read_text(encoding="utf-8", errors="replace")[-2500:]
            raise RuntimeError(f"{exc}; backend exit code={proc.poll()}; backend log={detail}") from exc
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=8)
            log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "smoke"))
    parser.add_argument("--unpacked", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "preflight":
            preflight()
        else:
            if args.unpacked is None:
                parser.error("smoke requires --unpacked")
            smoke(args.unpacked)
    except Exception as exc:
        print(f"Release audit failed: {exc}", file=sys.stderr)
        sys.exit(1)
