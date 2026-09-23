import { describe, it, expect } from "vitest";
import { validateCaseConfig } from "../src/data/caseConfigValidator.js";

describe("Stage B.1C: FP Filter Case Config & Result Binding Tests", () => {
  it("should validate fp_filter case configuration", () => {
    const fpConfig = {
      id: "fp_filter",
      display_name: "F-P干涉滤光片",
      category: "teaching_thinfilm",
      visualization_template: "defect-cavity",
    };
    expect(validateCaseConfig(fpConfig).valid).toBe(true);
  });
});
