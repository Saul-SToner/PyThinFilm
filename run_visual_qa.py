"""Inventory and contact-sheet QA for every exported PyThinFilm figure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from thinfilm.plotting import apply_plot_style


def inspect_png(path: Path, *, require_vectors: bool) -> dict[str, object]:
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    height, width = rgb.shape[:2]
    nonwhite = np.any(rgb < 248, axis=2)
    if np.any(nonwhite):
        ys, xs = np.where(nonwhite)
        margins = {"left": int(xs.min()), "right": int(width - 1 - xs.max()), "top": int(ys.min()), "bottom": int(height - 1 - ys.max())}
    else:
        margins = {key: 0 for key in ("left", "right", "top", "bottom")}
    issues: list[str] = []
    if width < 600 or height < 350:
        issues.append("low_pixel_dimensions")
    if float(np.std(rgb)) < 3.0:
        issues.append("nearly_blank")
    if any(value <= 1 for value in margins.values()):
        issues.append("content_touches_edge")
    svg = path.with_suffix(".svg")
    pdf = path.with_suffix(".pdf")
    if require_vectors and not svg.is_file():
        issues.append("missing_svg")
    if require_vectors and not pdf.is_file():
        issues.append("missing_pdf")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path.resolve()), "name": path.name, "width_px": width, "height_px": height,
        "aspect": width / height, "content_fraction": float(np.mean(nonwhite)), **{f"margin_{key}_px": value for key, value in margins.items()},
        "svg": str(svg.resolve()) if svg.is_file() else "", "pdf": str(pdf.resolve()) if pdf.is_file() else "",
        "sha256": digest, "issues": issues,
    }


def make_contact_sheets(records: list[dict[str, object]], output_dir: Path, *, per_sheet: int = 12) -> list[str]:
    apply_plot_style()
    paths: list[str] = []
    for page, start in enumerate(range(0, len(records), per_sheet), start=1):
        subset = records[start:start + per_sheet]
        fig, axes = plt.subplots(3, 4, figsize=(14, 10), facecolor="white")
        for ax in axes.ravel():
            ax.axis("off")
        for ax, record in zip(axes.ravel(), subset):
            with Image.open(str(record["path"])) as image:
                ax.imshow(image.convert("RGB"))
            issue_text = ", ".join(record["issues"])
            color = "#B64342" if issue_text else "#272727"
            ax.set_title(f"{record['name']}\n{issue_text or 'auto: pass'}", fontsize=6, color=color, loc="left")
            ax.axis("off")
        fig.suptitle(f"PyThinFilm visual QA — page {page}", fontsize=11, fontweight="semibold")
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        sheet = output_dir / f"contact_sheet_{page:02d}.png"
        fig.savefig(sheet, dpi=160, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        paths.append(str(sheet))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/visual_qa"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    files: list[tuple[Path, bool]] = []
    for root in args.roots:
        expanded = Path(str(root)).expanduser()
        require_vectors = expanded.name == "thinfilm_outputs"
        files.extend((path, require_vectors) for path in sorted(expanded.rglob("*.png")) if "visual_qa" not in path.parts)
    records = [inspect_png(path, require_vectors=require_vectors) for path, require_vectors in files]
    hash_counts: dict[str, int] = {}
    for row in records:
        hash_counts[str(row["sha256"])] = hash_counts.get(str(row["sha256"]), 0) + 1
    for row in records:
        if hash_counts[str(row["sha256"])] > 1:
            row["issues"].append("exact_duplicate")
    json_path = args.output_dir / "visual_qa_inventory.json"
    csv_path = args.output_dir / "visual_qa_inventory.csv"
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["path", "name", "width_px", "height_px", "aspect", "content_fraction", "margin_left_px", "margin_right_px", "margin_top_px", "margin_bottom_px", "svg", "pdf", "sha256", "issues"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow({**row, "issues": ";".join(row["issues"])})
    sheets = make_contact_sheets(records, args.output_dir)
    summary = {
        "total": len(records), "auto_pass": sum(not row["issues"] for row in records),
        "flagged": sum(bool(row["issues"]) for row in records), "contact_sheets": sheets,
        "inventory_json": str(json_path), "inventory_csv": str(csv_path),
    }
    (args.output_dir / "visual_qa_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
