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

export function sampleSolarSpectrum(caseResult, polarization, wavelengthNm) {
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

export function getSolarComparisonPoints(caseResult, polarization = "TE") {
  const pol = polarization === "TM" ? "TM" : "TE";
  const wavelengths = caseResult.wavelength_nm || [];
  const reflectance = caseResult[pol]?.R || [];
  if (!wavelengths.length || wavelengths.length !== reflectance.length) {
    throw new Error("太阳减反膜正式光谱轴与 R 数组不一致");
  }

  let minIndex = 0;
  let maxIndex = 0;
  let nearest550Index = 0;
  for (let index = 1; index < reflectance.length; index += 1) {
    if (reflectance[index] < reflectance[minIndex]) minIndex = index;
    if (reflectance[index] > reflectance[maxIndex]) maxIndex = index;
    if (Math.abs(wavelengths[index] - 550) < Math.abs(wavelengths[nearest550Index] - 550)) nearest550Index = index;
  }
  return {
    lowReflectionNm: Number(wavelengths[minIndex]),
    lowReflectionR: Number(reflectance[minIndex]),
    relativeHighNm: Number(wavelengths[maxIndex]),
    relativeHighR: Number(reflectance[maxIndex]),
    engineering550Nm: Number(wavelengths[nearest550Index]),
  };
}

export function classifyReflectance(reflectance) {
  if (reflectance < 0.02) return { id: "LOW_REFLECTION", label: "低反射点：反射波被明显抑制" };
  if (reflectance >= 0.4) return { id: "RELATIVE_HIGH", label: "相对高反射点：反射波不可忽略" };
  return { id: "INTERMEDIATE", label: "中等反射点：反射与透射均可见" };
}
