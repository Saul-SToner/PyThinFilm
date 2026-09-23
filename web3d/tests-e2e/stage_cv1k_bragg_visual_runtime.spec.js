import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const evidenceDir = resolve("../docs/visualization/runtime/stage_cv1k");

test("Bragg visual prototype exposes formal periods and same-wavelength TE/TM comparison", async ({ page }) => {
  const consoleErrors = [];
  const pageErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/apps/bragg-reflector/");
  await page.waitForFunction(() => Boolean(window.__BRAGG_VISUAL_STORY_DEBUG__));

  expect(await page.evaluate(() => window.__BRAGG_VISUAL_STORY_DEBUG__.regionIds)).toEqual([
    "period_1",
    "period_2",
    "period_3",
    "terminal_h",
  ]);
  expect(await page.evaluate(() => window.__BRAGG_VISUAL_STORY_DEBUG__.markerCount)).toBe(4);
  await expect(page.locator(".bragg-material-legend")).toContainText("H 高折射率");
  await expect(page.locator(".bragg-material-legend")).toContainText("L 低折射率");

  await page.locator('[data-bragg-region="period_2"]').click();
  expect(await page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.selectedLayerIndex)).toBe(2);
  expect(await page.evaluate(() => window.__BRAGG_VISUAL_STORY_DEBUG__.selectedRegion)).toBe("period_2");

  await page.locator("[data-guide-start]").click();
  await page.locator("[data-step-action]").click();
  await page.locator("[data-guide-next]").click();
  await page.locator("[data-step-action]").click();
  await expect(page.locator("#wavelength-readout")).toContainText("498.00 nm · TE");
  await expect(page.locator("#bragg-value-te")).toHaveText("96.38%");
  await expect(page.locator("#bragg-value-tm")).toHaveText("79.16%");
  await expect(page.locator("#bragg-delta-r")).toContainText("17.22 个百分点");

  const stateBeforeFocus = await page.evaluate(() => ({
    wavelength: window.__ENGINEERING_APP_DEBUG__.waveInfo.selectedWavelengthNm,
    polarization: window.__ENGINEERING_APP_DEBUG__.app.polarization,
    stepIndex: window.__GUIDED_TEACHING_DEBUG__.stepIndex,
    rendererCount: window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount,
    canvasCount: document.querySelectorAll("canvas").length,
  }));
  const readingGuideBox = await page.locator(".bragg-structure-guide").boundingBox();
  const readingDrawerBox = await page.locator("#guided-teaching-drawer").boundingBox();
  expect(readingGuideBox.x + readingGuideBox.width).toBeLessThanOrEqual(readingDrawerBox.x);
  await page.screenshot({ path: resolve(evidenceDir, "bragg_reading.png"), fullPage: true });

  await page.locator(".bragg-reading-toggle").click();
  await expect(page.locator("#guided-teaching-drawer")).toHaveClass(/is-model-focus/);
  await expect(page.locator(".bragg-reading-toggle")).toHaveText("阅读解释");
  await expect(page.locator(".bragg-model-focus-summary")).toContainText("步骤 2 / 5");
  expect(await page.evaluate(() => window.__BRAGG_VISUAL_STORY_DEBUG__.viewMode)).toBe("MODEL");
  expect(await page.evaluate(() => ({
    wavelength: window.__ENGINEERING_APP_DEBUG__.waveInfo.selectedWavelengthNm,
    polarization: window.__ENGINEERING_APP_DEBUG__.app.polarization,
    stepIndex: window.__GUIDED_TEACHING_DEBUG__.stepIndex,
    rendererCount: window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount,
    canvasCount: document.querySelectorAll("canvas").length,
  }))).toEqual(stateBeforeFocus);
  await page.screenshot({ path: resolve(evidenceDir, "bragg_model_focus.png"), fullPage: true });

  await page.locator(".bragg-reading-toggle").click();
  await expect(page.locator(".guide-progress")).toContainText("步骤 2 / 5");
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});
