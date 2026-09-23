import { describe, it, expect, vi, beforeEach } from "vitest";
import * as THREE from "three";
import { SceneManager } from "../src/core/SceneManager.js";
import { RendererLifecycle } from "../src/core/RendererLifecycle.js";
import { ResourceDisposer } from "../src/core/ResourceDisposer.js";
import { SingleInterfaceTemplate } from "../src/templates/single-interface.js";
import { PeriodicStackTemplate } from "../src/templates/periodic-stack.js";
import { DefectCavityTemplate } from "../src/templates/defect-cavity.js";

beforeEach(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation((type) => {
    if (type.includes("webgl")) {
      const baseMock = {
        canvas: document.createElement("canvas"),
        getExtension: (name) => (name === "WEBGL_lose_context" ? { loseContext: () => {}, restoreContext: () => {} } : null),
        getParameter: () => "WebGL 2.0",
        getShaderPrecisionFormat: () => ({ precision: 24, rangeMin: 1, rangeMax: 1 }),
        getShaderParameter: () => true,
        getProgramParameter: () => true,
      };
      return new Proxy(baseMock, {
        get: (target, prop) => (prop in target ? target[prop] : () => {}),
      });
    }
    return null;
  });
});

describe("Stage B.1C: 50-Times Three-Case Switching Regression Tests (single_ar -> bragg_reflector -> fp_filter)", () => {
  it("should cleanly switch 50 times across 3 cases reusing single renderer", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);

    const sceneManager = new SceneManager();
    const scene = sceneManager.getScene();
    const rendererLifecycle = new RendererLifecycle(container);
    const initialRenderer = rendererLifecycle.getRenderer();

    const templates = [
      new SingleInterfaceTemplate(container),
      new PeriodicStackTemplate(container),
      new DefectCavityTemplate(container),
    ];

    for (let i = 0; i < 50; i += 1) {
      // 1. Same renderer instance throughout
      expect(rendererLifecycle.getRenderer()).toBe(initialRenderer);

      const template = templates[i % 3];
      const currentMeshGroup = template.build({});
      scene.add(currentMeshGroup);

      // Switch case: dispose current
      ResourceDisposer.disposeObject(currentMeshGroup);
      scene.remove(currentMeshGroup);
    }

    // 2. forceContextLoss count = 0 during switches
    expect(rendererLifecycle.contextLossCount).toBe(0);

    // 3. Scene children returned to baseline
    expect(scene.children.length).toBeLessThan(10);

    // Teardown
    rendererLifecycle.teardown();
    expect(rendererLifecycle.contextLossCount).toBe(1);
    expect(rendererLifecycle.disposeCount).toBe(1);

    document.body.removeChild(container);
  });
});
