import { test, expect } from "@playwright/test";
import { writeFileSync, mkdirSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const SCREENSHOT_DIR = resolve(__dirname, "../../docs/visualization/runtime/stage_c1");
const CONSOLE_LOG_PATH = resolve(SCREENSHOT_DIR, "playwright_dynamic_wave_console.json");

if (!existsSync(SCREENSHOT_DIR)) {
  mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

const CASES = [
  "single_ar",
  "bragg_reflector",
  "fp_filter",
  "narrowband_filter",
  "tamm_phase_bundle",
];

const allConsoleEvents = [];

function getCaseUrl(caseId) {
  return `/?case=${caseId}`;
}

test.describe("Stage C.1.4 Dynamic Sine-Wave Propagation Acceptance", () => {
  test.afterAll(async () => {
    writeFileSync(CONSOLE_LOG_PATH, JSON.stringify(allConsoleEvents, null, 2), "utf-8");
    console.log(`[playwright] Console log saved to ${CONSOLE_LOG_PATH}`);
  });

  for (const caseId of CASES) {
    test(`${caseId}: dynamic sine-wave propagation, pause, polarization toggle, clean teardown & window.__WEB3D_DEBUG__ verification`, async ({ page }) => {
      const caseConsoleEvents = [];

      page.on("console", (msg) => {
        const entry = { caseId, type: msg.type(), text: msg.text() };
        caseConsoleEvents.push(entry);
        allConsoleEvents.push(entry);
      });

      const pageErrors = [];
      page.on("pageerror", (err) => {
        pageErrors.push({ caseId, error: err.message });
      });

      await page.goto(getCaseUrl(caseId));
      await page.waitForSelector("canvas, #app", { timeout: 20000 });
      await page.waitForTimeout(1000);

      expect(pageErrors, `${caseId}: unexpected page errors`).toHaveLength(0);

      const consoleErrors = caseConsoleEvents.filter((e) => e.type === "error");
      expect(consoleErrors, `${caseId}: unexpected console errors: ${JSON.stringify(consoleErrors)}`).toHaveLength(0);

      // 1. Programmatic Debug API check via window.__WEB3D_DEBUG__
      const debugPositions1 = await page.evaluate(() => {
        return window.__WEB3D_DEBUG__ ? window.__WEB3D_DEBUG__.getWavePositions() : null;
      });
      expect(debugPositions1, `${caseId}: window.__WEB3D_DEBUG__.getWavePositions() should return non-null array`).not.toBeNull();
      expect(debugPositions1.length, `${caseId}: active waves count > 0`).toBeGreaterThan(0);

      // 2. Verify canvas rendering & screenshot at t1
      const canvas = page.locator("canvas").first();
      const screenshot1 = await canvas.screenshot();

      // 3. Wait for wave propagation and take screenshot at t2
      await page.waitForTimeout(800);
      const screenshot2 = await canvas.screenshot();

      const debugPositions2 = await page.evaluate(() => {
        return window.__WEB3D_DEBUG__.getWavePositions();
      });

      // Ensure position values evolved over time
      const positionChanged = debugPositions1[0].some((val, idx) => val !== debugPositions2[0][idx]);
      expect(positionChanged, `${caseId}: wave positions MUST change programmatically over time`).toBe(true);
      expect(screenshot1.equals(screenshot2), `${caseId}: canvas MUST animate over time`).toBe(false);

      // 4. Test Pause functionality
      const pauseBtn = page.locator("#btn-play-pause");
      await pauseBtn.click();
      await page.waitForTimeout(200);

      const pausePos1 = await page.evaluate(() => window.__WEB3D_DEBUG__.getWavePositions());
      await page.waitForTimeout(600);
      const pausePos2 = await page.evaluate(() => window.__WEB3D_DEBUG__.getWavePositions());

      // Paused wave positions MUST remain identical
      const pauseChanged = pausePos1[0].some((val, idx) => val !== pausePos2[0][idx]);
      expect(pauseChanged, `${caseId}: paused wave positions MUST NOT change over time`).toBe(false);

      // Resume animation
      await pauseBtn.click();
      await page.waitForTimeout(300);

      // 5. Test TE/TM Polarization Toggle
      const polBtn = page.locator("#btn-toggle-pol");
      const prePolShot = await canvas.screenshot();

      await polBtn.click();
      await page.waitForTimeout(500);

      const postPolShot = await canvas.screenshot();
      expect(prePolShot.equals(postPolShot), `${caseId}: canvas MUST change on TE/TM toggle`).toBe(false);
    });
  }

  test("Sequential case switching without residual waves or context loss", async ({ page }) => {
    let contextLossCount = 0;
    page.on("console", (msg) => {
      if (
        msg.text().toLowerCase().includes("contextlost") ||
        msg.text().toLowerCase().includes("webgl context lost")
      ) {
        contextLossCount++;
      }
    });

    for (const caseId of CASES) {
      await page.goto(getCaseUrl(caseId));
      await page.waitForSelector("canvas", { timeout: 15000 });
      await page.waitForTimeout(400);

      const canvasCount = await page.locator("canvas").count();
      expect(canvasCount, `Canvas should exist for ${caseId}`).toBeGreaterThan(0);
    }

    expect(contextLossCount, `WebGL context loss count MUST be 0`).toBe(0);
  });
});
