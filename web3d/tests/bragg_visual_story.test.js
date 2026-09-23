import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  BRAGG_STRUCTURE_REGIONS,
  getBraggPolarizationComparison,
} from "../apps/bragg-reflector/BraggVisualStory.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const formal = JSON.parse(readFileSync(resolve(ROOT, "public/results/bragg_reflector.json"), "utf8"));

describe("Bragg case-specific visual story", () => {
  it("maps the formal H/L/H/L/H/L/H sequence to three periods plus terminal H", () => {
    const covered = BRAGG_STRUCTURE_REGIONS.flatMap((region) =>
      Array.from({ length: region.layerEnd - region.layerStart + 1 }, (_, offset) => region.layerStart + offset)
    );

    expect(formal.layers.map((layer) => layer.type)).toEqual(["H", "L", "H", "L", "H", "L", "H"]);
    expect(covered).toEqual([0, 1, 2, 3, 4, 5, 6]);
    expect(new Set(covered).size).toBe(7);
    expect(BRAGG_STRUCTURE_REGIONS.slice(0, 3).every((region) => region.sequence === "H/L")).toBe(true);
    expect(BRAGG_STRUCTURE_REGIONS[3]).toMatchObject({ id: "terminal_h", layerStart: 6, layerEnd: 6, sequence: "H" });
  });

  it("reads the formal TE/TM polarization split at 498 nm without recomputation", () => {
    const comparison = getBraggPolarizationComparison(formal, 498);
    expect(comparison.wavelengthNm).toBe(498);
    expect(comparison.teR).toBe(formal.stopband_metrics.TE.selected_segment.max_R);
    expect(comparison.tmR).toBe(formal.stopband_metrics.TM.selected_segment.max_R);
    expect(comparison.deltaR).toBeCloseTo(0.172214, 6);
  });
});
