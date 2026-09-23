import { SceneManager } from "./core/SceneManager.js";
import { CameraManager } from "./core/CameraManager.js";
import { RendererLifecycle } from "./core/RendererLifecycle.js";
import { ResourceDisposer } from "./core/ResourceDisposer.js";
import { AnimationController } from "./core/AnimationController.js";

import { SingleInterfaceTemplate } from "./templates/single-interface.js";
import { PeriodicStackTemplate } from "./templates/periodic-stack.js";
import { DefectCavityTemplate } from "./templates/defect-cavity.js";
import { MetalDbrInterfaceTemplate } from "./templates/metal-dbr-interface.js";

import { loadCaseRegistry } from "./data/registryLoader.js";
import { validateCaseConfig } from "./data/caseConfigValidator.js";
import { loadCaseResult } from "./data/caseResultLoader.js";

import { renderCaseSelector } from "./ui/caseSelector.js";
import { renderParameterPanel } from "./ui/parameterPanel.js";
import { renderEvidencePanel } from "./ui/evidencePanel.js";
import { renderStatusBadges } from "./ui/statusBadge.js";
import { setupErrorBoundary, showErrorModal } from "./ui/errorBoundary.js";

class App {
  constructor() {
    this.container = document.querySelector("#canvas-container");
    this.registry = null;
    this.currentCaseConfig = null;
    this.currentCaseResult = null;
    
    this.sceneManager = null;
    this.cameraManager = null;
    this.rendererLifecycle = null;

    this.currentTemplateInstance = null;
    this.currentTemplateGroup = null;

    this.isExploded = false;
    this.currentPolarization = "TE";
    this.currentWavelengthNm = null;

    this.templateMap = {
      "single-interface": SingleInterfaceTemplate,
      "periodic-stack": PeriodicStackTemplate,
      "defect-cavity": DefectCavityTemplate,
      "metal-dbr-interface": MetalDbrInterfaceTemplate,
    };
  }

  async init() {
    setupErrorBoundary();

    try {
      this.registry = await loadCaseRegistry();
      this.initEngine();
      this.initUI();
      
      const appSelf = this;
      // Expose debug interface for automated E2E & unit inspection
      window.__WEB3D_DEBUG__ = {
        app: appSelf,
        get rendererInstanceCount() { return appSelf.rendererLifecycle && appSelf.rendererLifecycle.renderer ? 1 : 0; },
        get rendererDisposeCount() { return appSelf.rendererLifecycle ? appSelf.rendererLifecycle.rendererDisposeCount : 0; },
        get forceContextLossCount() { return appSelf.rendererLifecycle ? appSelf.rendererLifecycle.contextLossCount : 0; },
        get animationCancelCount() { return appSelf.rendererLifecycle ? appSelf.rendererLifecycle.animationCancelCount : 0; },
        get caseUpdateSubscriptionRemovalCount() { return appSelf.animationController ? appSelf.animationController.caseUpdateSubscriptionRemovalCount : 0; },
        get geometryDisposeCount() { return ResourceDisposer.geometryDisposeCount; },
        get materialDisposeCount() { return ResourceDisposer.materialDisposeCount; },
        get eventListenerRemovalCount() { return ResourceDisposer.eventListenerRemovalCount; },
        get activeWaveCount() {
          return (appSelf.currentTemplateInstance && appSelf.currentTemplateInstance.waveRenderer)
            ? appSelf.currentTemplateInstance.waveRenderer.waveCount : 0;
        },
        getWavePositions: () => {
          return (appSelf.currentTemplateInstance && appSelf.currentTemplateInstance.waveRenderer)
            ? appSelf.currentTemplateInstance.waveRenderer.getWavePositions() : [];
        },
        setWavelength: (wl) => appSelf.setWavelength(wl),
        setPolarization: (pol) => {
          appSelf.currentPolarization = pol;
          appSelf.setWavelength(appSelf.currentWavelengthNm);
        },
        get currentCaseConfig() { return appSelf.currentCaseConfig; },
        get currentCaseResult() { return appSelf.currentCaseResult; },
        get animationState() {
          return appSelf.animationController ? { isPlaying: appSelf.animationController.isPlaying, time: appSelf.animationController.time } : null;
        },
      };

      // Check URL query parameters for initial case (e.g. ?case=app_solar_cell_ar)
      const urlParams = new URLSearchParams(window.location.search);
      const urlCaseId = urlParams.get("case");
      const targetCaseId = (urlCaseId && this.registry.cases.some((c) => c.id === urlCaseId))
        ? urlCaseId
        : (this.registry.cases && this.registry.cases.length > 0 ? this.registry.cases[0].id : null);

      if (targetCaseId) {
        await this.loadCase(targetCaseId);
      }
    } catch (err) {
      showErrorModal("引擎初始化失败", err.message);
    }
  }

