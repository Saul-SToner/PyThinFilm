import * as THREE from "three";
import { sampleEngineeringSpectrum } from "../../src/apps/shared/engineeringSpectrum.js";

export const BRAGG_STRUCTURE_REGIONS = Object.freeze([
  Object.freeze({ id: "period_1", label: "周期 1", layerStart: 0, layerEnd: 1, focusLayer: 0, sequence: "H/L" }),
  Object.freeze({ id: "period_2", label: "周期 2", layerStart: 2, layerEnd: 3, focusLayer: 2, sequence: "H/L" }),
  Object.freeze({ id: "period_3", label: "周期 3", layerStart: 4, layerEnd: 5, focusLayer: 4, sequence: "H/L" }),
  Object.freeze({ id: "terminal_h", label: "终止层", layerStart: 6, layerEnd: 6, focusLayer: 6, sequence: "H" }),
]);

export function getBraggPolarizationComparison(caseResult, wavelengthNm) {
  const te = sampleEngineeringSpectrum(caseResult, "TE", wavelengthNm);
  const tm = sampleEngineeringSpectrum(caseResult, "TM", wavelengthNm);
  return Object.freeze({
    wavelengthNm: te.selectedWavelengthNm,
    teR: te.rSelected,
    tmR: tm.rSelected,
    deltaR: te.rSelected - tm.rSelected,
  });
}

export class BraggVisualStory {
  constructor(root, app, teaching) {
    this.root = root;
    this.app = app;
    this.teaching = teaching;
    this.stage = root.querySelector(".solar-stage");
    this.drawer = document.querySelector("#guided-teaching-drawer");
    this.cleanup = [];
    this.stateObserver = null;
    this.modelFocus = false;
    this.structureMarkers = null;
  }

  init() {
    document.body.classList.add("bragg-visual-prototype");
    this.root.classList.add("bragg-visual-prototype__app");
    this.buildStructureMarkers();
    this.renderStructureGuide();
    this.installReadingToggle();
    this.observeFormalState();
    this.updateNarrativeState();
    this.exposeDebugApi();
  }

  buildStructureMarkers() {
    const meshes = this.app.caseScene?.layerMeshes || [];
    if (meshes.length !== 7) throw new Error("Bragg 视觉原型需要正式七层 H/L/H/L/H/L/H 结构");
    this.structureMarkers = new THREE.Group();
    this.structureMarkers.name = "bragg_period_structure_markers";
    this.structureMarkers.userData.semantics = "STRUCTURE_GROUPING_NOT_FIELD_STRENGTH";

    BRAGG_STRUCTURE_REGIONS.forEach((region) => {
      const regionMeshes = meshes.slice(region.layerStart, region.layerEnd + 1);
      const top = Math.max(...regionMeshes.map((mesh) => mesh.position.y + mesh.geometry.parameters.height / 2));
      const bottom = Math.min(...regionMeshes.map((mesh) => mesh.position.y - mesh.geometry.parameters.height / 2));
      const x = -3.18;
      const z = 2.04;
      const tick = region.id === "terminal_h" ? 0.22 : 0.14;
      const points = [
        new THREE.Vector3(x, top, z), new THREE.Vector3(x - tick, top, z),
        new THREE.Vector3(x - tick, top, z), new THREE.Vector3(x - tick, bottom, z),
        new THREE.Vector3(x - tick, bottom, z), new THREE.Vector3(x, bottom, z),
      ];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const material = new THREE.LineBasicMaterial({
        color: region.id === "terminal_h" ? 0x6d817d : 0x879b9e,
        transparent: true,
        opacity: region.id === "terminal_h" ? 0.98 : 0.82,
      });
      const marker = new THREE.LineSegments(geometry, material);
      marker.name = `bragg_${region.id}_structure_marker`;
      marker.userData.regionId = region.id;
      this.structureMarkers.add(marker);
    });

    this.app.caseScene.group.add(this.structureMarkers);
  }

