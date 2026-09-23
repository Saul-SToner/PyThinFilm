# -*- coding: utf-8 -*-
"""EMT Physics Audit Script."""

import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from guided_grating.emt import GratingLayer, emt_layer_spectrum, check_emt_applicability

print("=" * 60)
print("EMT Physics Audit")
print("=" * 60)

# 1. Energy conservation test
print("\n1. Energy Conservation Test (Lossless)")
for n_low, n_high in [(1.45, 3.4), (1.0, 3.5), (1.46, 2.30)]:
    g = GratingLayer(980, 200, n_low, n_high, 0.55)
    wl = np.linspace(1450, 1650, 50)
    result = emt_layer_spectrum(wl, g)
    total = result["R"] + result["T"] + result["A"]
    max_residue = np.max(np.abs(result["energy_residue"]))
    status = "PASS" if max_residue < 1e-5 else "FAIL"
    print(f"  n_low={n_low}, n_high={n_high}: max residue = {max_residue:.2e} [{status}]")

# 2. TE/TM normal incidence consistency
print("\n2. TE/TM Normal Incidence Consistency (各向异性)")
g = GratingLayer(980, 200, 1.45, 3.4, 0.5)
r_te = emt_layer_spectrum([1550.0], g, theta_deg=0.0, pol="TE")
r_tm = emt_layer_spectrum([1550.0], g, theta_deg=0.0, pol="TM")
print(f"  TE R = {r_te['R'][0]:.6f}")
print(f"  TM R = {r_tm['R'][0]:.6f}")
print(f"  Anisotropic Splitting Present: {abs(r_te['R'][0] - r_tm['R'][0]) > 1e-6}")

# 3. Uniform layer limit
print("\n3. Uniform Layer Limit (ff -> 1)")
g_uniform = GratingLayer(980, 200, 1.45, 3.4, 0.999)
r_uniform = emt_layer_spectrum([1550.0], g_uniform, n_substrate=1.45)
print(f"  ff=0.999: R = {r_uniform['R'][0]:.6f}")
print(f"  ff=0.999: T = {r_uniform['T'][0]:.6f}")
print(f"  ff=0.999: A = {r_uniform['A'][0]:.6f}")

# 4. EMT Applicability assessment test
print("\n4. EMT Applicability Assessment")
for period in [100.0, 300.0, 600.0, 1200.0]:
    app = check_emt_applicability(period, 1.0, 3.4, 1550.0)
    print(f"  Period={period}nm: rho={app['rho']:.4f} | status={app['status']} | is_valid={app['is_valid']}")

# 5. Physical trend: thickness -> R
print("\n5. Physical Trend: Thickness vs R")
for d in [50, 150, 250, 350, 450]:
    g = GratingLayer(980, d, 1.45, 3.4, 0.55)
    r = emt_layer_spectrum([1550.0], g)
    print(f"  Thickness={d}nm: R={r['R'][0]:.6f}")

print("\n" + "=" * 60)
print("Audit Complete")
print("=" * 60)
