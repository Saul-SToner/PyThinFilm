import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { CameraManager } from "../src/core/CameraManager.js";
import { SceneManager } from "../src/core/SceneManager.js";
import { CAMERA_PRESETS, isValidCameraPreset } from "../src/visual/cameraPresets.js";

describe("Stage C.V1A camera presets", () => {
  it("declares the three required valid presets and no TOP_VIEW", () => {
    expect(Object.keys(CAMERA_PRESETS)).toEqual([
      "ISOMETRIC_SECTION",
      "SIDE_SECTION",
      "OPTICAL_PATH",
    ]);
    Object.keys(CAMERA_PRESETS).forEach((name) => expect(isValidCameraPreset(name)).toBe(true));
    expect(isValidCameraPreset("TOP_VIEW")).toBe(false);
  });

  it("frames bounds and resets to ISOMETRIC_SECTION", () => {
    const container = document.createElement("div");
    const manager = new CameraManager(container);
    const bounds = new THREE.Box3(
      new THREE.Vector3(-3, -3, -2),
      new THREE.Vector3(3, 0, 2)
    );
    manager.setDefaultPreset("ISOMETRIC_SECTION", bounds);
    const defaultPosition = manager.getCamera().position.clone();

    expect(manager.currentPresetName).toBe("ISOMETRIC_SECTION");
    expect(manager.applyPreset("SIDE_SECTION", bounds)).toBe(true);
    expect(manager.currentPresetName).toBe("SIDE_SECTION");
    expect(manager.getCamera().position.equals(defaultPosition)).toBe(false);

    manager.resetView();
    expect(manager.currentPresetName).toBe("ISOMETRIC_SECTION");
    expect(manager.getCamera().position.distanceTo(defaultPosition)).toBeLessThan(1e-10);
  });

  it("extends academic fog for unusually tall structures", () => {
    const sceneManager = new SceneManager();
    sceneManager.applyVisualTheme("ACADEMIC_LIGHT");
    const camera = new THREE.PerspectiveCamera();
    camera.position.set(0, 0, 50);
    expect(sceneManager.fitFogToCamera(camera, new THREE.Vector3())).toBe(true);
    expect(sceneManager.getScene().fog.near).toBeGreaterThan(18);
    expect(sceneManager.getScene().fog.far).toBeGreaterThan(36);
  });
});
