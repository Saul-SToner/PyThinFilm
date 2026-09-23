import { getEvidenceCaseConfig } from "./evidenceCaseConfigs.js";
import { SceneManager } from "../../core/SceneManager.js";
import { CameraManager } from "../../core/CameraManager.js";
import { RendererLifecycle } from "../../core/RendererLifecycle.js";
import { EvidenceThreeScene } from "./EvidenceThreeScene.js";

const SVG_NS = "http://www.w3.org/2000/svg";

function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "number") {
    const magnitude = Math.abs(value);
    if ((magnitude > 0 && magnitude < 1e-4) || magnitude >= 1e5) return value.toExponential(3);
    return Number.isInteger(value) ? String(value) : value.toFixed(magnitude < 0.1 ? 6 : 4).replace(/0+$/, "").replace(/\.$/, "");
  }
  if (Array.isArray(value)) return value.map(formatValue).join(" – ");
  return String(value);
}

function statusLabel(status) {
  return ({
    READY_EXTERNAL: "外部证据就绪",
    READY_EXTERNAL_WITH_LIMITS: "证据就绪 · 有限制",
    DEGRADED_PARTIAL_INPUT: "降级 · 部分输入缺失",
    TEMPLATE_ONLY: "仅输入模板",
  })[status] || status;
}

function createSvgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NS, name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
  return element;
}

function renderChart(container, series) {
  if (!series.length) {
    container.innerHTML = '<div class="evidence-empty">该案例没有可诚实绘制的连续曲线。</div>';
    return;
  }
  const allX = series.flatMap((item) => item.x || []).filter(Number.isFinite);
  const allY = series.flatMap((item) => item.y || []).filter(Number.isFinite);
  if (!allX.length || !allY.length) {
    container.innerHTML = '<div class="evidence-empty">曲线数组为空。</div>';
    return;
  }
  let xMin = Math.min(...allX); let xMax = Math.max(...allX);
  let yMin = Math.min(...allY); let yMax = Math.max(...allY);
  if (xMax === xMin) xMax = xMin + 1;
  if (yMax === yMin) yMax = yMin + 1;
  const yPad = (yMax - yMin) * 0.08;
  yMin -= yPad; yMax += yPad;
  const width = 900; const height = 430;
  const margin = { left: 78, right: 28, top: 28, bottom: 62 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const sx = (x) => margin.left + ((x - xMin) / (xMax - xMin)) * plotW;
  const sy = (y) => margin.top + (1 - (y - yMin) / (yMax - yMin)) * plotH;
  const svg = createSvgElement("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": "正式外部证据曲线" });
  const grid = createSvgElement("g", { class: "chart-grid" });
  for (let index = 0; index <= 5; index += 1) {
    const x = margin.left + (plotW * index) / 5;
    const y = margin.top + (plotH * index) / 5;
    grid.append(createSvgElement("line", { x1: x, y1: margin.top, x2: x, y2: margin.top + plotH }));
    grid.append(createSvgElement("line", { x1: margin.left, y1: y, x2: margin.left + plotW, y2: y }));
    const xText = createSvgElement("text", { x, y: margin.top + plotH + 24, "text-anchor": "middle" });
    xText.textContent = formatValue(xMin + ((xMax - xMin) * index) / 5);
    grid.append(xText);
    const yText = createSvgElement("text", { x: margin.left - 12, y: y + 4, "text-anchor": "end" });
    yText.textContent = formatValue(yMax - ((yMax - yMin) * index) / 5);
    grid.append(yText);
  }
  svg.append(grid);
  series.forEach((item) => {
    const points = (item.x || []).map((x, index) => [Number(x), Number(item.y?.[index])]).filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y));
    if (!points.length) return;
    const pathData = points.map(([x, y], index) => `${index ? "L" : "M"}${sx(x).toFixed(2)},${sy(y).toFixed(2)}`).join(" ");
    svg.append(createSvgElement("path", { d: pathData, fill: "none", stroke: item.color || "#6f879b", "stroke-width": 2.4, "vector-effect": "non-scaling-stroke" }));
  });
  const xLabel = createSvgElement("text", { x: margin.left + plotW / 2, y: height - 14, class: "axis-label", "text-anchor": "middle" });
  xLabel.textContent = series[0].x_label || "x";
  svg.append(xLabel);
  const yLabel = createSvgElement("text", { x: 18, y: margin.top + plotH / 2, class: "axis-label", transform: `rotate(-90 18 ${margin.top + plotH / 2})`, "text-anchor": "middle" });
  yLabel.textContent = series[0].y_label || "y";
  svg.append(yLabel);
  container.replaceChildren(svg);
  const legend = document.createElement("div");
  legend.className = "chart-legend";
  legend.innerHTML = series.map((item) => `<span><i style="background:${item.color || "#6f879b"}"></i>${item.label}</span>`).join("");
  container.append(legend);
}

