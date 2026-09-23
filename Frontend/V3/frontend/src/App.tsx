import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  ChevronDown,
  CircleHelp,
  Download,
  FileText,
  ImageIcon,
  Info,
  Loader2,
  Moon,
  Play,
  Sun,
  X,
  FlaskConical,
} from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DesignWorkbench } from "@/components/design/DesignWorkbench";
import { PowerSpectrumControls, formatPowerTick, powerAxisDomain, preferredPowerQuantity, type PowerQuantity } from "@/components/design/PowerSpectrumControls";
import type { DesignDraft } from "@/types/design";

const browserApiHost = window.location.hostname || "127.0.0.1";
const API_BASE_URL = window.thinfilmDesktop?.apiBaseUrl ?? `http://${browserApiHost}:8122`;
const teachingImageModules = import.meta.glob("./assets/for_teaching/*.png", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

type Primitive = string | number | boolean | null;

interface TeachingCase {
  case_id: string;
  title_cn: string;
  title_en: string;
  design_type: string;
  default_params: Record<string, Primitive>;
  category?: string;
  category_label?: string;
  access_mode?: "interactive" | "result" | "evidence";
  has_live_simulation?: boolean;
  physics_model?: string;
  structure?: string;
  materials?: string[];
  physics_data_status?: string;
  migration_status?: string;
  data_dependencies?: string;
  calculation_source?: string;
  notes?: string;
  review_boundary?: string;
  learning_goal?: string;
  coating_function?: string;
  application_scene?: string;
  design_task?: string;
  system_experiment?: {
    system_template: string;
    complexity: string;
    default_views: string[];
    primary_question: string;
  } | null;
  optiland?: {
    enabled: boolean;
    level: "deep" | "light" | "none";
    system_template?: string;
    system_family?: string;
    observables: string[];
  };
}

interface CaseLibraryResponse {
  physical_case_count: number;
  interactive_case_count: number;
  static_case_count: number;
  cases: TeachingCase[];
}

interface LibrarySeries {
  label: string;
  x: number[];
  y: number[];
  x_label: string;
  x_unit: string;
}

interface CaseLibraryDetail extends TeachingCase {
  title: string;
  generated_at: string;
  evidence_status: string;
  model_scope: Primitive | Record<string, unknown>;
  semantic_limit: Primitive | Record<string, unknown>;
  layers: Array<Record<string, Primitive>>;
  series: LibrarySeries[];
  summary_cards: Array<{ label: string; value: Primitive; unit?: string; note?: string }>;
  table: { columns: string[]; rows: Primitive[][] };
  limitations: string[];
  external_data_provenance: unknown;
}

interface SimulationResult {
  case_id: string;
  title_cn: string;
  title_en: string;
  design_type: string;
  summary: Record<string, Primitive>;
  layers: Array<Record<string, Primitive>>;
  series: {
    wavelength_nm: number[];
    R: number[];
    T: number[];
    A: number[];
  };
  figure_explanations?: Record<string, Primitive>;
  figure_explanation?: string | Record<string, Primitive>;
  files: Record<string, string>;
}

interface ChartRow extends Record<string, number> {
  wavelength_nm: number;
  R: number;
  T: number;
  A: number;
}

interface MaterialOption {
  material_id: string;
  display_name_zh: string;
  display_name_en: string;
  category: string;
  suitable_roles: string[];
  locked_roles: string[];
  lambda_min_nm: number;
  lambda_max_nm: number;
  n_at_550nm: number;
  k_at_550nm: number;
}

interface MaterialIndexResult extends MaterialOption {
  wavelength_nm: number;
  n: number;
  k: number;
  method: string;
  in_range: boolean;
}

interface FigureExplanationDialog {
  title: string;
  body: string;
}

const PARAMETER_LABELS: Record<string, string> = {
  theta_deg: "入射角",
  pol: "偏振态",
  lambda0_nm: "设计波长",
  n_incident: "入射介质折射率",
  n_substrate: "基底折射率",
  n_low: "低折射率层折射率",
  n_porous: "多孔层折射率",
  n_mid: "中间折射率层折射率",
  n_high: "高折射率层折射率",
  n_high_2: "第二高折射率层折射率",
  k_incident: "入射介质消光系数",
  k_substrate: "基底消光系数",
  k_low: "低折射率层消光系数",
  k_mid: "中间层消光系数",
  k_high: "高折射率层消光系数",
  k_high_2: "第二高折射率层消光系数",
  periods: "周期数",
  slices_per_period: "每周期切片数",
  total_layers: "总层数",
  n_top: "渐变层顶部折射率",
  n_bottom: "渐变层底部折射率",
  d_total_nm: "总厚度",
  num_gradient_layers: "渐变层数量",
  gradient_type: "渐变类型",
  layer_indices: "自定义层折射率序列",
  layer_thickness_nm: "自定义层厚度序列",
  fp_spacer_kind: "F-P 腔层类型",
  beamsplitter_front_halfwave_low: "前置低折射率半波层",
};

const SUMMARY_LABELS: Record<string, string> = {
  avg_R_300_1100nm: "300–1100 nm 平均反射率",
  avg_R_bare_Si: "裸硅平均反射率",
  bandwidth_R_lt_2pct_nm: "反射率低于 2% 的带宽",
  avg_R_visible: "可见波段平均反射率",
  avg_R_single_layer: "单层基准平均反射率",
  avg_T_visible: "可见波段平均透射率",
  R_at_550nm: "550 nm 反射率",
  R_at_1064nm: "1064 nm 反射率",
  R_blue_450nm: "450 nm 反射率",
  R_green_550nm: "550 nm 反射率",
  R_red_650nm: "650 nm 反射率",
  peak_transmittance: "峰值透射率",
  peak_reflectance: "峰值反射率",
  peak_wavelength_nm: "峰值波长",
  fwhm_nm: "半高全宽",
  fsr_nm: "自由光谱范围（估计）",
  finesse: "精细度（估计）",
  off_peak_transmission: "带外透射率",
  off_peak_transmission_dB: "带外透射水平（dB）",
  isolation_dB: "带外衰减（dB）",
  stopband_width_nm: "高反带宽",
  num_layers: "膜层数",
  index_ratio: "折射率比",
  min_R: "最低反射率",
  peak_R: "最高反射率",
  min_R_wavelength_nm: "最低反射波长",
  max_residual: "最大能量残差",
  wavelength_at_R_min_nm: "最低反射波长",
  wavelength_at_R_max_nm: "最高反射波长",
  wavelength_at_T_max_nm: "最高透射波长",
  solver: "专用求解器",
  primary_curve: "主要观察量",
  curve_min: "曲线最小值",
  curve_max: "曲线最大值",
  ag_thickness_nm: "Ag 厚度",
  dbr_periods: "DBR 周期数",
  beta: "切向波矢 β",
  polarization: "偏振态",
  R_at_lambda0: "中心反射率",
  T_at_lambda0: "中心透射率",
  A_at_lambda0: "中心吸收率",
  R_min: "最小反射率",
  R_min_wavelength_nm: "最小反射波长",
  R_max: "最大反射率",
  R_max_wavelength_nm: "最大反射波长",
  T_min: "最小透射率",
  T_min_wavelength_nm: "最小透射波长",
  T_max: "最大透射率",
  T_max_wavelength_nm: "最大透射波长",
  A_min: "最小吸收率",
  A_min_wavelength_nm: "最小吸收波长",
  A_max: "最大吸收率",
  A_max_wavelength_nm: "最大吸收波长",
};

const LAYER_LABELS: Record<string, string> = {
  name: "层名",
  n: "折射率",
  thickness_nm: "厚度",
  layer_index: "层序号",
  layer_name: "层名",
  n_real: "折射率实部",
  n_imag: "折射率虚部",
  y_start_nm: "起始位置",
  y_end_nm: "结束位置",
};

const UNIT_LABELS: Record<string, string> = {
  theta_deg: "deg",
  lambda0_nm: "nm",
  d_total_nm: "nm",
  layer_thickness_nm: "nm",
  R_min_wavelength_nm: "nm",
  R_max_wavelength_nm: "nm",
  T_min_wavelength_nm: "nm",
  T_max_wavelength_nm: "nm",
  A_min_wavelength_nm: "nm",
  A_max_wavelength_nm: "nm",
  thickness_nm: "nm",
  ag_thickness_nm: "nm",
  y_start_nm: "nm",
  y_end_nm: "nm",
};

const REFRACTIVE_INDEX_PARAMS = new Set([
  "n_incident",
  "n_substrate",
  "n_low",
  "n_porous",
  "n_mid",
  "n_high",
  "n_high_2",
  "n_top",
  "n_bottom",
]);

const K_PARAM_FOR_N: Record<string, string> = {
  n_incident: "k_incident",
  n_substrate: "k_substrate",
  n_low: "k_low",
  n_mid: "k_mid",
  n_high: "k_high",
  n_high_2: "k_high_2",
};
const MATERIAL_CONTROLLED_K_PARAMS = new Set(Object.values(K_PARAM_FOR_N));
const DESIGN_WAVELENGTH_MIN_NM = 400;
const DESIGN_WAVELENGTH_MAX_NM = 750;
const INCIDENT_ANGLE_MIN_DEG = 0;
const INCIDENT_ANGLE_MAX_DEG = 89;

const PARAMETER_HELP: Record<string, string> = {
  theta_deg: "入射光线与膜层法线之间的夹角。角度越大，光在膜层中的等效光程和反射/透射曲线会发生偏移。",
  pol: "入射光偏振态。p 偏振和 s 偏振在斜入射时会得到不同的反射率与透射率。",
  lambda0_nm: "薄膜结构的设计中心波长。四分之一波长层、半波层和滤光片中心峰位通常围绕该波长设计。",
  n_incident: "入射侧介质的折射率，通常为空气。它决定光进入第一层薄膜前的边界条件。",
  n_substrate: "基底材料的折射率，通常为玻璃。它决定最后一层薄膜与基底之间的光学匹配。",
  n_low: "低折射率膜层的折射率，用于减反膜、周期堆和滤光片中的 L 层。",
  n_porous: "多孔二氧化硅等效折射率。孔隙率越高，等效折射率通常越低。",
  n_mid: "三层减反结构中的中间折射率层，用于在低折射率层和高折射率层之间过渡匹配。",
  n_high: "高折射率膜层的折射率，用于双层结构、周期堆或滤光片中的 H 层。",
  n_high_2: "第二类高折射率层的折射率，常用于高反膜、F-P 结构或分束膜的高折射率材料。",
  k_incident: "入射介质消光系数，表示吸收损耗。0 表示近似无吸收。",
  k_substrate: "基底消光系数，表示基底材料吸收损耗。0 表示近似无吸收。",
  k_low: "低折射率膜层消光系数，表示该层材料吸收损耗。",
  k_mid: "中间折射率膜层消光系数，表示该层材料吸收损耗。",
  k_high: "高折射率膜层消光系数，表示该层材料吸收损耗。",
  k_high_2: "第二高折射率膜层消光系数，表示该层材料吸收损耗。",
  periods: "周期堆叠次数。周期数越多，反射带或滤波特征通常越明显，但膜层总数也会增加。",
  slices_per_period: "Rugate 渐变结构中每个周期拆分的离散层数。数值越高，渐变越平滑。",
  total_layers: "渐变或离散近似结构的总层数。层数越多，结构越接近连续折射率分布。",
  n_top: "等效渐变层顶部折射率，通常靠近空气侧。",
  n_bottom: "等效渐变层底部折射率，通常靠近基底侧。",
  d_total_nm: "等效渐变层或自定义结构的总物理厚度。",
  num_gradient_layers: "用于近似连续渐变折射率的离散层数量。",
  gradient_type: "渐变折射率分布类型，例如线性渐变。",
  layer_indices: "自定义多层结构中各层折射率序列。",
  layer_thickness_nm: "自定义多层结构中各层厚度序列。",
  fp_spacer_kind: "F-P 滤光片中心腔层类型，决定谐振腔使用低折射率层还是高折射率层。",
  beamsplitter_front_halfwave_low: "中性分束膜前端是否加入低折射率半波层，用于调整中心波长处的分束效果。",
};

const CASE_IMAGE_FILES: Record<string, string> = {
  quarter_wave_single_layer: "01_四分之一波长单层减反膜.png",
  half_wave_single_layer: "02_半波长单层相位膜.png",
  single_ar: "39_单层减反射膜.png",
  quarter_wave_double_layer: "03_四分之一波长双层减反膜.png",
  double_ar: "40_双层减反射膜.png",
  triple_ar: "29_三层渐变折射率减反膜.png",
  quarter_wave_stack: "04_四分之一波长周期堆_QW_Stack.png",
  bragg_reflector: "05_Bragg高反膜结构与光学特性.png",
  high_reflector: "41_高反射膜.png",
  fp_filter: "06_FP滤光片结构与原理.png",
  fp_single_halfwave: "37_单半波型FP窄带滤光片.png",
  fp_double_halfwave: "31_双半波型FP耦合腔滤光片.png",
  narrowband_filter: "07_窄带滤光片结构与光学特性.png",
  neutral_beamsplitter: "08_中性分束薄膜结构与光学特性.png",
  rugate_filter: "09_Rugate渐变折射率滤光片.png",
  porous_sio2_layer: "10_多孔SiO2减反膜.png",
  porous_double_ar: "11_多孔双层减反膜.png",
  moth_eye_effective_gradient: "12_蛾眼等效渐变层减反膜.png",
};

function displayLabel(key: string, labels: Record<string, string> = PARAMETER_LABELS): string {
  return labels[key] ?? key;
}

function formatValue(value: Primitive): string {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return "-";
    }
    if (Math.abs(value) >= 1000 || Math.abs(value) < 0.001) {
      return value.toExponential(3);
    }
    return value.toLocaleString("zh-CN", { maximumFractionDigits: 4 });
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  if (value === null || value === undefined) {
    return "-";
  }
  return String(value);
}

