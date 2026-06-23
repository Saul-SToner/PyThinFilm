"""RCWA Physics Audit Script."""

import numpy as np
from guided_grating.rcwa import GratingLayer, rcwa_1d, rcwa_convergence_test

print("=" * 60)
print("RCWA Physics Audit")
print("=" * 60)

# 1. Energy conservation test
print("\n1. Energy Conservation Test")
for n_low, n_high in [(1.45, 3.4), (1.0, 3.5), (1.46, 2.30)]:
    g = GratingLayer(980, 200, n_low, n_high, 0.55)
    wl = np.linspace(1450, 1650, 50)
    result = rcwa_1d(wl, g)
    total = result["R"] + result["T"] + result["A"]
    max_error = np.max(np.abs(total - 1.0))
    status = "PASS" if max_error < 0.01 else "FAIL"
    print(f"  n_low={n_low}, n_high={n_high}: max error = {max_error:.6f} [{status}]")

# 2. TE/TM normal incidence consistency
print("\n2. TE/TM Normal Incidence Consistency")
g = GratingLayer(980, 200, 1.45, 3.4, 0.5)
r_te = rcwa_1d([1550.0], g, theta_deg=0.0, pol="TE")
r_tm = rcwa_1d([1550.0], g, theta_deg=0.0, pol="TM")
print(f"  TE R = {r_te['R'][0]:.6f}")
print(f"  TM R = {r_tm['R'][0]:.6f}")
print(f"  Different: {abs(r_te['R'][0] - r_tm['R'][0]) > 1e-6}")

# 3. Uniform layer limit
print("\n3. Uniform Layer Limit (ff -> 1)")
g_uniform = GratingLayer(980, 200, 1.45, 3.4, 0.999)
r_uniform = rcwa_1d([1550.0], g_uniform, n_substrate=1.45)
print(f"  ff=0.999: R = {r_uniform['R'][0]:.6f}")
print(f"  ff=0.999: T = {r_uniform['T'][0]:.6f}")
print(f"  ff=0.999: A = {r_uniform['A'][0]:.6f}")

# 4. Convergence test
print("\n4. Convergence Test")
g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
conv = rcwa_convergence_test(g, wavelength_nm=1550.0, order_range=[3, 5, 7, 10, 15])
R_vals = [r["R"] for r in conv["results"]]
print(f"  Orders: {[r['num_orders'] for r in conv['results']]}")
print(f"  R values: {[f'{r:.6f}' for r in R_vals]}")
print(f"  Converged: {conv['converged']}")
if len(R_vals) >= 2:
    print(f"  Last 2 diff: {abs(R_vals[-1] - R_vals[-2]):.8f}")

# 5. Physical trend: thickness -> R
print("\n5. Physical Trend: Thickness vs R")
for n_layers in [1, 3, 5, 7, 9]:
    d = n_layers * 50
    g = GratingLayer(980, d, 1.45, 3.4, 0.55)
    r = rcwa_1d([1550.0], g)
    print(f"  Thickness={d}nm: R={r['R'][0]:.6f}")

# 6. Wavelength dependence
print("\n6. Wavelength Dependence")
g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
for wl in [1000, 1550, 2000]:
    r = rcwa_1d([wl], g)
    print(f"  λ={wl}nm: R={r['R'][0]:.6f}")

print("\n" + "=" * 60)
print("Audit Complete")
print("=" * 60)
