import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const PUBLIC = resolve(__dirname, "../public");

function loadJson(name) {
  const p = resolve(PUBLIC, "results", `${name}.json`);
  return JSON.parse(readFileSync(p, "utf-8"));
}

describe("Stage C.2.1B-1.1 Four Engineering Cases Result JSON Binding & Audit Tests", () => {
  it("loads and validates app_solar_cell_ar.json", () => {
    const data = loadJson("app_solar_cell_ar");
    expect(data.case_id).toBe("app_solar_cell_ar");
    expect(data.template_mode).toBe("GENERIC_MULTILAYER_MODE");
    expect(data.run_builder_parameter_match).toBe(true);
    expect(data.layer_stack_hash).toBeTruthy();
    expect(data.coating_layer_count).toBe(3);
    expect(data.layers.map((l) => l.name)).toEqual(["SiO2", "TiO2", "MgF2"]);
    expect(data.TE.R.length).toBeGreaterThan(0);
    expect(data.metrics.avg_R_300_1100nm).toBeCloseTo(0.3868, 2);
  });

  it("loads and validates app_wdm_filter.json isolation metrics", () => {
    const data = loadJson("app_wdm_filter");
    expect(data.case_id).toBe("app_wdm_filter");
    expect(data.template_mode).toBe("DEFECT_CAVITY_MODE");
    expect(data.run_builder_parameter_match).toBe(true);
    expect(data.layer_stack_hash).toBeTruthy();
    expect(data.coating_layer_count).toBe(17);
    expect(data.layers[8].name).toBe("C");
    
    // Isolation sign & relation assertions
    expect(data.metrics.isolation_dB).toBeGreaterThanOrEqual(0.0);
    expect(data.metrics.off_peak_transmission_dB).toBeLessThanOrEqual(0.0);
    expect(Math.abs(data.metrics.isolation_dB + data.metrics.off_peak_transmission_dB)).toBeLessThan(1e-4);
  });

  it("loads and validates app_laser_mirror.json", () => {
    const data = loadJson("app_laser_mirror");
    expect(data.case_id).toBe("app_laser_mirror");
    expect(data.template_mode).toBe("DBR_PERIODIC_MODE");
    expect(data.run_builder_parameter_match).toBe(true);
    expect(data.coating_layer_count).toBe(17);
    expect(data.TE.R.length).toBeGreaterThan(0);
    expect(data.metrics.peak_reflectance).toBeGreaterThan(0.99);
  });

  it("loads and validates app_phone_lens_ar.json", () => {
    const data = loadJson("app_phone_lens_ar");
    expect(data.case_id).toBe("app_phone_lens_ar");
    expect(data.template_mode).toBe("GENERIC_MULTILAYER_MODE");
    expect(data.run_builder_parameter_match).toBe(true);
    expect(data.coating_layer_count).toBe(3);
    expect(data.layers.map((l) => l.name)).toEqual(["SiO2", "ZrO2", "MgF2"]);
    expect(data.TE.R.length).toBeGreaterThan(0);
    expect(data.metrics.avg_R_visible).toBeCloseTo(0.155, 2);
  });
});
