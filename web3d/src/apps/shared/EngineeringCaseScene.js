import * as THREE from "three";
import { SineWaveRenderer } from "../../core/SineWaveRenderer.js";
import { ResourceDisposer } from "../../core/ResourceDisposer.js";
import { getVisualTheme } from "../../visual/visualTheme.js";
import { mapThicknessNm, THICKNESS_MAPPING } from "../../visual/thicknessMapping.js";
import {
  createLayerAppearance,
  createLayerOutline,
  setLayerInteractionState,
} from "../../visual/layerAppearance.js";
import { sampleEngineeringSpectrum } from "./engineeringSpectrum.js";

export const ENGINEERING_WAVE_DISPLAY_SCALE = 2.2;

function cleanMaterialName(name) {
  return String(name || "Substrate").replace(/\s*\(.*\)\s*$/, "");
}

function layerMaterialName(layer) {
  return String(layer.name || layer.type || `Layer-${layer.layer_index || "?"}`);
}

export class EngineeringCaseScene {
  constructor({ config, container, camera, domElement, onLayerFocus, onWaveInfo }) {
    this.config = config;
    this.container = container;
    this.camera = camera;
    this.domElement = domElement;
    this.onLayerFocus = onLayerFocus;
    this.onWaveInfo = onWaveInfo;
    this.group = new THREE.Group();
    this.group.name = config.sceneName;
    this.waveRenderer = new SineWaveRenderer();
    this.group.add(this.waveRenderer.getGroup());
    this.caseResult = null;
    this.polarization = "TE";
    this.selectedWavelengthNm = null;
    this.waveAmpInfo = null;
    this.layerMeshes = [];
    this.structureMeshes = [];
    this.resources = [];
    this.listenerCleanup = [];
    this.hoveredLayerIndex = null;
    this.selectedLayerIndex = null;
    this.directionGroup = null;
    this.polarizationArrow = null;
  }

  build(caseResult, options = {}) {
    this.caseResult = caseResult;
    this.polarization = options.polarization || "TE";
    this.selectedWavelengthNm = options.selectedWavelengthNm;
    const layers = caseResult.layers || [];
    if (layers.length !== this.config.expectedLayerCount) {
      throw new Error(`${this.config.caseId} 正式膜层应为 ${this.config.expectedLayerCount} 层，实际为 ${layers.length} 层`);
    }

    const width = 6;
    const depth = 4;
    let currentY = 0;
    layers.forEach((layer, index) => {
      const visualThickness = mapThicknessNm(layer.thickness_nm);
      const geometry = new THREE.BoxGeometry(width, visualThickness, depth);
      const materialName = layerMaterialName(layer);
      const appearance = createLayerAppearance(materialName, { themeId: "ACADEMIC_LIGHT", opacity: 0.9 });
      const mesh = new THREE.Mesh(geometry, appearance.material);
      mesh.name = `${this.config.slug}_layer_${index + 1}_${materialName}`;
      mesh.position.y = currentY - visualThickness / 2;
      mesh.userData = {
        isInteractiveLayer: true,
        layerIndex: index,
        layerNumber: index + 1,
        materialName,
        thicknessNm: Number(layer.thickness_nm),
      };
      mesh.add(createLayerOutline(geometry, appearance.outlineColor));
      this.group.add(mesh);
      this.layerMeshes.push(mesh);
      this.structureMeshes.push(mesh);
      this.resources.push(mesh);
      currentY -= visualThickness;
    });

    const substrateLabel = caseResult.substrate?.name || "Substrate";
    const substrateGeometry = new THREE.BoxGeometry(width + 0.3, THICKNESS_MAPPING.substrateVisual, depth + 0.3);
    const substrateAppearance = createLayerAppearance(cleanMaterialName(substrateLabel), { themeId: "ACADEMIC_LIGHT", opacity: 0.96 });
    const substrate = new THREE.Mesh(substrateGeometry, substrateAppearance.material);
    substrate.name = `${this.config.slug}_substrate`;
    substrate.position.y = currentY - THICKNESS_MAPPING.substrateVisual / 2;
    substrate.userData = { materialName: substrateLabel, isSubstrate: true };
    substrate.add(createLayerOutline(substrateGeometry, substrateAppearance.outlineColor));
    this.group.add(substrate);
    this.structureMeshes.push(substrate);
    this.resources.push(substrate);

    this.rebuildWaves();
    this.rebuildPolarizationArrow();
    this.setupInteraction();
    return this.group;
  }