  renderStructureGuide() {
    const guide = document.createElement("section");
    guide.className = "bragg-structure-guide";
    guide.setAttribute("aria-label", "Bragg 正式周期结构与偏振对照");
    guide.innerHTML = `
      <header>
        <span>正式七层结构</span>
        <div class="bragg-material-legend" aria-label="H 与 L 材料角色图例">
          <span><i class="is-h"></i>H 高折射率</span><span><i class="is-l"></i>L 低折射率</span>
        </div>
      </header>
      <div class="bragg-structure-guide__regions">
        ${BRAGG_STRUCTURE_REGIONS.map((region) => `
          <button data-bragg-region="${region.id}" data-layer-start="${region.layerStart}" data-layer-end="${region.layerEnd}">
            <strong>${region.label}</strong><span>${region.sequence} · 第 ${region.layerStart + 1}${region.layerEnd === region.layerStart ? "" : `–${region.layerEnd + 1}`} 层</span>
          </button>`).join("")}
      </div>
      <div class="bragg-polarization-comparison" aria-label="同一波长正式 TE TM 反射率对照">
        <div class="bragg-polarization-comparison__head"><span>正式 JSON 插值 · 同一波长</span><strong id="bragg-compare-wavelength">—</strong></div>
        <div class="bragg-compare-row" data-compare-pol="TE"><b>TE</b><div><i id="bragg-bar-te"></i></div><strong id="bragg-value-te">—</strong></div>
        <div class="bragg-compare-row" data-compare-pol="TM"><b>TM</b><div><i id="bragg-bar-tm"></i></div><strong id="bragg-value-tm">—</strong></div>
        <small id="bragg-delta-r">—</small>
      </div>`;
    this.stage.append(guide);

    guide.querySelectorAll("[data-bragg-region]").forEach((button) => {
      const region = BRAGG_STRUCTURE_REGIONS.find((item) => item.id === button.dataset.braggRegion);
      const select = () => this.app.caseScene.setSelectedLayer(region.focusLayer);
      button.addEventListener("click", select);
      this.cleanup.push(() => button.removeEventListener("click", select));
    });
  }

  installReadingToggle() {
    if (!this.drawer) throw new Error("Bragg 教学抽屉未初始化");
    const header = this.drawer.querySelector(":scope > header");
    const closeButton = header.querySelector("[data-teaching-close]");
    const actions = document.createElement("div");
    actions.className = "bragg-drawer-view-actions";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "bragg-reading-toggle";
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
    let summary = this.drawer.querySelector(".bragg-model-focus-summary");
    if (!summary) {
      summary = document.createElement("p");
      summary.className = "bragg-model-focus-summary";
      this.drawer.querySelector(":scope > header > div:first-child").append(summary);
    }
    const debug = window.__GUIDED_TEACHING_DEBUG__;
    summary.textContent = debug?.mode === "GUIDED_LEARNING"
      ? `引导保持在步骤 ${Number(debug.stepIndex) + 1} / 5`
      : "自由探索状态保持不变";
  }

  observeFormalState() {
    this.stateObserver = new MutationObserver(() => this.updateNarrativeState());
    ["#wavelength-readout", "#value-r", "#layer-list"].forEach((selector) => {
      const node = this.root.querySelector(selector);
      if (node) this.stateObserver.observe(node, { childList: true, subtree: true, attributes: true });
    });
  }

  updateNarrativeState() {
    const comparison = getBraggPolarizationComparison(this.app.caseResult, this.app.selectedWavelengthNm);
    const percent = (value) => `${(100 * value).toFixed(2)}%`;
    this.root.querySelector("#bragg-compare-wavelength").textContent = `${comparison.wavelengthNm.toFixed(2)} nm`;
    this.root.querySelector("#bragg-value-te").textContent = percent(comparison.teR);
    this.root.querySelector("#bragg-value-tm").textContent = percent(comparison.tmR);
    this.root.querySelector("#bragg-bar-te").style.width = percent(comparison.teR);
    this.root.querySelector("#bragg-bar-tm").style.width = percent(comparison.tmR);
    this.root.querySelector("#bragg-delta-r").textContent = `TE − TM = ${(100 * comparison.deltaR).toFixed(2)} 个百分点`;
    this.root.querySelectorAll("[data-compare-pol]").forEach((row) => row.classList.toggle("is-active", row.dataset.comparePol === this.app.polarization));

    const selected = this.app.caseScene?.selectedLayerIndex;
    this.root.querySelectorAll("[data-bragg-region]").forEach((button) => {
      const start = Number(button.dataset.layerStart);
      const end = Number(button.dataset.layerEnd);
      button.classList.toggle("is-selected", Number.isInteger(selected) && selected >= start && selected <= end);
    });
  }

  exposeDebugApi() {
    const story = this;
    window.__BRAGG_VISUAL_STORY_DEBUG__ = {
      get viewMode() { return story.modelFocus ? "MODEL" : "READING"; },
      get markerCount() { return story.structureMarkers?.children.length || 0; },
      get selectedRegion() { return story.root.querySelector("[data-bragg-region].is-selected")?.dataset.braggRegion || null; },
      get comparison() { return getBraggPolarizationComparison(story.app.caseResult, story.app.selectedWavelengthNm); },
      regionIds: BRAGG_STRUCTURE_REGIONS.map((region) => region.id),
    };
  }

  dispose() {
    this.stateObserver?.disconnect();
    this.cleanup.splice(0).forEach((cleanup) => cleanup());
    if (this.structureMarkers) {
      this.structureMarkers.removeFromParent();
      this.structureMarkers.traverse((object) => {
        object.geometry?.dispose?.();
        object.material?.dispose?.();
      });
    }
    this.root.querySelector(".bragg-structure-guide")?.remove();
    this.drawer?.classList.remove("is-model-focus");
    document.body.classList.remove("bragg-visual-prototype");
    delete window.__BRAGG_VISUAL_STORY_DEBUG__;
  }
}
