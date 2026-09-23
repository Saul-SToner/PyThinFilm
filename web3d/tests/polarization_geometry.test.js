import { describe, it, expect } from "vitest";
import * as THREE from "three";
import { stableTransverseBasis, SineWaveRenderer } from "../src/core/SineWaveRenderer.js";

describe("Arbitrary 3D Propagation Basis Orthogonality Tests", () => {
  const testVectors = [
    new THREE.Vector3(1, 0, 0),
    new THREE.Vector3(0, 1, 0),
    new THREE.Vector3(0, 0, 1),
    new THREE.Vector3(1, 1, 1).normalize(),
    new THREE.Vector3(-0.5, 0.8, -0.33).normalize(),
  ];

  it("stableTransverseBasis guarantees strict orthogonality (|dot| < 1e-8) for arbitrary 3D rays", () => {
    for (const k of testVectors) {
      const { te, tm } = stableTransverseBasis(k);

      const dotTE_k = Math.abs(te.dot(k));
      const dotTM_k = Math.abs(tm.dot(k));
      const dotTE_TM = Math.abs(te.dot(tm));

      expect(dotTE_k, `|TE . k| for k=${JSON.stringify(k)}`).toBeLessThan(1e-8);
      expect(dotTM_k, `|TM . k| for k=${JSON.stringify(k)}`).toBeLessThan(1e-8);
      expect(dotTE_TM, `|TE . TM| for k=${JSON.stringify(k)}`).toBeLessThan(1e-8);

      expect(te.length(), "TE vector unit length").toBeCloseTo(1.0, 6);
      expect(tm.length(), "TM vector unit length").toBeCloseTo(1.0, 6);
    }
  });

  it("TE polarization oscillates strictly in transverse plane", () => {
    const waveRenderer = new SineWaveRenderer();
    waveRenderer.build([
      {
        id: "te_wave",
        start: [0, 5, 0],
        end: [0, 0, 0],
        amplitude: 0.5,
        wavelength: 1.0,
        speed: 1.0,
        pol: "TE",
        color: 0xef4444,
      },
    ]);

    waveRenderer.update(0.25);
    const line = waveRenderer.getGroup().children[0];
    const posAttr = line.geometry.attributes.position;

    let hasNonZeroZ = false;
    let hasXDisplacement = false;

    for (let i = 0; i < posAttr.count; i++) {
      if (Math.abs(posAttr.getZ(i)) > 0.001) hasNonZeroZ = true;
      if (Math.abs(posAttr.getX(i)) > 0.001) hasXDisplacement = true;
    }

    expect(hasNonZeroZ).toBe(true);
    expect(hasXDisplacement).toBe(false);
  });
});
