import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { getCameraPreset } from "../visual/cameraPresets.js";

export class CameraManager {
  constructor(container) {
    this.container = container;
    const aspect = container.clientWidth / container.clientHeight || 1.0;
    
    this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
    this.camera.position.set(0, 4, 12);

    this.controls = null;
    this.defaultPresetName = null;
    this.currentPresetName = null;
    this.presetBounds = null;
  }

  initControls(rendererDomElement) {
    if (this.controls) {
      this.controls.dispose();
    }
    this.controls = new OrbitControls(this.camera, rendererDomElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.minDistance = 3;
    this.controls.maxDistance = 30;
    this.controls.target.set(0, 0, 0);
    this.controls.update();
  }

  onResize() {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    if (width > 0 && height > 0) {
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
    }
  }

  resetView() {
    if (this.defaultPresetName && this.presetBounds) {
      this.applyPreset(this.defaultPresetName, this.presetBounds);
      return;
    }
    this.camera.position.set(0, 4, 12);
    if (this.controls) {
      this.controls.target.set(0, 0, 0);
      this.controls.update();
    }
  }

  setDefaultPreset(presetName, bounds) {
    this.defaultPresetName = presetName;
    this.presetBounds = bounds ? bounds.clone() : null;
    this.applyPreset(presetName, this.presetBounds);
  }

  clearDefaultPreset() {
    this.defaultPresetName = null;
    this.currentPresetName = null;
    this.presetBounds = null;
    if (this.controls) {
      this.controls.minDistance = 3;
      this.controls.maxDistance = 30;
    }
  }

  applyPreset(presetName, bounds = this.presetBounds) {
    const preset = getCameraPreset(presetName);
    if (!preset || !bounds || bounds.isEmpty()) return false;

    const center = bounds.getCenter(new THREE.Vector3());
    const target = center.clone().add(new THREE.Vector3(...(preset.targetOffset || [0, 0, 0])));
    const size = bounds.getSize(new THREE.Vector3());
    const radius = Math.max(size.length() / 2, 1);
    const direction = new THREE.Vector3(...preset.direction).normalize();
    const distance = Math.max(radius * preset.distanceFactor, 5.5);

    this.camera.position.copy(target).addScaledVector(direction, distance);
    this.camera.lookAt(target);
    this.camera.near = Math.max(distance / 100, 0.05);
    this.camera.far = Math.max(distance * 20, 100);
    this.camera.updateProjectionMatrix();

    if (this.controls) {
      this.controls.target.copy(target);
      this.controls.minDistance = Math.max(radius * preset.minDistanceFactor, 2.4);
      this.controls.maxDistance = Math.max(radius * preset.maxDistanceFactor, 12);
      this.controls.update();
    }
    this.camera.updateMatrixWorld(true);

    this.currentPresetName = preset.id;
    return true;
  }

  getCamera() {
    return this.camera;
  }

  getControls() {
    return this.controls;
  }

  dispose() {
    if (this.controls) {
      this.controls.dispose();
      this.controls = null;
    }
  }
}
