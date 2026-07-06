"""Build a repository-wide figure audit manifest and enforce delivery gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from thinfilm.figure_audit import collect_figure_audits, write_audit_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Audit JSON files or directories to scan")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/figure_audit"))
    parser.add_argument("--require-audits", action="store_true", help="Fail when no audit files are found")
    args = parser.parse_args()

    manifest = collect_figure_audits(args.paths)
    if args.require_audits and manifest["counts"]["total"] == 0:
        manifest["gate_status"] = "fail"
        manifest["malformed"].append({"path": "", "error": "no figure audit files found"})
        manifest["counts"]["malformed"] += 1
    files = write_audit_manifest(args.output_dir, manifest)
    print(json.dumps({"gate_status": manifest["gate_status"], "counts": manifest["counts"], "files": files}, ensure_ascii=False, indent=2))
    return 1 if manifest["gate_status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