function fileLabel(key: string): string {
  const labels: Record<string, string> = {
    csv: "CSV",
    json: "JSON",
    txt: "TXT",
    main_png: "主图",
    png: "R/T/A",
    rta_png: "R/T/A",
    analysis_png: "分析图",
  };
  return labels[key] ?? key;
}

function normalizedFigureExplanations(result: SimulationResult | null): Record<string, string> {
  if (!result) {
    return {};
  }
  const source = result.figure_explanations ?? result.figure_explanation;
  if (typeof source === "string") {
    return { rta_desc: source, analysis_desc: source };
  }
  if (!source || typeof source !== "object") {
    return {};
  }
  return Object.fromEntries(
    Object.entries(source).map(([key, value]) => [key, value === null || value === undefined ? "" : String(value)]),
  );
}

function figureExplanationForFile(result: SimulationResult | null, fileKey: string): FigureExplanationDialog {
  const explanations = normalizedFigureExplanations(result);
  if (fileKey.includes("analysis")) {
    return {
      title: explanations.analysis_title || `${fileLabel(fileKey)}物理说明`,
      body: explanations.analysis_desc || "当前图片暂无物理原理说明。",
    };
  }
  return {
    title: explanations.rta_title || `${fileLabel(fileKey)}物理说明`,
    body: explanations.rta_desc || "当前图片暂无物理原理说明。",
  };
}

function isImagePath(path: string): boolean {
  return /\.(png|jpg|jpeg|webp)$/i.test(path);
}

function isVisibleOutputFile(key: string): boolean {
  // Interactive spectrum already owns R/T/A; keep only complementary figures.
  return !["analysis_png", "png", "rta_png"].includes(key);
}

function clampDesignWavelength(value: Primitive): number {
  const numericValue = typeof value === "number" && Number.isFinite(value) ? value : 550;
  return Math.min(DESIGN_WAVELENGTH_MAX_NM, Math.max(DESIGN_WAVELENGTH_MIN_NM, Math.round(numericValue)));
}

function clampIncidentAngle(value: Primitive): number {
  const numericValue = typeof value === "number" && Number.isFinite(value) ? value : 0;
  return Math.min(INCIDENT_ANGLE_MAX_DEG, Math.max(INCIDENT_ANGLE_MIN_DEG, Math.round(numericValue)));
}

function isRefractiveIndexParam(name: string): boolean {
  return REFRACTIVE_INDEX_PARAMS.has(name);
}

function materialOptionsForRole(role: string, materials: MaterialOption[]): MaterialOption[] {
  const directMatches = materials.filter(
    (material) => material.suitable_roles.includes(role) || material.locked_roles.includes(role),
  );
  if (directMatches.length > 0) {
    return directMatches;
  }
  return materials.filter((material) => material.category === "介质");
}

function closestMaterialForValue(role: string, value: Primitive, materials: MaterialOption[]): string {
  const options = materialOptionsForRole(role, materials);
  if (options.length === 0) {
    return "";
  }
  if (role === "n_incident") {
    return options.find((item) => item.material_id === "Air")?.material_id ?? options[0].material_id;
  }
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return options[0].material_id;
  }
  return [...options].sort(
    (left, right) => Math.abs(left.n_at_550nm - value) - Math.abs(right.n_at_550nm - value),
  )[0].material_id;
}

function initialMaterialSelections(params: Record<string, Primitive>, materials: MaterialOption[]): Record<string, string> {
  const selections: Record<string, string> = {};
  for (const [name, value] of Object.entries(params)) {
    if (isRefractiveIndexParam(name)) {
      selections[name] = closestMaterialForValue(name, value, materials);
    }
  }
  return selections;
}

function normalizeParams(nextParams: Record<string, Primitive>): Record<string, Primitive> {
  if (!("lambda0_nm" in nextParams)) {
    return "theta_deg" in nextParams
      ? { ...nextParams, theta_deg: clampIncidentAngle(nextParams.theta_deg) }
      : nextParams;
  }
  return {
    ...nextParams,
    lambda0_nm: clampDesignWavelength(nextParams.lambda0_nm),
    ...("theta_deg" in nextParams ? { theta_deg: clampIncidentAngle(nextParams.theta_deg) } : {}),
  };
}

function parameterHelpText(name: string, selectedCase: TeachingCase | null): string {
  const base = PARAMETER_HELP[name] ?? "该参数会作为当前案例的输入值传入薄膜光学仿真，用于计算 R/T/A 光谱。";
  if (!selectedCase) {
    return base;
  }
  return `在「${selectedCase.title_cn}」中，${base}`;
}

function ParameterHelpIcon({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        className="inline-flex h-5 w-5 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="参数说明"
      >
        <CircleHelp className="h-3.5 w-3.5" />
      </button>
      <span className="pointer-events-none absolute left-full top-1/2 z-40 ml-2 hidden w-72 -translate-y-1/2 rounded-md border bg-popover bg-card px-3 py-2 text-xs leading-relaxed text-card-foreground shadow-lg group-hover:block group-focus-within:block">
        {text}
      </span>
    </span>
  );
}

function teachingImageUrl(caseId: string): string | null {
  const fileName = CASE_IMAGE_FILES[caseId];
  if (!fileName) {
    return null;
  }
  const entry = Object.entries(teachingImageModules).find(([path]) => path.endsWith(`/${fileName}`));
  return entry?.[1] ?? null;
}

interface SpecialistCurve {
  label: string;
  x: number[];
  y: number[];
}

interface TammFieldProfile {
  key: string;
  label: string;
  wavelength_nm: number;
  depth_nm: number[];
  electric_intensity: number[];
}

interface TammFieldComparison {
  polarization: string;
  normalization: string;
  selection_basis: string;
  resonance_wavelength_nm: number;
  reference_wavelength_nm: number;
  field_quantity: string;
  interface_nm: number;
  layer_boundaries_nm: number[];
  profiles: TammFieldProfile[];
  metrics: Record<string, number>;
  validation: {
    energy_conservation_passed: boolean;
    max_tangential_e_relative_jump: number;
    tangential_e_continuity_passed: boolean;
  };
}

interface TammExperimentSettings {
  ag_thickness_nm: number;
  dbr_periods: number;
  beta: number;
  polarization: "p" | "s";
  wavelength_start_nm: number;
  wavelength_stop_nm: number;
}

const DEFAULT_TAMM_EXPERIMENT: TammExperimentSettings = {
  ag_thickness_nm: 30,
  dbr_periods: 3,
  beta: 0,
  polarization: "p",
  wavelength_start_nm: 400,
  wavelength_stop_nm: 800,
};

interface SpecialistTeachingGuide {
  solver: "RCWA" | "GeneralTmm" | "WPTherml";
  chartMeaning: string;
  focus: string;
  physics: string;
  application: string;
  boundary: string;
}

