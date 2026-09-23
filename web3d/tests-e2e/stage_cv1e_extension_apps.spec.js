import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const evidenceDir = resolve("../docs/visualization/runtime/stage_cv1e");
const entries = [
  ["smart-window", "app_smart_window", 3, "smart_window.png"],
  ["guided-grating-emt", "guided_grating_emt", 1, "guided_grating_emt.png"],
  ["material-library", "mat_library_demo", 1, null],
  ["pdrc-cooling", "pdrc_cooling_bundle", 6, "pdrc_cooling.png"],
  ["rugate-80layer-table", "rugate_80layer_table", 80, "rugate_table.png"],
];

test.describe("Stage C.V1E reproducible extension apps", () => {
  for (const [slug, caseId, layerCount, screenshot] of entries) {
    test(`${caseId} loads its own Python contract`, async ({ page }) => {
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
      await page.locator('[data-preset-index="1"]').click();
      await page.locator("#btn-polarization").click();
      await expect(page.locator("#wavelength-readout")).toContainText("TM");
      await page.locator("#btn-side").click();
      await page.locator("#btn-reset").click();
      await expect.poll(() => page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount)).toBe(1);
      if (screenshot) await page.screenshot({ path: resolve(evidenceDir, screenshot), fullPage: true });
      expect(consoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
    });
  }
});
