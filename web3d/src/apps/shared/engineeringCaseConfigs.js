const lowHighReflectance = ({ r }) => {
  if (r < 0.08) return { id: "LOW_REFLECTION", label: "低反射：透射波占主导" };
  if (r >= 0.7) return { id: "RELATIVE_HIGH", label: "高反射：反射波占主导" };
  return { id: "INTERMEDIATE", label: "中等反射：反射与透射并存" };
};

const filterPassStop = ({ t }) => {
  if (t >= 0.8) return { id: "LOW_REFLECTION", label: "透射峰：透射波占主导" };
  if (t <= 0.1) return { id: "RELATIVE_HIGH", label: "阻带：反射波占主导" };
  return { id: "INTERMEDIATE", label: "滤光片边缘：反射与透射并存" };
};

const singleLayerPresets = Object.freeze([
  { id: "minimum", label: "最低反射", selector: "minR" },
  { id: "design", label: "550 nm", wavelengthNm: 550 },
  { id: "maximum", label: "相对高反", selector: "maxR" },
]);

const dbrPresets = Object.freeze([
  { id: "design", label: "550 nm", wavelengthNm: 550 },
  { id: "peak", label: "反射峰值", selector: "maxR" },
  { id: "contrast", label: "带外对照", selector: "minR" },
]);

const fpPresets = Object.freeze([
  { id: "pass", label: "透射峰值", selector: "maxT" },
  { id: "design", label: "550 nm", wavelengthNm: 550 },
  { id: "stop", label: "最深阻带", selector: "minT" },
]);

