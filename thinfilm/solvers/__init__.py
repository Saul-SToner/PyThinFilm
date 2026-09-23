"""Optional specialist solver adapters.

The adapters are deliberately lazy: importing PyThinFilm does not require
RCWA, GeneralTmm, or WPTherml to be installed.  Each backend exposes a
small capability probe so the application can show an honest unavailable
state instead of silently substituting a different physical model.
"""

from .registry import solver_status, specialist_solver_status

__all__ = ["solver_status", "specialist_solver_status"]
