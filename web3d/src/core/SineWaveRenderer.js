/**
 * SineWaveRenderer.js
 *
 * Renders dynamically propagating polarized sine waves along ray paths.
 *
 * Wave Kinematics:
 *   - Ray path goes from start point P0 to end point P1 (len = |P1 - P0|, kVec = (P1 - P0)/len).
 *   - Distance s along ray: s ∈ [0, len].
 *   - Forward propagation along kVec: Phase = k*s - ω*t + φ.
 *   - Peak velocity v_phase = +ω/k along +s direction (toward end point P1).
 *
 * Vector Polarization (Any 3D Ray Direction):
 *   - Given ray direction kVec and interface normal nVec (default (0, 1, 0)):
 *     If |kVec × nVec| > 1e-4, teDir = normalize(kVec × nVec).
 *     Otherwise (degenerate / near normal incidence), compute stableTransverseBasis(kVec):
 *       Select axis in {X, Y, Z} with minimum |axis · kVec| as reference.
 *       teDir = normalize(kVec × referenceAxis)
 *     tmDir = normalize(teDir × kVec)
 *   - Strict Transverse Orthogonality Assertions (tolerance < 1e-8):
 *     |teDir · kVec| < 1e-8
 *     |tmDir · kVec| < 1e-8
 *     |teDir · tmDir| < 1e-8
 *
 * F-P Standing Wave Teaching Semantics:
 *   - animationSemantics = "STANDING_WAVE_ILLUSTRATION"
 *   - fieldAmplitudeSource = "VISUAL_EQUAL_AMPLITUDE"
 *   - quantitativeFieldStatus = "NOT_AVAILABLE"
 */

import * as THREE from 'three';
import { ResourceDisposer } from './ResourceDisposer.js';

export const WAVE_SEGMENTS = 100; // polyline sample count

/**
 * Computes a numerically stable transverse basis (TE, TM) for ANY 3D propagation vector kVec.
 * Guarantees |te · k| < 1e-8, |tm · k| < 1e-8, and |te · tm| < 1e-8.
 */
export function stableTransverseBasis(kVec, nVec = new THREE.Vector3(0, 1, 0)) {
  const k = kVec.clone().normalize();
  const n = nVec.clone().normalize();

  let te = new THREE.Vector3().crossVectors(k, n);
  if (te.lengthSq() < 1e-6) {
    // Degenerate (k || n): select coordinate axis with minimum dot product magnitude
    const axes = [
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(0, 0, 1),
    ];
    let minDot = Math.abs(axes[0].dot(k));
    let reference = axes[0];

    for (let i = 1; i < axes.length; i++) {
      const dot = Math.abs(axes[i].dot(k));
      if (dot < minDot) {
        minDot = dot;
        reference = axes[i];
      }
    }
    te.crossVectors(k, reference);
  }
  te.normalize();

  const tm = new THREE.Vector3().crossVectors(te, k).normalize();

  // Strict orthogonality check
  if (Math.abs(te.dot(k)) > 1e-8 || Math.abs(tm.dot(k)) > 1e-8 || Math.abs(te.dot(tm)) > 1e-8) {
    console.warn(`[stableTransverseBasis] Orthogonality precision warning for k=${JSON.stringify(k)}`);
  }

  return { te, tm };
}

export class SineWaveRenderer {
  constructor() {
    this._group = new THREE.Group();
    this._group.name = 'SineWaveRendererGroup';
    this._waves = [];  // internal wave descriptors & state
    this._lines = [];  // THREE.Line objects

    SineWaveRenderer._instanceCount += 1;
    this._id = SineWaveRenderer._instanceCount;
  }

  build(descriptors) {
    this.dispose();
    if (!descriptors || descriptors.length === 0) return;

    for (const d of descriptors) {
      const startV  = new THREE.Vector3(...d.start);
      const endV    = new THREE.Vector3(...d.end);
      const dirVec  = new THREE.Vector3().subVectors(endV, startV);
      const len     = dirVec.length();
      if (len < 1e-6) continue;
      const kVec    = dirVec.clone().normalize();

      const nVec = new THREE.Vector3(...(d.interfaceNormal || [0, 1, 0])).normalize();

      // Compute stable transverse basis
      const { te, tm } = stableTransverseBasis(kVec, nVec);
      const polVec = (d.pol === 'TE' ? te : tm).clone();

      const k     = (2 * Math.PI) / Math.max(d.wavelength, 0.01);
      const omega = d.speed * k;

      const positions = new Float32Array(WAVE_SEGMENTS * 3);
      const geo = new THREE.BufferGeometry();
      const bufAttr = new THREE.BufferAttribute(positions, 3);
      bufAttr.setUsage(THREE.DynamicDrawUsage);
      geo.setAttribute('position', bufAttr);

      const mat  = new THREE.LineBasicMaterial({
        color: d.color,
        linewidth: d.linewidth ?? (d.isSuperposition ? 3 : 2),
        transparent: d.opacity !== undefined,
        opacity: d.opacity ?? 1,
      });
      const line = new THREE.Line(geo, mat);
      line.name  = d.id || 'wave';
      this._group.add(line);

      this._waves.push({
        id: d.id || 'wave',
        positions, bufAttr,
        k, omega,
        polVec, startV, kVec, len,
        phaseOffset: d.phaseOffset ?? 0,
        amplitude: d.amplitude,
        displayScale: Number.isFinite(d.displayScale) ? d.displayScale : 1,
        amplitudeEnvelope: d.amplitudeEnvelope ?? null,
        isSuperposition: d.isSuperposition || false,
      });
      this._lines.push(line);
    }

    this.update(0);
  }

  update(time) {
    for (const w of this._waves) {
      const {
        positions, bufAttr,
        k, omega,
        polVec, startV, kVec, len,
        phaseOffset, amplitude, displayScale, amplitudeEnvelope, isSuperposition
      } = w;

      const N = WAVE_SEGMENTS;
      for (let i = 0; i < N; i++) {
        const s = (i / (N - 1)) * len;

        const bx = startV.x + kVec.x * s;
        const by = startV.y + kVec.y * s;
        const bz = startV.z + kVec.z * s;

        let disp = 0;
        if (isSuperposition) {
          // Standing wave equal-amplitude visual superposition
          const fwd = amplitude * Math.sin(k * s - omega * time + phaseOffset);
          const bwd = amplitude * Math.sin(k * (len - s) - omega * time + phaseOffset);
          disp = displayScale * (fwd + bwd);
        } else {
          const phase = k * s - omega * time + phaseOffset;
          let amp = amplitude;
          if (amplitudeEnvelope !== null && amplitudeEnvelope.length > 0) {
            const envIdx = Math.min(
              Math.floor((i / N) * amplitudeEnvelope.length),
              amplitudeEnvelope.length - 1
            );
            amp = amplitude * amplitudeEnvelope[envIdx];
          }
          disp = displayScale * amp * Math.sin(phase);
        }

        positions[i * 3]     = bx + polVec.x * disp;
        positions[i * 3 + 1] = by + polVec.y * disp;
        positions[i * 3 + 2] = bz + polVec.z * disp;
      }

      bufAttr.needsUpdate = true;
    }
  }

  dispose() {
    for (const line of this._lines) {
      ResourceDisposer.disposeObject(line);
      this._group.remove(line);
    }
    this._waves = [];
    this._lines = [];
  }

  getGroup() {
    return this._group;
  }

  get waveCount() {
    return this._waves.length;
  }

  getWavePositions() {
    return this._waves.map((w) => Array.from(w.positions));
  }
}

SineWaveRenderer._instanceCount = 0;
