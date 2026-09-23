export class GuidedTeachingController {
  constructor(root, app, teaching) {
    this.root = root;
    this.app = app;
    this.teaching = teaching;
    this.mode = "FREE_EXPLORATION";
    this.stepIndex = 0;
    this.quizCorrect = false;
    this.observer = null;
  }

  static async create(root, app, caseId) {
    const url = new URL(`../../teaching/${caseId}.json`, window.location.href);
    const response = await fetch(url);
    if (!response.ok) throw new Error(`教学契约加载失败：HTTP ${response.status}`);
    const teaching = await response.json();
    if (teaching.case_id !== caseId) throw new Error("教学契约 case_id 不匹配");
    return new GuidedTeachingController(root, app, teaching);
  }

  init() {
    this.renderEntry();
    this.renderDrawer();
    this.renderBoundaryBadge();
    this.bind();
    this.observeState();
    this.updateSnapshot();
    this.exposeDebugApi();
  }

  renderEntry() {
    const card = document.createElement("section");
    card.className = "panel-section teaching-entry";
    card.innerHTML = `<div class="teaching-entry__head"><span>本科教学解释</span><em id="teaching-mode-label">自由探索</em></div><p>${this.teaching.problem_statement}</p><div class="teaching-entry__focus">${this.teaching.focus_labels.map((item) => `<span>${item}</span>`).join("")}</div><div class="teaching-entry__actions"><button data-teaching-open>打开原理讲解</button><button data-guide-start>进入引导学习</button></div>`;
    this.root.querySelector(".solar-panel").prepend(card);
  }

  renderDrawer() {
    const drawer = document.createElement("aside");
    drawer.id = "guided-teaching-drawer";
    drawer.className = "teaching-drawer is-hidden";
    drawer.setAttribute("aria-label", `${this.teaching.teaching_title}教学讲解`);
    drawer.innerHTML = `<header><div><span>本科教学案例</span><strong>${this.teaching.teaching_title}</strong></div><button data-teaching-close>关闭</button></header><nav><button data-tab="overview" class="is-active">自由探索说明</button><button data-tab="guide">引导学习</button><button data-tab="advanced">进阶内容</button></nav><div id="teaching-drawer-content" class="teaching-drawer__content"></div>`;
    document.body.append(drawer);
    this.renderOverview();
  }

  renderBoundaryBadge() {
    const badge = document.createElement("div");
    badge.className = "teaching-illustration-badge";
    badge.innerHTML = "<strong>教学示意</strong><span>正弦线与视觉厚度不代表定量空间电场</span>";
    this.root.querySelector(".solar-stage").append(badge);
  }

  bind() {
    document.querySelector("[data-guide-start]").addEventListener("click", () => this.startGuide());
    document.querySelector("[data-teaching-open]").addEventListener("click", () => this.open("overview"));
    document.querySelector("[data-teaching-close]").addEventListener("click", () => this.close());
    document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => this.open(button.dataset.tab)));
  }

  observeState() {
    this.observer = new MutationObserver(() => {
      this.updateSnapshot();
      if (this.mode === "GUIDED_LEARNING") this.refreshStep();
    });
    ["#wavelength-readout", "#value-r", "#value-t", "#value-a", "#layer-list"].forEach((selector) => {
      const node = this.root.querySelector(selector);
      if (node) this.observer.observe(node, { childList: true, subtree: true, attributes: true });
    });
  }

  updateSnapshot() {
    const target = document.querySelector("#teaching-formal-snapshot");
    if (!target) return;
    const value = (selector) => this.root.querySelector(selector)?.textContent || "—";
    target.innerHTML = [["当前波长", value("#wavelength-readout")], ["正式 R", value("#value-r")], ["正式 T", value("#value-t")], ["正式 A", value("#value-a")]].map(([label, current]) => `<span><small>${label}</small><strong>${current}</strong></span>`).join("");
  }

  open(tab) {
    document.querySelector("#guided-teaching-drawer").classList.remove("is-hidden");
    document.querySelectorAll("[data-tab]").forEach((button) => button.classList.toggle("is-active", button.dataset.tab === tab));
    if (tab === "guide") this.renderGuide();
    else if (tab === "advanced") this.renderAdvanced();
    else this.renderOverview();
  }

  close() { document.querySelector("#guided-teaching-drawer").classList.add("is-hidden"); }

  renderOverview() {
    const content = document.querySelector("#teaching-drawer-content");
    content.innerHTML = `<section class="teaching-block"><span class="teaching-eyebrow">解决什么问题</span><p class="teaching-lead">${this.teaching.problem_statement}</p></section><section class="teaching-block"><span class="teaching-eyebrow">正式计算结果</span><div id="teaching-formal-snapshot" class="formal-snapshot"></div><p class="teaching-caption">来自当前 Python 正式 JSON，随波长与偏振实时更新。</p></section><section class="teaching-block"><span class="teaching-eyebrow">学习目标</span><ul>${this.teaching.learning_objectives.map((item) => `<li>${item}</li>`).join("")}</ul></section><section class="teaching-block teaching-warning"><strong>${this.teaching.context_callout.title}</strong><p>${this.teaching.context_callout.text}</p></section><button class="teaching-primary" data-overview-guide>开始引导学习</button>`;
    content.querySelector("[data-overview-guide]").addEventListener("click", () => this.startGuide());
    this.updateSnapshot();
  }

  renderAdvanced() {
    document.querySelector("#teaching-drawer-content").innerHTML = `<section class="teaching-block"><span class="teaching-eyebrow">展开推导</span>${this.teaching.formula_sections.map((item) => `<details><summary>${item.title}</summary><code>${item.formula}</code><p>${item.explanation}</p></details>`).join("")}</section><section class="teaching-block"><span class="teaching-eyebrow">常见误区</span><ul>${this.teaching.common_misconceptions.map((item) => `<li>${item}</li>`).join("")}</ul></section><section class="teaching-block"><span class="teaching-eyebrow">模型边界</span><ul>${this.teaching.model_boundaries.map((item) => `<li>${item}</li>`).join("")}</ul></section>`;
  }

  startGuide() {
    this.mode = "GUIDED_LEARNING";
    this.stepIndex = 0;
    this.quizCorrect = false;
    document.querySelector("#teaching-mode-label").textContent = "引导学习";
    this.open("guide");
  }

  exitGuide() {
    this.mode = "FREE_EXPLORATION";
    document.querySelector("#teaching-mode-label").textContent = "自由探索";
    this.open("overview");
  }

  renderGuide() {
    const step = this.teaching.guided_steps[this.stepIndex];
    const total = this.teaching.guided_steps.length;
    const content = document.querySelector("#teaching-drawer-content");
    content.innerHTML = `<div class="guide-progress"><span>步骤 ${this.stepIndex + 1} / ${total}</span><i style="width:${((this.stepIndex + 1) / total) * 100}%"></i></div><section class="teaching-block guide-step"><span class="teaching-eyebrow">${step.title}</span><p class="teaching-lead">${step.instruction}</p>${this.renderAction(step)}<div id="guide-completion" class="guide-completion">等待完成操作</div></section><section class="teaching-block expected-observation"><span class="teaching-eyebrow">你应该看到什么</span><p>${step.expected_observation}</p><small>证据字段：${step.evidence_fields.join(" · ")}</small></section><div class="guide-navigation"><button data-guide-exit>退出引导</button><button data-guide-prev ${this.stepIndex === 0 ? "disabled" : ""}>上一步</button><button data-guide-next ${this.isComplete(step) ? "" : "disabled"}>${this.stepIndex === total - 1 ? "完成" : "下一步"}</button></div>`;
    content.querySelector("[data-guide-exit]").addEventListener("click", () => this.exitGuide());
    content.querySelector("[data-guide-prev]").addEventListener("click", () => { this.stepIndex -= 1; this.renderGuide(); });
    content.querySelector("[data-guide-next]").addEventListener("click", () => { if (this.stepIndex === total - 1) this.exitGuide(); else { this.stepIndex += 1; this.renderGuide(); } });
    content.querySelector("[data-step-action]")?.addEventListener("click", () => this.performAction(step));
    content.querySelectorAll("[data-quiz-option]").forEach((button) => button.addEventListener("click", () => this.answerQuiz(step, button.dataset.quizOption)));
    this.refreshStep();
  }

  renderAction(step) {
    if (step.action.type === "quiz") return `<div class="quiz-options">${step.action.options.map((item) => `<button data-quiz-option="${item.id}">${item.label}</button>`).join("")}</div><div id="quiz-feedback"></div>`;
    return `<button class="teaching-primary" data-step-action>${step.action.label}</button>`;
  }

  performAction(step) {
    const action = step.action;
    if (Number.isInteger(action.layer_index)) this.app.caseScene.setSelectedLayer(action.layer_index);
    if (action.polarization) this.app.setPolarization(action.polarization);
    if (Number.isFinite(action.wavelength_nm)) this.app.setWavelength(action.wavelength_nm);
    this.refreshStep();
  }

  answerQuiz(step, id) {
    const option = step.action.options.find((item) => item.id === id);
    this.quizCorrect = Boolean(option?.correct);
    const feedback = document.querySelector("#quiz-feedback");
    feedback.textContent = this.quizCorrect ? step.action.correct_feedback : step.action.incorrect_feedback;
    feedback.className = this.quizCorrect ? "quiz-feedback is-correct" : "quiz-feedback is-wrong";
    this.refreshStep();
  }

  isComplete(step) {
    const action = step.action;
    if (action.type === "quiz") return this.quizCorrect;
    if (Number.isInteger(action.layer_index) && this.app.caseScene?.selectedLayerIndex !== action.layer_index) return false;
    if (action.polarization && this.app.polarization !== action.polarization) return false;
    if (Number.isFinite(action.wavelength_nm) && Math.abs(this.app.selectedWavelengthNm - action.wavelength_nm) >= 0.01) return false;
    return true;
  }

  refreshStep() {
    const step = this.teaching.guided_steps[this.stepIndex];
    if (!step) return;
    const complete = this.isComplete(step);
    const status = document.querySelector("#guide-completion");
    const next = document.querySelector("[data-guide-next]");
    if (status) { status.textContent = complete ? "已完成 · 可继续" : "等待完成操作"; status.classList.toggle("is-complete", complete); }
    if (next) next.disabled = !complete;
  }

  exposeDebugApi() {
    const controller = this;
    window.__GUIDED_TEACHING_DEBUG__ = {
      get mode() { return controller.mode; },
      get stepIndex() { return controller.stepIndex; },
      get stepId() { return controller.teaching.guided_steps[controller.stepIndex]?.id || null; },
      get stepComplete() { return controller.isComplete(controller.teaching.guided_steps[controller.stepIndex]); },
      caseId: this.teaching.case_id,
    };
  }
}
