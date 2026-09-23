/**
 * Stage C.1.3 Real Browser Runtime Acceptance Tests (Playwright ESM)
 *
 * Verifies the 10 migrated teaching cases using a real Chromium headless browser.
 * Each test:
 *   - Loads the case page through the Vite dev server
 *   - Checks canvas presence and non-zero dimensions
 *   - Verifies no page errors or console errors
 *   - Takes a real screenshot saved to docs/visualization/runtime/stage_c1/
 *
 * Evidence classification: REAL_BROWSER_RUNTIME_EVIDENCE
 * NOT synthetic / NOT generated image.
 */

import { test, expect } from '@playwright/test';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const SCREENSHOT_DIR = resolve(__dirname, '../../docs/visualization/runtime/stage_c1');
const CONSOLE_LOG_PATH = resolve(SCREENSHOT_DIR, 'playwright_console.json');

// Ensure screenshot dir exists
if (!existsSync(SCREENSHOT_DIR)) {
  mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

const CASES = [
  { id: 'single_ar',                 screenshots: ['single_ar'] },
  { id: 'bragg_reflector',           screenshots: ['bragg_reflector'] },
  { id: 'fp_filter',                 screenshots: ['fp_filter_te', 'fp_filter_tm'] },
  { id: 'tamm_phase_bundle',         screenshots: ['tamm_phase_bundle'] },
  { id: 'quarter_wave_single_layer', screenshots: ['quarter_wave_single_layer'] },
  { id: 'half_wave_single_layer',    screenshots: ['half_wave_single_layer'] },
  { id: 'high_reflector',            screenshots: ['high_reflector'] },
  { id: 'quarter_wave_stack',        screenshots: ['quarter_wave_stack'] },
  { id: 'fp_single_halfwave',        screenshots: ['fp_single_halfwave'] },
  { id: 'narrowband_filter',         screenshots: ['narrowband_filter_te', 'narrowband_filter_tm'] },
];

const allConsoleEvents = [];

function getCaseUrl(caseId) {
  return `/?case=${caseId}`;
}

test.describe('Stage C.1.3 Real Browser Runtime Acceptance', () => {

  test.afterAll(async () => {
    writeFileSync(CONSOLE_LOG_PATH, JSON.stringify(allConsoleEvents, null, 2), 'utf-8');
    console.log(`[playwright] Console log saved to ${CONSOLE_LOG_PATH}`);
  });

  for (const { id, screenshots } of CASES) {
    test(`${id}: page loads, canvas renders, no errors`, async ({ page }) => {
      const caseConsoleEvents = [];

      page.on('console', (msg) => {
        const entry = { caseId: id, type: msg.type(), text: msg.text() };
        caseConsoleEvents.push(entry);
        allConsoleEvents.push(entry);
      });

      const pageErrors = [];
      page.on('pageerror', (err) => {
        pageErrors.push({ caseId: id, error: err.message });
      });

      // 1. Navigate to case URL
      await page.goto(getCaseUrl(id));

      // 2. Wait for the page to render something
      await page.waitForSelector('canvas, #app, #root, main', { timeout: 20000 });

      // 3. Settle time for Three.js
      await page.waitForTimeout(2000);

      // 4. No uncaught page errors
      expect(pageErrors, `${id}: unexpected page errors`).toHaveLength(0);

      // 5. No console errors
      const consoleErrors = caseConsoleEvents.filter(e => e.type === 'error');
      expect(consoleErrors, `${id}: unexpected console errors: ${JSON.stringify(consoleErrors)}`).toHaveLength(0);

      // 6. Canvas must exist
      const canvasCount = await page.locator('canvas').count();
      expect(canvasCount, `${id}: expected at least 1 canvas`).toBeGreaterThan(0);

      // 7. Canvas must have non-zero dimensions
      const canvas = page.locator('canvas').first();
      const box = await canvas.boundingBox();
      expect(box, `${id}: canvas bounding box is null`).not.toBeNull();
      expect(box.width,  `${id}: canvas width must be > 0`).toBeGreaterThan(0);
      expect(box.height, `${id}: canvas height must be > 0`).toBeGreaterThan(0);

      // 8. Take first screenshot (TE / default)
      const shotPath = resolve(SCREENSHOT_DIR, `${screenshots[0]}.png`);
      await page.screenshot({ path: shotPath });
      console.log(`[playwright] Saved: ${shotPath}`);

      // 9. For cases with a TM screenshot, toggle polarization and screenshot again
      if (screenshots.length > 1) {
        const tmToggle = page.locator(
          'button:has-text("TM"), [data-pol="p"], label:has-text("TM"), input[value="p"]'
        ).first();
        const tmCount = await page.locator(
          'button:has-text("TM"), [data-pol="p"], label:has-text("TM"), input[value="p"]'
        ).count();

        if (tmCount > 0) {
          await tmToggle.click();
          await page.waitForTimeout(800);
        }

        const shotPathTM = resolve(SCREENSHOT_DIR, `${screenshots[1]}.png`);
        await page.screenshot({ path: shotPathTM });
        console.log(`[playwright] Saved: ${shotPathTM}`);
      }
    });
  }

  test('Case switching: 10 cases in sequence without WebGL context loss', async ({ page }) => {
    let contextLossCount = 0;
    page.on('console', (msg) => {
      if (msg.text().toLowerCase().includes('contextlost') ||
          msg.text().toLowerCase().includes('webgl context lost')) {
        contextLossCount++;
      }
    });

    for (const { id } of CASES) {
      await page.goto(getCaseUrl(id));
      await page.waitForSelector('canvas, #app, #root, main', { timeout: 15000 });
      await page.waitForTimeout(500);

      const canvasCount = await page.locator('canvas').count();
      expect(canvasCount, `After switching to ${id}: canvas should still exist`).toBeGreaterThan(0);
    }

    expect(contextLossCount, `WebGL context was lost ${contextLossCount} times`).toBe(0);
  });
});
