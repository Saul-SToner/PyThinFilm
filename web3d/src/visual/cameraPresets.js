export const CAMERA_PRESETS = Object.freeze({
  ISOMETRIC_SECTION: Object.freeze({
    id: "ISOMETRIC_SECTION",
    direction: Object.freeze([1.15, 0.82, 1.35]),
    targetOffset: Object.freeze([0.72, 0, 0]),
    distanceFactor: 3.25,
    minDistanceFactor: 0.72,
    maxDistanceFactor: 5.4,
  }),
  SIDE_SECTION: Object.freeze({
    id: "SIDE_SECTION",
    direction: Object.freeze([0.08, 0.08, 1.8]),
    targetOffset: Object.freeze([0.7, 0, 0]),
    distanceFactor: 3.05,
    minDistanceFactor: 0.72,
    maxDistanceFactor: 5.4,
  }),
  OPTICAL_PATH: Object.freeze({
    id: "OPTICAL_PATH",
    direction: Object.freeze([0.0, 0.72, 1.9]),
    targetOffset: Object.freeze([0.72, 0, 0]),
    distanceFactor: 3.25,
    minDistanceFactor: 0.72,
    maxDistanceFactor: 5.8,
  }),
});

export function getCameraPreset(presetName) {
  return CAMERA_PRESETS[presetName] || null;
}

export function isValidCameraPreset(presetName) {
  const preset = getCameraPreset(presetName);
  return Boolean(
    preset
    && preset.direction.length === 3
    && preset.direction.every(Number.isFinite)
    && preset.distanceFactor > 0
    && preset.minDistanceFactor > 0
    && preset.maxDistanceFactor > preset.minDistanceFactor
  );
}
