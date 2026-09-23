/**
 * spectrumWaveAmp.js
 *
 * Calculates visual sine wave amplitudes tied to the selected wavelength and polarization
 * in the R/T spectrum with zero-power suppression.
 *
 * Zero-Power Suppression Rules:
 *   - Strictly zero or numerical noise (<= 1e-10) -> amplitude = 0, suppressedAsZero = true.
 *   - Very small non-zero component -> minimumVisible (0.04), exaggerated = true.
 *   - Normal component -> incidentAmplitude * sqrt(power).
 *   - Large component -> clamped to maximumVisible (0.35), exaggerated = true.
 */

export function visualAmplitude(power, incidentAmplitude = 0.25, options = {}) {
  const {
    zeroThreshold = 1e-10,
    minimumVisible = 0.04,
    maximumVisible = 0.35,
  } = options;

  const safePower = Math.max(0, Number(power));

  if (!Number.isFinite(safePower) || safePower <= zeroThreshold) {
    return {
      amplitude: 0,
      exaggerated: false,
      suppressedAsZero: true,
    };
  }

  const rawAmplitude = incidentAmplitude * Math.sqrt(safePower);
  const amplitude = Math.max(
    minimumVisible,
    Math.min(maximumVisible, rawAmplitude)
  );

  return {
    amplitude,
    exaggerated: amplitude !== rawAmplitude,
    suppressedAsZero: false,
  };
}

export function calculateWaveAmplitudesFromSpectrum(caseResult, polarization = "TE", selectedWavelengthNm = null) {
  let wl = selectedWavelengthNm;
  if (!wl) {
    if (caseResult && caseResult.case_id) {
      if (caseResult.case_id === "app_solar_cell_ar") wl = 550;
      else if (caseResult.case_id === "app_wdm_filter") wl = caseResult.metrics?.peak_wavelength_nm || 1550;
      else if (caseResult.case_id === "app_laser_mirror") wl = 1064;
      else if (caseResult.case_id === "app_phone_lens_ar") wl = 550;
    }
  }
  if (!wl) wl = 550;

  let rSelected = 0.5;
  let tSelected = 0.5;

  const polKey = (polarization === "TM" && caseResult && caseResult.TM) ? "TM" : "TE";
  const polData = caseResult ? caseResult[polKey] : null;

  const wList = (caseResult && (caseResult.wavelength_nm || caseResult.wavelengths)) ||
                (polData && (polData.wavelength_nm || polData.wavelengths)) || [];
  const rList = polData ? polData.R : [];
  const tList = polData ? polData.T : [];

  if (wList && wList.length > 0 && rList && rList.length === wList.length && tList && tList.length === wList.length) {
    if (wl <= wList[0]) {
      rSelected = rList[0];
      tSelected = tList[0];
    } else if (wl >= wList[wList.length - 1]) {
      rSelected = rList[rList.length - 1];
      tSelected = tList[tList.length - 1];
    } else {
      let idx = 0;
      for (let i = 0; i < wList.length - 1; i++) {
        if (wl >= wList[i] && wl <= wList[i + 1]) {
          idx = i;
          break;
        }
      }
      const frac = (wl - wList[idx]) / (wList[idx + 1] - wList[idx]);
      rSelected = rList[idx] + frac * (rList[idx + 1] - rList[idx]);
      tSelected = tList[idx] + frac * (tList[idx + 1] - tList[idx]);
    }
  }

  rSelected = Math.max(0, Math.min(1, rSelected));
  tSelected = Math.max(0, Math.min(1, tSelected));

  const baseIncidentAmp = 0.25;
  const rAmpRes = visualAmplitude(rSelected, baseIncidentAmp);
  const tAmpRes = visualAmplitude(tSelected, baseIncidentAmp);

  const rawRAmp = baseIncidentAmp * Math.sqrt(rSelected);
  const rawTAmp = baseIncidentAmp * Math.sqrt(tSelected);

  const isExaggerated = rAmpRes.exaggerated || tAmpRes.exaggerated;

  return {
    selectedWavelengthNm: wl,
    rSelected,
    tSelected,
    rawRAmp,
    rawTAmp,
    rAmp: rAmpRes.amplitude,
    tAmp: tAmpRes.amplitude,
    rSuppressed: rAmpRes.suppressedAsZero,
    tSuppressed: tAmpRes.suppressedAsZero,
    isExaggerated,
    VISUAL_AMPLITUDE_EXAGGERATED: isExaggerated,
    waveAmplitudeSource: "SELECTED_WAVELENGTH_R_T_SCHEMATIC",
    animationSemantics: "TEACHING_ILLUSTRATION",
  };
}
