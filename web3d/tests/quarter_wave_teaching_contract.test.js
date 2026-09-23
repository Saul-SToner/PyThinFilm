import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const WEB3D_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const teaching = JSON.parse(readFileSync(resolve(WEB3D_ROOT, "public/teaching/quarter_wave_single_layer.json"), "utf8"));
const formal = JSON.parse(readFileSync(resolve(WEB3D_ROOT, "public/results/quarter_wave_single_layer.json"), "utf8"));

describe("quarter-wave undergraduate teaching contract", () => {
  it("binds the current formal case instead of a duplicate", () => {
    expect(teaching.case_id).toBe(formal.case_id);
    expect(teaching.audience.primary).toBe("UNDERGRADUATE");
    expect(teaching.teaching_modes).toEqual(["FREE_EXPLORATION", "GUIDED_LEARNING"]);
    expect(teaching.formal_context.incidence_angle_deg).toBe(formal.incidence_angle_deg);
    expect(teaching.formal_context.film_thickness_nm).toBe(formal.layers[0].thickness_nm);
    expect(teaching.formal_context.te_r_550).toBe(formal.design_point_550nm.TE.R);
    expect(teaching.formal_context.tm_r_550).toBe(formal.design_point_550nm.TM.R);
  });

  it("defines case-specific evidence-bound guided steps", () => {
    expect(teaching.guided_steps.map((step) => step.id)).toEqual([
      "identify_layer", "design_wavelength", "off_design", "polarization", "summary_quiz",
    ]);
    expect(teaching.guided_steps.every((step) => step.evidence_fields.length > 0)).toBe(true);
    expect(teaching.guided_steps.some((step) => step.action.type === "set_thickness")).toBe(false);
  });

  it("does not claim normal-incidence TE/TM equivalence for the 45-degree export", () => {
    expect(teaching.formal_context.incidence_angle_deg).toBe(45);
    expect(teaching.formal_context.te_r_550).not.toBe(teaching.formal_context.tm_r_550);
    expect(teaching.common_misconceptions.join(" ")).toContain("45°");
  });
});

