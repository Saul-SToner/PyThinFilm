import * as THREE from "three";
import { SineWaveRenderer } from "../core/SineWaveRenderer.js";
import { calculateWaveAmplitudesFromSpectrum } from "../core/spectrumWaveAmp.js";

export class DefectCavityTemplate {
  constructor(container) {
    this.container = container;
    this.group = new THREE.Group();
    this.group.name = "DefectCavityTemplateGroup";
    this.waveRenderer = new SineWaveRenderer();
    this.group.add(this.waveRenderer.getGroup());
    
    // Explicit Mode Flags & Semantics
    this.templateMode = "DEFECT_CAVITY_MODE";
    this.animationSemantics = "TEACHING_ILLUSTRATION";
    this.waveAmplitudeSource = "SELECTED_WAVELENGTH_R_T_SCHEMATIC";
    this.fieldAmplitudeSource = "VISUAL_EQUAL_AMPLITUDE";
    this.quantitativeFieldStatus = "NOT_AVAILABLE";

    this.caseResult = null;
    this.polarization = "TE";
    this.selectedWavelengthNm = 1550;
    this.cavityYCenter = 0;
    this.waveAmpInfo = null;
  }

  build(caseResult, options = {}) {
    this.dispose();
    this.group.add(this.waveRenderer.getGroup());

    this.caseResult = caseResult;
    this.options = options;
    const isExploded = options.isExploded || false;
    this.polarization = options.polarization || "TE";
    if (options.selectedWavelengthNm) {
      this.selectedWavelengthNm = options.selectedWavelengthNm;
    } else if (caseResult && caseResult.metrics && caseResult.metrics.peak_wavelength_nm) {
      this.selectedWavelengthNm = caseResult.metrics.peak_wavelength_nm;
    }

    const layersData = (caseResult && caseResult.layers) ? caseResult.layers : [
      { layer_index: 1, type: "H", role: "mirror_layer", n: 2.15, thickness_nm: 63.95 },
      { layer_index: 2, type: "L", role: "mirror_layer", n: 1.38, thickness_nm: 99.64 },
      { layer_index: 3, type: "H", role: "mirror_layer", n: 2.15, thickness_nm: 63.95 },
      { layer_index: 4, type: "L", role: "mirror_layer", n: 1.38, thickness_nm: 99.64 },
      { layer_index: 5, type: "H", role: "mirror_layer", n: 2.15, thickness_nm: 63.95 },
      { layer_index: 6, type: "L", role: "mirror_layer", n: 1.38, thickness_nm: 99.64 },
      { layer_index: 7, type: "C", role: "cavity_spacer", n: 1.38, thickness_nm: 199.28 },
      { layer_index: 8, type: "L", role: "mirror_layer", n: 1.38, thickness_nm: 99.64 },
      { layer_index: 9, type: "H", role: "mirror_layer", n: 2.15, thickness_nm: 63.95 },
      { layer_index: 10, type: "L", role: "mirror_layer", n: 1.38, thickness_nm: 99.64 },
      { layer_index: 11, type: "H", role: "mirror_layer", n: 2.15, thickness_nm: 63.95 },
      { layer_index: 12, type: "L", role: "mirror_layer", n: 1.38, thickness_nm: 99.64 },
      { layer_index: 13, type: "H", role: "mirror_layer", n: 2.15, thickness_nm: 63.95 },
    ];

    let currentY = 0;
    const width = 6;
    const depth = 4;
    this.cavityYCenter = 0;

    // Ambient Air
    const airGeo = new THREE.BoxGeometry(width, 0.4, depth);
    const airMat = new THREE.MeshStandardMaterial({ color: 0x93c5fd, transparent: true, opacity: 0.15 });
    const airMesh = new THREE.Mesh(airGeo, airMat);
    airMesh.position.y = currentY - 0.2;
    this.group.add(airMesh);
    currentY -= 0.4 + (isExploded ? 0.25 : 0.02);

    layersData.forEach((layer) => {
      const isCavity = layer.type === "C";
      const isH = layer.type === "H";
      const thicknessVisual = isCavity ? 0.5 : Math.max(0.18, (layer.thickness_nm || 80) / 220);

      let color = 0x60a5fa;
      if (isCavity) color = 0x14b8a6;
      else if (isH) color = 0xf59e0b;

      const geo = new THREE.BoxGeometry(width, thicknessVisual, depth);
      const mat = new THREE.MeshStandardMaterial({
        color: color,
        transparent: true,
        opacity: isCavity ? 0.9 : 0.7,
        roughness: isCavity ? 0.1 : 0.25,
        emissive: isCavity ? 0x0f766e : 0x000000,
        emissiveIntensity: isCavity ? 0.4 : 0.0,
      });
      const mesh = new THREE.Mesh(geo, mat);

      const gap = isExploded ? 0.25 : 0.015;
      const posY = currentY - thicknessVisual / 2;
      mesh.position.y = posY;
      if (isCavity) {
        this.cavityYCenter = posY;
      }
      this.group.add(mesh);
      currentY -= thicknessVisual + gap;
    });

    // Glass Substrate
    const subGeo = new THREE.BoxGeometry(width, 1.0, depth);
    const subMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.85 });
    const subMesh = new THREE.Mesh(subGeo, subMat);
    subMesh.position.y = currentY - 0.5;
    this.group.add(subMesh);

    // Rays & Wave Descriptors using Selected Wavelength Spectrum R/T
    this.rebuildWaveDescriptors();

    // Polarization Helper Arrow
    const polDir = this.polarization === "TE" ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(1, 0, 0);
    const polHex = this.polarization === "TE" ? 0xf59e0b : 0xec4899;
    const arrow = new THREE.ArrowHelper(polDir, new THREE.Vector3(0, 2.2, 0), 1.5, polHex, 0.4, 0.2);
    arrow.name = "polarization_arrow";
    this.group.add(arrow);

    return this.group;
  }

  rebuildWaveDescriptors() {
    this.waveAmpInfo = calculateWaveAmplitudesFromSpectrum(
      this.caseResult,
      this.polarization,
      this.selectedWavelengthNm
    );
    this.selectedWavelengthNm = this.waveAmpInfo.selectedWavelengthNm;

    const angleRad = (45 * Math.PI) / 180;
    const incStart = [-4 * Math.sin(angleRad), 4 * Math.cos(angleRad), 0];
    const origin = [0, 0, 0];
    const refEnd = [4 * Math.sin(angleRad), 4 * Math.cos(angleRad), 0];
    const transEnd = [2 * Math.sin(angleRad * 0.7), -5 * Math.cos(angleRad * 0.7), 0];

    const cavityTop = [0, this.cavityYCenter + 0.25, 0];
    const cavityBottom = [0, this.cavityYCenter - 0.25, 0];

    const waveDescriptors = [
      {
        id: "incident_wave",
        start: incStart,
        end: origin,
        amplitude: 0.25,
        wavelength: 0.8,
        speed: 2.0,
        pol: this.polarization,
        color: 0xef4444,
      },
      {
        id: "reflected_wave",
        start: origin,
        end: refEnd,
        amplitude: this.waveAmpInfo.rAmp,
        wavelength: 0.8,
        speed: 2.0,
        pol: this.polarization,
        color: 0x3b82f6,
      },
      {
        id: "transmitted_wave",
        start: origin,
        end: transEnd,
        amplitude: this.waveAmpInfo.tAmp,
        wavelength: 0.6,
        speed: 2.0,
        pol: this.polarization,
        color: 0x10b981,
      },
      // Teaching standing wave illustration
      {
        id: "cavity_standing_wave_superposition",
        start: cavityTop,
        end: cavityBottom,
        amplitude: 0.22,
        wavelength: 0.25,
        speed: 2.0,
        pol: this.polarization,
        color: 0x14b8a6,
        isSuperposition: true,
      },
    ];

    this.waveRenderer.build(waveDescriptors);
  }

  setWavelengthAndPolarization(wavelengthNm, polarization) {
    if (wavelengthNm) this.selectedWavelengthNm = wavelengthNm;
    if (polarization) this.polarization = polarization;
    this.rebuildWaveDescriptors();
  }

  updateAnimation(timeSeconds) {
    if (this.waveRenderer) {
      this.waveRenderer.update(timeSeconds);
    }
  }

  dispose() {
    if (this.waveRenderer) {
      this.waveRenderer.dispose();
    }
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose());
        else child.material.dispose();
      }
      this.group.remove(child);
    }
  }
}
