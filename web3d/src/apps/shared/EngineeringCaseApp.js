import { SceneManager } from "../../core/SceneManager.js";
import { CameraManager } from "../../core/CameraManager.js";
import { RendererLifecycle } from "../../core/RendererLifecycle.js";
import { AnimationController } from "../../core/AnimationController.js";
import { EngineeringCaseScene, ENGINEERING_WAVE_DISPLAY_SCALE } from "./EngineeringCaseScene.js";
import { resolvePresetWavelength } from "./engineeringSpectrum.js";

export class EngineeringCaseApp {
  constructor(root, config) {
    this.root = root;
    this.config = config;
    this.canvasContainer = root.querySelector("#engineering-canvas");
    this.caseResult = null;
    this.polarization = "TE";
    this.selectedWavelengthNm = null;
    this.sceneManager = null;
    this.cameraManager = null;
    this.rendererLifecycle = null;
    this.animationController = null;
    this.caseScene = null;
    this.lastTimestamp = 0;
    this.boundResize = () => this.onResize();
  }

  async init() {
    try {
      this.caseResult = await this.loadFormalResult();
      this.selectedWavelengthNm = this.resolvePreset(this.config.presets[0]);
      this.renderStaticContent();
      this.configureWavelengthControls();
      this.initEngine();
      this.bindControls();
      this.exposeDebugApi();
    } catch (error) {
      const boundary = this.root.querySelector("#engineering-error");
      boundary.textContent = `${this.config.caseId} 独立 App 初始化失败：${error.message}`;
      boundary.classList.remove("hidden");
      throw error;
    }
  }

  async loadFormalResult() {
    const resultUrl = new URL(`../../results/${this.config.caseId}.json`, window.location.href);
    const response = await fetch(resultUrl);
    if (!response.ok) throw new Error(`正式 JSON 加载失败：HTTP ${response.status}`);
    const result = await response.json();
    if (result.case_id !== this.config.caseId) throw new Error("正式 JSON case_id 不匹配");
    if (!Array.isArray(result.layers) || result.layers.length !== this.config.expectedLayerCount) {
      throw new Error(`正式膜层数量不是 ${this.config.expectedLayerCount}`);
    }
    return result;
  }

  resolvePreset(preset) {
    return resolvePresetWavelength(this.caseResult, this.polarization, preset);
  }

  renderStaticContent() {
    this.root.querySelector("#case-title").textContent = this.config.title;
    this.root.querySelector("#case-kicker").textContent = this.config.kicker;
    this.root.querySelector("#case-id").textContent = this.config.caseId;
    this.root.querySelector("#display-scale-note").textContent = `${ENGINEERING_WAVE_DISPLAY_SCALE.toFixed(1)}×`;
    this.root.querySelector("#layer-list").innerHTML = this.caseResult.layers.map((layer, index) => `
      <div class="layer-row" data-layer-index="${index}">
        <span class="layer-number">${index + 1}</span>
        <strong>${layer.name || layer.type || `Layer-${index + 1}`}</strong>
        <span>${Number(layer.thickness_nm).toFixed(4)} nm</span>
      </div>
    `).join("");
    this.config.presets.forEach((preset, index) => {
      const button = this.root.querySelector(`[data-preset-index="${index}"]`);
      button.textContent = preset.label;
      button.dataset.testid = `preset-${preset.id}`;
    });
    this.root.querySelector("#semantic-caveat").textContent = this.config.caveat;
  }

  configureWavelengthControls() {
    const wavelengths = this.caseResult.wavelength_nm;
    const slider = this.root.querySelector("#wavelength-slider");
    slider.min = String(wavelengths[0]);
    slider.max = String(wavelengths[wavelengths.length - 1]);
    slider.step = String(wavelengths.length > 1 ? wavelengths[1] - wavelengths[0] : 1);
    slider.value = String(this.selectedWavelengthNm);
  }

  initEngine() {
    this.sceneManager = new SceneManager();
    this.sceneManager.applyVisualTheme("ACADEMIC_LIGHT");
    this.cameraManager = new CameraManager(this.canvasContainer);
    this.rendererLifecycle = new RendererLifecycle(this.canvasContainer);
    this.cameraManager.initControls(this.rendererLifecycle.getDomElement());
    this.animationController = new AnimationController();
    this.caseScene = new EngineeringCaseScene({
      config: this.config,
      container: this.canvasContainer,
      camera: this.cameraManager.getCamera(),
      domElement: this.rendererLifecycle.getDomElement(),
      onLayerFocus: (layer, state) => this.updateLayerFocus(layer, state),
      onWaveInfo: (waveInfo) => this.updateWaveReadout(waveInfo),
    });
    this.sceneManager.getScene().add(this.caseScene.build(this.caseResult, {
      polarization: this.polarization,
      selectedWavelengthNm: this.selectedWavelengthNm,
    }));
    this.cameraManager.setDefaultPreset("ISOMETRIC_SECTION", this.caseScene.getStructureBounds());
    this.fitFogToCamera();
    window.addEventListener("resize", this.boundResize);
    this.rendererLifecycle.startLoop((timestamp) => {
      this.cameraManager.getControls()?.update();
      if (!this.lastTimestamp) this.lastTimestamp = timestamp;
      const deltaSeconds = Math.min((timestamp - this.lastTimestamp) / 1000, 0.1);
      this.lastTimestamp = timestamp;
      const time = this.animationController.update(deltaSeconds);
      this.caseScene.updateAnimation(time);
      this.rendererLifecycle.getRenderer().render(this.sceneManager.getScene(), this.cameraManager.getCamera());
    });
  }

