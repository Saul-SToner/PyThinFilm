import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const evidenceDir = resolve("../docs/visualization/runtime/stage_cv1b");
const cases = [
  {
    slug: "wdm-filter",
    caseId: "app_wdm_filter",
    layers: 17,
    screenshot: "wdm_default.png",
    contrastScreenshot: "wdm_stopband.png",
    assertDefault: (wave) => expect(wave.tSelected).toBeGreaterThan(0.9),
    contrastTestId: "preset-contrast",
    assertContrast: (wave) => expect(wave.tSelected).toBeLessThan(0.1),
  },
  {
    slug: "laser-mirror",
    caseId: "app_laser_mirror",
    layers: 17,
    screenshot: "laser_default.png",
    contrastScreenshot: "laser_low_reflection.png",
    assertDefault: (wave) => expect(wave.rSelected).toBeGreaterThan(0.99),
    contrastTestId: "preset-contrast",
    assertContrast: (wave) => expect(wave.rSelected).toBeLessThan(0.2),
  },
  {
    slug: "phone-lens-ar",
    caseId: "app_phone_lens_ar",
    layers: 3,
    screenshot: "phone_default.png",
    contrastScreenshot: "phone_green.png",
    assertDefault: (wave) => expect(wave.selectedWavelengthNm).toBeCloseTo(450, 0),
    contrastTestId: "preset-green",
    assertContrast: (wave) => expect(wave.selectedWavelengthNm).toBeCloseTo(550, 0),
  },
];

test.describe("Stage C.V1B standalone engineering apps", () => {
  for (const entry of cases) {
    test(`${entry.caseId} loads as an isolated app`, async ({ page }) => {
      const consoleErrors = [];
      const pageErrors = [];
      page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
      page.on("pageerror", (error) => pageErrors.push(error.message));

      await page.goto(`/apps/${entry.slug}/`);
      await page.waitForFunction(() => window.__ENGINEERING_APP_DEBUG__?.activeWaveCount === 3);
      const state = await page.evaluate(() => ({
        caseId: window.__ENGINEERING_APP_DEBUG__.caseId,
        rendererCount: window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount,
        layerCount: window.__ENGINEERING_APP_DEBUG__.getLayerScreenPositions().length,
        wave: window.__ENGINEERING_APP_DEBUG__.waveInfo,
      }));
      expect(state.caseId).toBe(entry.caseId);
      expect(state.rendererCount).toBe(1);
      expect(state.layerCount).toBe(entry.layers);
      entry.assertDefault(state.wave);

      await page.screenshot({ path: resolve(evidenceDir, entry.screenshot), fullPage: true });
      await page.getByTestId(entry.contrastTestId).click();
      const contrastWave = await page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.waveInfo);
      entry.assertContrast(contrastWave);
      await page.screenshot({ path: resolve(evidenceDir, entry.contrastScreenshot), fullPage: true });

      await page.locator("#btn-side").click();
      await expect.poll(() => page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.currentCameraPreset)).toBe("SIDE_SECTION");
      await page.locator("#btn-reset").click();
      await expect.poll(() => page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.currentCameraPreset)).toBe("ISOMETRIC_SECTION");

      await page.locator("#btn-play-pause").click();
      await page.waitForTimeout(50);
      const pausedAt = await page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.animationState.time);
      await page.waitForTimeout(120);
      const after = await page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.animationState.time);
      expect(after).toBeCloseTo(pausedAt, 5);
      expect(consoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
    });
  }

  test("all four engineering entries use distinct document runtimes", async ({ page }) => {
    for (const path of ["solar-ar", "wdm-filter", "laser-mirror", "phone-lens-ar"]) {
      await page.goto(`/apps/${path}/`);
      await expect(page.locator("canvas")).toHaveCount(1);
      await expect(page.locator("a.back-link")).toHaveAttribute("href", "../../");
    }
  });
});
