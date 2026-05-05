from __future__ import annotations

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(r"C:\Users\L2791\thinfilm_outputs")


def output_file(name: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / name
