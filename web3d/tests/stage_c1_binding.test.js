import { describe, it, expect } from "vitest";
import { validateCaseConfig } from "../src/data/caseConfigValidator.js";

const STAGE_C1_CASES = [
  { id: "quarter_wave_single_layer", visualization_template: "single-interface" },
  { id: "half_wave_single_layer", visualization_template: "single-interface" },
  { id: "high_reflector", visualization_template: "periodic-stack" },
  { id: "quarter_wave_stack", visualization_template: "periodic-stack" },
  { id: "fp_single_halfwave", visualization_template: "defect-cavity" },
  { id: "narrowband_filter", visualization_template: "defect-cavity" },
];

describe("Stage C.1: 6 Teaching Cases Case Config & Binding Validation", () => {
  STAGE_C1_CASES.forEach(({ id, visualization_template }) => {
    it(`should validate case config for ${id}`, () => {
      const config = {
        id,
        display_name: id,
        category: "teaching_main_branch",
        visualization_template,
      };
      expect(validateCaseConfig(config).valid).toBe(true);
    });
  });
});