function renderShell(root) {
  root.className = "evidence-app";
  root.innerHTML = `
    <header class="evidence-header"><div><div id="evidence-kicker" class="evidence-kicker"></div><h1 id="evidence-title"></h1></div><div class="header-actions"><span id="evidence-status" class="evidence-status"></span><a href="../../">返回通用案例浏览器</a></div></header>
    <main class="evidence-layout">
      <section class="evidence-main">
        <div id="summary-cards" class="summary-grid"></div>
        <article class="evidence-card three-card"><div class="section-heading"><span>Three.js 科研场景</span><button id="reset-three-view" type="button">重置视角</button></div><div id="evidence-three-canvas" class="evidence-three-canvas"></div><p id="three-scene-note" class="three-scene-note"></p></article>
        <article class="evidence-card chart-card"><div class="section-heading"><span>正式证据曲线</span><small>SVG · 非像素验收</small></div><div id="evidence-chart" class="evidence-chart"></div></article>
        <article class="evidence-card table-card"><div class="section-heading"><span>分析结果表</span><small>由正式契约读取</small></div><div class="table-scroll"><table><thead id="evidence-table-head"></thead><tbody id="evidence-table-body"></tbody></table></div></article>
      </section>
      <aside class="evidence-sidebar">
        <article class="evidence-card"><div class="section-heading"><span>外部数据来源</span><small>仅显示文件名与哈希</small></div><div id="provenance-list" class="provenance-list"></div></article>
        <article class="evidence-card"><div class="section-heading"><span>语义与限制</span></div><ul id="limitations" class="limitations"></ul></article>
        <article class="evidence-card contract-card"><div class="section-heading"><span>契约信息</span></div><dl><dt>case_id</dt><dd id="contract-case-id"></dd><dt>计算来源</dt><dd id="contract-source"></dd><dt>证据哈希</dt><dd id="contract-hash"></dd></dl></article>
      </aside>
    </main>
    <div id="evidence-error" class="evidence-error hidden" role="alert"></div>`;
}

export class EvidenceCaseApp {
  constructor(root, caseId) {
    this.root = root;
    this.config = getEvidenceCaseConfig(caseId);
    this.contract = null;
    this.sceneManager = null;
    this.cameraManager = null;
    this.rendererLifecycle = null;
    this.evidenceScene = null;
    this.boundResize = () => this.onResize();
    this.boundDispose = () => this.dispose();
  }

  async init() {
    renderShell(this.root);
    try {
      const url = new URL(`../../evidence/${this.config.caseId}.json`, window.location.href);
      const response = await fetch(url);
      if (!response.ok) throw new Error(`证据 JSON 加载失败：HTTP ${response.status}`);
      this.contract = await response.json();
      if (this.contract.case_id !== this.config.caseId) throw new Error("证据 case_id 不匹配");
      this.render();
      this.initThreeScene();
      this.exposeDebugApi();
    } catch (error) {
      const boundary = this.root.querySelector("#evidence-error");
      boundary.textContent = `${this.config.caseId} 初始化失败：${error.message}`;
      boundary.classList.remove("hidden");
      throw error;
    }
  }

