import { SceneManager } from "../../core/SceneManager.js";
import { CameraManager } from "../../core/CameraManager.js";
import { RendererLifecycle } from "../../core/RendererLifecycle.js";
import { AnimationController } from "../../core/AnimationController.js";
import { SolarArScene, SOLAR_WAVE_DISPLAY_SCALE } from "./SolarArScene.js";
import {
  classifyReflectance,
  getSolarComparisonPoints,
} from "./solarSpectrum.js";

export class SolarArApp {
  constructor(root) {
    this.root = root;
    this.canvasContainer = root.querySelector("#solar-canvas");
    this.caseResult = null;
    this.comparisonPoints = null;
    this.polarization = "TE";
    this.selectedWavelengthNm = null;
    this.sceneManager = null;
    this.cameraManager = null;
    this.rendererLifecycle = null;
    this.animationController = null;
    this.solarScene = null;
    this.lastTimestamp = 0;
    this.boundResize = () => this.onResize();
  }

  async init() {
    try {
      this.caseResult = await this.loadFormalResult();
      this.comparisonPoints = getSolarComparisonPoints(this.caseResult, this.polarization);
      this.selectedWavelengthNm = this.comparisonPoints.lowReflectionNm;
      this.renderLayerList();
      this.configureWavelengthControls();
      this.initEngine();
      this.bindControls();
      this.exposeDebugApi();
    } catch (error) {
      const boundary = this.root.querySelector("#solar-error");
      boundary.textContent = `独立 solar App 初始化失败：${error.message}`;
      boundary.classList.remove("hidden");
      throw error;
    }
  }

  async loadFormalResult() {
    const resultUrl = new URL("../../results/app_solar_cell_ar.json", window.location.href);
    const response = await fetch(resultUrl);
    if (!response.ok) throw new Error(`正式 JSON 加载失败：HTTP ${response.status}`);
    const result = await response.json();
    if (result.case_id !== "app_solar_cell_ar") throw new Error("正式 JSON case_id 不匹配");
    if (!Array.isArray(result.layers) || result.layers.length !== 3) throw new Error("正式膜层不是三层");
    return result;
  }

  initEngine() {
    this.sceneManager = new SceneManager();
    this.sceneManager.applyVisualTheme("ACADEMIC_LIGHT");
    this.cameraManager = new CameraManager(this.canvasContainer);
    this.rendererLifecycle = new RendererLifecycle(this.canvasContainer);
    this.cameraManager.initControls(this.rendererLifecycle.getDomElement());
    this.animationController = new AnimationController();

    this.solarScene = new SolarArScene({
      container: this.canvasContainer,
      camera: this.cameraManager.getCamera(),
      domElement: this.rendererLifecycle.getDomElement(),
      onLayerFocus: (layer, state) => this.updateLayerFocus(layer, state),
      onWaveInfo: (waveInfo) => this.updateWaveReadout(waveInfo),
    });
    const group = this.solarScene.build(this.caseResult, {
      polarization: this.polarization,
      selectedWavelengthNm: this.selectedWavelengthNm,
    });
    this.sceneManager.getScene().add(group);
    this.cameraManager.setDefaultPreset("ISOMETRIC_SECTION", this.solarScene.getStructureBounds());

    window.addEventListener("resize", this.boundResize);
    this.rendererLifecycle.startLoop((timestamp) => {
      const controls = this.cameraManager.getControls();
      if (controls) controls.update();
      if (!this.lastTimestamp) this.lastTimestamp = timestamp;
      const deltaSeconds = Math.min((timestamp - this.lastTimestamp) / 1000, 0.1);
      this.lastTimestamp = timestamp;
      const time = this.animationController.update(deltaSeconds);
      this.solarScene.updateAnimation(time);
      this.rendererLifecycle.getRenderer().render(
        this.sceneManager.getScene(),
        this.cameraManager.getCamera()
      );
    });
  }

