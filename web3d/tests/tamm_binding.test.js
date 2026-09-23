import { describe, it, expect } from "vitest";
import { MetalDbrInterfaceTemplate } from "../src/templates/metal-dbr-interface.js";
import { SineWaveRenderer } from "../src/core/SineWaveRenderer.js";
import { readFileSync } from "fs";
import { resolve } from "path";

const PUBLIC = resolve(__dirname, "../public");

function loadJson(name) {
  const p = resolve(PUBLIC, "results", `${name}.json`);
  return JSON.parse(readFileSync(p, "utf-8"));
}

describe("Tamm Python Field Profile Binding, Spatial Regions & Wave Envelope Tests", () => {
  it("binds Python field profile from tamm_phase_bundle.json and satisfies H1_region_peak > deep_DBR_region_peak", () => {
    const data = loadJson("tamm_phase_bundle");
    const template = new MetalDbrInterfaceTemplate(null);
    template.build(data, { polarization: "TE" });

    expect(template.fieldEnvelopeSource).toBe("PYTHON_FIELD_PROFILE");
    expect(template.fieldEnvelope.length).toBeGreaterThan(0);
    expect(template.fieldEnvelope.every(Number.isFinite)).toBe(true);

    const len = template.fieldEnvelope.length;
    // Peak is in H1 region (z ~ 77nm, normalized_abs_E2 = 1.0)
    const h1RegionPeak = Math.max(...template.fieldEnvelope.slice(0, Math.floor(len * 0.3)));
    // Deep DBR tail region (z > 450nm)
    const deepDbrRegionPeak = Math.max(...template.fieldEnvelope.slice(Math.floor(len * 0.8)));

    expect(h1RegionPeak).toBeCloseTo(1.0, 3); // Peak in H1
    expect(h1RegionPeak).toBeGreaterThan(deepDbrRegionPeak);
  });

  it("gracefully falls back to ANALYTIC_VISUAL_ENVELOPE when python field profile is absent", () => {
    const template = new MetalDbrInterfaceTemplate(null);
    template.build(null, { polarization: "TM" });

    expect(template.fieldEnvelopeSource).toBe("ANALYTIC_VISUAL_ENVELOPE");
    expect(template.fieldEnvelope.length).toBeGreaterThan(0);
    expect(template.fieldEnvelope.every(Number.isFinite)).toBe(true);
  });

  it("verifies that amplitudeEnvelope dynamically changes wave positions in space at t > 0", () => {
    const rendererFlat = new SineWaveRenderer();
    const rendererDecay = new SineWaveRenderer();

    const flatEnv = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0];
    const decayEnv = [1.0, 0.8, 0.5, 0.3, 0.1, 0.05, 0.02, 0.01, 0.0, 0.0];

    const descFlat = [{
      id: "wave_flat",
      start: [0, 5, 0],
      end: [0, 0, 0],
      amplitude: 1.0,
      wavelength: 1.0,
      speed: 1.0,
      pol: "TE",
      color: 0xff0000,
      amplitudeEnvelope: flatEnv,
    }];

    const descDecay = [{
      id: "wave_decay",
      start: [0, 5, 0],
      end: [0, 0, 0],
      amplitude: 1.0,
      wavelength: 1.0,
      speed: 1.0,
      pol: "TE",
      color: 0x00ff00,
      amplitudeEnvelope: decayEnv,
    }];

    rendererFlat.build(descFlat);
    rendererDecay.build(descDecay);

    rendererFlat.update(0.25);
    rendererDecay.update(0.25);

    const posFlat = rendererFlat.getWavePositions()[0];
    const posDecay = rendererDecay.getWavePositions()[0];

    // Check Z displacement component (TE oscillation axis) at middle index of segment
    const midIdx = Math.floor(posFlat.length / 2); // Z coordinate is index + 2
    const zIdx = Math.floor(midIdx / 3) * 3 + 2;

    expect(Math.abs(posFlat[zIdx])).toBeGreaterThan(0.001);
    expect(Math.abs(posFlat[zIdx] - posDecay[zIdx])).toBeGreaterThan(0.001);
  });
});