const SPECIALIST_TEACHING_GUIDES: Record<string, SpecialistTeachingGuide> = {
  guided_grating_emt: {
    solver: "RCWA",
    chartMeaning: "横轴是入射波长，纵轴是周期光栅对各衍射通道汇总后的反射、透射与吸收功率比例。",
    focus: "观察共振峰谷的位置、线宽以及 R/T/A 是否满足能量守恒；峰位移动代表周期结构的相位匹配条件发生变化。",
    physics: "RCWA 将横向周期介电常数展开为傅里叶级数，求解不同衍射级之间的电磁耦合，因此它不是把光栅简单等效成均匀薄膜。",
    application: "可用于判断亚波长光栅在耦光、滤波、增透或波导入耦器中的工作波段。",
    boundary: "当前模型为一维矩形周期光栅和有限傅里叶谐波数；结果不代表任意二维图形，也不包含制造粗糙度与有限口径效应。",
  },
  tamm_interface_priority: {
    solver: "GeneralTmm",
    chartMeaning: "两条曲线分别给出 p、s 偏振的反射率，用于比较界面态对偏振的选择性。",
    focus: "比较反射谷和 p/s 差异；反射谷只提供候选特征，还需结合相位与场分布，不能据此确认界面态。",
    physics: "金属层与 Bragg 反射镜相接时，两侧反射相位可能满足界面态条件，从而在高反背景中形成窄特征。",
    application: "可对应窄带选择、偏振敏感探测和镜头镀膜中的界面共振增强。",
    boundary: "采用案例保存的常数复折射率与平面无限膜层；未包含材料随波长变化的完整色散、粗糙度及有限光束效应。",
  },
  tamm_phase_bundle: {
    solver: "GeneralTmm",
    chartMeaning: "曲线展示 p、s 偏振复反射系数的相位角，而不是反射功率。",
    focus: "观察相位快速跃迁的位置，并将其与反射率谷对应；±180° 附近的换支是相位表示方式造成的，不是物理量突然发散。",
    physics: "多层膜共振附近复反射系数可能快速变化；相位变化是辅助证据，不是独立的界面态判据。",
    application: "适合分析相位型传感、共振判据以及对相位敏感的干涉镀膜设计。",
    boundary: "显示的是反射相位，不是传播相位或群时延；相位展开与绝对零点需在进一步定量分析时单独处理。",
  },
  tamm_phase_candidates: {
    solver: "GeneralTmm",
    chartMeaning: "反射率与吸收率放在同一候选波长轴上，用于筛选可能的界面态。",
    focus: "优先寻找反射降低且吸收同时增强的波段，再结合相位曲线确认，避免只凭单个峰谷下结论。",
    physics: "有损金属附近的局域态会把入射能量集中在界面，从而改变反射并提高耗散。",
    application: "可用于从宽波段扫描中挑选传感、吸收增强或窄带器件的候选设计波长。",
    boundary: "候选曲线只完成初筛，不能单独证明局域场位置；最终判定还需要相位或场分布证据。",
  },
  tamm_phase_focus: {
    solver: "GeneralTmm",
    chartMeaning: "当前主曲线为整个平面 Ag/DBR 膜系的吸收率；局域电场在独立卡片中计算。",
    focus: "观察吸收峰的位置和宽度；峰越高表示结构内耗散越强，但不等同于某一点的电场强度越高。",
    physics: "有损金属产生耗散，干涉改变能量分布；是否在界面局域需检查场分布，吸收峰不能单独证明局域态。",
    application: "可联系增强吸收、热探测、光热转换和界面敏感器件。",
    boundary: "主曲线仍表示整体吸收率；真实 |E|² 已在独立的“界面场分布”卡片中由 GeneralTmm 复电场直接计算，两者不可混为同一物理量。",
  },
  tamm_reflection_phase_screen: {
    solver: "GeneralTmm",
    chartMeaning: "p、s 反射相位曲线用于直接筛查界面态相位条件及偏振差异。",
    focus: "寻找相位快速变化区，并注意相位在 ±180° 处的周期换支；应与功率谱共同判断。",
    physics: "多层膜的复反射振幅包含幅值和相位，界面共振会同时改变二者。",
    application: "可用于相位筛选、干涉系统补偿和偏振相关镀膜设计。",
    boundary: "当前未执行相位展开，图中的跳变可能是角度主值区间边界，而非结构不连续。",
  },
  tamm_interface_window_bundle: {
    solver: "GeneralTmm",
    chartMeaning: "p、s 反射率曲线描述界面态可工作的光谱窗口。",
    focus: "比较低反射窗口的中心、宽度和偏振一致性，而不是只看单一波长的最小值。",
    physics: "Bragg 禁带与金属反射相位共同限定界面态能够存在和被外部光耦合的波段。",
    application: "可用于确定窄带探测器、滤光片或传感镀膜的可用工作窗口。",
    boundary: "窗口基于理想平面膜系和当前材料参数；温度、厚度误差及入射角分布会使窗口偏移或展宽。",
  },
  tamm_interface_window_scan: {
    solver: "GeneralTmm",
    chartMeaning: "横轴 β 是归一化切向波矢，曲线表示固定中心波长下反射率随斜入射条件的变化。",
    focus: "观察低反射区在 β 方向的位置和宽度；它代表角度容差趋势，但 β 不能在所有介质中直接当作角度。",
    physics: "改变切向波矢会改变各层的纵向传播常数与反射相位，因此界面态条件随入射方向移动。",
    application: "可用于估计镀膜在不同视场角或倾斜入射条件下的稳定性。",
    boundary: "当前扫描 β 而非直接扫描空气中的角度；换算角度时必须同时考虑入射介质折射率和波长。",
  },
  pdrc_cooling_bundle: {
    solver: "WPTherml",
    chartMeaning: "R/T/A 光谱描述辐射制冷膜系从可见光到红外波段的反射、透射和吸收；热平衡下吸收率也对应发射率。",
    focus: "同时关注太阳波段的低吸收和中红外大气窗口附近的高发射能力，不能只追求单个峰值。",
    physics: "介质干涉层调控光谱选择性，金属背反射层抑制透射；依据基尔霍夫定律，方向和波长相同条件下发射率等于吸收率。",
    application: "对应被动日间辐射制冷、热管理表面以及红外发射率工程。",
    boundary: "当前只显示膜系光谱，不等于净制冷功率；尚未联合太阳辐照、大气透过率、对流和环境温度求热平衡。",
  },
};

const LIBRARY_LINE_COLORS = ["#0f766e", "#2563eb", "#d97706", "#9333ea", "#dc2626", "#0891b2"];

