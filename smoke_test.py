from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _run(command: list[str]) -> None:
    label = " ".join(command)
    print(f"[smoke] running: {label}")
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.returncode != 0:
        raise SystemExit(f"[smoke] failed with exit code {completed.returncode}: {label}")


def main() -> None:
    _configure_console()
    print(f"[smoke] python: {sys.executable}")
    print(f"[smoke] version: {sys.version}")
    print("[smoke] checking package imports")
    import thinfilm  # noqa: F401
    from thinfilm import export_teaching_case_outputs, list_teaching_cases  # noqa: F401
    from thinfilm import export_real_material_library_outputs, simulate_teaching_design_real_materials  # noqa: F401
    import guided_grating  # noqa: F401

    print("[smoke] import ok")

    python = sys.executable
    commands = [
        [python, "-c", "import thinfilm; print('thinfilm import ok')"],
        [
            python,
            "-c",
            "from thinfilm import export_teaching_case_outputs, list_teaching_cases; print('teaching imports ok')",
        ],
        [
            python,
            "-c",
            "from thinfilm import export_real_material_library_outputs, simulate_teaching_design_real_materials; print('material imports ok')",
        ],
        [python, "run_teaching_demo.py", "--list"],
        [python, "run_teaching_demo.py", "--case", "single_ar"],
        [python, "run_teaching_demo.py", "--catalog"],
        [python, "run_guided_grating_demo.py"],
        [python, "run_material_library_demo.py", "--case", "single_ar"],
        [
            python,
            "run_figure_audit_gate.py",
            str(Path.home() / "thinfilm_outputs"),
            "--output-dir",
            str(ROOT / "outputs" / "smoke_figure_audit"),
            "--require-audits",
        ],
        [python, "run_case.py", "--list"],
        [python, "run_case.py", "--group", "frontier", "--case", "model_tree", "--", "--show"],
    ]
    for command in commands:
        _run(command)

    print("[smoke] all checks passed")


if __name__ == "__main__":
    main()
