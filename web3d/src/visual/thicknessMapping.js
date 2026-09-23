export const THICKNESS_MAPPING = Object.freeze({
  minVisual: 0.22,
  maxVisual: 0.64,
  referenceNm: 120,
  exponent: 0.58,
  substrateVisual: 1.65,
});

export function mapThicknessNm(thicknessNm, options = {}) {
  const config = { ...THICKNESS_MAPPING, ...options };
  const thickness = Math.max(0, Number(thicknessNm) || 0);
  const normalized = Math.pow(thickness / config.referenceNm, config.exponent);
  const mapped = config.minVisual + normalized * (config.maxVisual - config.minVisual);
  return Math.min(config.maxVisual, Math.max(config.minVisual, mapped));
}
