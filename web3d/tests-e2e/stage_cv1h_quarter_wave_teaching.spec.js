import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const evidenceDir = resolve("../docs/visualization/runtime/stage_cv1h");

test("quarter-wave case supports free exploration and optional guided learning", async ({ page }) => {
  const consoleErrors = [];
  const pageErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/apps/quarter-wave-single-layer/");
  await page.waitForFunction(() => Boolean(window.__QUARTER_WAVE_TEACHING_DEBUG__));
  await expect(page.locator("#teaching-mode-label")).toHaveText("自由探索");
  await expect(page.locator(".teaching-illustration-badge")).toContainText("不代表定量空间电场");
  await expect(page.locator(".power-section .section-label")).toContainText("正式光谱插值");
  expect(await page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount)).toBe(1);
  await page.screenshot({ path: resolve(evidenceDir, "quarter_wave_free.png"), fullPage: true });

  await page.locator("[data-guide-start]").click();
  await expect(page.locator("#teaching-mode-label")).toHaveText("引导学习");
  await expect(page.locator(".guide-progress")).toContainText("步骤 1 / 5");

  await page.locator("[data-step-action]").click();
  await expect.poll(() => page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.selectedLayerIndex)).toBe(0);
  await expect(page.locator("#guide-completion")).toContainText("已完成");
  await page.locator("[data-guide-next]").click();

  await page.locator("[data-step-action]").click();
  await expect.poll(() => page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.waveInfo.selectedWavelengthNm)).toBe(550);
  await expect(page.locator(".expected-observation")).toContainText("R=4.0048%");
  await page.locator("[data-guide-next]").click();

  await page.locator("[data-step-action]").click();
  await expect.poll(() => page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.waveInfo.selectedWavelengthNm)).toBe(650);
  await page.locator("[data-guide-next]").click();

  await page.locator("[data-step-action]").click();
  await expect(page.locator("#wavelength-readout")).toContainText("TM");
  await expect(page.locator(".expected-observation")).toContainText("45° 斜入射");
  await page.locator("[data-guide-next]").click();

  await page.locator('[data-quiz-option="oblique"]').click();
  await expect(page.locator("#quiz-feedback")).toContainText("正确");
  await expect(page.locator("[data-guide-next]")).toBeEnabled();
  await page.screenshot({ path: resolve(evidenceDir, "quarter_wave_guided.png"), fullPage: true });
  await page.locator("[data-guide-next]").click();
  await expect(page.locator("#teaching-mode-label")).toHaveText("自由探索");

  await page.locator('[data-teaching-tab="advanced"]').click();
  await expect(page.locator("details")).toHaveCount(2);
  expect(await page.evaluate(() => [...document.querySelectorAll("details")].every((item) => !item.open))).toBe(true);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});
