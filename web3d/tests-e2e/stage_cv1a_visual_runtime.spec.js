import { test, expect } from "@playwright/test";
import { mkdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const OUTPUT_DIR = resolve(__dirname, "../../docs/visualization/runtime/stage_cv1a");
mkdirSync(OUTPUT_DIR, { recursive: true });

async function capture(page, name) {
  await page.waitForTimeout(160);
  await page.screenshot({ path: resolve(OUTPUT_DIR, name), fullPage: true });
}

test.describe("Stage C.V1A standalone solar AR app", () => {
  test("isolates runtime and makes low/high reflection wave differences observable", async ({ page }) => {
    const consoleErrors = [];
    const pageErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", (error) => pageErrors.push(error.message));

    await page.goto("/apps/solar-ar/");
    await page.waitForSelector("canvas", { timeout: 15000 });
    await page.waitForFunction(() => window.__SOLAR_AR_DEBUG__?.waveInfo);

    const initial = await page.evaluate(() => ({
      rendererCount: window.__SOLAR_AR_DEBUG__.rendererInstanceCount,
      waveCount: window.__SOLAR_AR_DEBUG__.activeWaveCount,
      preset: window.__SOLAR_AR_DEBUG__.currentCameraPreset,
      layerCount: window.__SOLAR_AR_DEBUG__.app.solarScene.layerMeshes.length,
      waveInfo: window.__SOLAR_AR_DEBUG__.waveInfo,
    }));
    expect(initial.rendererCount).toBe(1);
    expect(initial.waveCount).toBe(3);
    expect(initial.preset).toBe("ISOMETRIC_SECTION");
    expect(initial.layerCount).toBe(3);
    expect(initial.waveInfo.rSelected).toBeLessThan(0.01);
    expect(initial.waveInfo.tSelected).toBeGreaterThan(0.99);
    await expect(page.locator("#spectral-verdict")).toContainText("低反射点");
    await capture(page, "solar_default.png");
    await capture(page, "solar_te.png");

    await page.locator("#btn-550nm").click();
    const at550 = await page.evaluate(() => window.__SOLAR_AR_DEBUG__.waveInfo);
    expect(at550.rSelected).toBeGreaterThan(0.4);
    expect(at550.tSelected).toBeLessThan(0.6);
    await expect(page.locator("#spectral-caveat")).toContainText("不能把该点自动称为“减反”");

    await page.locator("#btn-relative-high").click();
    const relativeHigh = await page.evaluate(() => window.__SOLAR_AR_DEBUG__.waveInfo);
    expect(relativeHigh.rSelected).toBeGreaterThan(initial.waveInfo.rSelected * 100);
    await expect(page.locator("#spectral-verdict")).toContainText("相对高反射点");
    await capture(page, "solar_relative_high.png");

    await page.locator("#btn-low-reflection").click();
    const lowAgain = await page.evaluate(() => window.__SOLAR_AR_DEBUG__.waveInfo);
    expect(lowAgain.rSelected).toBeLessThan(0.01);
    await capture(page, "solar_low_reflection.png");

    await page.locator("#btn-side").click();
    expect(await page.evaluate(() => window.__SOLAR_AR_DEBUG__.currentCameraPreset)).toBe("SIDE_SECTION");
    await capture(page, "solar_side.png");

    await page.locator("#btn-optical").click();
    expect(await page.evaluate(() => window.__SOLAR_AR_DEBUG__.currentCameraPreset)).toBe("OPTICAL_PATH");
    await capture(page, "solar_optical_path.png");

    await page.locator("#btn-reset").click();
    expect(await page.evaluate(() => window.__SOLAR_AR_DEBUG__.currentCameraPreset)).toBe("ISOMETRIC_SECTION");
    await page.waitForTimeout(100);

    const layerPositions = await page.evaluate(() => window.__SOLAR_AR_DEBUG__.getLayerScreenPositions());
    await page.mouse.click(layerPositions[1].x, layerPositions[1].y);
    expect(await page.evaluate(() => window.__SOLAR_AR_DEBUG__.selectedLayerIndex)).toBe(1);
    await expect(page.locator("#layer-detail")).toContainText("TiO2");

    const canvasBox = await page.locator("canvas").boundingBox();
    await page.mouse.click(canvasBox.x + 8, canvasBox.y + canvasBox.height - 8);
    expect(await page.evaluate(() => window.__SOLAR_AR_DEBUG__.selectedLayerIndex)).toBeNull();

    const beforeAnimation = await page.evaluate(() => window.__SOLAR_AR_DEBUG__.animationState.time);
    await page.waitForTimeout(180);
    const afterAnimation = await page.evaluate(() => window.__SOLAR_AR_DEBUG__.animationState.time);
    expect(afterAnimation).toBeGreaterThan(beforeAnimation);
    await page.locator("#btn-play-pause").click();
    const pausedAt = await page.evaluate(() => window.__SOLAR_AR_DEBUG__.animationState.time);
    await page.waitForTimeout(160);
    expect(await page.evaluate(() => window.__SOLAR_AR_DEBUG__.animationState.time)).toBeCloseTo(pausedAt, 5);
    await page.locator("#btn-play-pause").click();

    await page.locator("#btn-polarization").click();
    await expect(page.locator("#wavelength-readout")).toContainText("TM");
    await capture(page, "solar_tm.png");
    await page.locator("#btn-polarization").click();

    expect(pageErrors).toEqual([]);
    expect(consoleErrors).toEqual([]);
  });

  test("keeps the legacy case browser separate", async ({ page }) => {
    await page.goto("/?case=app_solar_cell_ar");
    await page.waitForSelector("canvas", { timeout: 15000 });
    await page.waitForFunction(() => window.__WEB3D_DEBUG__?.currentCaseConfig?.id === "app_solar_cell_ar");
    expect(await page.locator("#solar-ar-app").count()).toBe(0);
    expect(await page.locator("#btn-low-reflection").count()).toBe(0);
    expect(await page.evaluate(() => window.__WEB3D_DEBUG__.rendererInstanceCount)).toBe(1);
  });
});
