from __future__ import annotations

import json

from thinfilm import export_rugate_comsol_layer_table


def main() -> None:
    files = export_rugate_comsol_layer_table()
    print(json.dumps(files, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
