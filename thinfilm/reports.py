"""Report and output helpers."""

from __future__ import annotations

import json
from typing import Dict, List

from .config import OUTPUT_DIR, calibrate_thickness_nm, format_angle_label


def save_text_report(filename: str, lines: List[str]) -> None:
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(str(line) + "\n")
    print(f"Saved report: {path}")

def save_json_report(filename: str, payload: Dict) -> None:
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Saved json: {path}")

def save_rows_csv(filename: str, header: List[str], rows: List[List]) -> None:
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for row in rows:
            f.write(",".join(str(x) for x in row) + "\n")
    print(f"Saved csv: {path}")

__all__ = [
    "calibrate_thickness_nm",
    "format_angle_label",
    "save_json_report",
    "save_rows_csv",
    "save_text_report",
]
