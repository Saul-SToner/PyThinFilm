import { describe, expect, it } from "vitest";
import { EVIDENCE_CASE_CONFIGS, getEvidenceCaseConfig } from "../src/apps/evidence/evidenceCaseConfigs.js";

describe("external evidence app configuration", () => {
  it("declares twelve unique standalone entries", () => {
    const entries = Object.entries(EVIDENCE_CASE_CONFIGS);
    expect(entries).toHaveLength(12);
    expect(new Set(entries.map(([, config]) => config.slug)).size).toBe(12);
    expect(entries.every(([, config]) => config.sceneType && config.sceneNote)).toBe(true);
  });

  it("resolves immutable configs without inventing renderer state", () => {
    const config = getEvidenceCaseConfig("advanced_ar_bundle");
    expect(config).toEqual(expect.objectContaining({
      caseId: "advanced_ar_bundle",
      slug: "advanced-ar-bundle",
    }));
    expect(Object.isFrozen(config)).toBe(true);
  });

  it("rejects undeclared cases", () => {
    expect(() => getEvidenceCaseConfig("unknown_case")).toThrow(/未声明外部证据案例/);
  });
});
