import * as THREE from "three";

export const FP_STRUCTURE_REGIONS = Object.freeze([
  Object.freeze({ id: "incident_dbr", label: "入射侧 DBR", layerStart: 0, layerEnd: 5, focusLayer: 0 }),
  Object.freeze({ id: "defect_cavity", label: "中央缺陷腔", layerStart: 6, layerEnd: 6, focusLayer: 6 }),
  Object.freeze({ id: "substrate_dbr", label: "基底侧 DBR", layerStart: 7, layerEnd: 12, focusLayer: 7 }),
]);

const CAVITY_INDEX = 6;

export class FpVisualStory {
  constructor(root, app, teaching) {
    this.root = root;
    this.app = app;
    this.teaching = teaching;
    this.stage = root.querySelector(".solar-stage");
    this.drawer = document.querySelector("#guided-teaching-drawer");
    this.cleanup = [];
    this.frameId = null;
    this.stateObserver = null;
    this.modelFocus = false;
    this.cavityMarker = null;
  }

  init() {
    document.body.classList.add("fp-filter-visual-prototype");
    this.root.classList.add("fp-filter-visual-prototype__app");
    this.decorateCavityLayer();
    this.renderStructureGuide();
    this.installReadingToggle();
    this.observeFormalState();
    this.updateNarrativeState();
    this.updateCavityPin();
    this.exposeDebugApi();
  }

  decorateCavityLayer() {
    const mesh = this.app.caseScene?.layerMeshes?.[CAVITY_INDEX];
    if (!mesh) throw new Error("F-P 视觉原型无法定位第 7 层中央缺陷腔");
    const geometry = new THREE.EdgesGeometry(mesh.geometry, 12);
    const material = new THREE.LineBasicMaterial({
      color: 0x5f7f77,
      transparent: true,
      opacity: 0.96,
      linewidth: 1,
    });
    this.cavityMarker = new THREE.LineSegments(geometry, material);
    this.cavityMarker.name = "fp_defect_cavity_structure_marker";
    this.cavityMarker.scale.set(1.012, 1.04, 1.012);
    this.cavityMarker.renderOrder = 5;
    this.cavityMarker.userData.semantics = "STRUCTURE_MARKER_NOT_FIELD_STRENGTH";
    mesh.add(this.cavityMarker);
  }

  renderStructureGuide() {
    const guide = document.createElement("section");
    guide.className = "fp-structure-guide";
    guide.setAttribute("aria-label", "F-P 正式结构分组标注");
    guide.innerHTML = `
      <header><span>正式结构分组</span><small>结构标注，不代表场强</small></header>
      <div class="fp-structure-guide__regions">
        ${FP_STRUCTURE_REGIONS.map((region) => `
          <button data-fp-region="${region.id}" data-layer-start="${region.layerStart}" data-layer-end="${region.layerEnd}">
            <strong>${region.label}</strong>
            <span>${region.layerStart === region.layerEnd ? `第 ${region.layerStart + 1} 层` : `第 ${region.layerStart + 1}–${region.layerEnd + 1} 层`}</span>
          </button>`).join("")}
      </div>
      <div class="fp-formal-state" aria-live="polite"><span>正式光谱状态</span><strong id="fp-formal-state-value">—</strong></div>`;
    this.stage.append(guide);

    guide.querySelectorAll("[data-fp-region]").forEach((button) => {
      const region = FP_STRUCTURE_REGIONS.find((item) => item.id === button.dataset.fpRegion);
      const select = () => this.app.caseScene.setSelectedLayer(region.focusLayer);
      button.addEventListener("click", select);
      this.cleanup.push(() => button.removeEventListener("click", select));
    });

    const pin = document.createElement("button");
    pin.className = "fp-cavity-pin";
    pin.innerHTML = "<span>第 7 层</span><strong>中央缺陷腔</strong>";
    pin.setAttribute("aria-label", "选中第 7 层中央缺陷腔");
    const selectCavity = () => this.app.caseScene.setSelectedLayer(CAVITY_INDEX);
    pin.addEventListener("click", selectCavity);
    this.cleanup.push(() => pin.removeEventListener("click", selectCavity));
    this.stage.append(pin);
    this.cavityPin = pin;
  }

