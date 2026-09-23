import { describe, it, expect } from "vitest";
import { validateCaseConfig } from "../src/data/caseConfigValidator.js";

describe("Stage B.1B: Case Config & Result Binding Tests", () => {
  it("should validate single_ar and bragg_reflector case configurations", () => {
    const singleArConfig = {
      id: "single_ar",
      display_name: "单层增透膜",
      category: "teaching_thinfilm",
      visualization_template: "single-interface",
    };
    expect(validateCaseConfig(singleArConfig).valid).toBe(true);

    const braggConfig = {
      id: "bragg_reflector",
      display_name: "Bragg反射镜",
      category: "teaching_thinfilm",
      visualization_template: "periodic-stack",
    };
    expect(validateCaseConfig(braggConfig).valid).toBe(true);
  });
});
