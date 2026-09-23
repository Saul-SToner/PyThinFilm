import * as THREE from "three";

export class WavePathBuilder {
  constructor() {
    this.rayGroup = new THREE.Group();
    this.rayGroup.name = "WavePathGroup";
  }

  buildRays(incidenceAngleDeg = 0) {
    const angleRad = (incidenceAngleDeg * Math.PI) / 180;
    
    // Incident Ray
    const incPoints = [
      new THREE.Vector3(-4 * Math.sin(angleRad), 4 * Math.cos(angleRad), 0),
      new THREE.Vector3(0, 0, 0),
    ];
    const incGeo = new THREE.BufferGeometry().setFromPoints(incPoints);
    const incMat = new THREE.LineBasicMaterial({ color: 0xef4444, linewidth: 2 });
    const incLine = new THREE.Line(incGeo, incMat);
    this.rayGroup.add(incLine);

    // Reflected Ray
    const refPoints = [
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(4 * Math.sin(angleRad), 4 * Math.cos(angleRad), 0),
    ];
    const refGeo = new THREE.BufferGeometry().setFromPoints(refPoints);
    const refMat = new THREE.LineBasicMaterial({ color: 0x3b82f6, linewidth: 2 });
    const refLine = new THREE.Line(refGeo, refMat);
    this.rayGroup.add(refLine);

    // Transmitted Ray
    const transPoints = [
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(3 * Math.sin(angleRad * 0.7), -3 * Math.cos(angleRad * 0.7), 0),
    ];
    const transGeo = new THREE.BufferGeometry().setFromPoints(transPoints);
    const transMat = new THREE.LineBasicMaterial({ color: 0x10b981, linewidth: 2 });
    const transLine = new THREE.Line(transGeo, transMat);
    this.rayGroup.add(transLine);

    return this.rayGroup;
  }
}
