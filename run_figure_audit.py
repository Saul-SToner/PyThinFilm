"""Audit the scientific evidence behind an exported spectrum figure."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from thinfilm.figure_audit import (
    audit_external_comparison,
    audit_rta_data,
    build_figure_audit,
    write_figure_audit,
)


def _columns(path: Path) -> dict[str, list[float]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Empty CSV: {path}")
    return {name: [float(row[name]) for row in rows] for name in rows[0]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="R/T/A spectrum or theory/reference comparison CSV")
    parser.add_argument("--output", type=Path, help="Audit JSON path")
    parser.add_argument("--title", default="Figure audit")
    parser.add_argument("--figure-id", default="figure")
    parser.add_argument("--evidence-level", choices=("theory", "real_material_theory", "external_validation", "approximation", "placeholder"))
    parser.add_argument("--reference-file", type=Path)
    parser.add_argument("--reference-label", default="external reference")
    args = parser.parse_args()

    data = _columns(args.csv)
    lower = {key.lower(): key for key in data}
    if all(key in lower for key in ("r", "t", "a")):
        wl_key = lower.get("wavelength_nm") or lower.get("lambda_um") or lower.get("wavelength")
        if wl_key is None:
            raise ValueError("R/T/A CSV requires wavelength_nm, lambda_um, or wavelength")
        check = audit_rta_data(data[wl_key], data[lower["r"]], data[lower["t"]], data[lower["a"]])
        level = args.evidence_level or "theory"
    elif all(key in lower for key in ("theory", "reference")):
        residual_key = lower.get("error") or lower.get("residual")
        check = audit_external_comparison(
            data[lower["theory"]], data[lower["reference"]],
            reference_label=args.reference_label,
            reference_file=args.reference_file,
            residual=None if residual_key is None else data[residual_key],
        )
        level = args.evidence_level or "external_validation"
    else:
        raise ValueError("CSV must contain R/T/A or theory/reference columns")

    audit = build_figure_audit(
        figure_id=args.figure_id,
        title=args.title,
        evidence_level=level,
        checks=[check],
        source_files=[args.csv, *([] if args.reference_file is None else [args.reference_file])],
    )
    output = args.output or args.csv.with_name(f"{args.csv.stem}_figure_audit.json")
    write_figure_audit(output, audit)
    print(json.dumps({"status": audit["status"], "output": str(output), "issues": audit["issues"]}, ensure_ascii=False, indent=2))
    return 1 if audit["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
