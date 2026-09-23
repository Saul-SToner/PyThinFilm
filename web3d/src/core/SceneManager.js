import * as THREE from "three";
import { getVisualTheme } from "../visual/visualTheme.js";

export class SceneManager {
  constructor() {
    this.scene = new THREE.Scene();
    this.currentThemeId = null;
    this.applyVisualTheme("LEGACY_DARK");
  }

  applyVisualTheme(themeId) {
    const theme = getVisualTheme(themeId);
    if (this.currentThemeId === theme.id) return;

    const managedLights = this.scene.children.filter((child) => child.userData?.managedVisualLight);
    managedLights.forEach((light) => this.scene.remove(light));

    this.scene.background = new THREE.Color(theme.background);
    this.scene.fog = theme.fog
      ? new THREE.Fog(theme.fog.color, theme.fog.near, theme.fog.far)
      : null;

    if (theme.lights.hemisphere) {
      const config = theme.lights.hemisphere;
      const light = new THREE.HemisphereLight(config.skyColor, config.groundColor, config.intensity);
      light.userData.managedVisualLight = true;
      this.scene.add(light);
    }

    if (theme.lights.ambient) {
      const config = theme.lights.ambient;
      const light = new THREE.AmbientLight(config.color, config.intensity);
      light.userData.managedVisualLight = true;
      this.scene.add(light);
    }

    for (const key of ["directionalPrimary", "directionalFill"]) {
      const config = theme.lights[key];
      if (!config) continue;
      const light = new THREE.DirectionalLight(config.color, config.intensity);
      light.position.set(...config.position);
      light.userData.managedVisualLight = true;
      this.scene.add(light);
    }

    this.currentThemeId = theme.id;
  }

  getScene() {
    return this.scene;
  }

  fitFogToCamera(camera, target) {
    if (!this.scene.fog || !camera || !target) return false;
    const distance = camera.position.distanceTo(target);
    this.scene.fog.near = Math.max(18, distance * 0.55);
    this.scene.fog.far = Math.max(36, distance * 1.9);
    return true;
  }
}
