import { describe, expect, it } from "vitest";
import { mapThicknessNm, THICKNESS_MAPPING } from "../src/visual/thicknessMapping.js";

describe("Stage C.V1A thickness mapping", () => {
  it("is monotonically non-decreasing for increasing physical thickness", () => {
    const physical = [0, 1, 5, 15, 40, 60, 80, 100, 120, 180, 300, 1000];
    const visual = physical.map(mapThicknessNm);
    for (let index = 1; index < visual.length; index += 1) {
      expect(visual[index]).toBeGreaterThanOrEqual(visual[index - 1]);
    }
  });

  it("enforces minimum visibility and maximum visual thickness", () => {
    expect(mapThicknessNm(0)).toBe(THICKNESS_MAPPING.minVisual);
    expect(mapThicknessNm(1e9)).toBe(THICKNESS_MAPPING.maxVisual);
    expect(mapThicknessNm(94.1781)).toBeGreaterThanOrEqual(THICKNESS_MAPPING.minVisual);
    expect(mapThicknessNm(94.1781)).toBeLessThanOrEqual(THICKNESS_MAPPING.maxVisual);
  });
});
