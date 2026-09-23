import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ENGINEERING_CASE_CONFIGS } from "../src/apps/shared/engineeringCaseConfigs.js";
import { resolvePresetWavelength, sampleEngineeringSpectrum } from "../src/apps/shared/engineeringSpectrum.js";

const load = (caseId) => JSON.parse(readFileSync(resolve("public/results", `${caseId}.json`), "utf8"));

describe("standalone engineering case contracts", () => {
  for (const config of Object.values(ENGINEERING_CASE_CONFIGS)) {
    it(`${config.caseId} keeps formal layers and resolves all view presets`, () => {
      const result = load(config.caseId);
      expect(result.layers).toHaveLength(config.expectedLayerCount);
      for (const preset of config.presets) {
        const wavelengthNm = resolvePresetWavelength(result, "TE", preset);
        expect(wavelengthNm).toBeGreaterThanOrEqual(result.wavelength_nm[0]);
        expect(wavelengthNm).toBeLessThanOrEqual(result.wavelength_nm.at(-1));
        const sample = sampleEngineeringSpectrum(result, "TE", wavelengthNm);
        expect(sample.rSelected + sample.tSelected + sample.absorptance).toBeCloseTo(1, 6);
      }
    });
  }

  it("separates WDM passband from stopband using formal T", () => {
    const config = ENGINEERING_CASE_CONFIGS.app_wdm_filter;
    const result = load(config.caseId);
    const pass = sampleEngineeringSpectrum(result, "TE", resolvePresetWavelength(result, "TE", config.presets[0]));
    const stop = sampleEngineeringSpectrum(result, "TE", resolvePresetWavelength(result, "TE", config.presets[2]));
    expect(pass.tSelected).toBeGreaterThan(0.9);
    expect(stop.tSelected).toBeLessThan(0.1);
  });

  it("keeps the laser target in the high-reflection regime", () => {
    const result = load("app_laser_mirror");
    const target = sampleEngineeringSpectrum(result, "TE", 1064);
    expect(target.rSelected).toBeGreaterThan(0.99);
  });
});
