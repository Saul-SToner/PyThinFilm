const MATERIALS = Object.freeze({
  Air: Object.freeze({ color: 0xdfe8ec, roughness: 1.0, metalness: 0 }),
  SiO2: Object.freeze({ color: 0xb9ced8, roughness: 0.72, metalness: 0 }),
  TiO2: Object.freeze({ color: 0xc8b79f, roughness: 0.66, metalness: 0 }),
  MgF2: Object.freeze({ color: 0xb8cbbd, roughness: 0.74, metalness: 0 }),
  ZrO2: Object.freeze({ color: 0xc4bdcf, roughness: 0.68, metalness: 0 }),
  Al2O3: Object.freeze({ color: 0xcbbebc, roughness: 0.7, metalness: 0 }),
  Glass: Object.freeze({ color: 0xaabfc9, roughness: 0.64, metalness: 0 }),
  Substrate: Object.freeze({ color: 0x8d9aa5, roughness: 0.78, metalness: 0 }),
  Si: Object.freeze({ color: 0x7d8994, roughness: 0.82, metalness: 0 }),
  Ag: Object.freeze({ color: 0xaab0b5, roughness: 0.4, metalness: 0.72 }),
  Au: Object.freeze({ color: 0xb8a77f, roughness: 0.42, metalness: 0.68 }),
  H: Object.freeze({ color: 0xc8b79f, roughness: 0.68, metalness: 0 }),
  L: Object.freeze({ color: 0xb9ced8, roughness: 0.72, metalness: 0 }),
  C: Object.freeze({ color: 0xb8cbbd, roughness: 0.72, metalness: 0 }),
  QW: Object.freeze({ color: 0xb8cbbd, roughness: 0.74, metalness: 0 }),
});

function normalizeMaterialName(materialName) {
  const raw = String(materialName || "Unknown").trim();
  const aliases = {
    silica: "SiO2",
    titania: "TiO2",
    silicon: "Si",
    substrate: "Substrate",
  };
  return aliases[raw.toLowerCase()] || raw;
}

function stableHash(text) {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function hslToHex(hue, saturation, lightness) {
  const s = saturation / 100;
  const l = lightness / 100;
  const chroma = (1 - Math.abs(2 * l - 1)) * s;
  const hPrime = hue / 60;
  const x = chroma * (1 - Math.abs((hPrime % 2) - 1));
  const [r1, g1, b1] = hPrime < 1 ? [chroma, x, 0]
    : hPrime < 2 ? [x, chroma, 0]
      : hPrime < 3 ? [0, chroma, x]
        : hPrime < 4 ? [0, x, chroma]
          : hPrime < 5 ? [x, 0, chroma]
            : [chroma, 0, x];
  const m = l - chroma / 2;
  const toByte = (value) => Math.round((value + m) * 255);
  return (toByte(r1) << 16) | (toByte(g1) << 8) | toByte(b1);
}

export function getMaterialAppearance(materialName) {
  const normalized = normalizeMaterialName(materialName);
  if (MATERIALS[normalized]) return { ...MATERIALS[normalized], materialName: normalized, isFallback: false };

  const hash = stableHash(normalized.toLowerCase());
  return {
    materialName: normalized,
    color: hslToHex(hash % 360, 18, 64),
    roughness: 0.72,
    metalness: 0,
    isFallback: true,
  };
}

export const MATERIAL_PALETTE = MATERIALS;
