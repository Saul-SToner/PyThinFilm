import { describe, expect, it } from "vitest";
import * as THREE from "three";
import {
  createLayerAppearance,
  createLayerOutline,
  setLayerInteractionState,
} from "../src/visual/layerAppearance.js";

describe("Stage C.V1A layer appearance", () => {
  it("creates dielectric layers without metalness and with a fine outline", () => {
    const geometry = new THREE.BoxGeometry(1, 0.2, 1);
    const appearance = createLayerAppearance("SiO2");
    const outline = createLayerOutline(geometry, appearance.outlineColor);

    expect(appearance.material.metalness).toBe(0);
    expect(appearance.material.roughness).toBeGreaterThan(0.5);
    expect(outline.isLineSegments).toBe(true);
    expect(outline.material.opacity).toBeLessThan(1);

    outline.geometry.dispose();
    outline.material.dispose();
    appearance.material.dispose();
    geometry.dispose();
  });

  it("applies hover, persistent selection, and reset states without replacing the mesh", () => {
    const appearance = createLayerAppearance("TiO2");
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), appearance.material);

    setLayerInteractionState(mesh, { hovered: true, selected: false });
    expect(mesh.userData.interactionState).toEqual({ hovered: true, selected: false });
    expect(mesh.scale.x).toBeGreaterThan(1);

    setLayerInteractionState(mesh, { hovered: false, selected: true });
    expect(mesh.userData.interactionState).toEqual({ hovered: false, selected: true });
    expect(mesh.material.emissiveIntensity).toBeGreaterThan(0);

    setLayerInteractionState(mesh, { hovered: false, selected: false });
    expect(mesh.scale.x).toBe(1);
    expect(mesh.material.emissiveIntensity).toBe(0);

    mesh.geometry.dispose();
    mesh.material.dispose();
  });
});
