from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json

from thinfilm import export_rugate_comsol_layer_table


def main() -> None:
    files = export_rugate_comsol_layer_table()
    print(json.dumps(files, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
