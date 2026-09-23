import { describe, it, expect } from "vitest";
import { PeriodicStackTemplate } from "../src/templates/periodic-stack.js";
import { readFileSync } from "fs";
import { resolve } from "path";

const PUBLIC = resolve(__dirname, "../public");

function loadJson(name) {
  const p = resolve(PUBLIC, "results", `${name}.json`);
  return JSON.parse(readFileSync(p, "utf-8"));
}

describe("PeriodicStackTemplate GENERIC_MULTILAYER_MODE & Dynamic Wave Semantics Tests", () => {
  it("validates app_solar_cell_ar GENERIC_MULTILAYER_MODE flags", () => {
    const data = loadJson("app_solar_cell_ar");
    const template = new PeriodicStackTemplate(null);
    template.build(data, { polarization: "TE" });

    expect(template.templateMode).toBe("GENERIC_MULTILAYER_MODE");
    expect(template.isGenericMultilayerMode).toBe(true);
    expect(template.showDbrStopband).toBe(false);
    expect(template.showPeriodCount).toBe(false);
    expect(template.showRepresentativeInternalDbrWaves).toBe(false);
    expect(template.waveAmplitudeSource).toBe("SELECTED_WAVELENGTH_R_T_SCHEMATIC");
    expect(template.animationSemantics).toBe("TEACHING_ILLUSTRATION");
  });

  it("validates app_phone_lens_ar GENERIC_MULTILAYER_MODE flags", () => {
    const data = loadJson("app_phone_lens_ar");
    const template = new PeriodicStackTemplate(null);
    template.build(data, { polarization: "TM" });

    expect(template.templateMode).toBe("GENERIC_MULTILAYER_MODE");
    expect(template.isGenericMultilayerMode).toBe(true);
    expect(template.showDbrStopband).toBe(false);
    expect(template.showPeriodCount).toBe(false);
    expect(template.showRepresentativeInternalDbrWaves).toBe(false);
    expect(template.waveAmplitudeSource).toBe("SELECTED_WAVELENGTH_R_T_SCHEMATIC");
    expect(template.animationSemantics).toBe("TEACHING_ILLUSTRATION");
  });

  it("remains in DBR_PERIODIC_MODE for high_reflector and laser mirror but uses SELECTED_WAVELENGTH_R_T_SCHEMATIC", () => {
    const data = loadJson("app_laser_mirror");
    const template = new PeriodicStackTemplate(null);
    template.build(data, { polarization: "TE" });

    expect(template.templateMode).toBe("DBR_PERIODIC_MODE");
    expect(template.isGenericMultilayerMode).toBe(false);
    expect(template.showDbrStopband).toBe(true);
    expect(template.showPeriodCount).toBe(true);
    expect(template.waveAmplitudeSource).toBe("SELECTED_WAVELENGTH_R_T_SCHEMATIC");
    expect(template.animationSemantics).toBe("TEACHING_ILLUSTRATION");
  });
});