  configureWavelengthControls() {
    const wavelengths = this.caseResult.wavelength_nm;
    const slider = this.root.querySelector("#wavelength-slider");
    slider.min = String(wavelengths[0]);
    slider.max = String(wavelengths[wavelengths.length - 1]);
    slider.step = String(wavelengths.length > 1 ? wavelengths[1] - wavelengths[0] : 1);
    slider.value = String(this.selectedWavelengthNm);
    this.root.querySelector("#display-scale-note").textContent = `${SOLAR_WAVE_DISPLAY_SCALE.toFixed(1)}×`;
  }

  renderLayerList() {
    const list = this.root.querySelector("#layer-list");
    list.innerHTML = this.caseResult.layers.map((layer, index) => `
      <div class="layer-row" data-layer-index="${index}">
        <span class="layer-number">${index + 1}</span>
        <strong>${layer.name}</strong>
        <span>${Number(layer.thickness_nm).toFixed(4)} nm</span>
      </div>
    `).join("");
  }

  bindControls() {
    const bind = (selector, handler) => this.root.querySelector(selector)?.addEventListener("click", handler);
    bind("#btn-isometric", () => this.setCameraPreset("ISOMETRIC_SECTION"));
    bind("#btn-side", () => this.setCameraPreset("SIDE_SECTION"));
    bind("#btn-optical", () => this.setCameraPreset("OPTICAL_PATH"));
    bind("#btn-reset", () => {
      this.setWavelength(this.comparisonPoints.lowReflectionNm);
      if (this.polarization !== "TE") this.setPolarization("TE");
      this.cameraManager.resetView();
      this.solarScene.clearSelection();
    });
    bind("#btn-play-pause", () => {
      const playing = this.animationController.togglePlayPause();
      this.root.querySelector("#btn-play-pause").textContent = playing ? "暂停" : "播放";
    });
    bind("#btn-polarization", () => this.setPolarization(this.polarization === "TE" ? "TM" : "TE"));
    bind("#btn-low-reflection", () => this.setWavelength(this.comparisonPoints.lowReflectionNm));
    bind("#btn-550nm", () => this.setWavelength(this.comparisonPoints.engineering550Nm));
    bind("#btn-relative-high", () => this.setWavelength(this.comparisonPoints.relativeHighNm));
    this.root.querySelector("#wavelength-slider")?.addEventListener("input", (event) => {
      this.setWavelength(Number(event.target.value));
    });
  }

  setCameraPreset(presetName) {
    return this.cameraManager.applyPreset(presetName, this.solarScene.getStructureBounds());
  }

  setWavelength(wavelengthNm) {
    this.selectedWavelengthNm = Number(wavelengthNm);
    this.root.querySelector("#wavelength-slider").value = String(this.selectedWavelengthNm);
    this.solarScene.setWavelength(this.selectedWavelengthNm);
  }

  setPolarization(polarization) {
    this.polarization = polarization === "TM" ? "TM" : "TE";
    this.comparisonPoints = getSolarComparisonPoints(this.caseResult, this.polarization);
    this.solarScene.setPolarization(this.polarization);
    this.root.querySelector("#btn-polarization").textContent = this.polarization === "TE" ? "切换为 TM" : "切换为 TE";
  }

