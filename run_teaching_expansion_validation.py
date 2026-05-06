from __future__ import annotations

import argparse
import json
from pathlib import Path

from thinfilm import (
    export_teaching_expansion_validation_bundle_from_template,
    export_teaching_expansion_validation_templates,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or run expansion-case validation templates for the teaching thin-film platform."
    )
    parser.add_argument(
        "--template-out",
        action="store_true",
        help="Only export an empty validation template bundle for expansion cases.",
    )
    parser.add_argument(
        "--template-file",
        type=str,
        default="",
        help="Filled JSON/CSV template file used to run expansion-case validation.",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="teaching_expansion_validation_cli",
        help="Output filename prefix.",
    )
    parser.add_argument(
        "--reference-label",
        type=str,
        default="COMSOL",
        help="Reference label written into output summaries.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.template_out or not args.template_file:
        files = export_teaching_expansion_validation_templates(
            prefix=args.prefix,
            reference_label=args.reference_label,
        )
        print(json.dumps({"mode": "template_only", "files": files}, ensure_ascii=False, indent=2))
        return

    template_path = Path(args.template_file)
    files = export_teaching_expansion_validation_bundle_from_template(
        str(template_path),
        prefix=args.prefix,
        reference_label=args.reference_label,
    )
    print(
        json.dumps(
            {
                "mode": "run_validation",
                "template_file": str(template_path),
                "manifest": files["manifest"],
                "suite_files": files["suite_files"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
