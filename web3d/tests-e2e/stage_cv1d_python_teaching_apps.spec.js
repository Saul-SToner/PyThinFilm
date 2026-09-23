import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const evidenceDir = resolve("../docs/visualization/runtime/stage_cv1d");
const entries = [
  ["porous-sio2-layer", "porous_sio2_layer", 1, "porous_single.png"],
  ["porous-double-ar", "porous_double_ar", 2, null],
  ["moth-eye-gradient", "moth_eye_effective_gradient", 5, "moth_eye_gradient.png"],
  ["double-ar", "double_ar", 2, null],
  ["quarter-wave-double-layer", "quarter_wave_double_layer", 2, null],
  ["triple-ar", "triple_ar", 3, null],
  ["fp-double-halfwave", "fp_double_halfwave", 21, "fp_double_halfwave.png"],
  ["rugate-filter", "rugate_filter", 80, "rugate_80_layers.png"],
  ["neutral-beamsplitter", "neutral_beamsplitter", 4, "neutral_beamsplitter.png"],
];

test.describe("Stage C.V1D Python-exported teaching apps", () => {
  for (const [slug, caseId, layerCount, screenshot] of entries) {
    test(`${caseId} binds its new formal JSON without runtime coupling`, async ({ page }) => {
      const consoleErrors = [];
      const pageErrors = [];
      page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
      page.on("pageerror", (error) => pageErrors.push(error.message));
      await page.goto(`/apps/${slug}/`);
      await page.waitForFunction(() => window.__ENGINEERING_APP_DEBUG__?.activeWaveCount === 3);
      const state = await page.evaluate(() => ({
        caseId: window.__ENGINEERING_APP_DEBUG__.caseId,
        rendererCount: window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount,
        layerCount: window.__ENGINEERING_APP_DEBUG__.getLayerScreenPositions().length,
        wave: window.__ENGINEERING_APP_DEBUG__.waveInfo,
      }));
      expect(state.caseId).toBe(caseId);
      expect(state.rendererCount).toBe(1);
      expect(state.layerCount).toBe(layerCount);
      expect(state.wave.rSelected + state.wave.tSelected + state.wave.absorptance).toBeCloseTo(1, 5);
      await expect(page.locator(".layer-row")).toHaveCount(layerCount);
      await page.locator('[data-preset-index="1"]').click();
      await page.locator("#btn-polarization").click();
      await expect(page.locator("#wavelength-readout")).toContainText("TM");
      await page.locator("#btn-reset").click();
      await expect.poll(() => page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount)).toBe(1);
      if (screenshot) await page.screenshot({ path: resolve(evidenceDir, screenshot), fullPage: true });
      expect(consoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
    });
  }
});
