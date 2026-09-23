import * as THREE from "three";
import { getMaterialAppearance } from "./materialPalette.js";
import { getVisualTheme } from "./visualTheme.js";

export function createLayerAppearance(materialName, options = {}) {
  const theme = getVisualTheme(options.themeId || "ACADEMIC_LIGHT");
  const palette = getMaterialAppearance(materialName);
  const material = new THREE.MeshStandardMaterial({
    color: palette.color,
    roughness: palette.roughness,
    metalness: palette.metalness,
    transparent: true,
    opacity: options.opacity ?? 0.88,
    emissive: 0x000000,
    emissiveIntensity: 0,
  });
  material.userData.baseColor = palette.color;
  material.userData.materialName = palette.materialName;

  return {
    material,
    outlineColor: theme.outlineColor,
    palette,
  };
}

export function createLayerOutline(geometry, color) {
  const outlineGeometry = new THREE.EdgesGeometry(geometry, 20);
  const outlineMaterial = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0.72,
    linewidth: 1,
  });
  const outline = new THREE.LineSegments(outlineGeometry, outlineMaterial);
  outline.name = "layer_outline";
  outline.renderOrder = 3;
  return outline;
}

export function setLayerInteractionState(mesh, state = {}) {
  if (!mesh?.material) return;
  const theme = getVisualTheme("ACADEMIC_LIGHT");
  const selected = Boolean(state.selected);
  const hovered = Boolean(state.hovered);
  const emissive = selected
    ? theme.interaction.selectedEmissive
    : hovered
      ? theme.interaction.hoverEmissive
      : 0x000000;
  const scale = selected
    ? theme.interaction.selectedScale
    : hovered
      ? theme.interaction.hoverScale
      : 1;

  mesh.material.emissive.setHex(emissive);
  mesh.material.emissiveIntensity = selected ? 0.42 : hovered ? 0.25 : 0;
  mesh.scale.set(scale, 1, scale);
  mesh.userData.interactionState = { hovered, selected };
}
