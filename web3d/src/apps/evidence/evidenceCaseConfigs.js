const SCENE_NOTES = Object.freeze({
  phase: "相位与筛选指标的三维数据轨迹，不是界面本征场复原。",
  interface: "局域统计结果的三维样本柱，不是二维场热力图。",
  template: "输入模板的三维参考平面，不代表一次已完成的仿真。",
  spectrum: "正式光谱的三维数据轨迹，不复原未提供的表面几何。",
  trend: "参数扫描趋势的三维数据轨迹。",
  validation: "Python—COMSOL 误差指标的三维验证场景，不拼接不同结构。",
});

export const EVIDENCE_CASE_CONFIGS = Object.freeze({
  tamm_interface_priority: { slug: "tamm-interface-priority", title: "Tamm 界面态优先极化筛选", kicker: "外部数据证据 · Tamm", sceneType: "phase", sceneNote: SCENE_NOTES.phase },
  tamm_phase_candidates: { slug: "tamm-phase-candidates", title: "Tamm 相位匹配候选点搜寻", kicker: "外部数据证据 · Tamm", sceneType: "phase", sceneNote: SCENE_NOTES.phase },
  tamm_phase_focus: { slug: "tamm-phase-focus", title: "Tamm 相位聚焦与吸收增强", kicker: "外部数据证据 · Tamm", sceneType: "phase", sceneNote: SCENE_NOTES.phase },
  tamm_reflection_phase_screen: { slug: "tamm-reflection-phase-screen", title: "Tamm 界面反射相位多波长筛选", kicker: "外部数据证据 · Tamm", sceneType: "phase", sceneNote: SCENE_NOTES.phase },
  tamm_interface_window_bundle: { slug: "tamm-interface-window-bundle", title: "Tamm 界面窗口束", kicker: "外部数据证据 · 局域统计", sceneType: "interface", sceneNote: SCENE_NOTES.interface },
  tamm_interface_window_scan: { slug: "tamm-interface-window-scan", title: "Tamm 界面窗口扫描", kicker: "外部数据证据 · 稳健性扫描", sceneType: "interface", sceneNote: SCENE_NOTES.interface },
  absorbing_baseline_template: { slug: "absorbing-baseline-template", title: "吸收表面基线模板", kicker: "输入契约 · 模板", sceneType: "template", sceneNote: SCENE_NOTES.template },
  absorbing_surface_bundle: { slug: "absorbing-surface-bundle", title: "吸收表面综合计算束", kicker: "外部数据证据 · 吸收表面", sceneType: "spectrum", sceneNote: SCENE_NOTES.spectrum },
  absorbing_surface_gain: { slug: "absorbing-surface-gain", title: "吸收表面增益模型", kicker: "外部数据证据 · 基准对比", sceneType: "spectrum", sceneNote: SCENE_NOTES.spectrum },
  absorbing_surface_gain_trend: { slug: "absorbing-surface-gain-trend", title: "吸收表面增益趋势", kicker: "外部数据证据 · 参数趋势", sceneType: "trend", sceneNote: SCENE_NOTES.trend },
  advanced_ar_bundle: { slug: "advanced-ar-bundle", title: "高级增透膜计算束", kicker: "外部数据证据 · Python—COMSOL 验证", sceneType: "validation", sceneNote: SCENE_NOTES.validation },
  porous_double_ar_topic_bundle: { slug: "porous-double-ar-topic", title: "多孔双层增透专题", kicker: "外部数据证据 · 专题验证", sceneType: "validation", sceneNote: SCENE_NOTES.validation },
});

export function getEvidenceCaseConfig(caseId) {
  const config = EVIDENCE_CASE_CONFIGS[caseId];
  if (!config) throw new Error(`未声明外部证据案例：${caseId}`);
  return Object.freeze({ caseId, ...config });
}
