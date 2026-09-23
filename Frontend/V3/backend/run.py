from __future__ import annotations

import sys

import uvicorn


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--optiland-render":
        from experiments.optiland_draft_render import main as render_main

        sys.argv.pop(1)
        raise SystemExit(render_main())
    if len(sys.argv) > 1 and sys.argv[1] == "--optiland-comparison":
        from experiments.optiland_real_material_ar_comparison import main as comparison_main

        sys.argv.pop(1)
        raise SystemExit(comparison_main())

    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=8122, reload=False)
