import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { FP_STRUCTURE_REGIONS } from "../apps/fp-filter/FpVisualStory.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

describe("F-P case-specific visual story", () => {
  it("maps all 13 formal layers into two DBRs and one central cavity", () => {
    const formal = JSON.parse(readFileSync(resolve(ROOT, "public/results/fp_filter.json"), "utf8"));
    const covered = FP_STRUCTURE_REGIONS.flatMap((region) =>
      Array.from({ length: region.layerEnd - region.layerStart + 1 }, (_, offset) => region.layerStart + offset)
    );

    expect(covered).toEqual(Array.from({ length: formal.layers.length }, (_, index) => index));
    expect(new Set(covered).size).toBe(formal.layers.length);
    expect(FP_STRUCTURE_REGIONS.map((region) => region.id)).toEqual([
      "incident_dbr",
      "defect_cavity",
      "substrate_dbr",
    ]);
    expect(formal.layers[6].type).toBe("C");
    expect(FP_STRUCTURE_REGIONS[1]).toMatchObject({ layerStart: 6, layerEnd: 6, focusLayer: 6 });
  });

  it("keeps every visual region annotation structural rather than field-derived", () => {
    expect(FP_STRUCTURE_REGIONS.every((region) => !/field|场强|enhancement/i.test(region.label))).toBe(true);
  });
});
