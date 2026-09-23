import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const load = (folder, caseId) => JSON.parse(readFileSync(resolve(ROOT, `public/${folder}/${caseId}.json`), "utf8"));
const caseIds = ["bragg_reflector", "fp_filter", "tamm_phase_bundle"];

describe("case-specific teaching mainline contracts", () => {
  it("declares distinct undergraduate content and evidence-bound steps", () => {
    const contracts = caseIds.map((caseId) => load("teaching", caseId));
    expect(new Set(contracts.map((item) => item.problem_statement)).size).toBe(3);
    for (const contract of contracts) {
      expect(contract.audience.primary).toBe("UNDERGRADUATE");
      expect(contract.guided_steps).toHaveLength(5);
      expect(contract.guided_steps.every((step) => step.evidence_fields.length > 0)).toBe(true);
      expect(contract.guided_steps.some((step) => step.action.type === "set_thickness")).toBe(false);
      expect(contract.formula_sections.length).toBeGreaterThanOrEqual(2);
    }
  });

  it("binds Bragg stopband claims to formal metrics", () => {
    const teaching = load("teaching", "bragg_reflector");
    const formal = load("results", "bragg_reflector");
    expect(teaching.formal_context.layer_count).toBe(formal.layers.length);
    expect(teaching.formal_context.te_peak_r).toBe(formal.stopband_metrics.TE.selected_segment.max_R);
    expect(teaching.formal_context.tm_peak_r).toBe(formal.stopband_metrics.TM.selected_segment.max_R);
    expect(teaching.formal_context.te_stopband_nm).toEqual([
      formal.stopband_metrics.TE.selected_segment.start_nm,
      formal.stopband_metrics.TE.selected_segment.end_nm,
    ]);
  });

  it("distinguishes the F-P defect mode from global transmission maxima", () => {
    const teaching = load("teaching", "fp_filter");
    const formal = load("results", "fp_filter");
    expect(teaching.formal_context.te_peak_nm).toBe(formal.resonance_metrics.TE.selected_peak.wavelength_nm);
    expect(teaching.formal_context.tm_peak_nm).toBe(formal.resonance_metrics.TM.selected_peak.wavelength_nm);
    expect(formal.global_transmission_metrics.TE.wavelength_nm).not.toBe(teaching.formal_context.te_peak_nm);
    expect(teaching.formal_context.te_q).toBe(formal.case_specific_metrics.audited_linewidth_TE.q_factor);
  });

  it("keeps the Tamm conclusion at leaky-candidate strength", () => {
    const teaching = load("teaching", "tamm_phase_bundle");
    const formal = load("results", "tamm_phase_bundle");
    expect(teaching.formal_context.candidate_wavelength_nm).toBe(formal.selected_candidate.wavelength_nm);
    expect(teaching.formal_context.candidate_a).toBe(formal.selected_candidate.A);
    expect(teaching.formal_context.phase_residual_deg).toBe(formal.common_reference_phase_metrics.phase_residual_common_deg);
    expect(formal.tamm_validation_status).toBe("PHASE_MATCHED_LEAKY_CANDIDATE");
    expect(teaching.context_callout.text).toContain("PHASE_MATCHED_LEAKY_CANDIDATE");
  });
});
