import { describe, it, expect } from "vitest";
import { SingleInterfaceTemplate } from "../src/templates/single-interface.js";
import { DefectCavityTemplate } from "../src/templates/defect-cavity.js";
import { ResourceDisposer } from "../src/core/ResourceDisposer.js";

describe("Wave Lifecycle & Resource Disposal Metrics Tests", () => {
  it("disposes wave objects completely when template dispose is called", () => {
    const t = new SingleInterfaceTemplate(null);
    t.build(null, { polarization: "TE" });

    expect(t.waveRenderer.waveCount).toBe(3);

    const initialGeoCount = ResourceDisposer.geometryDisposeCount;
    const initialMatCount = ResourceDisposer.materialDisposeCount;

    t.dispose();

    expect(t.waveRenderer.waveCount).toBe(0);
    expect(t.group.children.length).toBe(0);

    expect(ResourceDisposer.geometryDisposeCount).toBeGreaterThan(initialGeoCount);
    expect(ResourceDisposer.materialDisposeCount).toBeGreaterThan(initialMatCount);
  });

  it("verifies F-P teaching standing wave semantics and clean disposal", () => {
    const cavityTemp = new DefectCavityTemplate(null);
    cavityTemp.build(null, { polarization: "TM" });

    expect(cavityTemp.animationSemantics).toBe("TEACHING_ILLUSTRATION");
    expect(cavityTemp.fieldAmplitudeSource).toBe("VISUAL_EQUAL_AMPLITUDE");
    expect(cavityTemp.quantitativeFieldStatus).toBe("NOT_AVAILABLE");
    expect(cavityTemp.waveRenderer.waveCount).toBe(4);

    cavityTemp.dispose();

    expect(cavityTemp.waveRenderer.waveCount).toBe(0);
    expect(cavityTemp.group.children.length).toBe(0);
  });
});
