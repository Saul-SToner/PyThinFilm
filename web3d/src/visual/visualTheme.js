export const VISUAL_THEMES = Object.freeze({
  LEGACY_DARK: Object.freeze({
    id: "LEGACY_DARK",
    background: 0x0b0f17,
    lights: Object.freeze({
      ambient: Object.freeze({ color: 0xffffff, intensity: 0.8 }),
      directionalPrimary: Object.freeze({ color: 0xffffff, intensity: 1.2, position: [5, 10, 7] }),
      directionalFill: Object.freeze({ color: 0x3b82f6, intensity: 0.5, position: [-5, -5, -5] }),
    }),
  }),
  ACADEMIC_LIGHT: Object.freeze({
    id: "ACADEMIC_LIGHT",
    background: 0xedf0ed,
    fog: Object.freeze({ color: 0xedf0ed, near: 18, far: 36 }),
    lights: Object.freeze({
      hemisphere: Object.freeze({ skyColor: 0xf7f8f4, groundColor: 0xc8ced2, intensity: 1.25 }),
      directionalPrimary: Object.freeze({ color: 0xfffdf7, intensity: 1.35, position: [7, 10, 8] }),
      ambient: Object.freeze({ color: 0xdde3e6, intensity: 0.42 }),
    }),
    outlineColor: 0x56626c,
    waveColors: Object.freeze({
      incident: 0xa85f59,
      reflected: 0x587a98,
      transmitted: 0x668d7a,
      polarizationTE: 0xb1884f,
      polarizationTM: 0x8b6f89,
    }),
    interaction: Object.freeze({
      hoverEmissive: 0x27343d,
      selectedEmissive: 0x425867,
      hoverScale: 1.012,
      selectedScale: 1.022,
    }),
  }),
});

export function getVisualTheme(themeId) {
  return VISUAL_THEMES[themeId] || VISUAL_THEMES.LEGACY_DARK;
}