  render() {
    const contract = this.contract;
    this.root.querySelector("#evidence-kicker").textContent = this.config.kicker;
    this.root.querySelector("#evidence-title").textContent = this.config.title;
    const status = this.root.querySelector("#evidence-status");
    status.textContent = statusLabel(contract.evidence_status);
    status.dataset.status = contract.evidence_status;
    this.root.querySelector("#summary-cards").innerHTML = (contract.summary_cards || []).map((card) => `
      <article class="summary-card"><span>${card.label}</span><strong>${formatValue(card.value)}${card.unit ? ` <small>${card.unit}</small>` : ""}</strong>${card.note ? `<p>${card.note}</p>` : ""}</article>`).join("");
    renderChart(this.root.querySelector("#evidence-chart"), contract.series || []);
    const columns = contract.table?.columns || [];
    this.root.querySelector("#evidence-table-head").innerHTML = columns.length ? `<tr>${columns.map((column) => `<th>${column}</th>`).join("")}</tr>` : "";
    this.root.querySelector("#evidence-table-body").innerHTML = (contract.table?.rows || []).map((row) => `<tr>${row.map((value) => `<td>${formatValue(value)}</td>`).join("")}</tr>`).join("") || `<tr><td class="empty-cell" colspan="${Math.max(columns.length, 1)}">此案例没有结果行。</td></tr>`;
    this.root.querySelector("#provenance-list").innerHTML = (contract.external_data_provenance || []).map((item) => `
      <div class="provenance-row" data-status="${item.status}"><div><strong>${item.role}</strong><span>${item.file_name}</span></div><em>${item.status === "AVAILABLE" ? `${(item.size_bytes / 1024).toFixed(1)} KiB` : "缺失"}</em><code>${item.sha256 ? item.sha256.slice(0, 16) : "NO HASH"}</code></div>`).join("");
    this.root.querySelector("#limitations").innerHTML = (contract.limitations || []).map((item) => `<li>${item}</li>`).join("");
    this.root.querySelector("#contract-case-id").textContent = contract.case_id;
    this.root.querySelector("#contract-source").textContent = contract.calculation_source;
    this.root.querySelector("#contract-hash").textContent = contract.evidence_hash;
    this.root.querySelector("#three-scene-note").textContent = this.config.sceneNote;
  }

  initThreeScene() {
    const container = this.root.querySelector("#evidence-three-canvas");
    this.sceneManager = new SceneManager();
    this.sceneManager.applyVisualTheme("ACADEMIC_LIGHT");
    this.cameraManager = new CameraManager(container);
    this.rendererLifecycle = new RendererLifecycle(container);
    this.cameraManager.initControls(this.rendererLifecycle.getDomElement());
    this.evidenceScene = new EvidenceThreeScene(this.config);
    this.sceneManager.getScene().add(this.evidenceScene.build(this.contract));
    this.cameraManager.setDefaultPreset("ISOMETRIC_SECTION", this.evidenceScene.getBounds());
    this.sceneManager.fitFogToCamera(this.cameraManager.getCamera(), this.cameraManager.getControls()?.target);
    this.root.querySelector("#reset-three-view").addEventListener("click", () => this.resetThreeView());
    window.addEventListener("resize", this.boundResize);
    window.addEventListener("beforeunload", this.boundDispose, { once: true });
    this.rendererLifecycle.startLoop(() => {
      this.cameraManager.getControls()?.update();
      this.rendererLifecycle.getRenderer().render(this.sceneManager.getScene(), this.cameraManager.getCamera());
    });
  }

  resetThreeView() {
    this.cameraManager?.resetView();
    this.sceneManager?.fitFogToCamera(this.cameraManager?.getCamera(), this.cameraManager?.getControls()?.target);
    return this.cameraManager?.currentPresetName || null;
  }

  onResize() {
    this.cameraManager?.onResize();
    this.rendererLifecycle?.onResize();
  }

  exposeDebugApi() {
    const app = this;
    window.__EVIDENCE_APP_DEBUG__ = {
      caseId: this.config.caseId,
      get evidenceStatus() { return app.contract?.evidence_status || null; },
      get seriesCount() { return app.contract?.series?.length || 0; },
      get tableRowCount() { return app.contract?.table?.rows?.length || 0; },
      get provenanceStatuses() { return (app.contract?.external_data_provenance || []).map((item) => item.status); },
      get rendererInstanceCount() { return app.rendererLifecycle?.getRenderer() ? 1 : 0; },
      get cameraPreset() { return app.cameraManager?.currentPresetName || null; },
      get sceneType() { return app.config.sceneType; },
      resetView: () => app.resetThreeView(),
    };
  }

  dispose() {
    window.removeEventListener("resize", this.boundResize);
    window.removeEventListener("beforeunload", this.boundDispose);
    this.evidenceScene?.dispose();
    this.cameraManager?.dispose();
    this.rendererLifecycle?.teardown();
    this.evidenceScene = null;
  }
}
