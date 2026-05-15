from __future__ import annotations

import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_case_script(relative_script: str) -> None:
    script = ROOT / relative_script
    if not script.exists():
        raise SystemExit(f"Case entry script not found: {script}")
    sys.path.insert(0, str(ROOT))
    runpy.run_path(str(script), run_name="__main__")
