"""Wavelength Division Multiplexing (WDM) Filter Design.

Engineering Background:
    WDM filters separate different wavelength channels in fiber optic
    communications. A Fabry-Perot filter provides narrowband transmission
    at the target wavelength.

Design Goal:
    Narrowband transmission at 1550 nm (C-band) with high channel isolation.

Structure:
    Air / [DBR] / Half-wave cavity / [DBR] / Air
    DBR = TiO2/SiO2 alternating quarter-wave layers

Key Metrics:
    - Peak transmittance at 1550 nm
    - Full width at half maximum (FWHM)
    - Free spectral range (FSR)
    - Channel isolation (off-peak rejection)

Teaching Value:
    Demonstrates Fabry-Perot interferometer principle.
    Shows relationship between cavity finesse and filter bandwidth.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from thinfilm.education import (
    LayerSpec,
    build_fp_single_halfwave_layers,
    multilayer_rt_spectrum,
)


# ---------------------------------------------------------------------------
# Design parameters
# ---------------------------------------------------------------------------

LAMBDA0_NM = 1550.0  # C-band center wavelength
N_AIR = 1.0
N_SIO2 = 1.46
N_TIO2 = 2.30
N_SUBSTRATE = 1.46  # Silica fiber

PERIODS = 4  # DBR periods (each period = H+L)
CAVITY_KIND = "L"  # Half-wave cavity using low-index material


def build_wdm_filter_layers() -> list[LayerSpec]:
    """Build WDM filter layer stack."""
    return build_fp_single_halfwave_layers(
        LAMBDA0_NM, N_TIO2, N_SIO2, PERIODS, spacer_kind=CAVITY_KIND,
    )


def run_wdm_filter(
    wavelengths_nm: np.ndarray | None = None,
    save_html: bool = False,
    output_dir: str | None = None,
) -> Dict[str, Any]:
    """Run WDM filter simulation.

    Parameters
    ----------
    wavelengths_nm : array, optional
        Wavelength grid. Default: 1500-1600 nm, 500 points.
    save_html : bool
        If True, save Plotly interactive HTML.
    output_dir : str, optional
        Directory for output files.

    Returns
    -------
    dict
        Contains structure, metrics, wavelengths, R/T/A arrays.
    """
    if wavelengths_nm is None:
        wavelengths_nm = np.linspace(1500, 1600, 500)

    layers = build_wdm_filter_layers()

    result = multilayer_rt_spectrum(
        wavelengths_nm,
        layers,
        n_incident=N_AIR,
        n_substrate=N_SUBSTRATE,
        theta0_deg=0.0,
        pol="p",
    )

    R = result["R"]
    T = result["T"]
    A = result["A"]

    # Engineering metrics
    T_peak = float(np.max(T))
    T_peak_wl = float(wavelengths_nm[np.argmax(T)])

    # FWHM calculation
    T_half = T_peak / 2.0
    above_half = T >= T_half
    if np.any(above_half):
        indices = np.where(above_half)[0]
        fwhm_nm = float(wavelengths_nm[indices[-1]] - wavelengths_nm[indices[0]])
    else:
        fwhm_nm = 0.0

    # FSR (free spectral range) - distance between adjacent transmission peaks
    # For a simple F-P: FSR ≈ λ²/(2*n_cavity*d_cavity)
    n_cavity = N_SIO2
    d_cavity_nm = LAMBDA0_NM  # Half-wave cavity (λ₀/2 optical thickness)
    fsr_nm = (LAMBDA0_NM ** 2) / (2 * n_cavity * d_cavity_nm)

    # Channel isolation (off-peak rejection)
    off_peak_mask = np.abs(wavelengths_nm - T_peak_wl) > 2 * fwhm_nm
    if np.any(off_peak_mask):
        off_peak_T = float(np.mean(T[off_peak_mask]))
    else:
        off_peak_T = 1e-4

    eps_floor = 1e-10
    off_peak_T_clamped = max(off_peak_T, eps_floor)
    off_peak_transmission_dB = float(10.0 * np.log10(off_peak_T_clamped))
    isolation_dB = float(-10.0 * np.log10(off_peak_T_clamped))

    # Finesse
    finesse = fsr_nm / fwhm_nm if fwhm_nm > 0 else 0.0

    metrics = {
        "peak_transmittance": T_peak,
        "peak_wavelength_nm": T_peak_wl,
        "fwhm_nm": fwhm_nm,
        "fsr_nm": fsr_nm,
        "finesse": finesse,
        "off_peak_transmission": off_peak_T,
        "off_peak_transmission_dB": off_peak_transmission_dB,
        "isolation_dB": isolation_dB,
        "isolation_definition": "-10*log10(T_off_peak)",
        "off_peak_definition": "10*log10(T_off_peak)",
        "epsilon_floor": eps_floor,
        "num_dbr_periods": PERIODS,
    }

    structure = {
        "layers": [
            {"material": f"{'TiO2' if i % 2 == 0 else 'SiO2'}",
             "thickness_nm": LAMBDA0_NM / (4 * (N_TIO2 if i % 2 == 0 else N_SIO2)),
             "n": N_TIO2 if i % 2 == 0 else N_SIO2}
            for i in range(2 * PERIODS)
        ],
        "cavity": {"material": "SiO2 (half-wave)", "n": N_SIO2},
        "substrate": "SiO2 (n=1.46)",
        "design_wavelength_nm": LAMBDA0_NM,
    }

    if save_html and output_dir:
        try:
            from thinfilm.plotly_charts import plot_rta_spectrum
            fig = plot_rta_spectrum(
                wavelengths_nm, R, T, A,
                title="WDM 滤光片透射特性",
                design_type=f"FP F-P ({PERIODS} periods, FWHM={fwhm_nm:.1f}nm)",
            )
            from pathlib import Path
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(out / "wdm_filter_spectrum.html"))
        except ImportError:
            pass

    return {
        "case_id": "wdm_filter",
        "title": "WDM 通信滤光片",
        "wavelengths_nm": wavelengths_nm,
        "R": R,
        "T": T,
        "A": A,
        "metrics": metrics,
        "structure": structure,
        "physics": {
            "principle": "Fabry-Perot 腔谐振透射，只有满足共振条件的波长能通过",
            "key_insight": f"FSR ≈ {fsr_nm:.1f} nm，精细度 F ≈ {finesse:.1f}",
        },
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_wdm_filter(save_html=True, output_dir="outputs/wdm_filter")

    print("=" * 60)
    print("WDM 通信滤光片设计")
    print("=" * 60)
    print(f"\n膜系结构: Air / [TiO2/SiO2]x{PERIODS} / SiO2(HW) / [TiO2/SiO2]x{PERIODS} / SiO2")
    print(f"\n关键指标:")
    print(f"  峰值透射率: {result['metrics']['peak_transmittance']:.4f}")
    print(f"  中心波长: {result['metrics']['peak_wavelength_nm']:.2f} nm")
    print(f"  FWHM: {result['metrics']['fwhm_nm']:.2f} nm")
    print(f"  FSR: {result['metrics']['fsr_nm']:.1f} nm")
    print(f"  精细度: {result['metrics']['finesse']:.1f}")
    print(f"  通道隔离: {result['metrics']['isolation_dB']:.1f} dB")
    print(f"\n物理原理: {result['physics']['principle']}")
