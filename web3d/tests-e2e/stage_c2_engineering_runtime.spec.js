import { test, expect } from "@playwright/test";
import { mkdirSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const SCREENSHOT_DIR = resolve(__dirname, "../../docs/visualization/runtime/stage_c2_1");
if (!existsSync(SCREENSHOT_DIR)) {
  mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

const LOSSLESS_ENGINEERING_CASES = [
  { id: "app_solar_cell_ar", expectedMode: "GENERIC_MULTILAYER_MODE", expectDbrUi: false },
  { id: "app_wdm_filter", expectedMode: "DEFECT_CAVITY_MODE", expectDbrUi: false },
  { id: "app_laser_mirror", expectedMode: "DBR_PERIODIC_MODE", expectDbrUi: true },
  { id: "app_phone_lens_ar", expectedMode: "GENERIC_MULTILAYER_MODE", expectDbrUi: false },
];

test.describe("Stage C.2.1B-1.1 Lossless Engineering Cases E2E Runtime Acceptance & Selected Spectrum Wave Amp", () => {
  for (const c of LOSSLESS_ENGINEERING_CASES) {
    test(`${c.id}: load, verify template_mode, dynamic waves, pause/play, TE/TM toggle & screenshot`, async ({ page }) => {
      const pageErrors = [];
      const consoleErrors = [];

      page.on("pageerror", (err) => pageErrors.push(err.message));
      page.on("console", (msg) => {
        if (msg.type() === "error") consoleErrors.push(msg.text());
      });

      await page.goto(`/?case=${c.id}`);
      await page.waitForSelector("canvas", { timeout: 15000 });
      await page.waitForTimeout(500);

      // Check debug interface & current case config
      await page.waitForFunction(() => window.__WEB3D_DEBUG__ && window.__WEB3D_DEBUG__.currentCaseConfig);
      const debugState = await page.evaluate(() => {
        const app = window.__WEB3D_DEBUG__.app;
        const tmpl = app.currentTemplateInstance;
        return {
          caseId: app.currentCaseConfig.id,
          gitCommit: app.currentCaseResult ? app.currentCaseResult.git_commit : null,
          templateMode: tmpl ? tmpl.templateMode : null,
          showDbrStopband: tmpl ? tmpl.showDbrStopband : null,
          showPeriodCount: tmpl ? tmpl.showPeriodCount : null,
          waveAmplitudeSource: tmpl ? tmpl.waveAmplitudeSource : null,
          activeWaveCount: window.__WEB3D_DEBUG__.activeWaveCount,
          rendererInstanceCount: window.__WEB3D_DEBUG__.rendererInstanceCount,
          forceContextLossCount: window.__WEB3D_DEBUG__.forceContextLossCount,
        };
      });

      expect(debugState.caseId).toBe(c.id);
      expect(debugState.templateMode).toBe(c.expectedMode);

      if (c.expectedMode === "GENERIC_MULTILAYER_MODE") {
        expect(debugState.showDbrStopband).toBe(false);
        expect(debugState.showPeriodCount).toBe(false);
      }

      expect(debugState.waveAmplitudeSource).toBe("SELECTED_WAVELENGTH_R_T_SCHEMATIC");

      expect(debugState.activeWaveCount).toBeGreaterThanOrEqual(3);
      expect(debugState.rendererInstanceCount).toBe(1);
      expect(debugState.forceContextLossCount).toBe(0);

      expect(pageErrors).toHaveLength(0);
      expect(consoleErrors).toHaveLength(0);

      // Capture screenshot
      const screenshotPath = resolve(SCREENSHOT_DIR, `${c.id}.png`);
      await page.screenshot({ path: screenshotPath });

      // Toggle pause/play
      const btnPause = page.locator("#btn-play-pause");
      if (await btnPause.count() > 0) {
        await btnPause.click();
        await page.waitForTimeout(100);
        await btnPause.click();
      }

      // Toggle polarization TE / TM
      const btnPol = page.locator("#btn-toggle-pol");
      if (await btnPol.count() > 0) {
        await btnPol.click();
        await page.waitForTimeout(100);
        await btnPol.click();
      }
    });
  }

  test("WDM filter selected wavelength dynamic wave response (peak 1550nm vs off-peak 1500nm)", async ({ page }) => {
    const pageErrors = [];
    const consoleErrors = [];

    page.on("pageerror", (err) => pageErrors.push(err.message));
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto("/?case=app_wdm_filter");
    await page.waitForSelector("canvas", { timeout: 15000 });

    // Set peak wavelength 1550nm without page reload
    await page.evaluate(() => window.__WEB3D_DEBUG__.setWavelength(1550));
    await page.waitForTimeout(300);

    const peakWaveAmp = await page.evaluate(() => {
      const tmpl = window.__WEB3D_DEBUG__.app.currentTemplateInstance;
      const positions = window.__WEB3D_DEBUG__.getWavePositions(); // [inc, ref, trans, cavity]
      const transWavePos = positions[2] || [];
      // Calculate max deviation from mean position in transmitted wave
      let maxDev = 0;
      for (let i = 0; i < transWavePos.length; i += 3) {
        const x = transWavePos[i];
        const y = transWavePos[i + 1];
        const z = transWavePos[i + 2];
        const dev = Math.abs(z); // TE polarization displacement is along Z
        if (dev > maxDev) maxDev = dev;
      }
      return {
        rAmp: tmpl.waveAmpInfo.rAmp,
        tAmp: tmpl.waveAmpInfo.tAmp,
        tSelected: tmpl.waveAmpInfo.tSelected,
        transWaveMaxDevZ: maxDev,
      };
    });

    // Set off-peak wavelength 1500nm without page reload
    await page.evaluate(() => window.__WEB3D_DEBUG__.setWavelength(1500));
    await page.waitForTimeout(300);

    const offWaveAmp = await page.evaluate(() => {
      const tmpl = window.__WEB3D_DEBUG__.app.currentTemplateInstance;
      const positions = window.__WEB3D_DEBUG__.getWavePositions();
      const transWavePos = positions[2] || [];
      let maxDev = 0;
      for (let i = 0; i < transWavePos.length; i += 3) {
        const dev = Math.abs(transWavePos[i + 2]);
        if (dev > maxDev) maxDev = dev;
      }
      return {
        rAmp: tmpl.waveAmpInfo.rAmp,
        tAmp: tmpl.waveAmpInfo.tAmp,
        tSelected: tmpl.waveAmpInfo.tSelected,
        transWaveMaxDevZ: maxDev,
      };
    });

    // Assert peak transmission wave amplitude is significantly larger than off-peak
    expect(peakWaveAmp.tAmp).toBeGreaterThan(offWaveAmp.tAmp * 2.0);
    expect(peakWaveAmp.tSelected).toBeGreaterThan(0.9);
    expect(offWaveAmp.tSelected).toBeLessThan(0.05);

    expect(pageErrors).toHaveLength(0);
    expect(consoleErrors).toHaveLength(0);
  });

  test("Sequential engineering case switching without context loss or UI leftover", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("canvas", { timeout: 15000 });

    for (const c of LOSSLESS_ENGINEERING_CASES) {
      await page.evaluate((caseId) => window.__WEB3D_DEBUG__.app.loadCase(caseId), c.id);
      await page.waitForTimeout(400);

      const activeCaseId = await page.evaluate(() => window.__WEB3D_DEBUG__.currentCaseConfig.id);
      expect(activeCaseId).toBe(c.id);
    }

    const debugState = await page.evaluate(() => ({
      rendererInstanceCount: window.__WEB3D_DEBUG__.rendererInstanceCount,
      caseUpdateSubscriptionRemovalCount: window.__WEB3D_DEBUG__.caseUpdateSubscriptionRemovalCount,
    }));

    expect(debugState.rendererInstanceCount).toBe(1);
    expect(debugState.caseUpdateSubscriptionRemovalCount).toBeGreaterThanOrEqual(3);
  });
});