  initEngine() {
    this.sceneManager = new SceneManager();
    this.cameraManager = new CameraManager(this.container);
    this.rendererLifecycle = new RendererLifecycle(this.container);

    this.cameraManager.initControls(this.rendererLifecycle.getDomElement());

    this.animationController = new AnimationController();
    this.lastTimestamp = 0;

    window.addEventListener("resize", () => {
      this.cameraManager.onResize();
      this.rendererLifecycle.onResize();
    });

    // Start Animation Render Loop using deltaTime
    this.rendererLifecycle.startLoop((timestamp) => {
      const controls = this.cameraManager.getControls();
      if (controls) controls.update();

      if (!this.lastTimestamp) this.lastTimestamp = timestamp;
      const deltaSeconds = Math.min((timestamp - this.lastTimestamp) / 1000, 0.1);
      this.lastTimestamp = timestamp;

      const animTime = this.animationController.update(deltaSeconds);

      if (this.currentTemplateInstance && typeof this.currentTemplateInstance.updateAnimation === "function") {
        this.currentTemplateInstance.updateAnimation(animTime);
      }

      this.rendererLifecycle.getRenderer().render(
        this.sceneManager.getScene(),
        this.cameraManager.getCamera()
      );
    });
  }

  initUI() {
    const listContainer = document.querySelector("#case-list-container");
    if (listContainer && this.registry) {
      renderCaseSelector(listContainer, this.registry.cases, "", (selectedId) => {
        this.loadCase(selectedId);
      });
    }

    // Button Events
    document.querySelector("#btn-play-pause")?.addEventListener("click", () => {
      if (this.animationController) {
        const isPlaying = this.animationController.togglePlayPause();
        const btn = document.querySelector("#btn-play-pause");
        if (btn) btn.textContent = isPlaying ? "暂停" : "播放";
      }
    });

    document.querySelector("#btn-reset-view")?.addEventListener("click", () => {
      this.cameraManager.resetView();
    });

    document.querySelector("#btn-toggle-pol")?.addEventListener("click", () => {
      this.currentPolarization = this.currentPolarization === "TE" ? "TM" : "TE";
      if (this.currentTemplateInstance && typeof this.currentTemplateInstance.setWavelengthAndPolarization === "function") {
        this.currentTemplateInstance.setWavelengthAndPolarization(this.currentWavelengthNm, this.currentPolarization);
      } else {
        this.rebuildSceneObjects();
      }
    });

    document.querySelector("#btn-explode-layers")?.addEventListener("click", () => {
      this.isExploded = !this.isExploded;
      this.rebuildSceneObjects();
    });
  }

  setWavelength(wl) {
    this.currentWavelengthNm = wl;
    if (this.currentTemplateInstance && typeof this.currentTemplateInstance.setWavelengthAndPolarization === "function") {
      this.currentTemplateInstance.setWavelengthAndPolarization(wl, this.currentPolarization);
    } else {
      this.rebuildSceneObjects();
    }
  }

  async loadCase(caseId) {
    const caseConfig = this.registry.cases.find((c) => c.id === caseId);
    if (!caseConfig) {
      showErrorModal("无效案例", `找不到 ID 为 ${caseId} 的案例配置。`);
      return;
    }

    const validation = validateCaseConfig(caseConfig);
    if (!validation.valid) {
      showErrorModal("案例配置校验失败", validation.reason);
      return;
    }

    // Check template mapping existence
    const TemplateClass = this.templateMap[caseConfig.visualization_template];
    if (!TemplateClass) {
      showErrorModal("未接入 3D 模板", `模板 '${caseConfig.visualization_template}' 尚未接入统一 Web3D 引擎。`);
      return;
    }

    // Load case result JSON
    const resultRes = await loadCaseResult(caseId);
    if (!resultRes.available && (caseConfig.migration_status === "MIGRATION_VERIFIED" || caseConfig.migration_status === "MIGRATED")) {
      showErrorModal("数据缺失", `案例 '${caseId}' 缺失 Python 计算导出 JSON 文件 (${resultRes.reason})。`);
      return;
    }

    this.disposeCurrentObjects();

    this.currentCaseConfig = caseConfig;
    this.currentCaseResult = resultRes.data;
    this.currentWavelengthNm = null; // reset to default for newly loaded case

    // Update UI Panels
    renderParameterPanel(document.querySelector("#parameter-panel"), caseConfig);
    renderEvidencePanel(document.querySelector("#evidence-panel"), caseConfig);
    renderStatusBadges(document.querySelector("#status-badge-container"), caseConfig);

    const listContainer = document.querySelector("#case-list-container");
    if (listContainer) {
      renderCaseSelector(listContainer, this.registry.cases, caseId, (id) => this.loadCase(id));
    }

    // Build 3D Scene Objects
    this.rebuildSceneObjects();
  }

  disposeCurrentObjects() {
    const scene = this.sceneManager.getScene();
    if (this.currentTemplateInstance) {
      this.currentTemplateInstance.dispose();
      this.currentTemplateInstance = null;
      if (this.animationController) {
        this.animationController.notifyCaseUnsubscribed();
      }
    }
    if (this.currentTemplateGroup) {
      ResourceDisposer.disposeObject(this.currentTemplateGroup);
      scene.remove(this.currentTemplateGroup);
      this.currentTemplateGroup = null;
    }
  }

  rebuildSceneObjects() {
    this.disposeCurrentObjects();

    if (!this.currentCaseConfig) return;

    const TemplateClass = this.templateMap[this.currentCaseConfig.visualization_template];
    if (!TemplateClass) return;

    const scene = this.sceneManager.getScene();

    this.currentTemplateInstance = new TemplateClass(this.container);
    this.currentTemplateGroup = this.currentTemplateInstance.build(this.currentCaseResult, {
      isExploded: this.isExploded,
      polarization: this.currentPolarization,
      selectedWavelengthNm: this.currentWavelengthNm,
    });

    scene.add(this.currentTemplateGroup);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const app = new App();
  app.init();
});
