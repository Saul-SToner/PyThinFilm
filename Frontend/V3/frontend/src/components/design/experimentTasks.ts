import type { DesignDraft } from "@/types/design";

export interface ExperimentTask {
  id: string;
  title: string;
  stage: "物理规律" | "工程应用";
  question: string;
  objectives: string[];
  steps: string[];
  prompts: string[];
  starterDesign: DesignDraft;
}

const baseDesign: Omit<DesignDraft, "layers"> = {
  schema_version: "1.0",
  incident_material_id: "Air",
  substrate_material_id: "N-BK7",
  spectrum: { start_nm: 450, stop_nm: 800, points: 351 },
  angle_deg: 0,
  polarization: "p",
  out_of_range_policy: "error",
  probe_wavelength_nm: 550,
  experiment_task_id: "single-layer-ar",
};

function quarterWaveLayers(periods: number) {
  return Array.from({ length: periods }).flatMap((_, index) => [
    { id: `h-${index + 1}`, material_id: "TiO2", thickness_nm: 63.95, enabled: true },
    { id: `l-${index + 1}`, material_id: "SiO2", thickness_nm: 94.1, enabled: true },
  ]);
}

export const EXPERIMENT_TASKS: ExperimentTask[] = [
  {
    id: "single-layer-ar",
    title: "实验1：单层减反与光学厚度",
    stage: "物理规律",
    question: "固定材料时，为什么存在一个使550 nm附近反射率最低的膜层厚度？",
    objectives: ["观察上下表面反射光的相消干涉", "验证四分之一波长光学厚度条件"],
    steps: ["先写下对最佳厚度的预测", "保存初始99.6 nm结果", "分别尝试70、100、130 nm", "比较反射谷位置与深度", "用 n·d≈λ/4 解释观察结果"],
    prompts: ["厚度增大时反射谷向哪个方向移动？", "最低反射率是否只由厚度决定？"],
    starterDesign: { ...baseDesign, layers: [{ id: "ar-layer", material_id: "MgF2", thickness_nm: 99.6, enabled: true }] },
  },
  {
    id: "bragg-reflector",
    title: "实验2：Bragg反射镜的周期增强",
    stage: "工程应用",
    question: "高、低折射率层周期数增加时，高反射带如何变化？",
    objectives: ["理解多界面反射的相干叠加", "测量反射带宽度与峰值反射率"],
    steps: ["加载3周期起始结构并保存", "复制高低折射率层得到4周期", "继续增加到5周期", "比较R峰值和R≥90%带宽", "总结周期数带来的性能与厚度代价"],
    prompts: ["反射峰和带宽是否以相同速度增加？", "层序互换会不会改变空气侧响应？"],
    starterDesign: { ...baseDesign, experiment_task_id: "bragg-reflector", layers: quarterWaveLayers(3) },
  },
  {
    id: "fp-cavity",
    title: "实验3：F-P腔的共振透射",
    stage: "物理规律",
    question: "两个反射镜之间的腔层厚度如何决定窄带透射峰？",
    objectives: ["识别F-P共振透射峰", "理解腔长、线宽与Q因子的关系"],
    steps: ["保存起始腔结构结果", "将中间SiO2腔层厚度增加10%", "观察透射峰波长移动", "增加两侧反射层并比较FWHM", "根据往返相位条件解释峰位"],
    prompts: ["腔层变厚后共振峰向长波还是短波移动？", "反射镜增强时峰值和线宽如何变化？"],
    starterDesign: {
      ...baseDesign,
      spectrum: { start_nm: 500, stop_nm: 620, points: 601 },
      experiment_task_id: "fp-cavity",
      layers: [
        ...quarterWaveLayers(2),
        { id: "cavity", material_id: "SiO2", thickness_nm: 376.4, enabled: true },
        ...quarterWaveLayers(2).reverse().map((layer) => ({ ...layer, id: `right-${layer.id}` })),
      ],
    },
  },
];

export function cloneDesign(design: DesignDraft): DesignDraft {
  return JSON.parse(JSON.stringify(design)) as DesignDraft;
}