  rebuildWaves() {
    this.waveAmpInfo = sampleEngineeringSpectrum(this.caseResult, this.polarization, this.selectedWavelengthNm);
    this.selectedWavelengthNm = this.waveAmpInfo.selectedWavelengthNm;
    const theme = getVisualTheme("ACADEMIC_LIGHT");
    const angleRad = Math.PI / 4;
    const origin = [0, 0, 0];
    const descriptors = [
      {
        id: "incident_wave",
        start: [-4 * Math.sin(angleRad), 4 * Math.cos(angleRad), 0], end: origin,
        amplitude: 0.25, wavelength: 0.8, speed: 2, pol: this.polarization,
        color: theme.waveColors.incident, linewidth: 1, opacity: 0.92,
        displayScale: ENGINEERING_WAVE_DISPLAY_SCALE,
      },
      {
        id: "reflected_wave",
        start: origin, end: [4 * Math.sin(angleRad), 4 * Math.cos(angleRad), 0],
        amplitude: this.waveAmpInfo.rAmp, wavelength: 0.8, speed: 2, pol: this.polarization,
        color: theme.waveColors.reflected, linewidth: 1, opacity: 0.92,
        displayScale: ENGINEERING_WAVE_DISPLAY_SCALE,
      },
      {
        id: "transmitted_wave",
        start: origin, end: [1.5 * Math.sin(angleRad * 0.7), -4 * Math.cos(angleRad * 0.7), 0],
        amplitude: this.waveAmpInfo.tAmp, wavelength: 0.6, speed: 2, pol: this.polarization,
        color: theme.waveColors.transmitted, linewidth: 1, opacity: 0.92,
        displayScale: ENGINEERING_WAVE_DISPLAY_SCALE,
      },
    ];
    this.waveRenderer.build(descriptors);
    this.rebuildDirectionArrows(descriptors);
    this.onWaveInfo?.(this.waveAmpInfo);
  }

  rebuildDirectionArrows(descriptors) {
    if (this.directionGroup) {
      ResourceDisposer.disposeObject(this.directionGroup);
      this.resources = this.resources.filter((resource) => resource !== this.directionGroup);
    }
    this.directionGroup = new THREE.Group();
    this.directionGroup.name = `${this.config.slug}_wave_directions`;
    descriptors.forEach((descriptor) => {
      const start = new THREE.Vector3(...descriptor.start);
      const direction = new THREE.Vector3(...descriptor.end).sub(start);
      const length = direction.length();
      direction.normalize();
      this.directionGroup.add(new THREE.ArrowHelper(
        direction, start.clone().addScaledVector(direction, length * 0.62),
        0.52, descriptor.color, 0.15, 0.08
      ));
    });
    this.group.add(this.directionGroup);
    this.resources.push(this.directionGroup);
  }

  rebuildPolarizationArrow() {
    if (this.polarizationArrow) {
      ResourceDisposer.disposeObject(this.polarizationArrow);
      this.resources = this.resources.filter((resource) => resource !== this.polarizationArrow);
    }
    const theme = getVisualTheme("ACADEMIC_LIGHT");
    const direction = this.polarization === "TE" ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(1, 0, 0);
    const color = this.polarization === "TE" ? theme.waveColors.polarizationTE : theme.waveColors.polarizationTM;
    this.polarizationArrow = new THREE.ArrowHelper(direction, new THREE.Vector3(-0.55, 1.2, 0), 1, color, 0.23, 0.12);
    this.polarizationArrow.name = `${this.config.slug}_polarization_arrow`;
    this.group.add(this.polarizationArrow);
    this.resources.push(this.polarizationArrow);
  }

