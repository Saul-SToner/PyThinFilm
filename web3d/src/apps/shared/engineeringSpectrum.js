import { calculateWaveAmplitudesFromSpectrum } from "../../core/spectrumWaveAmp.js";

function interpolate(xValues, yValues, x) {
  if (!xValues.length || xValues.length !== yValues.length) return 0;
  if (x <= xValues[0]) return Number(yValues[0]);
  if (x >= xValues[xValues.length - 1]) return Number(yValues[yValues.length - 1]);
  for (let index = 0; index < xValues.length - 1; index += 1) {
    if (x >= xValues[index] && x <= xValues[index + 1]) {
      const fraction = (x - xValues[index]) / (xValues[index + 1] - xValues[index]);
      return Number(yValues[index]) + fraction * (Number(yValues[index + 1]) - Number(yValues[index]));
    }
  }
  return 0;
}

export function sampleEngineeringSpectrum(caseResult, polarization, wavelengthNm) {
  const pol = polarization === "TM" ? "TM" : "TE";
  const wavelengths = caseResult.wavelength_nm || [];
  const waveInfo = calculateWaveAmplitudesFromSpectrum(caseResult, pol, wavelengthNm);
  const absorptance = interpolate(wavelengths, caseResult[pol]?.A || [], waveInfo.selectedWavelengthNm);
  return {
    ...waveInfo,
    absorptance: Math.max(0, Math.min(1, absorptance)),
    polarization: pol,
  };
}

function extremumWavelength(caseResult, polarization, key, direction) {
  const wavelengths = caseResult.wavelength_nm || [];
  const values = caseResult[polarization]?.[key] || [];
  if (!wavelengths.length || wavelengths.length !== values.length) {
    throw new Error(`正式光谱 ${key} 数组与波长轴不一致`);
  }
  let selectedIndex = 0;
  for (let index = 1; index < values.length; index += 1) {
    if (direction === "min" ? values[index] < values[selectedIndex] : values[index] > values[selectedIndex]) {
      selectedIndex = index;
    }
  }
  return Number(wavelengths[selectedIndex]);
}

export function resolvePresetWavelength(caseResult, polarization, preset) {
  if (Number.isFinite(preset.wavelengthNm)) return Number(preset.wavelengthNm);
  if (Array.isArray(preset.path)) {
    const value = preset.path.reduce((current, segment) => current?.[segment === "$POL" ? polarization : segment], caseResult);
    if (Number.isFinite(Number(value))) return Number(value);
  }
  if (preset.metric && Number.isFinite(Number(caseResult.metrics?.[preset.metric]))) {
    return Number(caseResult.metrics[preset.metric]);
  }
  if (preset.selector === "minR") return extremumWavelength(caseResult, polarization, "R", "min");
  if (preset.selector === "maxR") return extremumWavelength(caseResult, polarization, "R", "max");
  if (preset.selector === "minT") return extremumWavelength(caseResult, polarization, "T", "min");
  if (preset.selector === "maxT") return extremumWavelength(caseResult, polarization, "T", "max");
  throw new Error(`无法解析光谱预设：${preset.id}`);
}
