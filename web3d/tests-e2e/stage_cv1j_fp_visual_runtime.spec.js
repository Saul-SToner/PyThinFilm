import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const evidenceDir = resolve("../docs/visualization/runtime/stage_cv1j");

test("F-P visual prototype separates reading and model observation without changing formal state", async ({ page }) => {
  const consoleErrors = [];
  const pageErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/apps/fp-filter/");
  await page.waitForFunction(() => Boolean(window.__FP_VISUAL_STORY_DEBUG__));

  expect(await page.evaluate(() => window.__FP_VISUAL_STORY_DEBUG__.regionIds)).toEqual([
    "incident_dbr",
    "defect_cavity",
    "substrate_dbr",
  ]);
  expect(await page.evaluate(() => window.__FP_VISUAL_STORY_DEBUG__.cavityMarkerCount)).toBe(1);
  await expect(page.locator(".fp-structure-guide")).toContainText("结构标注，不代表场强");
  await expect(page.locator(".fp-cavity-pin")).toContainText("中央缺陷腔");

  await page.locator('[data-fp-region="defect_cavity"]').click();
  expect(await page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.selectedLayerIndex)).toBe(6);
  expect(await page.evaluate(() => window.__FP_VISUAL_STORY_DEBUG__.selectedRegion)).toBe("defect_cavity");

  await page.locator("[data-guide-start]").click();
  await page.locator("[data-step-action]").click();
  await page.locator("[data-guide-next]").click();
  await page.locator("[data-step-action]").click();
  await expect(page.locator("#wavelength-readout")).toContainText("484.00 nm · TE");

  const stateBeforeFocus = await page.evaluate(() => ({
    wavelength: window.__ENGINEERING_APP_DEBUG__.waveInfo.selectedWavelengthNm,
    stepIndex: window.__GUIDED_TEACHING_DEBUG__.stepIndex,
    rendererCount: window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount,
    canvasCount: document.querySelectorAll("canvas").length,
  }));
  const readingGuideBox = await page.locator(".fp-structure-guide").boundingBox();
  const readingDrawerBox = await page.locator("#guided-teaching-drawer").boundingBox();
  const readingPinBox = await page.locator(".fp-cavity-pin").boundingBox();
  const stageBox = await page.locator(".solar-stage").boundingBox();
  expect(readingGuideBox.x + readingGuideBox.width).toBeLessThanOrEqual(readingDrawerBox.x);
  expect(readingPinBox.x).toBeGreaterThanOrEqual(stageBox.x);
  expect(readingPinBox.x + readingPinBox.width).toBeLessThanOrEqual(stageBox.x + stageBox.width);
  await page.screenshot({ path: resolve(evidenceDir, "fp_reading.png"), fullPage: true });

  await page.locator(".fp-reading-toggle").click();
  await expect(page.locator("#guided-teaching-drawer")).toHaveClass(/is-model-focus/);
  await expect(page.locator(".fp-reading-toggle")).toHaveText("阅读解释");
  await expect(page.locator(".fp-model-focus-summary")).toContainText("步骤 2 / 5");
  await expect(page.locator(".fp-cavity-pin")).toBeVisible();
  expect(await page.evaluate(() => window.__FP_VISUAL_STORY_DEBUG__.viewMode)).toBe("MODEL");
  expect(await page.evaluate(() => ({
    wavelength: window.__ENGINEERING_APP_DEBUG__.waveInfo.selectedWavelengthNm,
    stepIndex: window.__GUIDED_TEACHING_DEBUG__.stepIndex,
    rendererCount: window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount,
    canvasCount: document.querySelectorAll("canvas").length,
  }))).toEqual(stateBeforeFocus);
  await page.screenshot({ path: resolve(evidenceDir, "fp_model_focus.png"), fullPage: true });

  await page.locator(".fp-reading-toggle").click();
  await expect(page.locator("#guided-teaching-drawer")).not.toHaveClass(/is-model-focus/);
  await expect(page.locator(".guide-progress")).toContainText("步骤 2 / 5");
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});