function CaseLibraryDetailView({ detail }: { detail: CaseLibraryDetail }) {
  const [polarizationView, setPolarizationView] = useState("TE");
  const [powerQuantity, setPowerQuantity] = useState<PowerQuantity>(() => preferredPowerQuantity(detail.case_id));
  const hasPolarizations = detail.series.some((series) => /^TE [RTA]$/.test(series.label)) && detail.series.some((series) => /^TM [RTA]$/.test(series.label));
  const powerNames = hasPolarizations ? ["TE R", "TE T", "TE A", "TM R", "TM T", "TM A"] : ["R", "T", "A"];
  const hasPowerSpectrum = powerNames.slice(0, 3).every((name) => detail.series.some((series) => series.label === name));
  const displayedSeries = detail.series.filter((series) =>
    (!hasPolarizations || polarizationView === "both" || series.label.startsWith(`${polarizationView} `)) &&
    (!hasPowerSpectrum || powerQuantity === "all" || series.label.endsWith(` ${powerQuantity}`) || series.label === powerQuantity),
  ).slice(0, 6);
  const powerDomain = hasPowerSpectrum
    ? powerQuantity === "all" ? [0, 1] as [number, number] : powerAxisDomain(displayedSeries.flatMap((series) => series.y))
    : ["auto", "auto"] as [string, string];
  const summaryCards = detail.summary_cards.filter((card) => !["physical_equivalence_group", "variant_of", "result_reuse_policy", "status", "periods_param_explanation"].includes(card.label));
  const chartData = useMemo(() => {
    const rows = new Map<number, Record<string, Primitive>>();
    for (const series of displayedSeries) {
      series.x.forEach((x, index) => {
        const row = rows.get(x) ?? { x };
        row[series.label] = series.y[index];
        rows.set(x, row);
      });
    }
    return Array.from(rows.values()).sort((a, b) => Number(a.x) - Number(b.x));
  }, [displayedSeries]);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.slice(0, 8).map((card, index) => (
          <Card key={`${card.label}-${index}`} className="rounded-md shadow-sm">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="break-words text-xs leading-5 text-muted-foreground">{displayLabel(card.label, SUMMARY_LABELS)}</CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="break-words text-sm font-semibold leading-6">
                {formatValue(card.value)}{(card.unit || (card.label.endsWith("_nm") ? "nm" : "")) ? <span className="ml-1 text-xs text-muted-foreground">{card.unit || "nm"}</span> : null}
              </div>
              {card.note === "正值表示反射增加，减反表现变差" ? <p className="mt-1 text-xs text-muted-foreground">{card.note}</p> : null}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="rounded-md shadow-sm">
        <details><summary className="cursor-pointer p-4 text-sm font-medium">案例说明与数据边界</summary>
        <CardContent className="grid gap-3 text-sm md:grid-cols-2">
          <div><span className="text-muted-foreground">物理模型：</span>{detail.physics_model || "未注明"}</div>
          <div><span className="text-muted-foreground">结构：</span>{detail.structure || "未注明"}</div>
          <div><span className="text-muted-foreground">数据状态：</span>{detail.physics_data_status || detail.evidence_status || "正式导出结果"}</div>
          <div><span className="text-muted-foreground">数据依赖：</span>{detail.data_dependencies || "NONE"}</div>
          {detail.notes ? <p className="md:col-span-2 text-muted-foreground">{detail.notes}</p> : null}
        </CardContent>
        </details>
      </Card>

      {chartData.length > 0 ? (
        <div className="rounded-md border bg-card p-4 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>{detail.has_live_simulation ? "实时计算曲线" : detail.access_mode === "evidence" ? "外部证据曲线" : "正式结果曲线"}</span>
            <span>来源：{detail.calculation_source || (detail.has_live_simulation ? "PyThinFilm / tmmcore" : "案例结果数据")}</span>
          </div>
          {hasPolarizations ? <Select aria-label="曲线偏振" value={polarizationView} onChange={(event) => setPolarizationView(event.target.value)} className="mb-2 w-44"><option value="TE">s / TE 偏振</option><option value="TM">p / TM 偏振</option><option value="both">对比两种偏振</option></Select> : null}
          {hasPowerSpectrum ? <div className="mb-2"><PowerSpectrumControls value={powerQuantity} onChange={setPowerQuantity} values={displayedSeries.flatMap((series) => series.y)} /></div> : null}
          <div className="h-[390px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 24, bottom: 30, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="x" type="number" domain={["dataMin", "dataMax"]} height={48} tick={{ fontSize: 12 }} label={{ value: `${displayedSeries[0]?.x_label || "横坐标"}${displayedSeries[0]?.x_unit ? ` (${displayedSeries[0].x_unit})` : ""}`, position: "insideBottom", offset: -8 }} />
              <YAxis domain={powerDomain} tick={{ fontSize: 12 }} tickFormatter={hasPowerSpectrum ? (value) => formatPowerTick(Number(value), powerDomain as [number, number]) : undefined} width={68} label={{ value: hasPowerSpectrum ? "功率比例" : "数值", angle: -90, position: "insideLeft" }} />
              <Tooltip formatter={(value, name) => [hasPowerSpectrum ? `${(Number(value ?? 0) * 100).toFixed(3)}%` : formatValue(Number(value ?? 0)), String(name)]} />
              <Legend verticalAlign="top" align="center" height={36} wrapperStyle={{ lineHeight: "20px", paddingBottom: 8 }} />
              {displayedSeries.map((series, index) => (
                <Line key={series.label} type="monotone" dataKey={series.label} stroke={LIBRARY_LINE_COLORS[index]} strokeDasharray={series.label.startsWith("TM ") && polarizationView === "both" ? "5 3" : undefined} strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <Card className="rounded-md border-dashed bg-muted/20 shadow-none">
          <CardContent className="p-4 text-sm text-muted-foreground">
            {detail.access_mode === "evidence" || detail.evidence_status
              ? "该条目当前是证据/表格型案例，没有可直接绘制的连续光谱；请查看下方数据表、摘要和适用范围。"
              : "该案例暂无可绘制的光谱数据。"}
          </CardContent>
        </Card>
      )}

      {detail.layers.length > 0 ? (
        <div className="overflow-auto rounded-md border bg-card shadow-sm">
          <Table>
            <TableHeader><TableRow>{Object.keys(detail.layers[0] ?? {}).map((key) => <TableHead key={key}>{displayLabel(key, LAYER_LABELS)}</TableHead>)}</TableRow></TableHeader>
            <TableBody>{detail.layers.map((layer, index) => <TableRow key={index}>{Object.entries(layer).map(([key, value]) => <TableCell key={key}>{formatValue(value)}</TableCell>)}</TableRow>)}</TableBody>
          </Table>
        </div>
      ) : null}

      {detail.table.columns.length > 0 ? (
        <div className="overflow-auto rounded-md border bg-card shadow-sm">
          <Table>
            <TableHeader><TableRow>{detail.table.columns.map((column) => <TableHead key={column}>{displayLabel(column, SUMMARY_LABELS)}</TableHead>)}</TableRow></TableHeader>
            <TableBody>{detail.table.rows.map((row, index) => <TableRow key={index}>{row.map((value, column) => <TableCell key={column}>{formatValue(value)}</TableCell>)}</TableRow>)}</TableBody>
          </Table>
        </div>
      ) : null}

      {detail.limitations.length > 0 ? (
        <Card className="rounded-md border-amber-300/70 bg-amber-50/70 shadow-none dark:bg-amber-950/20">
          <CardHeader className="pb-2"><CardTitle className="text-sm">适用范围与限制</CardTitle></CardHeader>
          <CardContent><ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">{detail.limitations.map((item) => <li key={item}>{item}</li>)}</ul></CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function ApplicationRouteCard({ caseItem }: { caseItem: TeachingCase | null }) {
  if (!caseItem?.learning_goal && !caseItem?.application_scene) return null;
  return (
    <Card className="rounded-md border-primary/20 bg-primary/[0.025] shadow-none">
      <CardHeader className="p-3 pb-2"><CardTitle className="text-sm">应用线路</CardTitle></CardHeader>
      <CardContent className="grid gap-2 p-3 pt-0 text-xs leading-5 sm:grid-cols-2">
        <div><span className="text-muted-foreground">物理规律：</span>{caseItem.learning_goal}</div>
        <div><span className="text-muted-foreground">膜系功能：</span>{caseItem.coating_function}</div>
        <div><span className="text-muted-foreground">工程场景：</span>{caseItem.application_scene}</div>
        <div><span className="text-muted-foreground">设计任务：</span>{caseItem.design_task}</div>
      </CardContent>
    </Card>
  );
}

const SYSTEM_VIEW_LABELS: Record<string, string> = {
  layout_2d: "2D 光路",
  system_3d: "3D 系统",
  spot: "Spot 光斑",
  psf: "PSF 点扩散",
  mtf: "MTF 细节",
  spectrum: "光谱响应",
  phase: "反射相位",
  angle_scan: "角度扫描",
};

function SystemExperimentCard({ caseItem }: { caseItem: TeachingCase | null }) {
  const experiment = caseItem?.system_experiment;
  if (!experiment) return null;
  return (
    <Card className="rounded-md border-sky-500/25 bg-sky-500/[0.025] shadow-none">
      <details>
        <summary className="cursor-pointer list-none p-3 text-sm font-medium">系统实验草案</summary>
        <CardContent className="space-y-2 border-t p-3 pt-3 text-xs leading-5">
          <div><span className="text-muted-foreground">复杂度：</span>{experiment.complexity}</div>
          <div><span className="text-muted-foreground">核心问题：</span>{experiment.primary_question}</div>
          <p className="text-muted-foreground">此处为教学任务设想；实际可用分析以计算结果为准。</p>
        </CardContent>
      </details>
    </Card>
  );
}

function numericParam(value: Primitive, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function layerMaterialFromRow(row: Record<string, Primitive>, materials: MaterialOption[]): string {
  const explicit = row.material_id ?? row.material ?? row.material_name;
  if (typeof explicit === "string" && materials.some((item) => item.material_id === explicit)) return explicit;
  const index = typeof row.n_real === "number" ? row.n_real : typeof row.n === "number" ? row.n : NaN;
  if (Number.isFinite(index) && materials.length > 0) {
    return [...materials].sort((left, right) => Math.abs(left.n_at_550nm - index) - Math.abs(right.n_at_550nm - index))[0].material_id;
  }
  return materials.find((item) => item.material_id === "MgF2")?.material_id ?? materials[0]?.material_id ?? "MgF2";
}

function buildDraftFromCase(
  caseItem: TeachingCase,
  materials: MaterialOption[],
  sourceLayers: Array<Record<string, Primitive>>,
  materialSelections: Record<string, string>,
  detailSeries: LibrarySeries[] = [],
): DesignDraft {
  const params = caseItem.default_params;
  const wavelengthSeries = detailSeries[0]?.x ?? [];
  let start = wavelengthSeries.length > 1 ? Math.min(...wavelengthSeries) : 400;
  let stop = wavelengthSeries.length > 1 ? Math.max(...wavelengthSeries) : 700;
  const layers = sourceLayers.map((row, index) => {
    const name = String(row.name ?? row.role ?? "").toUpperCase();
    const role = name.includes("POROUS") ? "n_porous" : name === "M" ? "n_mid" : name.includes("H") ? "n_high" : "n_low";
    const materialId = materialSelections[role] || layerMaterialFromRow(row, materials);
    const thickness = numericParam(row.thickness_nm, numericParam(params.d_total_nm, 100) / Math.max(sourceLayers.length, 1));
    return { id: `case-${caseItem.case_id}-${index + 1}`, material_id: materialId, thickness_nm: Math.max(thickness, 0.1), enabled: true };
  });
  // Teaching cases may use constant-n materials outside the valid range of
  // their real-material replacements.  Keep the free-design draft inside the
  // common n,k coverage so the first recalculation cannot fail immediately.
  const incidentMaterialId = materialSelections.n_incident || closestMaterialForValue("n_incident", params.n_incident ?? 1, materials);
  const substrateMaterialId = materialSelections.n_substrate || closestMaterialForValue("n_substrate", params.n_substrate ?? 1.52, materials);
  const draftMaterialIds = [
    incidentMaterialId,
    ...layers.map((layer) => layer.material_id),
    substrateMaterialId,
  ];
  const draftMaterialRanges = draftMaterialIds
    .map((materialId) => materials.find((material) => material.material_id === materialId))
    .filter((material): material is MaterialOption => Boolean(material));
  if (draftMaterialRanges.length) {
    start = Math.max(start, ...draftMaterialRanges.map((material) => material.lambda_min_nm));
    stop = Math.min(stop, ...draftMaterialRanges.map((material) => material.lambda_max_nm));
    if (stop <= start) {
      throw new Error("所选材料与案例波段没有共同有效范围，请调整材料或波段。");
    }
  }
  return {
    schema_version: "1.0",
    solver: "tmmcore",
    incident_material_id: incidentMaterialId,
    substrate_material_id: substrateMaterialId,
    layers,
    spectrum: { start_nm: start, stop_nm: stop, points: 351 },
    angle_deg: numericParam(params.theta_deg, 0),
    polarization: params.pol === "s" ? "s" : "p",
    out_of_range_policy: "error",
    probe_wavelength_nm: Math.min(stop, Math.max(start, numericParam(params.lambda0_nm, 550))),
    experiment_task_id: null,
    system_template: caseItem.system_experiment?.system_template,
    optiland: caseItem.optiland,
    engineering_application: { case_title: caseItem.title_cn, goal: caseItem.coating_function ?? "比较当前膜系对系统能量的影响" },
  };
}

function CaseWorkspace({ onOpenDesign }: { onOpenDesign: (draft?: DesignDraft) => void }) {
  const [cases, setCases] = useState<TeachingCase[]>([]);
  const [materials, setMaterials] = useState<MaterialOption[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [params, setParams] = useState<Record<string, Primitive>>({});
  const [materialSelections, setMaterialSelections] = useState<Record<string, string>>({});
  const [materialResults, setMaterialResults] = useState<Record<string, MaterialIndexResult>>({});
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingMaterials, setLoadingMaterials] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [materialError, setMaterialError] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("thinfilm-theme");
    return saved === "dark" ? "dark" : "light";
  });
  const [tab, setTab] = useState("chart");
  const [powerQuantity, setPowerQuantity] = useState<PowerQuantity>("R");
  const [caseInfoOpen, setCaseInfoOpen] = useState(false);
  const [figureExplanation, setFigureExplanation] = useState<FigureExplanationDialog | null>(null);
  const [libraryDetail, setLibraryDetail] = useState<CaseLibraryDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [libraryCounts, setLibraryCounts] = useState({ total: 0, interactive: 0, static: 0 });
  const [transferring, setTransferring] = useState(false);
  const [specialistCurves, setSpecialistCurves] = useState<SpecialistCurve[] | null>(null);
  const [specialistAxis, setSpecialistAxis] = useState({ x: "波长 (nm)", y: "功率" });
  const [tammFieldComparison, setTammFieldComparison] = useState<TammFieldComparison | null>(null);
  const [tammExperiment, setTammExperiment] = useState<TammExperimentSettings>(DEFAULT_TAMM_EXPERIMENT);
  const [tammParameterComparison, setTammParameterComparison] = useState<SpecialistCurve[] | null>(null);
  const tammCaseIds = ["tamm_interface_priority", "tamm_phase_bundle", "tamm_phase_candidates", "tamm_phase_focus", "tamm_reflection_phase_screen", "tamm_interface_window_bundle", "tamm_interface_window_scan"];
  const thermalCaseIds = ["pdrc_cooling_bundle"];

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("thinfilm-theme", theme);
  }, [theme]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadCases() {
      try {
        setLoadingCases(true);
        const response = await fetch(`${API_BASE_URL}/api/case-library`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`案例加载失败：${response.status}`);
        }
        const data = (await response.json()) as CaseLibraryResponse;
        setCases(data.cases);
        setLibraryCounts({ total: data.physical_case_count, interactive: data.interactive_case_count, static: data.static_case_count });
        const firstCase = data.cases[0];
        if (firstCase) {
          setSelectedCaseId(firstCase.case_id);
          setParams(normalizeParams(firstCase.default_params));
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError(err instanceof Error ? err.message : "案例加载失败");
        }
      } finally {
        setLoadingCases(false);
      }
    }

    void loadCases();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadMaterials() {
      try {
        setLoadingMaterials(true);
        const response = await fetch(`${API_BASE_URL}/api/materials`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`材料加载失败：${response.status}`);
        }
        const data = (await response.json()) as MaterialOption[];
        setMaterials(data);
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setMaterialError(err instanceof Error ? err.message : "材料加载失败");
        }
      } finally {
        setLoadingMaterials(false);
      }
    }

    void loadMaterials();
    return () => controller.abort();
  }, []);

  const selectedCase = useMemo(
    () => cases.find((item) => item.case_id === selectedCaseId) ?? null,
    [cases, selectedCaseId],
  );
  const specialistCase = selectedCase?.case_id === "guided_grating_emt" || tammCaseIds.includes(selectedCase?.case_id ?? "") || thermalCaseIds.includes(selectedCase?.case_id ?? "");
  const canTransferToDesign = Boolean(selectedCase && selectedCase.has_live_simulation !== false && !specialistCase);

  const selectedCaseImage = useMemo(() => teachingImageUrl(selectedCaseId), [selectedCaseId]);

  useEffect(() => {
    if (!selectedCase || selectedCase.has_live_simulation !== false || specialistCase) {
      setLibraryDetail(null);
      return;
    }
    const caseId = selectedCase.case_id;
    const controller = new AbortController();
    async function loadDetail() {
      try {
        setLoadingDetail(true);
        setError(null);
        const response = await fetch(`${API_BASE_URL}/api/case-library/${encodeURIComponent(caseId)}`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`案例结果加载失败：${response.status}`);
        }
        setLibraryDetail((await response.json()) as CaseLibraryDetail);
      } catch (err) {
        if ((err as Error).name !== "AbortError") setError(err instanceof Error ? err.message : "案例结果加载失败");
      } finally {
        setLoadingDetail(false);
      }
    }
    void loadDetail();
    return () => controller.abort();
  }, [selectedCase]);

  useEffect(() => {
    if (!selectedCase || materials.length === 0 || Object.keys(materialSelections).length > 0) {
      return;
    }
    setMaterialSelections(initialMaterialSelections(selectedCase.default_params, materials));
  }, [materials, materialSelections, selectedCase]);

  useEffect(() => {
    const wavelengthNm = Number(params.lambda0_nm ?? 550);
    const entries = Object.entries(materialSelections).filter(([, materialId]) => materialId);
    if (!Number.isFinite(wavelengthNm) || entries.length === 0) {
      return;
    }

    const controller = new AbortController();

    async function calculateSelectedMaterials() {
      try {
        setMaterialError(null);
        const results = await Promise.all(
          entries.map(async ([role, materialId]) => {
            const response = await fetch(`${API_BASE_URL}/api/material-index`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              signal: controller.signal,
              body: JSON.stringify({ material_id: materialId, wavelength_nm: wavelengthNm }),
            });
            if (!response.ok) {
              const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
              throw new Error(payload?.detail ?? `材料计算失败：${response.status}`);
            }
            return [role, (await response.json()) as MaterialIndexResult] as const;
          }),
        );

        const nextResults = Object.fromEntries(results);
        setMaterialResults(nextResults);
        setParams((current) => {
          const nextParams = { ...current };
          for (const [role, material] of results) {
            nextParams[role] = material.n;
            const kRole = K_PARAM_FOR_N[role];
            if (kRole && kRole in nextParams) {
              nextParams[kRole] = material.k;
            }
          }
          return nextParams;
        });
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setMaterialError(err instanceof Error ? err.message : "材料计算失败");
        }
      }
    }

    void calculateSelectedMaterials();
    return () => controller.abort();
  }, [materialSelections, params.lambda0_nm]);

  const chartRows = useMemo<ChartRow[]>(() => {
    if (!result) {
      return [];
    }
    return result.series.wavelength_nm.map((wavelength, index) => ({
      wavelength_nm: wavelength,
      R: result.series.R[index],
      T: result.series.T[index],
      A: result.series.A[index],
    }));
  }, [result]);
  const activePowerDomain = powerQuantity === "all" ? [0, 1] as [number, number] : powerAxisDomain([
    ...chartRows.map((row) => row[powerQuantity]),
  ]);

  const specialistChartRows = useMemo(() => {
    if (!specialistCurves?.length) return [];
    return specialistCurves[0].x.map((x, index) => {
      const row: Record<string, number> = { x };
      specialistCurves.forEach((curve, curveIndex) => { row[`curve_${curveIndex}`] = curve.y[index]; });
      return row;
    });
  }, [specialistCurves]);

  const tammFieldRows = useMemo(() => {
    if (!tammFieldComparison?.profiles.length) return [];
    return tammFieldComparison.profiles[0].depth_nm.map((depth, index) => {
      const row: Record<string, number> = { depth_nm: depth };
      tammFieldComparison.profiles.forEach((profile, profileIndex) => {
        row[`field_${profileIndex}`] = profile.electric_intensity[index];
      });
      return row;
    });
  }, [tammFieldComparison]);

  const tammParameterComparisonRows = useMemo(() => {
    if (!tammParameterComparison?.length) return [];
    const rows = new Map<number, { x: number; baseline?: number; modified?: number }>();
    tammParameterComparison[0].x.forEach((x, index) => rows.set(x, { x, baseline: tammParameterComparison[0].y[index] }));
    tammParameterComparison[1].x.forEach((x, index) => rows.set(x, { ...(rows.get(x) ?? { x }), modified: tammParameterComparison[1].y[index] }));
    return [...rows.values()].sort((left, right) => left.x - right.x);
  }, [tammParameterComparison]);

  const specialistGuide = selectedCase ? SPECIALIST_TEACHING_GUIDES[selectedCase.case_id] ?? null : null;

  const specialistObservation = useMemo(() => {
    if (!result || !specialistGuide) return "";
    const primary = specialistCurves?.[0] ?? {
      label: selectedCase?.case_id === "pdrc_cooling_bundle" ? "吸收率 / 发射率 A" : "反射率 R",
      x: result.series.wavelength_nm,
      y: selectedCase?.case_id === "pdrc_cooling_bundle" ? result.series.A : result.series.R,
    };
    const samples = primary.x
      .map((x, index) => ({ x, y: primary.y[index] }))
      .filter((item) => Number.isFinite(item.x) && Number.isFinite(item.y));
    if (samples.length === 0) return "当前结果没有足够的有效采样点，无法生成定量观察。";
    const minimum = samples.reduce((best, item) => item.y < best.y ? item : best, samples[0]);
    const maximum = samples.reduce((best, item) => item.y > best.y ? item : best, samples[0]);
    const xLabel = specialistCurves ? specialistAxis.x : "波长 (nm)";
    return `${primary.label} 在本次扫描中的范围为 ${formatValue(minimum.y)}–${formatValue(maximum.y)}；最小值位于 ${xLabel} = ${formatValue(minimum.x)}，最大值位于 ${xLabel} = ${formatValue(maximum.x)}。极值用于定位特征，不应脱离线宽、相邻曲线和模型边界单独解释。`;
  }, [result, selectedCase?.case_id, specialistAxis.x, specialistCurves, specialistGuide]);

  const summaryRows = useMemo(
    () => Object.entries(result?.summary ?? {}).filter(([, value]) => typeof value !== "object"),
    [result],
  );

  const imageFiles = useMemo(
    () => Object.entries(result?.files ?? {}).filter(([key, value]) => isVisibleOutputFile(key) && isImagePath(value)),
    [result],
  );

  function selectCase(caseId: string) {
    if (running || transferring) return;
    setTab("chart");
    setPowerQuantity(preferredPowerQuantity(caseId));
    const nextCase = cases.find((item) => item.case_id === caseId);
    const nextParams = nextCase ? normalizeParams(nextCase.default_params) : {};
    setSelectedCaseId(caseId);
    setParams(nextParams);
    setMaterialSelections(nextCase ? initialMaterialSelections(nextParams, materials) : {});
    setMaterialResults({});
    setResult(null);
    setSpecialistCurves(null);
    setTammFieldComparison(null);
    setTammParameterComparison(null);
    setTammExperiment(DEFAULT_TAMM_EXPERIMENT);
    setLibraryDetail(null);
    setError(null);
    setCaseInfoOpen(false);
    setFigureExplanation(null);
  }

  function updateParam(name: string, value: Primitive) {
    setParams((current) => ({ ...current, [name]: value }));
  }

  function updateMaterialSelection(name: string, materialId: string) {
    setMaterialSelections((current) => ({ ...current, [name]: materialId }));
  }

  async function runSimulation() {
    if (!selectedCase) {
      return;
    }

    try {
      setRunning(true);
      setError(null);
      setFigureExplanation(null);
      const response = await fetch(`${API_BASE_URL}/api/simulations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_id: selectedCase.case_id,
          params,
          export_files: true,
        }),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? `仿真失败：${response.status}`);
      }

      const data = (await response.json()) as SimulationResult;
      setSpecialistCurves(null);
      setTammFieldComparison(null);
      setTammParameterComparison(null);
      setResult(data);
      setTab("chart");
    } catch (err) {
      setError(err instanceof Error ? err.message : "仿真失败");
    } finally {
      setRunning(false);
    }
  }

  async function runRcwaSimulation() {
    if (!selectedCase || selectedCase.case_id !== "guided_grating_emt") return;
    try {
      setRunning(true);
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/specialist/rcwa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          wavelength_start_um: 0.45,
          wavelength_stop_um: 0.85,
          wavelength_points: 81,
          period_um: 0.7,
          thickness_um: 0.2,
          n_grating: 2.0,
          n_void: 1.0,
          harmonics: 11,
        }),
      });
      const payload = (await response.json()) as { detail?: string; wavelength_um?: number[]; R?: number[]; T?: number[]; A?: number[]; period_um?: number; thickness_um?: number; harmonics?: number };
      if (!response.ok) throw new Error(payload.detail ?? `RCWA 仿真失败：${response.status}`);
      const wavelengths = payload.wavelength_um ?? [];
      const reflectance = payload.R ?? [];
      setResult({
        case_id: selectedCase.case_id,
        title_cn: selectedCase.title_cn,
        title_en: selectedCase.title_en,
        design_type: "rcwa",
        summary: {
          solver: "RCWA",
          primary_curve: "反射率 R",
          curve_min: reflectance.length ? Math.min(...reflectance) : 0,
          curve_max: reflectance.length ? Math.max(...reflectance) : 0,
          period_um: payload.period_um ?? 0.7,
          thickness_um: payload.thickness_um ?? 0.2,
          harmonics: payload.harmonics ?? 11,
        },
        layers: [{ model: "1D rectangular grating", period_um: payload.period_um ?? 0.7, thickness_um: payload.thickness_um ?? 0.2 }],
        series: { wavelength_nm: wavelengths.map((value) => value * 1000), R: reflectance, T: payload.T ?? [], A: payload.A ?? [] },
        files: {},
      });
      setSpecialistCurves(null);
      setTammFieldComparison(null);
      setTammParameterComparison(null);
      setTab("chart");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "RCWA 仿真失败");
    } finally {
      setRunning(false);
    }
  }

  async function runRemainingSpecialistSimulation() {
    if (!selectedCase || selectedCase.case_id === "guided_grating_emt") return;
    const isTamm = tammCaseIds.includes(selectedCase.case_id);
    const isThermal = thermalCaseIds.includes(selectedCase.case_id);
    if (!isTamm && !isThermal) return;
    try {
      setRunning(true);
      setError(null);
      const endpoint = isTamm ? "/api/specialist/generaltmm" : "/api/specialist/wptherml";
      const body: Record<string, Primitive> = isTamm
        ? { case_id: selectedCase.case_id, ...tammExperiment, wavelength_points: 81 }
        : { case_id: selectedCase.case_id, wavelength_start_nm: 300, wavelength_stop_nm: 13000, wavelength_points: 121, temperature_k: 300 };
      if (isTamm && tammExperiment.wavelength_stop_nm <= tammExperiment.wavelength_start_nm) throw new Error("扫描终止波长必须大于起始波长");
      const baselineBody: Record<string, Primitive> = { case_id: selectedCase.case_id, ...DEFAULT_TAMM_EXPERIMENT, wavelength_points: 81 };
      const settingsChanged = isTamm && JSON.stringify(tammExperiment) !== JSON.stringify(DEFAULT_TAMM_EXPERIMENT);
      const requestSolver = (requestBody: Record<string, Primitive>) => fetch(`${API_BASE_URL}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(requestBody) });
      const [response, baselineResponse] = await Promise.all([
        requestSolver(body),
        settingsChanged ? requestSolver(baselineBody) : Promise.resolve(null),
      ]);
      const payload = (await response.json()) as { detail?: string; solver?: string; wavelength_nm?: number[]; R?: number[]; T?: number[]; A?: number[]; curves?: SpecialistCurve[]; comparison_curve?: SpecialistCurve; x_label?: string; y_label?: string; field_comparison?: TammFieldComparison };
      if (!response.ok) throw new Error(payload.detail ?? `${isTamm ? "GeneralTmm" : "WPTherml"} 仿真失败：${response.status}`);
      const baselinePayload = baselineResponse ? (await baselineResponse.json()) as { detail?: string; comparison_curve?: SpecialistCurve } : null;
      if (baselineResponse && !baselineResponse.ok) throw new Error(baselinePayload?.detail ?? `基准方案计算失败：${baselineResponse.status}`);
      const primaryLabel = payload.curves?.[0]?.label ?? (isThermal ? "吸收率 / 发射率 A" : "反射率 R");
      const primaryValues = payload.curves?.[0]?.y ?? (isThermal ? payload.A : payload.R) ?? [];
      setResult({
        case_id: selectedCase.case_id,
        title_cn: selectedCase.title_cn,
        title_en: selectedCase.title_en,
        design_type: isTamm ? "generaltmm" : "wptherml",
        summary: {
          solver: isTamm ? (payload.solver === "pythinfilm-isotropic-tmm" ? "PyThinFilm TMM" : "GeneralTmm") : "WPTherml",
          primary_curve: primaryLabel,
          curve_min: primaryValues.length ? Math.min(...primaryValues) : 0,
          curve_max: primaryValues.length ? Math.max(...primaryValues) : 0,
          ...(isTamm ? { ag_thickness_nm: tammExperiment.ag_thickness_nm, dbr_periods: tammExperiment.dbr_periods, beta: tammExperiment.beta, polarization: tammExperiment.polarization } : {}),
        },
        layers: [],
        series: { wavelength_nm: payload.wavelength_nm ?? [], R: payload.R ?? [], T: payload.T ?? [], A: payload.A ?? [] },
        files: {},
      });
      setSpecialistCurves(payload.curves ?? null);
      setSpecialistAxis({ x: payload.x_label ?? "波长 (nm)", y: payload.y_label ?? "功率" });
      setTammFieldComparison(isTamm ? payload.field_comparison ?? null : null);
      setTammParameterComparison(
        settingsChanged && baselinePayload?.comparison_curve && payload.comparison_curve
          ? [
              { ...baselinePayload.comparison_curve, label: `基准：${baselinePayload.comparison_curve.label}` },
              { ...payload.comparison_curve, label: `修改：${payload.comparison_curve.label}` },
            ]
          : null,
      );
      setTab("chart");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "专用求解器仿真失败");
    } finally {
      setRunning(false);
    }
  }

  async function transferToDesign() {
    if (!selectedCase || !canTransferToDesign) return;
    try {
      setTransferring(true);
      let sourceLayers = libraryDetail?.layers ?? [];
      let sourceSeries = libraryDetail?.series ?? [];
      let currentResult = result;
      if (selectedCase.has_live_simulation !== false) {
        const response = await fetch(`${API_BASE_URL}/api/simulations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ case_id: selectedCase.case_id, params, export_files: false }),
        });
        if (!response.ok) throw new Error(`案例计算失败：${response.status}`);
        currentResult = (await response.json()) as SimulationResult;
        setResult(currentResult);
      }
      if (currentResult) sourceLayers = currentResult.layers;
      const generatedSeries = currentResult?.series;
      if (generatedSeries && generatedSeries.wavelength_nm.length > 1 && !sourceSeries.length) {
        sourceSeries = [{ label: "T", x: generatedSeries.wavelength_nm, y: generatedSeries.T, x_label: "波长", x_unit: "nm" }];
      }
      const draft = buildDraftFromCase({ ...selectedCase, default_params: params }, materials, sourceLayers, materialSelections, sourceSeries);
      onOpenDesign(draft);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "案例带入自由设计失败");
    } finally {
      setTransferring(false);
    }
  }

  return (
    <main className="flex h-screen min-h-0 flex-col bg-muted/30 text-foreground">
      <header className="flex h-16 shrink-0 items-center justify-between border-b bg-card/90 px-5 backdrop-blur">
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold tracking-tight">案例与证据库</h1>
          <p className="text-xs text-muted-foreground">教学仿真 · 工程应用 · 研究证据</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => onOpenDesign()}><FlaskConical />返回工作台</Button>
          <Button
            variant="outline"
            size="icon"
            title={theme === "dark" ? "切换到日间模式" : "切换到夜间模式"}
            onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
          >
            {theme === "dark" ? <Sun /> : <Moon />}
          </Button>
        </div>
      </header>

      <PanelGroup direction="horizontal" className="min-h-0 flex-1">
        <Panel defaultSize={34} minSize={26} maxSize={46} className="min-w-[330px] bg-background">
          <ScrollArea className="h-full border-r bg-card/45">
            <section className="flex min-h-full flex-col gap-4 p-4">
              <Card className="rounded-md shadow-none">
                <CardHeader className="p-3 pb-2">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <Label htmlFor="case">教学案例库（{libraryCounts.total} 例）</Label>
                    <p className="mt-1 text-[11px] text-muted-foreground">薄膜教学与专用求解实验</p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 px-2"
                    disabled={!selectedCaseImage}
                    title={selectedCaseImage ? "查看案例说明" : "当前案例暂无说明图片"}
                    onClick={() => setCaseInfoOpen(true)}
                  >
                    <Info />
                    案例说明
                  </Button>
                </div>
                </CardHeader>
                <CardContent className="p-3 pt-0">
                <Select
                  id="case"
                  value={selectedCaseId}
                  disabled={loadingCases || running || transferring || cases.length === 0}
                  onChange={(event) => selectCase(event.target.value)}
                >
                  {cases.map((item) => (
                    <option key={item.case_id} value={item.case_id}>
                      【{item.category_label}】{item.title_cn}
                    </option>
                  ))}
                </Select>
                </CardContent>
              </Card>

              <ApplicationRouteCard caseItem={selectedCase} />
              {selectedCase?.review_boundary ? <details className="rounded-md border bg-card p-3 text-xs"><summary className="cursor-pointer font-medium">模型适用范围</summary><p className="mt-2 leading-5 text-muted-foreground">{selectedCase.review_boundary}</p></details> : null}
              <SystemExperimentCard caseItem={selectedCase} />

              {selectedCase?.has_live_simulation !== false ? <Card className="rounded-md shadow-none">
                <CardHeader className="p-3 pb-2">
                  <CardTitle className="text-sm">参数输入</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3 p-3 pt-0">
                  {Object.entries(params)
                    .filter(([name]) => !MATERIAL_CONTROLLED_K_PARAMS.has(name))
                    .map(([name, value]) => {
                      const materialParam = isRefractiveIndexParam(name);
                      const materialOptions = materialParam ? materialOptionsForRole(name, materials) : [];
                      const selectedMaterialId =
                        materialSelections[name] || closestMaterialForValue(name, value, materials);
                      const materialResult = materialResults[name];

                      return (
                        <div key={name} className="flex flex-col gap-1.5">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex min-w-0 items-center gap-1.5">
                              <Label htmlFor={name}>{displayLabel(name)}</Label>
                              <ParameterHelpIcon text={parameterHelpText(name, selectedCase)} />
                            </div>
                            {UNIT_LABELS[name] && !materialParam && name !== "lambda0_nm" && name !== "theta_deg" ? (
                              <span className="text-xs text-muted-foreground">{UNIT_LABELS[name]}</span>
                            ) : null}
                          </div>
                          {materialParam ? (
                            <div className="flex flex-col gap-1.5">
                              <Select
                                id={name}
                                value={selectedMaterialId}
                                disabled={loadingMaterials || materialOptions.length === 0}
                                onChange={(event) => updateMaterialSelection(name, event.target.value)}
                              >
                                {materialOptions.map((material) => (
                                  <option key={material.material_id} value={material.material_id}>
                                    {material.display_name_zh}
                                  </option>
                                ))}
                              </Select>
                              <div className="rounded-md border bg-muted/40 px-3 py-2 text-xs leading-relaxed text-muted-foreground">
                                {materialResult ? (
                                  <span className="font-medium text-foreground">折射率 n = {formatValue(materialResult.n)}</span>
                                ) : (
                                  <span>{loadingMaterials ? "正在加载材料参数" : "等待材料折射率计算"}</span>
                                )}
                              </div>
                            </div>
                          ) : typeof value === "boolean" ? (
                            <div className="flex h-9 items-center justify-between rounded-md border bg-card px-3">
                              <span className="text-sm text-muted-foreground">{value ? "开启" : "关闭"}</span>
                              <Switch checked={value} onCheckedChange={(checked) => updateParam(name, checked)} />
                            </div>
                          ) : name === "pol" ? (
                            <Select id={name} value={String(value)} onChange={(event) => updateParam(name, event.target.value)}>
                              <option value="p">p 偏振</option>
                              <option value="s">s 偏振</option>
                            </Select>
                          ) : name === "theta_deg" ? (
                            <div className="flex flex-col gap-2">
                              <div className="flex items-center justify-between rounded-md border bg-card px-3 py-2">
                                <span className="text-lg font-semibold">{clampIncidentAngle(value)}</span>
                                <span className="text-xs text-muted-foreground">deg</span>
                              </div>
                              <input
                                id={name}
                                type="range"
                                min={INCIDENT_ANGLE_MIN_DEG}
                                max={INCIDENT_ANGLE_MAX_DEG}
                                step={1}
                                value={clampIncidentAngle(value)}
                                aria-label="入射角"
                                className="h-2 w-full cursor-pointer accent-primary"
                                onChange={(event) => updateParam(name, Number(event.target.value))}
                              />
                            </div>
                          ) : name === "lambda0_nm" ? (
                            <div className="flex flex-col gap-2">
                              <div className="flex items-center justify-between rounded-md border bg-card px-3 py-2">
                                <span className="text-lg font-semibold">{clampDesignWavelength(value)}</span>
                                <span className="text-xs text-muted-foreground">nm</span>
                              </div>
                              <input
                                id={name}
                                type="range"
                                min={DESIGN_WAVELENGTH_MIN_NM}
                                max={DESIGN_WAVELENGTH_MAX_NM}
                                step={1}
                                value={clampDesignWavelength(value)}
                                aria-label="设计波长"
                                className="h-2 w-full cursor-pointer accent-primary"
                                onChange={(event) => updateParam(name, Number(event.target.value))}
                              />
                            </div>
                          ) : typeof value === "number" ? (
                            <Input
                              id={name}
                              type="number"
                              value={Number.isFinite(value) ? String(value) : ""}
                              onChange={(event) => updateParam(name, Number(event.target.value))}
                            />
                          ) : (
                            <Input id={name} value={String(value ?? "")} onChange={(event) => updateParam(name, event.target.value)} />
                          )}
                        </div>
                      );
                    })}
                </CardContent>
              </Card> : (
                <Card className="rounded-md shadow-none">
                  <CardHeader className="p-3 pb-2"><CardTitle className="text-sm">案例属性</CardTitle></CardHeader>
                  <CardContent className="space-y-2 p-3 pt-0 text-sm">
                    <div className="rounded-md border bg-muted/40 p-3"><span className="text-muted-foreground">类型：</span>{specialistCase ? "专用求解器教学实验" : selectedCase?.access_mode === "evidence" ? "证据案例" : "正式导出结果"}</div>
                    <div><span className="text-muted-foreground">物理模型：</span>{selectedCase?.physics_model}</div>
                    <div><span className="text-muted-foreground">结构：</span>{selectedCase?.structure}</div>
                    <p className="text-xs leading-5 text-muted-foreground">{specialistCase ? "该案例使用已绑定的专用求解器；可在下方实验变量中修改受控参数。" : "该案例用于阅读已有计算与证据，不提供未经验证的在线参数改写。"}</p>
                  </CardContent>
                </Card>
              )}

              {tammCaseIds.includes(selectedCase?.case_id ?? "") ? (
                <details className="group rounded-md border bg-card shadow-none">
                  <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2.5 text-sm font-medium hover:bg-muted/40">
                    <span>实验变量</span>
                    <ChevronDown className="size-4 text-muted-foreground transition-transform group-open:rotate-180" />
                  </summary>
                  <div className="space-y-3 border-t p-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5"><Label htmlFor="tamm-ag">Ag 厚度 (nm)</Label><Input id="tamm-ag" type="number" min={5} max={150} step={1} value={tammExperiment.ag_thickness_nm} onChange={(event) => setTammExperiment((current) => ({ ...current, ag_thickness_nm: Number(event.target.value) }))} /></div>
                      <div className="space-y-1.5"><Label htmlFor="tamm-periods">DBR 周期数</Label><Input id="tamm-periods" type="number" min={1} max={8} step={1} value={tammExperiment.dbr_periods} onChange={(event) => setTammExperiment((current) => ({ ...current, dbr_periods: Number(event.target.value) }))} /></div>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between"><Label htmlFor="tamm-beta">归一化切向波矢 β</Label><span className="text-xs font-medium">{formatValue(tammExperiment.beta)}</span></div>
                      <input id="tamm-beta" type="range" min={0} max={0.95} step={0.01} value={tammExperiment.beta} className="h-2 w-full cursor-pointer accent-primary" onChange={(event) => setTammExperiment((current) => ({ ...current, beta: Number(event.target.value) }))} />
                    </div>
                    <div className="space-y-1.5"><Label htmlFor="tamm-pol">偏振</Label><Select id="tamm-pol" value={tammExperiment.polarization} onChange={(event) => setTammExperiment((current) => ({ ...current, polarization: event.target.value as "p" | "s" }))}><option value="p">p 偏振</option><option value="s">s 偏振</option></Select></div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5"><Label htmlFor="tamm-start">起始波长 (nm)</Label><Input id="tamm-start" type="number" min={200} step={10} value={tammExperiment.wavelength_start_nm} onChange={(event) => setTammExperiment((current) => ({ ...current, wavelength_start_nm: Number(event.target.value) }))} /></div>
                      <div className="space-y-1.5"><Label htmlFor="tamm-stop">终止波长 (nm)</Label><Input id="tamm-stop" type="number" min={210} step={10} value={tammExperiment.wavelength_stop_nm} onChange={(event) => setTammExperiment((current) => ({ ...current, wavelength_stop_nm: Number(event.target.value) }))} /></div>
                    </div>
                    <Button type="button" variant="outline" size="sm" className="w-full" onClick={() => setTammExperiment(DEFAULT_TAMM_EXPERIMENT)}>恢复基准参数</Button>
                    <p className="text-[11px] leading-4 text-muted-foreground">修改后运行会同时保留默认 30 nm Ag、3 周期 DBR、β=0、p 偏振基准用于对照。</p>
                  </div>
                </details>
              ) : null}

              <div className="grid gap-2 sm:grid-cols-2">
                {selectedCase?.case_id === "guided_grating_emt" ? <Button className="h-11" disabled={!selectedCase || running || transferring} onClick={() => void runRcwaSimulation()}>
                  {running ? <Loader2 className="animate-spin" /> : <Play />}
                  开始 RCWA 仿真
                </Button> : specialistCase ? <Button className="h-11" disabled={!selectedCase || running || transferring} onClick={() => void runRemainingSpecialistSimulation()}>
                  {running ? <Loader2 className="animate-spin" /> : <Play />}
                  {tammCaseIds.includes(selectedCase?.case_id ?? "") ? "开始 Tamm 仿真" : "开始 WPTherml 仿真"}
                </Button> : selectedCase?.has_live_simulation !== false ? <Button className="h-11" disabled={!selectedCase || running || transferring} onClick={() => void runSimulation()}>
                  {running ? <Loader2 className="animate-spin" /> : <Play />}
                  开始仿真
                </Button> : null}
                {canTransferToDesign ? <Button className="h-11" variant="outline" disabled={transferring} onClick={() => void transferToDesign()}>
                  {transferring ? <Loader2 className="animate-spin" /> : <FlaskConical />}
                  带入自由设计
                </Button> : null}
              </div>

              {error ? (
                <div className="flex gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                  <AlertCircle className="mt-0.5 size-4 shrink-0" />
                  <span>{error}</span>
                </div>
              ) : null}
              {materialError ? (
                <div className="flex gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                  <AlertCircle className="mt-0.5 size-4 shrink-0" />
                  <span>{materialError}</span>
                </div>
              ) : null}
            </section>
          </ScrollArea>
        </Panel>

        <PanelResizeHandle className="resize-handle" />

        <Panel minSize={54} className="bg-muted/30">
          <ScrollArea className="h-full">
            <section className="flex flex-col gap-4 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-card p-4 shadow-sm">
                <div>
                  <h2 className="text-lg font-semibold tracking-tight">输出面板</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {specialistCase
                      ? (result ? "专用求解器结果已生成" : "等待专用求解器计算")
                      : selectedCase?.has_live_simulation === false
                      ? (loadingDetail ? "正在读取正式案例数据" : "正式结果与证据数据")
                      : (result ? "仿真结果已生成" : "等待运行仿真")}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(result?.files ?? {})
                    .filter(([key]) => isVisibleOutputFile(key) && key !== "json" && key !== "txt" && key !== "audit_json")
                    .map(([key, value]) => (
                    <Button key={key} asChild variant="outline" size="sm" title={fileLabel(key)}>
                      <a href={`${API_BASE_URL}${value}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2">
                        {isImagePath(value) ? <ImageIcon /> : <Download />}
                        {fileLabel(key)}
                      </a>
                    </Button>
                  ))}
                </div>
              </div>

              {error ? <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 p-4 text-sm">{error}</div> : running ? (
                <div role="status" className="flex items-center gap-2 rounded-md border p-6 text-sm"><Loader2 className="size-4 animate-spin" />正在计算当前案例…</div>
              ) : selectedCase?.has_live_simulation === false && !specialistCase ? (
                loadingDetail ? (
                  <div className="flex min-h-[520px] items-center justify-center rounded-md border border-dashed bg-card/70">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="animate-spin" />正在加载案例数据</div>
                  </div>
                ) : libraryDetail ? (
                  <CaseLibraryDetailView key={selectedCaseId} detail={libraryDetail} />
                ) : (
                  <div className="flex min-h-[520px] items-center justify-center rounded-md border border-dashed bg-card/70 text-sm text-muted-foreground">暂无可展示的数据</div>
                )
              ) : !result ? (
                <div className="flex min-h-[520px] items-center justify-center rounded-md border border-dashed bg-card/70">
                  <div className="text-center">
                    <FileText className="mx-auto mb-3 size-10 text-muted-foreground" />
                    <p className="text-sm font-medium">请选择案例并开始仿真</p>
                    <p className="mt-1 text-xs text-muted-foreground">结果会显示在右侧曲线、指标和膜层表中</p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    {summaryRows.slice(0, 8).map(([key, value]) => (
                      <Card key={key} className="rounded-md shadow-sm">
                        <CardHeader className="p-4 pb-2">
                          <CardTitle className="break-words text-xs leading-5 text-muted-foreground">
                            {displayLabel(key, SUMMARY_LABELS)}
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="p-4 pt-0">
                          <div className="break-words text-sm font-semibold leading-6">
                            {formatValue(value)}
                            {UNIT_LABELS[key] ? <span className="ml-1 text-xs text-muted-foreground">{UNIT_LABELS[key]}</span> : null}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  <Tabs value={tab} onValueChange={setTab}>
                    <TabsList className="rounded-md">
                      <TabsTrigger value="chart">曲线</TabsTrigger>
                      {!specialistCase ? <TabsTrigger value="layers">膜层</TabsTrigger> : null}
                      {!specialistCase ? <TabsTrigger value="files">图片</TabsTrigger> : null}
                    </TabsList>

                    <TabsContent value="chart">
                      {!specialistCurves ? <div className="mb-2"><PowerSpectrumControls value={powerQuantity} onChange={setPowerQuantity} values={powerQuantity === "all" ? [] : chartRows.map((row) => row[powerQuantity])} /></div> : null}
                      <div className="h-[430px] rounded-md border bg-card p-4 shadow-sm">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={specialistCurves ? specialistChartRows : chartRows} margin={{ top: 8, right: 24, bottom: 30, left: 12 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                            <XAxis
                              dataKey={specialistCurves ? "x" : "wavelength_nm"}
                              type="number"
                              domain={["dataMin", "dataMax"]}
                              height={50}
                              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                              label={{ value: specialistCurves ? specialistAxis.x : "波长 (nm)", position: "insideBottom", offset: -8 }}
                            />
                            <YAxis
                              domain={specialistCurves ? ["auto", "auto"] : activePowerDomain}
                              tickFormatter={specialistCurves ? undefined : (value) => formatPowerTick(Number(value), activePowerDomain)}
                              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                              width={58}
                              label={{ value: specialistCurves ? specialistAxis.y : "功率比例", angle: -90, position: "insideLeft" }}
                            />
                            <Tooltip
                              formatter={(value, name) => [
                                specialistCurves ? formatValue(Number(value ?? 0)) : `${(Number(value ?? 0) * 100).toFixed(3)}%`,
                                specialistCurves && typeof name === "string" && name.startsWith("curve_")
                                  ? specialistCurves[Number(name.slice(6))]?.label ?? name
                                  : name === "R" ? "反射率 R" : name === "T" ? "透射率 T" : name === "A" ? "吸收率 A" : String(name),
                              ]}
                              labelFormatter={(value) => specialistCurves ? formatValue(Number(value)) : `${formatValue(Number(value))} nm`}
                            />
                            <Legend verticalAlign="top" align="center" height={38} wrapperStyle={{ lineHeight: "20px", paddingBottom: 8 }} />
                            {specialistCurves ? specialistCurves.map((curve, index) => (
                              <Line
                                key={`${curve.label}-${index}`}
                                type="monotone"
                                dataKey={`curve_${index}`}
                                name={curve.label}
                                stroke={["#0f766e", "#7c3aed", "#d97706", "#dc2626"][index % 4]}
                                 strokeWidth={2}
                                 dot={false}
                                 isAnimationActive={false}
                               />
                            )) : (
                              <>
                                {(powerQuantity === "all" || powerQuantity === "R") && <Line type="monotone" dataKey="R" name="反射 R" stroke="#0f766e" strokeWidth={2} dot={false} isAnimationActive={false} />}
                                {(powerQuantity === "all" || powerQuantity === "T") && <Line type="monotone" dataKey="T" name="透射 T" stroke="#2563eb" strokeWidth={2} dot={false} isAnimationActive={false} />}
                                {(powerQuantity === "all" || powerQuantity === "A") && <Line type="monotone" dataKey="A" name="吸收 A" stroke="#d97706" strokeWidth={2} dot={false} isAnimationActive={false} />}
                              </>
                            )}
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      {tammParameterComparison ? (
                        <details className="group mt-3 rounded-md border bg-card shadow-sm">
                          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium hover:bg-muted/40">
                            <span className="flex items-center gap-2"><FlaskConical className="size-4 text-primary" />基准方案 / 修改方案对照</span>
                            <ChevronDown className="size-4 text-muted-foreground transition-transform group-open:rotate-180" />
                          </summary>
                          <div className="border-t p-4">
                            <div className="h-[330px]">
                              <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={tammParameterComparisonRows} margin={{ top: 8, right: 24, bottom: 30, left: 12 }}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                  <XAxis dataKey="x" type="number" domain={["dataMin", "dataMax"]} height={50} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} label={{ value: specialistAxis.x, position: "insideBottom", offset: -8 }} />
                                  <YAxis domain={["auto", "auto"]} width={58} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} label={{ value: specialistAxis.y, angle: -90, position: "insideLeft" }} />
                                  <Tooltip formatter={(value, name) => [formatValue(Number(value ?? 0)), String(name)]} labelFormatter={(value) => formatValue(Number(value))} />
                                  <Legend verticalAlign="top" align="center" height={38} wrapperStyle={{ lineHeight: "20px", paddingBottom: 8 }} />
                                  <Line type="monotone" dataKey="baseline" name={tammParameterComparison[0].label} stroke="#64748b" strokeWidth={1.8} strokeDasharray="6 4" dot={false} connectNulls isAnimationActive={false} />
                                  <Line type="monotone" dataKey="modified" name={tammParameterComparison[1].label} stroke="#dc2626" strokeWidth={2.4} dot={false} connectNulls isAnimationActive={false} />
                                </LineChart>
                              </ResponsiveContainer>
                            </div>
                            <p className="mt-2 text-xs leading-5 text-muted-foreground">灰色虚线为固定基准方案，红色实线为当前实验变量方案；若修改扫描范围，两条曲线只在各自拥有数据的区间显示。</p>
                          </div>
                        </details>
                      ) : null}
                      {tammFieldComparison ? (
                        <details className="group mt-3 rounded-md border bg-card shadow-sm">
                          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                            <span className="flex items-center gap-2">
                              <FlaskConical className="size-4 text-primary" />
                              界面场分布
                              <span className="rounded-full border bg-muted px-2 py-0.5 text-[11px] font-normal text-muted-foreground">真实 |E|²</span>
                            </span>
                            <ChevronDown className="size-4 text-muted-foreground transition-transform group-open:rotate-180" />
                          </summary>
                          <div className="space-y-4 border-t p-4">
                            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                              <div className="rounded-md border p-3"><p className="text-[11px] text-muted-foreground">共振波长</p><p className="mt-1 font-semibold">{formatValue(tammFieldComparison.resonance_wavelength_nm)} nm</p></div>
                              <div className="rounded-md border p-3"><p className="text-[11px] text-muted-foreground">膜内峰值 |E|²</p><p className="mt-1 font-semibold">{formatValue(tammFieldComparison.metrics.resonance_peak_inside)}</p></div>
                              <div className="rounded-md border p-3"><p className="text-[11px] text-muted-foreground">峰值深度</p><p className="mt-1 font-semibold">{formatValue(tammFieldComparison.metrics.resonance_peak_depth_nm)} nm</p></div>
                              <div className="rounded-md border p-3"><p className="text-[11px] text-muted-foreground">界面增强比</p><p className="mt-1 font-semibold">{formatValue(tammFieldComparison.metrics.interface_enhancement_ratio)}×</p></div>
                            </div>
                            <div className="h-[360px] rounded-md border bg-background p-3">
                              <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={tammFieldRows} margin={{ top: 8, right: 24, bottom: 30, left: 18 }}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                  <XAxis dataKey="depth_nm" type="number" domain={["dataMin", "dataMax"]} height={50} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} tickFormatter={(value) => `${Math.round(Number(value))}`} label={{ value: "膜厚方向位置 (nm)", position: "insideBottom", offset: -8 }} />
                                  <YAxis domain={[0, "auto"]} width={62} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} label={{ value: "|E|² / |Einc|²", angle: -90, position: "insideLeft" }} />
                                  <Tooltip formatter={(value, name) => [formatValue(Number(value ?? 0)), String(name)]} labelFormatter={(value) => `${formatValue(Number(value))} nm`} />
                                  <Legend verticalAlign="top" align="center" height={38} wrapperStyle={{ lineHeight: "20px", paddingBottom: 8 }} />
                                  {tammFieldComparison.layer_boundaries_nm.filter((boundary) => Math.abs(boundary - tammFieldComparison.interface_nm) > 1e-8).map((boundary) => (
                                    <ReferenceLine key={boundary} x={boundary} stroke="hsl(var(--muted-foreground))" strokeDasharray="2 4" strokeOpacity={0.45} />
                                  ))}
                                  <ReferenceLine x={tammFieldComparison.interface_nm} stroke="#dc2626" strokeWidth={2} label={{ value: "Ag / DBR 界面", fill: "#dc2626", fontSize: 11, position: "insideTopRight" }} />
                                  {tammFieldComparison.profiles.map((profile, index) => (
                                    <Line key={profile.key} type="monotone" dataKey={`field_${index}`} name={`${profile.label} ${formatValue(profile.wavelength_nm)} nm`} stroke={index === 0 ? "#dc2626" : "#2563eb"} strokeWidth={index === 0 ? 2.4 : 1.8} strokeDasharray={index === 0 ? undefined : "6 4"} dot={false} isAnimationActive={false} />
                                  ))}
                                </LineChart>
                              </ResponsiveContainer>
                            </div>
                            <div className="grid gap-3 md:grid-cols-2">
                              <div className={`rounded-md border p-3 ${tammFieldComparison.validation.energy_conservation_passed ? "border-emerald-500/30 bg-emerald-500/5" : "border-destructive/40 bg-destructive/5"}`}>
                                <p className="text-xs font-semibold">能量守恒 {tammFieldComparison.validation.energy_conservation_passed ? "通过" : "未通过"}</p>
                                <p className="mt-1 text-xs text-muted-foreground">共振点误差：{formatValue(tammFieldComparison.metrics.energy_deviation)}</p>
                              </div>
                              <div className={`rounded-md border p-3 ${tammFieldComparison.validation.tangential_e_continuity_passed ? "border-emerald-500/30 bg-emerald-500/5" : "border-destructive/40 bg-destructive/5"}`}>
                                <p className="text-xs font-semibold">切向电场连续性 {tammFieldComparison.validation.tangential_e_continuity_passed ? "通过" : "未通过"}</p>
                                <p className="mt-1 text-xs text-muted-foreground">最大相对跳变：{formatValue(tammFieldComparison.validation.max_tangential_e_relative_jump)}</p>
                              </div>
                            </div>
                            <p className="text-xs leading-5 text-muted-foreground">实线为当前所选偏振在反射率最低点的总电场强度，虚线为扫描范围内高反射点对照；红色竖线是 Ag/DBR 界面，其余竖线是膜层边界。场分布由复电场直接计算，不由吸收率换算，也不自动确认界面本征态。</p>
                          </div>
                        </details>
                      ) : null}
                      {specialistCase && specialistGuide ? (
                        <details className="group mt-3 rounded-md border bg-card shadow-sm">
                          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                            <span className="flex items-center gap-2">
                              <BookOpen className="size-4 text-primary" />
                              如何读图与工程意义
                              <span className="rounded-full border bg-muted px-2 py-0.5 text-[11px] font-normal text-muted-foreground">
                                {specialistGuide.solver}
                              </span>
                            </span>
                            <ChevronDown className="size-4 text-muted-foreground transition-transform group-open:rotate-180" />
                          </summary>
                          <div className="grid gap-3 border-t p-4 md:grid-cols-2">
                            <div className="rounded-md bg-muted/40 p-3 md:col-span-2">
                              <p className="text-xs font-semibold text-foreground">本次结果观察</p>
                              <p className="mt-1 text-sm leading-6 text-muted-foreground">{specialistObservation}</p>
                            </div>
                            <div className="rounded-md border p-3">
                              <p className="text-xs font-semibold text-foreground">坐标与曲线</p>
                              <p className="mt-1 text-sm leading-6 text-muted-foreground">{specialistGuide.chartMeaning}</p>
                            </div>
                            <div className="rounded-md border p-3">
                              <p className="text-xs font-semibold text-foreground">重点看什么</p>
                              <p className="mt-1 text-sm leading-6 text-muted-foreground">{specialistGuide.focus}</p>
                            </div>
                            <div className="rounded-md border p-3">
                              <p className="text-xs font-semibold text-foreground">背后的物理</p>
                              <p className="mt-1 text-sm leading-6 text-muted-foreground">{specialistGuide.physics}</p>
                            </div>
                            <div className="rounded-md border p-3">
                              <p className="text-xs font-semibold text-foreground">工程应用</p>
                              <p className="mt-1 text-sm leading-6 text-muted-foreground">{specialistGuide.application}</p>
                            </div>
                            <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 md:col-span-2">
                              <p className="text-xs font-semibold text-foreground">模型边界</p>
                              <p className="mt-1 text-sm leading-6 text-muted-foreground">{specialistGuide.boundary}</p>
                            </div>
                          </div>
                        </details>
                      ) : null}
                    </TabsContent>

                    <TabsContent value="layers">
                      <div className="rounded-md border bg-card shadow-sm">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            {Object.keys(result.layers[0] ?? {}).map((key) => (
                              <TableHead key={key}>{displayLabel(key, LAYER_LABELS)}</TableHead>
                            ))}
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {result.layers.map((layer, index) => (
                            <TableRow key={index}>
                              {Object.entries(layer).map(([key, value]) => (
                                <TableCell key={key}>
                                  {formatValue(value)}
                                  {UNIT_LABELS[key] ? <span className="ml-1 text-xs text-muted-foreground">{UNIT_LABELS[key]}</span> : null}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                      </div>
                    </TabsContent>

                    <TabsContent value="files">
                      <div className="grid gap-4">
                        {imageFiles.map(([key, value]) => (
                          <Card key={key} className="rounded-md shadow-sm">
                            <CardHeader className="flex flex-row items-center justify-between gap-3">
                              <CardTitle>{fileLabel(key)}</CardTitle>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="shrink-0 gap-2"
                                onClick={() => setFigureExplanation(figureExplanationForFile(result, key))}
                              >
                                <Info className="h-4 w-4" />
                                物理说明
                              </Button>
                            </CardHeader>
                            <CardContent>
                              <img
                                src={`${API_BASE_URL}${value}`}
                                alt={fileLabel(key)}
                                className="max-h-[520px] w-full rounded-md border object-contain"
                              />
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </TabsContent>
                  </Tabs>
                </>
              )}
            </section>
          </ScrollArea>
        </Panel>
      </PanelGroup>

      {caseInfoOpen && selectedCase && selectedCaseImage ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="案例说明"
          onClick={() => setCaseInfoOpen(false)}
        >
          <div
            className="flex max-h-[92vh] w-full max-w-5xl flex-col rounded-lg border bg-card shadow-lg"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex shrink-0 items-center justify-between gap-3 border-b px-4 py-3">
              <h2 className="truncate text-base font-semibold">{selectedCase.title_cn}</h2>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                title="关闭"
                onClick={() => setCaseInfoOpen(false)}
              >
                <X />
              </Button>
            </div>
            <div className="min-h-0 overflow-auto p-4">
              <img
                src={selectedCaseImage}
                alt={`${selectedCase.title_cn}案例说明`}
                className="mx-auto max-h-[78vh] w-auto max-w-full rounded-md border object-contain"
              />
            </div>
          </div>
        </div>
      ) : null}

      {figureExplanation ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="物理说明"
          onClick={() => setFigureExplanation(null)}
        >
          <div
            className="flex max-h-[80vh] w-full max-w-2xl flex-col rounded-lg border bg-card shadow-lg"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex shrink-0 items-center justify-between gap-3 border-b px-4 py-3">
              <h2 className="truncate text-base font-semibold">{figureExplanation.title}</h2>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                title="关闭"
                onClick={() => setFigureExplanation(null)}
              >
                <X />
              </Button>
            </div>
            <div className="overflow-auto p-4">
              <p className="whitespace-pre-wrap text-sm leading-7 text-muted-foreground">{figureExplanation.body}</p>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

function App() {
  const [workspace, setWorkspace] = useState<"cases" | "design">("design");
  const [initialDraft, setInitialDraft] = useState<DesignDraft | null>(null);
  return workspace === "design" ? (
    <DesignWorkbench initialDraft={initialDraft ?? undefined} onOpenCases={() => setWorkspace("cases")} />
  ) : (
    <CaseWorkspace
      onOpenDesign={(draft) => {
        setInitialDraft(draft ?? null);
        setWorkspace("design");
      }}
    />
  );
}

export default App;
