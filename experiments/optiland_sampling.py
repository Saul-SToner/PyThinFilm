"""Working-band sampling with explicit refinement evidence."""
import numpy as np


def sample_spectrum(evaluate, start, stop, points=351, max_points=32001):
    if not 0 < start < stop:
        raise ValueError('工作波段无有效交集')
    count = min(max(351, int(points), int(np.ceil((stop-start)/0.25))+1), max_points)
    previous = None
    stable = 0
    error = None
    while True:
        wavelengths = np.linspace(start, stop, count)
        values = np.asarray(evaluate(wavelengths))
        if not np.isfinite(values).all():
            raise ValueError('光谱含非有限数值')
        if previous is not None:
            old_x, old_y = previous
            error = float(max(np.max(np.abs(y-np.interp(wavelengths,old_x,old))) for y,old in zip(values,old_y)))
            stable = stable+1 if error < 1e-3 else 0
        if stable >= 2 or count >= max_points:
            return wavelengths, values, {'points': count, 'max_step_nm': float(wavelengths[1]-wavelengths[0]), 'refinement_error': error, 'converged': stable >= 2, 'tolerance': 1e-3}
        previous = wavelengths, values
        count = min(2*count-1, max_points)
