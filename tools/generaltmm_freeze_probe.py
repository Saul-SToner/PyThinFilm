"""Check whether GeneralTmm can evaluate a film in a frozen Python process."""

import numpy as np
from GeneralTmm import Material, Tmm

print("GeneralTmm imported", flush=True)
solver = Tmm(wl=550e-9, beta=0.0)
print("Tmm constructed", flush=True)
solver.AddIsotropicLayer(float("inf"), Material.Static(1.0))
solver.AddIsotropicLayer(100e-9, Material.Static(1.5))
solver.AddIsotropicLayer(float("inf"), Material.Static(1.0))
print("Layers constructed", flush=True)
print("Intensity", solver.GetIntensityMatrix(), flush=True)
print("Amplitude", solver.GetAmplitudeMatrix(), flush=True)
