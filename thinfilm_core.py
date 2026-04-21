from __future__ import annotations

import sys
import types

from thinfilm import config as _config
from thinfilm.config import *  # noqa: F401,F403
from thinfilm.reports import *  # noqa: F401,F403
from thinfilm.io import *  # noqa: F401,F403
from thinfilm.optics import *  # noqa: F401,F403
from thinfilm.objectives import *  # noqa: F401,F403
from thinfilm.fitting import *  # noqa: F401,F403
from thinfilm.diagnostics import *  # noqa: F401,F403


class _ThinfilmCoreModule(types.ModuleType):
    def __getattribute__(self, name):
        config_names = object.__getattribute__(_config, "CONFIG_EXPORT_NAMES")
        if name in config_names:
            return getattr(_config, name)
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in getattr(_config, "CONFIG_EXPORT_NAMES", ()):
            setattr(_config, name, value)
            _config.push_runtime_config()
            return
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _ThinfilmCoreModule


if __name__ == "__main__":
    _config.sync_angle_config_aliases()
    print("Running file:", __file__)
    print("RUN_MODE =", _config.RUN_MODE)

    if _config.RUN_MODE == "preview_csv":
        run_preview_csv()
    elif _config.RUN_MODE == "export_clean_csv":
        run_export_clean_csv()
    elif _config.RUN_MODE == "fit_csv":
        run_fit_csv()
    elif _config.RUN_MODE == "fit_csv_with_theta2_search":
        run_fit_csv_with_theta2_search()
    elif _config.RUN_MODE == "single_angle_0deg_scan":
        run_single_angle_0deg_scan()
    elif _config.RUN_MODE == "objective_heatmap_d_theta2":
        run_objective_heatmap_d_theta2()
    elif _config.RUN_MODE == "batch_fit_csv":
        run_batch_fit_csv()
    elif _config.RUN_MODE == "batch_error_analysis":
        run_batch_error_analysis()
    elif _config.RUN_MODE == "single_sample_error_analysis":
        run_single_sample_error_analysis()
    elif _config.RUN_MODE == "fit_csv_compare_pols":
        run_fit_csv_compare_pols()
    elif _config.RUN_MODE == "compare_80deg_at_fixed_d":
        run_compare_80deg_at_fixed_d()
    elif _config.RUN_MODE == "theta2_scan_at_fixed_d":
        run_theta2_scan_at_fixed_d()
    else:
        raise ValueError("RUN_MODE is not valid")
