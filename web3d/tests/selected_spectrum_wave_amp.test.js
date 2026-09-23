import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";
import { PeriodicStackTemplate } from "../src/templates/periodic-stack.js";
import { DefectCavityTemplate } from "../src/templates/defect-cavity.js";
import { calculateWaveAmplitudesFromSpectrum, visualAmplitude } from "../src/core/spectrumWaveAmp.js";

const PUBLIC = resolve(__dirname, "../public");

function loadJson(name) {
  const p = resolve(PUBLIC, "results", `${name}.json`);
  return JSON.parse(readFileSync(p, "utf-8"));
}

describe("Selected Wavelength Spectrum Point Wave Amplitude & Zero-Power Suppression Tests", () => {
  it("verifies zero-power suppression algorithm (four boundary cases)", () => {
    const incAmp = 0.25;

    // R=1, T=0 -> tAmp=0
    const resT0 = visualAmplitude(0, incAmp);
    expect(resT0.amplitude).toBe(0);
    expect(resT0.suppressedAsZero).toBe(true);
    expect(resT0.exaggerated).toBe(false);

    // R=0, T=1 -> rAmp=0
    const resR0 = visualAmplitude(0, incAmp);
    expect(resR0.amplitude).toBe(0);
    expect(resR0.suppressedAsZero).toBe(true);

    // T=1e-14 -> tAmp=0 (under zeroThreshold 1e-10)
    const resNoise = visualAmplitude(1e-14, incAmp);
    expect(resNoise.amplitude).toBe(0);
    expect(resNoise.suppressedAsZero).toBe(true);
    expect(resNoise.exaggerated).toBe(false);

    // T=1e-5 -> tAmp > 0 and marked exaggerated
    const resSmall = visualAmplitude(1e-5, incAmp);
    expect(resSmall.amplitude).toBe(0.04); // clamped to minimumVisible
    expect(resSmall.suppressedAsZero).toBe(false);
    expect(resSmall.exaggerated).toBe(true);
  });

  it("1. wave amplitude changes when selectedWavelengthNm changes", () => {
    const data = loadJson("app_wdm_filter");
    const template = new DefectCavityTemplate(null);

    template.build(data, { selectedWavelengthNm: 1550, polarization: "TE" });
    const peakRAmp = template.waveAmpInfo.rAmp;
    const peakTAmp = template.waveAmpInfo.tAmp;

    template.setWavelengthAndPolarization(1500, "TE");
    const offRAmp = template.waveAmpInfo.rAmp;
    const offTAmp = template.waveAmpInfo.tAmp;

    expect(peakTAmp).toBeGreaterThan(offTAmp);
    expect(offRAmp).toBeGreaterThan(peakRAmp);
  });

  it("2. wave amplitude changes when polarization (TE/TM) switches with different spectra", () => {
    const data = loadJson("app_phone_lens_ar");
    const modifiedData = JSON.parse(JSON.stringify(data));
    modifiedData.TM = {
      wavelengths: modifiedData.TE.wavelengths,
      R: modifiedData.TE.R.map((r) => Math.min(1, r * 2.5 + 0.1)),
      T: modifiedData.TE.T.map((t) => Math.max(0, t * 0.7)),
    };

    const template = new PeriodicStackTemplate(null);
    template.build(modifiedData, { selectedWavelengthNm: 550, polarization: "TE" });
    const teRAmp = template.waveAmpInfo.rAmp;

    template.setWavelengthAndPolarization(550, "TM");
    const tmRAmp = template.waveAmpInfo.rAmp;

    expect(teRAmp).not.toBe(tmRAmp);
  });

  it("3. WDM transmitted wave is significantly stronger at peak (1550nm) than off-peak (1500nm)", () => {
    const data = loadJson("app_wdm_filter");
    const peakRes = calculateWaveAmplitudesFromSpectrum(data, "TE", 1550);
    const offRes = calculateWaveAmplitudesFromSpectrum(data, "TE", 1500);

    expect(peakRes.tSelected).toBeGreaterThan(0.9);
    expect(offRes.tSelected).toBeLessThan(0.05);
    expect(peakRes.tAmp).toBeGreaterThan(offRes.tAmp * 2.0);
  });

  it("4. Laser mirror reflected wave is significantly stronger than transmitted wave at 1064nm", () => {
    const data = loadJson("app_laser_mirror");
    const res = calculateWaveAmplitudesFromSpectrum(data, "TE", 1064);

    expect(res.rSelected).toBeGreaterThan(0.99);
    expect(res.tSelected).toBeLessThan(0.01);
    expect(res.rAmp).toBeGreaterThan(res.tAmp * 3.0);
  });

  it("5. Verifies formula uses sqrt(R/T) rather than R/T or spectrum mean", () => {
    const data = loadJson("app_phone_lens_ar");
    const res = calculateWaveAmplitudesFromSpectrum(data, "TE", 550);

    const baseIncident = 0.25;
    const expectedRawR = baseIncident * Math.sqrt(res.rSelected);
    const expectedRawT = baseIncident * Math.sqrt(res.tSelected);

    expect(res.rawRAmp).toBeCloseTo(expectedRawR, 6);
    expect(res.rawTAmp).toBeCloseTo(expectedRawT, 6);
    expect(res.rawRAmp).not.toBe(baseIncident * res.rSelected);
    
    const meanR = data.TE.R.reduce((a, b) => a + b, 0) / data.TE.R.length;
    expect(res.rSelected).not.toBe(meanR);
  });

  it("6. GENERIC_MULTILAYER_MODE still does NOT display DBR fields", () => {
    const data = loadJson("app_solar_cell_ar");
    const template = new PeriodicStackTemplate(null);
    template.build(data, { selectedWavelengthNm: 550 });

    expect(template.templateMode).toBe("GENERIC_MULTILAYER_MODE");
    expect(template.showDbrStopband).toBe(false);
    expect(template.showPeriodCount).toBe(false);
    expect(template.waveAmplitudeSource).toBe("SELECTED_WAVELENGTH_R_T_SCHEMATIC");
  });
});
