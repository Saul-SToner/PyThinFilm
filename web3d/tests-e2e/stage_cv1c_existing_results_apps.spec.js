import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const evidenceDir = resolve("../docs/visualization/runtime/stage_cv1c");
const entries = [
  ["quarter-wave-single-layer", "quarter_wave_single_layer", 1, "single_layer.png"],
  ["half-wave-single-layer", "half_wave_single_layer", 1, null],
  ["single-ar", "single_ar", 1, null],
  ["high-reflector", "high_reflector", 7, "high_reflector.png"],
  ["quarter-wave-stack", "quarter_wave_stack", 7, null],
  ["bragg-reflector", "bragg_reflector", 7, null],
  ["fp-single-halfwave", "fp_single_halfwave", 13, null],
  ["fp-filter", "fp_filter", 13, "fp_filter.png"],
  ["narrowband-filter", "narrowband_filter", 17, null],
  ["tamm-phase-bundle", "tamm_phase_bundle", 8, "tamm_phase.png"],
];

test.describe("Stage C.V1C existing formal-result standalone apps", () => {
  for (const [slug, caseId, layerCount, screenshot] of entries) {
    test(`${caseId} has an isolated formal-data runtime`, async ({ page }) => {
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
      await page.locator('[data-preset-index="2"]').click();
      await expect(page.locator("#wavelength-readout")).toContainText("nm");
      if (screenshot) await page.screenshot({ path: resolve(evidenceDir, screenshot), fullPage: true });
      expect(consoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
    });
  }
});
