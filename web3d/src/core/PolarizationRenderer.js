import * as THREE from "three";

export class PolarizationRenderer {
  constructor() {
    this.group = new THREE.Group();
    this.group.name = "PolarizationGroup";
    this.polarization = "TE";
  }

  setPolarization(pol = "TE") {
    this.polarization = pol;
    this.updateVectors();
  }

  updateVectors() {
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
      this.group.remove(child);
    }

    const dir = this.polarization === "TE" ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(1, 0, 0);
    const origin = new THREE.Vector3(0, 2, 0);
    const length = 1.5;
    const hex = this.polarization === "TE" ? 0xf59e0b : 0xec4899;

    const arrowHelper = new THREE.ArrowHelper(dir, origin, length, hex, 0.4, 0.2);
    this.group.add(arrowHelper);
  }

  getGroup() {
    this.updateVectors();
    return this.group;
  }
}
