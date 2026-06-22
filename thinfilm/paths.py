from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(os.environ.get("THINFILM_OUTPUT_DIR", Path.home() / "thinfilm_outputs"))

_OUTPUT_DIR_MADE: bool = False


def output_file(name: str) -> Path:
    global _OUTPUT_DIR_MADE
    if not _OUTPUT_DIR_MADE:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        _OUTPUT_DIR_MADE = True
    return OUTPUT_DIR / name
