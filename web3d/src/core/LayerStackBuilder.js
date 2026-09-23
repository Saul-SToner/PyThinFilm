import * as THREE from "three";

export class LayerStackBuilder {
  constructor() {
    this.materialColors = {
      Air: 0x93c5fd,
      MgF2: 0xa7f3d0,
      SiO2: 0x60a5fa,
      TiO2: 0xf59e0b,
      ZrO2: 0xc084fc,
      Al2O3: 0xf472b6,
      Ag: 0x9ca3af,
      Au: 0xfacc15,
      Si: 0x475569,
      Glass: 0x38bdf8,
      Substrate: 0x334155,
      Porous: 0x6ee7b7,
    };
  }

  getColorForMaterial(matName) {
    for (const key of Object.keys(this.materialColors)) {
      if (matName.includes(key)) return this.materialColors[key];
    }
    return 0x94a3b8;
  }

  buildStack(layersConfig, isExploded = false) {
    const group = new THREE.Group();
    group.name = "LayerStackGroup";

    let currentY = 0;
    const width = 6;
    const depth = 4;

    layersConfig.forEach((layer, idx) => {
      const thickness = Math.max(0.3, (layer.thickness_nm || 100) / 150);
      const geometry = new THREE.BoxGeometry(width, thickness, depth);
      const color = this.getColorForMaterial(layer.material || layer.name || "Default");
      
      const material = new THREE.MeshStandardMaterial({
        color: color,
        transparent: true,
        opacity: layer.material === "Air" ? 0.1 : 0.75,
        roughness: 0.2,
        metalness: layer.material === "Ag" || layer.material === "Au" ? 0.9 : 0.1,
      });

      const mesh = new THREE.Mesh(geometry, material);
      const gap = isExploded ? 0.4 : 0.02;
      
      mesh.position.y = currentY - thickness / 2;
      mesh.userData = { layerIndex: idx, config: layer };
      
      group.add(mesh);
      currentY -= thickness + gap;
    });

    return group;
  }
}
