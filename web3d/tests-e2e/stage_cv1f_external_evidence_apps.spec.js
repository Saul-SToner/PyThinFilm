import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

const evidenceDir = resolve("../docs/visualization/runtime/stage_cv1f");
const entries = [
  ["tamm-interface-priority", "tamm_interface_priority", "READY_EXTERNAL", null],
  ["tamm-phase-candidates", "tamm_phase_candidates", "READY_EXTERNAL", "tamm_phase_candidates.png"],
  ["tamm-phase-focus", "tamm_phase_focus", "READY_EXTERNAL", null],
  ["tamm-reflection-phase-screen", "tamm_reflection_phase_screen", "READY_EXTERNAL", null],
  ["tamm-interface-window-bundle", "tamm_interface_window_bundle", "DEGRADED_PARTIAL_INPUT", "tamm_window_degraded.png"],
  ["tamm-interface-window-scan", "tamm_interface_window_scan", "DEGRADED_PARTIAL_INPUT", null],
  ["absorbing-baseline-template", "absorbing_baseline_template", "TEMPLATE_ONLY", null],
  ["absorbing-surface-bundle", "absorbing_surface_bundle", "READY_EXTERNAL", null],
  ["absorbing-surface-gain", "absorbing_surface_gain", "READY_EXTERNAL", "absorbing_surface_gain.png"],
  ["absorbing-surface-gain-trend", "absorbing_surface_gain_trend", "READY_EXTERNAL", null],
  ["advanced-ar-bundle", "advanced_ar_bundle", "READY_EXTERNAL", "advanced_ar_bundle.png"],
  ["porous-double-ar-topic", "porous_double_ar_topic_bundle", "READY_EXTERNAL_WITH_LIMITS", null],
];

test.describe("Stage C.V1F external evidence apps", () => {
  for (const [slug, caseId, evidenceStatus, screenshot] of entries) {
    test(`${caseId} loads an isolated auditable contract`, async ({ page }) => {
      const consoleErrors = [];
      const pageErrors = [];
      page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
      page.on("pageerror", (error) => pageErrors.push(error.message));

      await page.goto(`/apps/${slug}/`);
      await page.waitForFunction(() => Boolean(window.__EVIDENCE_APP_DEBUG__?.caseId));
      const state = await page.evaluate(() => ({
        caseId: window.__EVIDENCE_APP_DEBUG__.caseId,
        evidenceStatus: window.__EVIDENCE_APP_DEBUG__.evidenceStatus,
        rendererCount: window.__EVIDENCE_APP_DEBUG__.rendererInstanceCount,
        seriesCount: window.__EVIDENCE_APP_DEBUG__.seriesCount,
        provenanceStatuses: window.__EVIDENCE_APP_DEBUG__.provenanceStatuses,
      }));

      expect(state.caseId).toBe(caseId);
      expect(state.evidenceStatus).toBe(evidenceStatus);
      expect(state.rendererCount).toBe(1);
      await expect(page.locator("#evidence-three-canvas canvas")).toHaveCount(1);
      await page.locator("#reset-three-view").click();
      await expect.poll(() => page.evaluate(() => window.__EVIDENCE_APP_DEBUG__.cameraPreset)).toBe("ISOMETRIC_SECTION");
      await expect(page.locator("#evidence-error")).toHaveClass(/hidden/);
      await expect(page.locator("#contract-case-id")).toHaveText(caseId);
      await expect(page.locator(".summary-card")).not.toHaveCount(0);
      await expect(page.locator(".provenance-row")).not.toHaveCount(0);

      if (evidenceStatus === "DEGRADED_PARTIAL_INPUT") {
        expect(state.provenanceStatuses).toContain("MISSING");
        await expect(page.locator('[data-status="MISSING"]')).toHaveCount(3);
      }
      if (evidenceStatus === "TEMPLATE_ONLY") {
        expect(state.seriesCount).toBe(0);
        await expect(page.locator(".evidence-empty")).toContainText("没有可诚实绘制");
      }
      if (screenshot) await page.screenshot({ path: resolve(evidenceDir, screenshot), fullPage: true });

      expect(consoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
    });
  }
});