  installReadingToggle() {
    if (!this.drawer) throw new Error("F-P 教学抽屉未初始化");
    const header = this.drawer.querySelector(":scope > header");
    const closeButton = header.querySelector("[data-teaching-close]");
    const actions = document.createElement("div");
    actions.className = "fp-drawer-view-actions";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "fp-reading-toggle";
    toggle.textContent = "观察模型";
    toggle.setAttribute("aria-pressed", "false");
    actions.append(toggle, closeButton);
    header.append(actions);

    const toggleView = () => this.setModelFocus(!this.modelFocus);
    toggle.addEventListener("click", toggleView);
    this.cleanup.push(() => toggle.removeEventListener("click", toggleView));
    this.viewToggle = toggle;

    const originalOpen = this.teaching.open.bind(this.teaching);
    this.teaching.open = (tab) => {
      originalOpen(tab);
      this.syncFocusSummary();
    };
  }

  setModelFocus(enabled) {
    this.modelFocus = Boolean(enabled);
    this.drawer.classList.toggle("is-model-focus", this.modelFocus);
    this.viewToggle.textContent = this.modelFocus ? "阅读解释" : "观察模型";
    this.viewToggle.setAttribute("aria-pressed", String(this.modelFocus));
    this.syncFocusSummary();
  }

  syncFocusSummary() {
    let summary = this.drawer.querySelector(".fp-model-focus-summary");
    if (!summary) {
      summary = document.createElement("p");
      summary.className = "fp-model-focus-summary";
      this.drawer.querySelector(":scope > header > div:first-child").append(summary);
    }
    const debug = window.__GUIDED_TEACHING_DEBUG__;
    summary.textContent = debug?.mode === "GUIDED_LEARNING"
      ? `引导保持在步骤 ${Number(debug.stepIndex) + 1} / 5`
      : "自由探索状态保持不变";
  }

  observeFormalState() {
    this.stateObserver = new MutationObserver(() => this.updateNarrativeState());
    ["#spectral-verdict", "#wavelength-readout", "#layer-list"].forEach((selector) => {
      const node = this.root.querySelector(selector);
      if (node) this.stateObserver.observe(node, { childList: true, subtree: true, attributes: true });
    });
  }

  updateNarrativeState() {
    const verdict = this.root.querySelector("#spectral-verdict");
    const target = this.root.querySelector("#fp-formal-state-value");
    if (target && verdict) {
      target.textContent = verdict.textContent;
      target.dataset.classification = verdict.dataset.classification || "INTERMEDIATE";
    }
    const selected = this.app.caseScene?.selectedLayerIndex;
    this.root.querySelectorAll("[data-fp-region]").forEach((button) => {
      const start = Number(button.dataset.layerStart);
      const end = Number(button.dataset.layerEnd);
      button.classList.toggle("is-selected", Number.isInteger(selected) && selected >= start && selected <= end);
    });
  }

  updateCavityPin() {
    if (!this.cavityPin || !this.stage.isConnected) return;
    const position = this.app.caseScene?.getLayerScreenPositions?.()[CAVITY_INDEX];
    if (position) {
      const stageRect = this.stage.getBoundingClientRect();
      const x = Math.max(110, Math.min(stageRect.width - 110, position.x - stageRect.left));
      const y = Math.max(130, Math.min(stageRect.height - 120, position.y - stageRect.top));
      this.cavityPin.style.left = `${x}px`;
      this.cavityPin.style.top = `${y}px`;
    }
    this.frameId = requestAnimationFrame(() => this.updateCavityPin());
  }

  exposeDebugApi() {
    const story = this;
    window.__FP_VISUAL_STORY_DEBUG__ = {
      get viewMode() { return story.modelFocus ? "MODEL" : "READING"; },
      get cavityMarkerCount() { return story.app.caseScene?.group.getObjectByName("fp_defect_cavity_structure_marker") ? 1 : 0; },
      get selectedRegion() { return story.root.querySelector("[data-fp-region].is-selected")?.dataset.fpRegion || null; },
      regionIds: FP_STRUCTURE_REGIONS.map((region) => region.id),
    };
  }

  dispose() {
    if (this.frameId !== null) cancelAnimationFrame(this.frameId);
    this.stateObserver?.disconnect();
    this.cleanup.splice(0).forEach((cleanup) => cleanup());
    this.cavityPin?.remove();
    this.root.querySelector(".fp-structure-guide")?.remove();
    this.cavityMarker?.removeFromParent();
    this.cavityMarker?.geometry.dispose();
    this.cavityMarker?.material.dispose();
    this.drawer?.classList.remove("is-model-focus");
    document.body.classList.remove("fp-filter-visual-prototype");
    delete window.__FP_VISUAL_STORY_DEBUG__;
  }
}
