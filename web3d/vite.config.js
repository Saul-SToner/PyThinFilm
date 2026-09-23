import { defineConfig } from "vite";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const additionalCaseSlugs = [
  "quarter-wave-single-layer", "half-wave-single-layer", "single-ar",
  "high-reflector", "quarter-wave-stack", "bragg-reflector",
  "fp-single-halfwave", "fp-filter", "narrowband-filter", "tamm-phase-bundle",
  "porous-sio2-layer", "porous-double-ar", "moth-eye-gradient", "double-ar",
  "quarter-wave-double-layer", "triple-ar", "fp-double-halfwave", "rugate-filter",
  "neutral-beamsplitter", "smart-window", "guided-grating-emt", "material-library",
  "pdrc-cooling", "rugate-80layer-table",
  "tamm-interface-priority", "tamm-phase-candidates", "tamm-phase-focus",
  "tamm-reflection-phase-screen", "tamm-interface-window-bundle", "tamm-interface-window-scan",
  "absorbing-baseline-template", "absorbing-surface-bundle", "absorbing-surface-gain",
  "absorbing-surface-gain-trend", "advanced-ar-bundle", "porous-double-ar-topic",
];

export default defineConfig({
  root: "./",
  base: "./",
  build: {
    outDir: "dist",
    assetsDir: "assets",
    sourcemap: false,
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        solarAr: resolve(__dirname, "apps/solar-ar/index.html"),
        wdmFilter: resolve(__dirname, "apps/wdm-filter/index.html"),
        laserMirror: resolve(__dirname, "apps/laser-mirror/index.html"),
        phoneLensAr: resolve(__dirname, "apps/phone-lens-ar/index.html"),
        ...Object.fromEntries(additionalCaseSlugs.map((slug) => [slug, resolve(__dirname, `apps/${slug}/index.html`)])),
      },
    },
  },
  server: {
    port: 3000,
    open: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    exclude: ["tests-e2e/**", "node_modules/**"],
  },
});