export const ENGINEERING_CASE_CONFIGS = Object.freeze({
  porous_sio2_layer: Object.freeze({
    caseId: "porous_sio2_layer", slug: "porous-sio2-layer", title: "多孔二氧化硅减反结构",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 1, sceneName: "StandalonePorousSio2LayerScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "正式光谱来自 porous_sio2_layer 的 Python 教学预设；多孔层按有效折射率模型表示。",
  }),
  porous_double_ar: Object.freeze({
    caseId: "porous_double_ar", slug: "porous-double-ar", title: "多孔双层减反膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 2, sceneName: "StandalonePorousDoubleArScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "两层结构、厚度和 R/T 均来自 Python porous_double_ar 正式导出。",
  }),
  moth_eye_effective_gradient: Object.freeze({
    caseId: "moth_eye_effective_gradient", slug: "moth-eye-gradient", title: "蛾眼等效渐变层减反膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 5, sceneName: "StandaloneMothEyeGradientScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "五层阶梯只表示 Python 中的等效渐变近似，不绘制亚波长蛾眼微结构。",
  }),
  double_ar: Object.freeze({
    caseId: "double_ar", slug: "double-ar", title: "双层减反射膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 2, sceneName: "StandaloneDoubleArScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "最低反射、设计点与对照点均来自当前 Python 正式光谱。",
  }),
  quarter_wave_double_layer: Object.freeze({
    caseId: "quarter_wave_double_layer", slug: "quarter-wave-double-layer", title: "四分之一波长双层减反膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 2, sceneName: "StandaloneQuarterWaveDoubleLayerScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "V 形增透行为由正式 R/T 光谱判断，屏幕厚度不是物理比例尺。",
  }),
  triple_ar: Object.freeze({
    caseId: "triple_ar", slug: "triple-ar", title: "三层渐变折射率减反膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 3, sceneName: "StandaloneTripleArScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "三层正式层序和折射率角色保持 Python 导出，不套用太阳能案例材料。",
  }),
  fp_double_halfwave: Object.freeze({
    caseId: "fp_double_halfwave", slug: "fp-double-halfwave", title: "双半波型 F-P 滤光片",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 21, sceneName: "StandaloneFpDoubleHalfwaveScene",
    presets: fpPresets, classify: filterPassStop,
    caveat: "二十一层双腔结构完整显示；外部示意波不是腔内定量驻波场。",
  }),
  rugate_filter: Object.freeze({
    caseId: "rugate_filter", slug: "rugate-filter", title: "Rugate 褶皱渐变折射率滤光片",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 80, sceneName: "StandaloneRugateFilterScene",
    presets: dbrPresets, classify: lowHighReflectance,
    caveat: "连续折射率调制由八十层离散近似显示；全部层来自 Python 正式导出。",
  }),
  neutral_beamsplitter: Object.freeze({
    caseId: "neutral_beamsplitter", slug: "neutral-beamsplitter", title: "中性分束膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 4, sceneName: "StandaloneNeutralBeamsplitterScene",
    presets: Object.freeze([
      { id: "design", label: "550 nm", wavelengthNm: 550 },
      { id: "minimum", label: "最低反射", selector: "minR" },
      { id: "maximum", label: "最高反射", selector: "maxR" },
    ]),
    classify({ r, t }) {
      if (Math.abs(r - 0.5) <= 0.05 && Math.abs(t - 0.5) <= 0.05) return { id: "INTERMEDIATE", label: "近中性分束：R/T 接近 50/50" };
      return { id: "RELATIVE_HIGH", label: "分束偏离：查看正式 R/T 数值" };
    },
    caveat: "分束性能依据 R 与 T 的数值平衡，不以两条示意波是否等宽作为定量判据。",
  }),
  quarter_wave_single_layer: Object.freeze({
    caseId: "quarter_wave_single_layer", slug: "quarter-wave-single-layer", title: "1/4 波长单层减反射膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 1, sceneName: "StandaloneQuarterWaveSingleLayerScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "最低反射、设计波长与相对高反均来自当前正式 TE/TM 光谱。",
  }),
  half_wave_single_layer: Object.freeze({
    caseId: "half_wave_single_layer", slug: "half-wave-single-layer", title: "1/2 波长单层相位膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 1, sceneName: "StandaloneHalfWaveSingleLayerScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "半波层的教学重点是相位等效；外部 R/T 波形不能替代膜内相位分析。",
  }),
  single_ar: Object.freeze({
    caseId: "single_ar", slug: "single-ar", title: "单层减反射膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 1, sceneName: "StandaloneSingleArScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "反射抑制结论依据正式 R；正弦波仅用于辅助比较。",
  }),
  high_reflector: Object.freeze({
    caseId: "high_reflector", slug: "high-reflector", title: "高反射膜",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 7, sceneName: "StandaloneHighReflectorScene",
    presets: dbrPresets, classify: lowHighReflectance,
    caveat: "反射带和带外对照来自同一正式光谱，不改变七层正式结构。",
  }),
  quarter_wave_stack: Object.freeze({
    caseId: "quarter_wave_stack", slug: "quarter-wave-stack", title: "1/4 波长 QW 膜堆",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 7, sceneName: "StandaloneQuarterWaveStackScene",
    presets: dbrPresets, classify: lowHighReflectance,
    caveat: "QW 膜堆通过正式 R/T 展示反射带；屏幕层厚采用视觉映射。",
  }),
  bragg_reflector: Object.freeze({
    caseId: "bragg_reflector", slug: "bragg-reflector", title: "布拉格反射镜（DBR）",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 7, sceneName: "StandaloneBraggReflectorScene",
    presets: dbrPresets, classify: lowHighReflectance,
    caveat: "550 nm、反射峰与带外点均读取正式光谱；TE/TM 分裂保持原数据。",
  }),
  fp_single_halfwave: Object.freeze({
    caseId: "fp_single_halfwave", slug: "fp-single-halfwave", title: "单半波型 F-P 滤光片",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 13, sceneName: "StandaloneFpSingleHalfwaveScene",
    presets: fpPresets, classify: filterPassStop,
    caveat: "透射峰和阻带来自正式光谱；示意波不表示腔内定量驻波场。",
  }),
  fp_filter: Object.freeze({
    caseId: "fp_filter", slug: "fp-filter", title: "F-P 腔窄带透射滤光片",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 13, sceneName: "StandaloneFpFilterScene",
    presets: Object.freeze([
      { id: "resonance", label: "缺陷模", path: ["resonance_metrics", "$POL", "selected_peak", "wavelength_nm"] },
      { id: "design", label: "550 nm", wavelengthNm: 550 },
      { id: "stop", label: "最深阻带", selector: "minT" },
    ]),
    classify: filterPassStop,
    caveat: "缺陷模优先使用正式 resonance_metrics；不把全光谱最大透射误称为腔内缺陷模。",
  }),
  narrowband_filter: Object.freeze({
    caseId: "narrowband_filter", slug: "narrowband-filter", title: "窄带透射滤光片",
    kicker: "PyThinFilm · 独立教学案例", expectedLayerCount: 17, sceneName: "StandaloneNarrowbandFilterScene",
    presets: fpPresets, classify: filterPassStop,
    caveat: "透射峰与最深阻带用于对比窄带滤光行为；保留十七层正式结构。",
  }),
  tamm_phase_bundle: Object.freeze({
    caseId: "tamm_phase_bundle", slug: "tamm-phase-bundle", title: "Tamm 反射相位相干匹配束",
    kicker: "PyThinFilm · 独立研究案例", expectedLayerCount: 8, sceneName: "StandaloneTammPhaseBundleScene",
    presets: Object.freeze([
      { id: "candidate", label: "候选点", path: ["selected_candidate", "wavelength_nm"] },
      { id: "maximum", label: "反射峰值", selector: "maxR" },
      { id: "minimum", label: "反射谷值", selector: "minR" },
    ]),
    classify({ r, a }) {
      if (a >= 0.1) return { id: "INTERMEDIATE", label: "有损候选点：吸收不可忽略" };
      return lowHighReflectance({ r });
    },
    caveat: "候选点读取正式 selected_candidate；当前固定复折射率和相位参考面限制继续有效。",
  }),
  app_wdm_filter: Object.freeze({
    caseId: "app_wdm_filter",
    slug: "wdm-filter",
    title: "WDM 窄带滤光片",
    kicker: "PyThinFilm · 独立工程应用",
    expectedLayerCount: 17,
    sceneName: "StandaloneWdmFilterScene",
    presets: Object.freeze([
      { id: "primary", label: "通带峰值", metric: "peak_wavelength_nm" },
      { id: "target", label: "1550 nm", wavelengthNm: 1550 },
      { id: "contrast", label: "最深阻带", selector: "minT" },
    ]),
    classify({ r, t }) {
      if (t >= 0.8) return { id: "LOW_REFLECTION", label: "通带：透射波占主导" };
      if (t <= 0.1) return { id: "RELATIVE_HIGH", label: "阻带：反射波占主导" };
      return { id: "INTERMEDIATE", label: "通带边缘：反射与透射并存" };
    },
    caveat: "通带与阻带均来自当前正式光谱；正弦波只表达对应 R/T 的教学示意振幅。",
  }),
  app_laser_mirror: Object.freeze({
    caseId: "app_laser_mirror",
    slug: "laser-mirror",
    title: "1064 nm 激光高反镜",
    kicker: "PyThinFilm · 独立工程应用",
    expectedLayerCount: 17,
    sceneName: "StandaloneLaserMirrorScene",
    presets: Object.freeze([
      { id: "primary", label: "1064 nm", wavelengthNm: 1064 },
      { id: "peak", label: "反射峰值", selector: "maxR" },
      { id: "contrast", label: "低反射对照", selector: "minR" },
    ]),
    classify({ r }) {
      if (r >= 0.99) return { id: "RELATIVE_HIGH", label: "高反射带：透射波被显著抑制" };
      if (r <= 0.1) return { id: "LOW_REFLECTION", label: "带外对照：反射较低" };
      return { id: "INTERMEDIATE", label: "带边：反射与透射并存" };
    },
    caveat: "高反射结论依据正式 R 数值；零功率或近零透射波按既有阈值抑制或标记放大。",
  }),
  app_phone_lens_ar: Object.freeze({
    caseId: "app_phone_lens_ar",
    slug: "phone-lens-ar",
    title: "手机镜头三层减反膜",
    kicker: "PyThinFilm · 独立工程应用",
    expectedLayerCount: 3,
    sceneName: "StandalonePhoneLensArScene",
    presets: Object.freeze([
      { id: "blue", label: "蓝光 450", wavelengthNm: 450 },
      { id: "green", label: "绿光 550", wavelengthNm: 550 },
      { id: "red", label: "红光 650", wavelengthNm: 650 },
    ]),
    classify({ r }) {
      if (r < 0.05) return { id: "LOW_REFLECTION", label: "低反射点：透射波占主导" };
      if (r >= 0.15) return { id: "RELATIVE_HIGH", label: "可见光反射偏高：反射波不可忽略" };
      return { id: "INTERMEDIATE", label: "中等反射：透射占主导但反射可见" };
    },
    caveat: "蓝、绿、红三个波长用于检查可见光颜色一致性；不得由单点波形替代全波段指标。",
  }),
  app_smart_window: Object.freeze({
    caseId: "app_smart_window", slug: "smart-window", title: "智能调温窗 Low-E 膜",
    kicker: "PyThinFilm · 独立工程应用", expectedLayerCount: 3, sceneName: "StandaloneSmartWindowScene",
    presets: Object.freeze([
      { id: "visible", label: "可见光 550", wavelengthNm: 550 },
      { id: "nir", label: "近红外 1000", wavelengthNm: 1000 },
      { id: "reflective", label: "反射峰值", selector: "maxR" },
    ]),
    classify({ r, t, a }) {
      if (t >= 0.6) return { id: "LOW_REFLECTION", label: "高透射点：透射波占主导" };
      if (r >= 0.5) return { id: "RELATIVE_HIGH", label: "热反射点：反射波占主导" };
      if (a >= 0.2) return { id: "INTERMEDIATE", label: "有损区：吸收不可忽略" };
      return { id: "INTERMEDIATE", label: "选择性过渡区" };
    },
    caveat: "当前正式 JSON 表示固定 WO3/NiO/Ag 光谱状态，不伪造电致变色切换过程。",
  }),
  guided_grating_emt: Object.freeze({
    caseId: "guided_grating_emt", slug: "guided-grating-emt", title: "一维亚波长光栅 EMT 零级近似",
    kicker: "PyThinFilm · 独立 EMT 教学案例", expectedLayerCount: 1, sceneName: "StandaloneGuidedGratingEmtScene",
    presets: Object.freeze([
      { id: "target", label: "1550 nm", wavelengthNm: 1550 },
      { id: "peak", label: "反射峰值", selector: "maxR" },
      { id: "minimum", label: "反射谷值", selector: "minR" },
    ]),
    classify: lowHighReflectance,
    caveat: "方块只表示 TE/TM 各向异性等效层；ρ≥1 的当前参数属于 EMT 失效边界，不代表真实光栅齿或全波衍射。",
  }),
  mat_library_demo: Object.freeze({
    caseId: "mat_library_demo", slug: "material-library", title: "真实材料库与色散插值演示",
    kicker: "PyThinFilm · 独立材料案例", expectedLayerCount: 1, sceneName: "StandaloneMaterialLibraryScene",
    presets: singleLayerPresets, classify: lowHighReflectance,
    caveat: "独立场景选用材料库中的 MgF2/SiO2 单层代表例；不是把全部材料同时画成一个膜系。",
  }),
  pdrc_cooling_bundle: Object.freeze({
    caseId: "pdrc_cooling_bundle", slug: "pdrc-cooling", title: "PDRC 被动辐射制冷评估束",
    kicker: "PyThinFilm · 独立研究案例", expectedLayerCount: 6, sceneName: "StandalonePdrcCoolingScene",
    presets: Object.freeze([
      { id: "solar", label: "太阳谱 550", wavelengthNm: 550 },
      { id: "window", label: "大气窗 10000", wavelengthNm: 10000 },
      { id: "absorbing", label: "吸收峰值", selector: "minT" },
    ]),
    classify({ r, t, a, wavelengthNm }) {
      if (wavelengthNm >= 8000 && wavelengthNm <= 13000 && a >= 0.7) return { id: "LOW_REFLECTION", label: "大气窗口高发射候选" };
      if (wavelengthNm <= 2500 && r >= 0.85) return { id: "RELATIVE_HIGH", label: "太阳波段高反射候选" };
      return { id: "INTERMEDIATE", label: "宽谱筛选点：查看正式 R/T/A" };
    },
    caveat: "这是 Python 内置有效光学常数的第一版宽谱筛选，不替代真实材料或 COMSOL 最终验证。",
  }),
  rugate_80layer_table: Object.freeze({
    caseId: "rugate_80layer_table", slug: "rugate-80layer-table", title: "80 层 Rugate 褶皱滤光片列表",
    kicker: "PyThinFilm · 独立研究导出案例", expectedLayerCount: 80, sceneName: "StandaloneRugate80LayerTableScene",
    presets: dbrPresets, classify: lowHighReflectance,
    caveat: "完整显示 COMSOL 友好表对应的八十层离散结构；光谱由同一 Python 层表送入 TMM 获得。",
  }),
});

export function getEngineeringCaseConfig(caseId) {
  const config = ENGINEERING_CASE_CONFIGS[caseId];
  if (!config) throw new Error(`未声明独立工程案例：${caseId}`);
  return config;
}
