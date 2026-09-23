export class QuarterWaveTeachingController {
  constructor(root, app, teaching) {
    this.root = root;
    this.app = app;
    this.teaching = teaching;
    this.mode = "FREE_EXPLORATION";
    this.stepIndex = 0;
    this.quizCorrect = false;
    this.observer = null;
  }

  static async create(root, app) {
    const url = new URL("../../teaching/quarter_wave_single_layer.json", window.location.href);
    const response = await fetch(url);
    if (!response.ok) throw new Error(`教学契约加载失败：HTTP ${response.status}`);
    const teaching = await response.json();
    if (teaching.case_id !== "quarter_wave_single_layer") throw new Error("教学契约 case_id 不匹配");
    return new QuarterWaveTeachingController(root, app, teaching);
  }

  init() {
    this.renderEntryCard();
    this.renderDrawer();
    this.renderIllustrationBadge();
    this.bindEvents();
    this.observeFormalState();
    this.updateFormalSnapshot();
    this.exposeDebugApi();
  }

  renderEntryCard() {
    const card = document.createElement("section");
    card.className = "panel-section teaching-entry";
    card.innerHTML = `
      <div class="teaching-entry__head"><span>本科教学解释</span><em id="teaching-mode-label">自由探索</em></div>
      <p>${this.teaching.problem_statement}</p>
      <div class="teaching-entry__focus"><span>观察层：单层 QW</span><span>参考波长：550 nm</span><span>观察量：R</span></div>
      <div class="teaching-entry__actions"><button data-teaching-open="overview">打开原理讲解</button><button data-guide-start>进入引导学习</button></div>`;
    this.root.querySelector(".solar-panel").prepend(card);
  }

  renderDrawer() {
    const drawer = document.createElement("aside");
    drawer.id = "quarter-wave-teaching-drawer";
    drawer.className = "teaching-drawer is-hidden";
    drawer.setAttribute("aria-label", "单层减反膜教学讲解");
    drawer.innerHTML = `
      <header><div><span>本科教学原型</span><strong>单层四分之一波减反膜</strong></div><button data-teaching-close aria-label="关闭教学面板">关闭</button></header>
      <nav><button data-teaching-tab="overview" class="is-active">自由探索说明</button><button data-teaching-tab="guide">引导学习</button><button data-teaching-tab="advanced">进阶内容</button></nav>
      <div id="teaching-drawer-content" class="teaching-drawer__content"></div>`;
    document.body.append(drawer);
    this.renderOverview();
  }

  renderIllustrationBadge() {
    const badge = document.createElement("div");
    badge.className = "teaching-illustration-badge";
    badge.innerHTML = "<strong>教学示意</strong><span>动态正弦线与视觉厚度不代表定量空间电场</span>";
    this.root.querySelector(".solar-stage").append(badge);
  }

  bindEvents() {
    document.querySelector("[data-guide-start]").addEventListener("click", () => this.startGuide());
    document.querySelector("[data-teaching-open]").addEventListener("click", () => this.openDrawer("overview"));
    document.querySelector("[data-teaching-close]").addEventListener("click", () => this.closeDrawer());
    document.querySelectorAll("[data-teaching-tab]").forEach((button) => button.addEventListener("click", () => this.openDrawer(button.dataset.teachingTab)));
  }

  observeFormalState() {
    this.observer = new MutationObserver(() => {
      this.updateFormalSnapshot();
      if (this.mode === "GUIDED_LEARNING") this.refreshStepState();
    });
    ["#wavelength-readout", "#value-r", "#value-t", "#value-a", "#layer-list"].forEach((selector) => {
      const node = this.root.querySelector(selector);
      if (node) this.observer.observe(node, { childList: true, subtree: true, attributes: true });
    });
  }

  updateFormalSnapshot() {
    const target = document.querySelector("#teaching-formal-snapshot");
    if (!target) return;
    target.innerHTML = `<span><small>当前波长</small><strong>${this.root.querySelector("#wavelength-readout")?.textContent || "—"}</strong></span><span><small>正式 R</small><strong>${this.root.querySelector("#value-r")?.textContent || "—"}</strong></span><span><small>正式 T</small><strong>${this.root.querySelector("#value-t")?.textContent || "—"}</strong></span><span><small>正式 A</small><strong>${this.root.querySelector("#value-a")?.textContent || "—"}</strong></span>`;
  }

  openDrawer(tab = "overview") {
    document.querySelector("#quarter-wave-teaching-drawer").classList.remove("is-hidden");
    document.querySelectorAll("[data-teaching-tab]").forEach((button) => button.classList.toggle("is-active", button.dataset.teachingTab === tab));
    if (tab === "guide") this.renderGuide();
    else if (tab === "advanced") this.renderAdvanced();
    else this.renderOverview();
  }

  closeDrawer() {
    document.querySelector("#quarter-wave-teaching-drawer").classList.add("is-hidden");
  }

  renderOverview() {
    const content = document.querySelector("#teaching-drawer-content");
    content.innerHTML = `
      <section class="teaching-block"><span class="teaching-eyebrow">解决什么问题</span><p class="teaching-lead">${this.teaching.problem_statement}</p></section>
      <section class="teaching-block"><span class="teaching-eyebrow">正式计算结果</span><div id="teaching-formal-snapshot" class="formal-snapshot"></div><p class="teaching-caption">来自当前 Python TMM 正式 JSON；数值随波长和偏振实时更新。</p></section>
      <section class="teaching-block"><span class="teaching-eyebrow">学习目标</span><ul>${this.teaching.learning_objectives.map((item) => `<li>${item}</li>`).join("")}</ul></section>
      <section class="teaching-block teaching-warning"><strong>当前不是正入射</strong><p>正式入射角为 45°，因此 TE/TM 结果不同；550 nm 是名义设计参考点，TE 反射谷约在 ${this.teaching.formal_context.te_min_r_wavelength_nm} nm。</p></section>
      <button class="teaching-primary" data-overview-guide>开始引导学习</button>`;
    content.querySelector("[data-overview-guide]").addEventListener("click", () => this.startGuide());
    this.updateFormalSnapshot();
  }

  renderAdvanced() {
    const content = document.querySelector("#teaching-drawer-content");
    content.innerHTML = `
      <section class="teaching-block"><span class="teaching-eyebrow">展开推导</span>${this.teaching.formula_sections.map((item) => `<details><summary>${item.title}</summary><code>${item.formula}</code><p>${item.explanation}</p></details>`).join("")}</section>
      <section class="teaching-block"><span class="teaching-eyebrow">常见误区</span><ul>${this.teaching.common_misconceptions.map((item) => `<li>${item}</li>`).join("")}</ul></section>
      <section class="teaching-block"><span class="teaching-eyebrow">模型边界</span><ul>${this.teaching.model_boundaries.map((item) => `<li>${item}</li>`).join("")}</ul></section>`;
  }

  startGuide() {
    this.mode = "GUIDED_LEARNING";
    this.stepIndex = 0;
    this.quizCorrect = false;
    document.querySelector("#teaching-mode-label").textContent = "引导学习";
    this.openDrawer("guide");
  }

  exitGuide() {
    this.mode = "FREE_EXPLORATION";
    document.querySelector("#teaching-mode-label").textContent = "自由探索";
    this.renderOverview();
    this.openDrawer("overview");
  }

  renderGuide() {
    const step = this.teaching.guided_steps[this.stepIndex];
    const total = this.teaching.guided_steps.length;
    const content = document.querySelector("#teaching-drawer-content");
    content.innerHTML = `
      <div class="guide-progress"><span>步骤 ${this.stepIndex + 1} / ${total}</span><i style="width:${((this.stepIndex + 1) / total) * 100}%"></i></div>
      <section class="teaching-block guide-step"><span class="teaching-eyebrow">${step.title}</span><p class="teaching-lead">${step.instruction}</p>${this.renderStepAction(step)}<div id="guide-completion" class="guide-completion">等待完成操作</div></section>
      <section class="teaching-block expected-observation"><span class="teaching-eyebrow">你应该看到什么</span><p>${step.expected_observation}</p><small>证据字段：${step.evidence_fields.join(" · ")}</small></section>
      <div class="guide-navigation"><button data-guide-exit>退出引导</button><button data-guide-prev ${this.stepIndex === 0 ? "disabled" : ""}>上一步</button><button data-guide-next ${this.isStepComplete(step) ? "" : "disabled"}>${this.stepIndex === total - 1 ? "完成" : "下一步"}</button></div>`;
    content.querySelector("[data-guide-exit]").addEventListener("click", () => this.exitGuide());
    content.querySelector("[data-guide-prev]").addEventListener("click", () => { this.stepIndex -= 1; this.renderGuide(); });
    content.querySelector("[data-guide-next]").addEventListener("click", () => {
      if (this.stepIndex === total - 1) this.exitGuide();
      else { this.stepIndex += 1; this.renderGuide(); }
    });
    content.querySelector("[data-step-action]")?.addEventListener("click", () => this.performStepAction(step));
    content.querySelectorAll("[data-quiz-option]").forEach((button) => button.addEventListener("click", () => this.answerQuiz(step, button.dataset.quizOption)));
    this.refreshStepState();
  }

  renderStepAction(step) {
    if (step.action.type === "quiz") return `<div class="quiz-options">${step.action.options.map((option) => `<button data-quiz-option="${option.id}">${option.label}</button>`).join("")}</div><div id="quiz-feedback"></div>`;
    return `<button class="teaching-primary" data-step-action>${step.action.label}</button>`;
  }

  performStepAction(step) {
    const action = step.action;
    if (action.type === "select_layer") this.app.caseScene.setSelectedLayer(action.layer_index);
    if (action.type === "set_wavelength") this.app.setWavelength(action.wavelength_nm);
    if (action.type === "set_polarization") this.app.setPolarization(action.polarization);
    this.refreshStepState();
  }

  answerQuiz(step, optionId) {
    const option = step.action.options.find((item) => item.id === optionId);
    this.quizCorrect = Boolean(option?.correct);
    const feedback = document.querySelector("#quiz-feedback");
    feedback.textContent = this.quizCorrect ? "正确：当前 45° 条件使反射谷偏移，并产生 TE/TM 分裂。" : "再想一想：应以正式入射角和反射曲线为证据。";
    feedback.className = this.quizCorrect ? "quiz-feedback is-correct" : "quiz-feedback is-wrong";
    this.refreshStepState();
  }

  isStepComplete(step) {
    if (step.action.type === "select_layer") return this.app.caseScene?.selectedLayerIndex === step.action.layer_index;
    if (step.action.type === "set_wavelength") return Math.abs(this.app.selectedWavelengthNm - step.action.wavelength_nm) < 0.01;
    if (step.action.type === "set_polarization") return this.app.polarization === step.action.polarization;
    if (step.action.type === "quiz") return this.quizCorrect;
    return false;
  }

  refreshStepState() {
    const step = this.teaching.guided_steps[this.stepIndex];
    if (!step) return;
    const complete = this.isStepComplete(step);
    const status = document.querySelector("#guide-completion");
    const next = document.querySelector("[data-guide-next]");
    if (status) { status.textContent = complete ? "已完成 · 可继续" : "等待完成操作"; status.classList.toggle("is-complete", complete); }
    if (next) next.disabled = !complete;
  }

  exposeDebugApi() {
    const controller = this;
    window.__QUARTER_WAVE_TEACHING_DEBUG__ = {
      get mode() { return controller.mode; },
      get stepIndex() { return controller.stepIndex; },
      get stepId() { return controller.teaching.guided_steps[controller.stepIndex]?.id || null; },
      get stepComplete() { return controller.isStepComplete(controller.teaching.guided_steps[controller.stepIndex]); },
      get drawerOpen() { return !document.querySelector("#quarter-wave-teaching-drawer")?.classList.contains("is-hidden"); },
      contractCaseId: this.teaching.case_id,
    };
  }

  dispose() {
    this.observer?.disconnect();
    document.querySelector("#quarter-wave-teaching-drawer")?.remove();
  }
}
