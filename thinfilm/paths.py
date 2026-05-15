from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(os.environ.get("THINFILM_OUTPUT_DIR", Path.home() / "thinfilm_outputs"))


def output_file(name: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / name