  setWavelength(wavelengthNm) {
    this.selectedWavelengthNm = Number(wavelengthNm);
    this.rebuildWaves();
  }

  setPolarization(polarization) {
    this.polarization = polarization === "TM" ? "TM" : "TE";
    this.rebuildWaves();
    this.rebuildPolarizationArrow();
  }

  updateAnimation(timeSeconds) { this.waveRenderer.update(timeSeconds); }

  setupInteraction() {
    if (!this.camera || !this.domElement) return;
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const pick = (event) => {
      const rect = this.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, this.camera);
      return raycaster.intersectObjects(this.layerMeshes, false)[0]?.object || null;
    };
    const onMove = (event) => {
      const mesh = pick(event);
      this.setHoveredLayer(mesh?.userData.layerIndex ?? null);
      this.domElement.style.cursor = mesh ? "pointer" : "grab";
    };
    const onLeave = () => this.setHoveredLayer(null);
    const onClick = (event) => {
      const mesh = pick(event);
      if (mesh) this.setSelectedLayer(mesh.userData.layerIndex);
      else this.clearSelection();
    };
    this.domElement.addEventListener("pointermove", onMove);
    this.domElement.addEventListener("pointerleave", onLeave);
    this.domElement.addEventListener("click", onClick);
    this.listenerCleanup.push(() => this.domElement.removeEventListener("pointermove", onMove));
    this.listenerCleanup.push(() => this.domElement.removeEventListener("pointerleave", onLeave));
    this.listenerCleanup.push(() => this.domElement.removeEventListener("click", onClick));
  }

  setHoveredLayer(index) { this.hoveredLayerIndex = Number.isInteger(index) ? index : null; this.refreshLayerState(); }
  setSelectedLayer(index) { this.selectedLayerIndex = Number.isInteger(index) ? index : null; this.refreshLayerState(); }
  clearSelection() { this.selectedLayerIndex = null; this.refreshLayerState(); }

  refreshLayerState() {
    this.layerMeshes.forEach((mesh, index) => setLayerInteractionState(mesh, {
      hovered: index === this.hoveredLayerIndex,
      selected: index === this.selectedLayerIndex,
    }));
    const focusIndex = this.selectedLayerIndex ?? this.hoveredLayerIndex;
    this.onLayerFocus?.(Number.isInteger(focusIndex) ? this.layerMeshes[focusIndex]?.userData : null, {
      selectedLayerIndex: this.selectedLayerIndex,
      hoveredLayerIndex: this.hoveredLayerIndex,
    });
  }

  getStructureBounds() {
    const bounds = new THREE.Box3();
    this.structureMeshes.forEach((resource) => bounds.expandByObject(resource));
    return bounds;
  }

  getLayerScreenPositions() {
    const rect = this.domElement.getBoundingClientRect();
    return this.layerMeshes.map((mesh) => {
      if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
      const point = mesh.localToWorld(new THREE.Vector3(0, 0, mesh.geometry.boundingBox.max.z + 0.002));
      const projected = point.project(this.camera);
      return {
        layerIndex: mesh.userData.layerIndex,
        x: rect.left + ((projected.x + 1) / 2) * rect.width,
        y: rect.top + ((1 - projected.y) / 2) * rect.height,
      };
    });
  }

  dispose() {
    this.listenerCleanup.splice(0).forEach((cleanup) => cleanup());
    this.waveRenderer.dispose();
    this.resources.splice(0).forEach((resource) => ResourceDisposer.disposeObject(resource));
    this.layerMeshes = [];
    this.structureMeshes = [];
    this.selectedLayerIndex = null;
    this.hoveredLayerIndex = null;
    this.directionGroup = null;
    this.polarizationArrow = null;
  }
}
