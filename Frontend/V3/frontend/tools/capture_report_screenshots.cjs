const { app, BrowserWindow } = require("electron");
const fs = require("fs");
const path = require("path");

const OUTPUT = path.resolve(__dirname, "..", "report-screenshots");
const URL = "http://127.0.0.1:5173/";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function evalJs(win, source) {
  return win.webContents.executeJavaScript(source, true);
}

async function clickButton(win, label) {
  const ok = await evalJs(
    win,
    `(() => {
      const wanted = ${JSON.stringify(label)};
      const el = [...document.querySelectorAll('button')].find((node) =>
        (node.innerText || '').replace(/\\s+/g, ' ').trim().includes(wanted)
      );
      if (!el) return false;
      el.click();
      return true;
    })()`,
  );
  if (!ok) throw new Error(`Button not found: ${label}`);
}

async function clickSummary(win, label) {
  const ok = await evalJs(
    win,
    `(() => {
      const wanted = ${JSON.stringify(label)};
      const el = [...document.querySelectorAll('summary')].find((node) =>
        (node.innerText || '').replace(/\\s+/g, ' ').trim().includes(wanted)
      );
      if (!el) return false;
      el.click();
      return true;
    })()`,
  );
  if (!ok) throw new Error(`Summary not found: ${label}`);
}

async function chooseCase(win, label) {
  const ok = await evalJs(
    win,
    `(() => {
      const select = document.querySelector('select#case');
      const wanted = ${JSON.stringify(label)};
      if (!select) return false;
      const option = [...select.options].find((item) => item.text === wanted);
      if (!option) return false;
      select.value = option.value;
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()`,
  );
  if (!ok) throw new Error(`Case option not found: ${label}`);
}

async function waitForText(win, text, timeoutMs = 45000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const found = await evalJs(
      win,
      `document.body && document.body.innerText.includes(${JSON.stringify(text)})`,
    );
    if (found) return;
    await sleep(500);
  }
  throw new Error(`Timed out waiting for text: ${text}`);
}

async function scrollToText(win, selector, label, block = "start") {
  const ok = await evalJs(
    win,
    `(() => {
      const wanted = ${JSON.stringify(label)};
      const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find((node) =>
        (node.innerText || '').replace(/\\s+/g, ' ').trim().includes(wanted)
      );
      if (!el) return false;
      el.scrollIntoView({ block: ${JSON.stringify(block)}, behavior: 'instant' });
      return true;
    })()`,
  );
  if (!ok) throw new Error(`Scroll target not found: ${label}`);
  await sleep(600);
}

async function capture(win, filename) {
  const image = await win.webContents.capturePage();
  fs.writeFileSync(path.join(OUTPUT, filename), image.toPNG());
}

async function run() {
  fs.mkdirSync(OUTPUT, { recursive: true });
  const win = new BrowserWindow({
    width: 1600,
    height: 1000,
    show: false,
    backgroundColor: "#ffffff",
    webPreferences: {
      backgroundThrottling: false,
      offscreen: true,
    },
  });
  await win.loadURL(URL);
  await waitForText(win, "PythonFilm");
  await sleep(2000);

  await capture(win, "01_v3_workspace.png");

  await clickSummary(win, "查看材料属性").catch(async () => {
    await evalJs(
      win,
      `(() => { const el = [...document.querySelectorAll('button')].find((n) => (n.innerText || '').includes('查看材料属性')); if (!el) return false; el.click(); return true; })()`,
    );
  });
  await sleep(500);
  await capture(win, "02_materials_and_3d.png");

  await clickButton(win, "光谱");
  await sleep(700);
  await scrollToText(win, "h3", "R / T / A 光谱", "start").catch(() => {});
  await capture(win, "07_rta_spacing_check.png");
  await clickButton(win, "概览");
  await sleep(300);

  await clickButton(win, "Optiland 系统分析");
  await waitForText(win, "能量传递", 60000);
  await scrollToText(win, "button", "Optiland 系统分析", "start");
  await capture(win, "03_optiland_system.png");

  await clickSummary(win, "鬼像与杂散光");
  await scrollToText(win, "details", "鬼像与杂散光", "start");
  await sleep(600);
  await capture(win, "08_optiland_ghost_stray.png");
  await clickSummary(win, "鬼像与杂散光");
  await clickSummary(win, "光谱与颜色");
  await scrollToText(win, "details", "光谱与颜色", "start");
  await sleep(600);
  await capture(win, "09_optiland_spectrum_color.png");
  await clickSummary(win, "光谱与颜色");

  await clickButton(win, "40例案例库");
  await waitForText(win, "案例与证据库");
  await sleep(800);
  await capture(win, "04_case_library.png");

  await chooseCase(win, "【虚拟实验（EMT）】一维亚波长光栅 EMT 零级近似");
  await waitForText(win, "开始 RCWA 仿真");
  await clickButton(win, "开始 RCWA 仿真");
  await waitForText(win, "专用求解器结果已生成", 60000);
  await scrollToText(win, "h2", "输出面板", "start");
  await capture(win, "05_rcwa_result.png");

  await chooseCase(win, "【研究拓展】Tamm 反射相位相干匹配束");
  await waitForText(win, "开始 GeneralTmm 仿真");
  await clickButton(win, "开始 GeneralTmm 仿真");
  await waitForText(win, "专用求解器结果已生成", 60000);
  await clickSummary(win, "界面场分布");
  await waitForText(win, "膜内峰值 |E|²");
  await scrollToText(win, "details", "界面场分布", "start");
  await sleep(1800);
  await capture(win, "06_tamm_field.png");

  win.destroy();
  app.quit();
}

app.whenReady().then(run).catch((error) => {
  console.error(error);
  app.exit(1);
});