  bindControls() {
    const bind = (selector, handler) => this.root.querySelector(selector)?.addEventListener("click", handler);
    bind("#btn-isometric", () => this.setCameraPreset("ISOMETRIC_SECTION"));
    bind("#btn-side", () => this.setCameraPreset("SIDE_SECTION"));
    bind("#btn-optical", () => this.setCameraPreset("OPTICAL_PATH"));
    bind("#btn-reset", () => {
      this.setWavelength(this.resolvePreset(this.config.presets[0]));
      if (this.polarization !== "TE") this.setPolarization("TE");
      this.cameraManager.resetView();
      this.fitFogToCamera();
      this.caseScene.clearSelection();
    });
    bind("#btn-play-pause", () => {
      const playing = this.animationController.togglePlayPause();
      this.root.querySelector("#btn-play-pause").textContent = playing ? "暂停" : "播放";
    });
    bind("#btn-polarization", () => this.setPolarization(this.polarization === "TE" ? "TM" : "TE"));
    this.config.presets.forEach((preset, index) => {
      bind(`[data-preset-index="${index}"]`, () => this.setWavelength(this.resolvePreset(preset)));
    });
    this.root.querySelector("#wavelength-slider")?.addEventListener("input", (event) => this.setWavelength(Number(event.target.value)));
  }

  setCameraPreset(presetName) {
    const applied = this.cameraManager.applyPreset(presetName, this.caseScene.getStructureBounds());
    if (applied) this.fitFogToCamera();
    return applied;
  }

  fitFogToCamera() {
    return this.sceneManager.fitFogToCamera(
      this.cameraManager.getCamera(),
      this.cameraManager.getControls()?.target
    );
  }

  setWavelength(wavelengthNm) {
    this.selectedWavelengthNm = Number(wavelengthNm);
    this.root.querySelector("#wavelength-slider").value = String(this.selectedWavelengthNm);
    this.caseScene.setWavelength(this.selectedWavelengthNm);
  }

  setPolarization(polarization) {
    this.polarization = polarization === "TM" ? "TM" : "TE";
    this.caseScene.setPolarization(this.polarization);
    this.root.querySelector("#btn-polarization").textContent = this.polarization === "TE" ? "切换为 TM" : "切换为 TE";
  }

  updateWaveReadout(waveInfo) {
    this.selectedWavelengthNm = waveInfo.selectedWavelengthNm;
    const r = waveInfo.rSelected;
    const t = waveInfo.tSelected;
    const a = waveInfo.absorptance;
    const classification = this.config.classify({ r, t, a, wavelengthNm: waveInfo.selectedWavelengthNm });
    const percent = (value) => `${(100 * value).toFixed(2)}%`;
    const amplitudeRatio = (amplitude) => (amplitude / 0.25).toFixed(3);
    this.root.querySelector("#wavelength-readout").textContent = `${waveInfo.selectedWavelengthNm.toFixed(2)} nm · ${this.polarization}`;
    const verdict = this.root.querySelector("#spectral-verdict");
    verdict.textContent = classification.label;
    verdict.dataset.classification = classification.id;
    this.root.querySelector("#value-r").textContent = percent(r);
    this.root.querySelector("#value-t").textContent = percent(t);
    this.root.querySelector("#value-a").textContent = percent(a);
    this.root.querySelector("#bar-r").style.width = percent(r);
    this.root.querySelector("#bar-t").style.width = percent(t);
    this.root.querySelector("#bar-a").style.width = percent(a);
    const note = waveInfo.isExaggerated ? " · 含最小可见值放大" : "";
    this.root.querySelector("#amplitude-readout").textContent = `示意振幅比：Ar/Ai = ${amplitudeRatio(waveInfo.rAmp)} · At/Ai = ${amplitudeRatio(waveInfo.tAmp)}${note}`;
    this.root.querySelector('[data-wave-callout="reflected"]').textContent = `反射 R ${percent(r)} · Ar/Ai ${amplitudeRatio(waveInfo.rAmp)}`;
    this.root.querySelector('[data-wave-callout="transmitted"]').textContent = `透射 T ${percent(t)} · At/Ai ${amplitudeRatio(waveInfo.tAmp)}`;
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

  onResize() { this.cameraManager.onResize(); this.rendererLifecycle.onResize(); }

  exposeDebugApi() {
    const app = this;
    window.__ENGINEERING_APP_DEBUG__ = {
      app,
      caseId: this.config.caseId,
      get rendererInstanceCount() { return app.rendererLifecycle?.getRenderer() ? 1 : 0; },
      get currentCameraPreset() { return app.cameraManager?.currentPresetName || null; },
      get selectedLayerIndex() { return app.caseScene?.selectedLayerIndex ?? null; },
      get waveInfo() { return app.caseScene?.waveAmpInfo || null; },
      get animationState() { return { isPlaying: app.animationController.isPlaying, time: app.animationController.time }; },
      get activeWaveCount() { return app.caseScene?.waveRenderer.waveCount || 0; },
      getLayerScreenPositions: () => app.caseScene.getLayerScreenPositions(),
      setWavelength: (value) => app.setWavelength(value),
    };
  }

  dispose() {
    window.removeEventListener("resize", this.boundResize);
    this.caseScene?.dispose();
    this.cameraManager?.dispose();
    this.rendererLifecycle?.teardown();
  }
}
