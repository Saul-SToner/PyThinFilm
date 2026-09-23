import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";
import {
  classifyReflectance,
  getSolarComparisonPoints,
  sampleSolarSpectrum,
} from "../src/apps/solar-ar/solarSpectrum.js";

const data = JSON.parse(readFileSync(resolve(__dirname, "../public/results/app_solar_cell_ar.json"), "utf-8"));

describe("standalone solar AR spectrum readout", () => {
  it("finds a genuinely low-reflection point and a distinct relative-high point", () => {
    const points = getSolarComparisonPoints(data, "TE");
    expect(points.lowReflectionR).toBeLessThan(0.01);
    expect(points.relativeHighR).toBeGreaterThan(0.4);
    expect(points.relativeHighR / points.lowReflectionR).toBeGreaterThan(100);
  });

  it("reports 550 nm as relative-high rather than automatically claiming anti-reflection", () => {
    const sample = sampleSolarSpectrum(data, "TE", 550);
    expect(sample.rSelected).toBeGreaterThan(0.4);
    expect(classifyReflectance(sample.rSelected).id).toBe("RELATIVE_HIGH");
  });

  it("keeps zero absorption and the R/T amplitude binding", () => {
    const points = getSolarComparisonPoints(data, "TE");
    const sample = sampleSolarSpectrum(data, "TE", points.lowReflectionNm);
    expect(sample.absorptance).toBe(0);
    expect(sample.rawRAmp).toBeCloseTo(0.25 * Math.sqrt(sample.rSelected), 8);
    expect(sample.rawTAmp).toBeCloseTo(0.25 * Math.sqrt(sample.tSelected), 8);
  });
});