  updateWaveReadout(waveInfo) {
    this.selectedWavelengthNm = waveInfo.selectedWavelengthNm;
    const reflectance = waveInfo.rSelected;
    const transmittance = waveInfo.tSelected;
    const absorptance = waveInfo.absorptance;
    const classification = classifyReflectance(reflectance);
    const percent = (value) => `${(100 * value).toFixed(2)}%`;
    const amplitudeRatio = (amplitude) => (amplitude / 0.25).toFixed(3);

    this.root.querySelector("#wavelength-readout").textContent = `${waveInfo.selectedWavelengthNm.toFixed(2)} nm · ${this.polarization}`;
    this.root.querySelector("#spectral-verdict").textContent = classification.label;
    this.root.querySelector("#spectral-verdict").dataset.classification = classification.id;
    this.root.querySelector("#spectral-caveat").textContent = this.getCaveat(waveInfo, classification.id);
    this.root.querySelector("#value-r").textContent = percent(reflectance);
    this.root.querySelector("#value-t").textContent = percent(transmittance);
    this.root.querySelector("#value-a").textContent = percent(absorptance);
    this.root.querySelector("#bar-r").style.width = percent(reflectance);
    this.root.querySelector("#bar-t").style.width = percent(transmittance);
    this.root.querySelector("#bar-a").style.width = percent(absorptance);
    this.root.querySelector("#amplitude-readout").textContent = `示意振幅比：Ar/Ai = ${amplitudeRatio(waveInfo.rAmp)} · At/Ai = ${amplitudeRatio(waveInfo.tAmp)}${waveInfo.isExaggerated ? " · 含最小可见值放大" : ""}`;
    this.root.querySelector('[data-wave-callout="reflected"]').textContent = `反射 R ${percent(reflectance)} · Ar/Ai ${amplitudeRatio(waveInfo.rAmp)}`;
    this.root.querySelector('[data-wave-callout="transmitted"]').textContent = `透射 T ${percent(transmittance)} · At/Ai ${amplitudeRatio(waveInfo.tAmp)}`;
  }

  getCaveat(waveInfo, classificationId) {
    if (Math.abs(waveInfo.selectedWavelengthNm - this.comparisonPoints.engineering550Nm) < 1) {
      const bareAverage = Number(this.caseResult.metrics?.avg_R_bare_Si);
      return `550 nm 处 R=${(100 * waveInfo.rSelected).toFixed(1)}%；当前正式 JSON 的裸 Si 参考仅提供波段平均值 ${(100 * bareAverage).toFixed(1)}%，不能把该点自动称为“减反”。`;
    }
    if (classificationId === "LOW_REFLECTION") {
      return "这是当前正式扫描内的最低反射点；反射示意波使用最小可见值放大并明确标记。";
    }
    return "“相对高反”只表示本案例扫描内 R 较高，不代表高反镜或相对裸 Si 的增反结论。";
  }

  updateLayerFocus(layer, state) {
    this.root.querySelectorAll("[data-layer-index]").forEach((row) => {
      const index = Number(row.dataset.layerIndex);
      row.classList.toggle("is-hovered", index === state.hoveredLayerIndex);
      row.classList.toggle("is-selected", index === state.selectedLayerIndex);
    });
    this.root.querySelector("#layer-detail").textContent = layer
      ? `第 ${layer.layerNumber} 层 · ${layer.materialName} · ${layer.thicknessNm.toFixed(4)} nm`
      : "悬停或点击膜层查看详情";
  }

  onResize() {
    this.cameraManager.onResize();
    this.rendererLifecycle.onResize();
  }

  exposeDebugApi() {
    const app = this;
    window.__SOLAR_AR_DEBUG__ = {
      app,
      get rendererInstanceCount() { return app.rendererLifecycle?.getRenderer() ? 1 : 0; },
      get currentCameraPreset() { return app.cameraManager?.currentPresetName || null; },
      get selectedLayerIndex() { return app.solarScene?.selectedLayerIndex ?? null; },
      get waveInfo() { return app.solarScene?.waveAmpInfo || null; },
      get animationState() { return { isPlaying: app.animationController.isPlaying, time: app.animationController.time }; },
      get activeWaveCount() { return app.solarScene?.waveRenderer.waveCount || 0; },
      getLayerScreenPositions: () => app.solarScene.getLayerScreenPositions(),
      setWavelength: (value) => app.setWavelength(value),
    };
  }

  dispose() {
    window.removeEventListener("resize", this.boundResize);
    this.solarScene?.dispose();
    this.cameraManager?.dispose();
    this.rendererLifecycle?.teardown();
  }
}
