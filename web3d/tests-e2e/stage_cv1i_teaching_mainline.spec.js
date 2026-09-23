import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const evidenceDir = resolve("../docs/visualization/runtime/stage_cv1i");
const cases = [
  ["bragg-reflector", "bragg_reflector", "constructive", "bragg_guided.png"],
  ["fp-filter", "fp_filter", "inside", "fp_guided.png"],
  ["tamm-phase-bundle", "tamm_phase_bundle", "candidate", "tamm_guided.png"],
];

test.describe("Stage C.V1I undergraduate teaching mainline", () => {
  for (const [slug, caseId, correctOption, screenshot] of cases) {
    test(`${caseId} has its own evidence-bound guided lesson`, async ({ page }) => {
      const consoleErrors = [];
      const pageErrors = [];
      page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
      page.on("pageerror", (error) => pageErrors.push(error.message));

      await page.goto(`/apps/${slug}/`);
      await page.waitForFunction(() => Boolean(window.__GUIDED_TEACHING_DEBUG__));
      expect(await page.evaluate(() => window.__GUIDED_TEACHING_DEBUG__.caseId)).toBe(caseId);
      expect(await page.evaluate(() => window.__ENGINEERING_APP_DEBUG__.rendererInstanceCount)).toBe(1);
      await expect(page.locator("#teaching-mode-label")).toHaveText("自由探索");
      await expect(page.locator(".teaching-illustration-badge")).toContainText("不代表定量空间电场");

      await page.locator("[data-guide-start]").click();
      for (let stepIndex = 0; stepIndex < 4; stepIndex += 1) {
        await expect(page.locator(".guide-progress")).toContainText(`步骤 ${stepIndex + 1} / 5`);
        await page.locator("[data-step-action]").click();
        await expect.poll(() => page.evaluate(() => window.__GUIDED_TEACHING_DEBUG__.stepComplete)).toBe(true);
        await page.locator("[data-guide-next]").click();
      }

      await page.locator(`[data-quiz-option="${correctOption}"]`).click();
      await expect(page.locator("#quiz-feedback")).toContainText("正确");
      await page.screenshot({ path: resolve(evidenceDir, screenshot), fullPage: true });
      await page.locator("[data-guide-next]").click();
      await expect(page.locator("#teaching-mode-label")).toHaveText("自由探索");
      await page.locator('[data-tab="advanced"]').click();
      await expect(page.locator("details")).toHaveCount(2);
      expect(await page.evaluate(() => [...document.querySelectorAll("details")].every((item) => !item.open))).toBe(true);

      expect(consoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
    });
  }
});
