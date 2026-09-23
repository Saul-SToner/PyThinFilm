import * as THREE from "three";
import { SineWaveRenderer } from "../core/SineWaveRenderer.js";

export class MetalDbrInterfaceTemplate {
  constructor(container) {
    this.container = container;
    this.group = new THREE.Group();
    this.group.name = "MetalDbrInterfaceTemplateGroup";
    this.waveRenderer = new SineWaveRenderer();
    this.group.add(this.waveRenderer.getGroup());
    this.fieldEnvelopeSource = "ANALYTIC_VISUAL_ENVELOPE";
    this.fieldEnvelope = [];
  }

  build(caseResult, options = {}) {
    this.dispose();
    this.group.add(this.waveRenderer.getGroup());

    const isExploded = options.isExploded || false;
    const polarization = options.polarization || "TE";

    const layersData = (caseResult && caseResult.layers) ? caseResult.layers : [
      { layer_index: 1, type: "Ag", role: "metal_absorber", n_real: 0.13, n_imag: 3.98, thickness_nm: 30.0 },
      { layer_index: 2, type: "H", role: "dbr_mirror_layer", n_real: 2.15, n_imag: 0.0, thickness_nm: 63.95 },
      { layer_index: 3, type: "L", role: "dbr_mirror_layer", n_real: 1.38, n_imag: 0.0, thickness_nm: 99.64 },
      { layer_index: 4, type: "H", role: "dbr_mirror_layer", n_real: 2.15, n_imag: 0.0, thickness_nm: 63.95 },
      { layer_index: 5, type: "L", role: "dbr_mirror_layer", n_real: 1.38, n_imag: 0.0, thickness_nm: 99.64 },
      { layer_index: 6, type: "H", role: "dbr_mirror_layer", n_real: 2.15, n_imag: 0.0, thickness_nm: 63.95 },
      { layer_index: 7, type: "L", role: "dbr_mirror_layer", n_real: 1.38, n_imag: 0.0, thickness_nm: 99.64 },
      { layer_index: 8, type: "H", role: "dbr_mirror_layer", n_real: 2.15, n_imag: 0.0, thickness_nm: 63.95 },
    ];

    let currentY = 0;
    const width = 6;
    const depth = 4;
    let interfaceY = 0;

    // Ambient Air
    const airGeo = new THREE.BoxGeometry(width, 0.4, depth);
    const airMat = new THREE.MeshStandardMaterial({ color: 0x93c5fd, transparent: true, opacity: 0.15 });
    const airMesh = new THREE.Mesh(airGeo, airMat);
    airMesh.position.y = currentY - 0.2;
    this.group.add(airMesh);
    currentY -= 0.4 + (isExploded ? 0.25 : 0.02);

    layersData.forEach((layer) => {
      const isMetal = layer.type === "Ag";
      const isH = layer.type === "H";
      const thicknessVisual = isMetal ? 0.3 : Math.max(0.18, (layer.thickness_nm || 80) / 220);

      let color = 0x94a3b8;
      if (!isMetal) color = isH ? 0xf59e0b : 0x60a5fa;

      const geo = new THREE.BoxGeometry(width, thicknessVisual, depth);
      const mat = new THREE.MeshStandardMaterial({
        color: color,
        metalness: isMetal ? 0.95 : 0.1,
        roughness: isMetal ? 0.15 : 0.3,
        transparent: true,
        opacity: isMetal ? 0.95 : 0.75,
        emissive: isMetal ? 0x475569 : 0x000000,
        emissiveIntensity: isMetal ? 0.3 : 0.0,
      });
      const mesh = new THREE.Mesh(geo, mat);

      const gap = isExploded ? 0.25 : 0.015;
      const posY = currentY - thicknessVisual / 2;
      mesh.position.y = posY;
      if (isMetal) {
        interfaceY = posY - thicknessVisual / 2; // Ag/DBR interface
      }
      this.group.add(mesh);
      currentY -= thicknessVisual + gap;
    });

    // Substrate Glass
    const subGeo = new THREE.BoxGeometry(width, 1.0, depth);
    const subMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.85 });
    const subMesh = new THREE.Mesh(subGeo, subMat);
    subMesh.position.y = currentY - 0.5;
    this.group.add(subMesh);

    // Rays & Waves (Normal Incidence)
    const incStart = [0, 3.5, 0];
    const origin = [0, 0, 0];
    const refEnd = [0, 3.5, 0];

    const interfaceTop = [0, interfaceY + 0.3, 0];
    const interfaceBottom = [0, interfaceY - 1.2, 0];

    // Check if Python JSON provides field_profile_candidate
    const rawCandidate = caseResult && caseResult.field_profile_candidate;
    let pythonFieldProfile = null;

    if (rawCandidate) {
      if (Array.isArray(rawCandidate.normalized_abs_E2)) {
        pythonFieldProfile = rawCandidate.normalized_abs_E2;
      } else if (Array.isArray(rawCandidate) && rawCandidate.length > 0) {
        const e2Vals = rawCandidate.map((item) => typeof item === "object" && item.E2 !== undefined ? Number(item.E2) : Number(item));
        const maxE2 = Math.max(...e2Vals, 1e-6);
        pythonFieldProfile = e2Vals.map((v) => v / maxE2);
      }
    }

    if (Array.isArray(pythonFieldProfile) && pythonFieldProfile.length > 0) {
      this.fieldEnvelopeSource = "PYTHON_FIELD_PROFILE";
      this.fieldEnvelope = pythonFieldProfile.map(Number);
    } else {
      this.fieldEnvelopeSource = "ANALYTIC_VISUAL_ENVELOPE";
      this.fieldEnvelope = [1.0, 0.92, 0.78, 0.58, 0.40, 0.26, 0.16, 0.09, 0.04, 0.01];
    }

    const waveDescriptors = [
      {
        id: "incident_wave",
        start: incStart,
        end: origin,
        amplitude: 0.25,
        wavelength: 0.8,
        speed: 2.0,
        pol: polarization,
        color: 0xef4444,
      },
      {
        id: "reflected_wave",
        start: origin,
        end: refEnd,
        amplitude: 0.22,
        wavelength: 0.8,
        speed: 2.0,
        pol: polarization,
        color: 0x3b82f6,
      },
      {
        id: "tamm_localized_wave",
        start: interfaceTop,
        end: interfaceBottom,
        amplitude: 0.45,
        wavelength: 0.35,
        speed: 2.0,
        pol: polarization,
        color: 0xec4899,
        amplitudeEnvelope: this.fieldEnvelope,
      },
    ];

    this.waveRenderer.build(waveDescriptors);

    // Polarization Arrow
    const polDir = polarization === "TE" ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(1, 0, 0);
    const polHex = polarization === "TE" ? 0xf59e0b : 0xec4899;
    const arrow = new THREE.ArrowHelper(polDir, new THREE.Vector3(0, 2.2, 0), 1.5, polHex, 0.4, 0.2);
    this.group.add(arrow);

    return this.group;
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
