import { describe, it, expect, vi, beforeEach } from "vitest";
import * as THREE from "three";
import { SceneManager } from "../src/core/SceneManager.js";
import { RendererLifecycle } from "../src/core/RendererLifecycle.js";
import { ResourceDisposer } from "../src/core/ResourceDisposer.js";
import { validateCaseConfig } from "../src/data/caseConfigValidator.js";

// Robust WebGL Proxy mock for headless JSDOM testing
beforeEach(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation((contextType) => {
    if (contextType.includes("webgl")) {
      const baseMock = {
        canvas: document.createElement("canvas"),
        getExtension: (name) => {
          if (name === "WEBGL_lose_context") {
            return { loseContext: () => {}, restoreContext: () => {} };
          }
          return null;
        },
        getParameter: () => "WebGL 2.0",
        getShaderPrecisionFormat: () => ({ precision: 24, rangeMin: 1, rangeMax: 1 }),
        getShaderParameter: () => true,
        getProgramParameter: () => true,
      };
      return new Proxy(baseMock, {
        get: (target, prop) => {
          if (prop in target) return target[prop];
          return () => {};
        },
      });
    }
    return null;
  });
});

describe("50 次场景切换生命周期回归测试 (Stage B.0.1)", () => {
  it("should validate case configuration schema correctly", () => {
    const validCase = {
      id: "single_ar",
      display_name: "单层增透膜",
      category: "teaching_thinfilm",
      visualization_template: "single-interface",
    };
    expect(validateCaseConfig(validCase).valid).toBe(true);

    const invalidCase = { id: "bad_case" };
    expect(validateCaseConfig(invalidCase).valid).toBe(false);
  });

  it("should execute 50 scene switches while reusing single WebGLRenderer and disposing resources cleanly", () => {
    const container = document.createElement("div");
    container.style.width = "800px";
    container.style.height = "600px";
    document.body.appendChild(container);

    const sceneManager = new SceneManager();
    const scene = sceneManager.getScene();
    const rendererLifecycle = new RendererLifecycle(container);

    const initialRenderer = rendererLifecycle.getRenderer();
    expect(initialRenderer).toBeDefined();

    let totalGeoDisposeCalls = 0;
    let totalMatDisposeCalls = 0;
    let totalTexDisposeCalls = 0;

    // Simulate 50 case switches
    for (let i = 0; i < 50; i += 1) {
      // 7. Verify Renderer instance remains the same object throughout all switches
      expect(rendererLifecycle.getRenderer()).toBe(initialRenderer);

      // Build mock case scene objects with spied dispose methods
      const mockGroup = new THREE.Group();
      mockGroup.name = `caseGroup_${i}`;

      const geo = new THREE.BoxGeometry(1, 1, 1);
      const mat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
      const tex = new THREE.Texture();
      mat.map = tex;

      const geoSpy = vi.spyOn(geo, "dispose");
      const matSpy = vi.spyOn(mat, "dispose");
      const texSpy = vi.spyOn(tex, "dispose");

      const mesh = new THREE.Mesh(geo, mat);
      mockGroup.add(mesh);
      scene.add(mockGroup);

      // Case switch: Dispose current scene subtree
      ResourceDisposer.disposeObject(mockGroup);
      scene.remove(mockGroup);

      if (geoSpy.mock.calls.length > 0) totalGeoDisposeCalls += 1;
      if (matSpy.mock.calls.length > 0) totalMatDisposeCalls += 1;
      if (texSpy.mock.calls.length > 0) totalTexDisposeCalls += 1;
    }

    // 1. Scene sub-nodes return to baseline lights
    expect(scene.children.length).toBeLessThan(10);

    // 2. Geometry.dispose called
    expect(totalGeoDisposeCalls).toBe(50);

    // 3. Material.dispose called
    expect(totalMatDisposeCalls).toBe(50);

    // 4. Texture.dispose called
    expect(totalTexDisposeCalls).toBe(50);

    // 8. forceContextLoss is NOT called during case switches
    expect(rendererLifecycle.contextLossCount).toBe(0);

    // 9. Teardown test: renderer.dispose and forceContextLoss called ONCE on app unmount
    rendererLifecycle.teardown();
    expect(rendererLifecycle.contextLossCount).toBe(1);
    expect(rendererLifecycle.disposeCount).toBe(1);

    document.body.removeChild(container);
  });
});
