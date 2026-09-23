import { useMemo, useState } from "react";
import { Activity, AlertCircle, ChevronDown, ExternalLink, Gauge, Ghost, Loader2, Palette, RefreshCw, ScanSearch } from "lucide-react";

import { API_BASE_URL } from "@/api/thinfilmClient";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import type { DesignDraft } from "@/types/design";

interface OptilandComparison {
  available: boolean;
  ready: boolean;
  error?: string;
  interpretation?: string;
  system_template?: string;
  system_family?: string;
  design?: Record<string, unknown>;
  metrics?: Record<string, number>;
  checks?: Record<string, boolean>;
  sampling?: { converged?: boolean; max_step_nm?: number };
  analysis_conditions?: { wavelength_nm?: number; field_deg?: number };
  artifacts?: Record<string, string>;
  branch_analysis?: { scope: string; bare?: { reflected_flux: number }; coated: { reflected_flux: number; transmitted_flux: number | null; direction_error: number; ledger: { accounted_residual: number } } };
  ghost_stray?: {
    probe_wavelength_nm?: number;
    model_scope?: string;
    coated?: { ghost_flux_standard_error?: number; detected_ghost_paths?: number; ray_count?: number; depth?: number };
  };
  spectrum_color?: {
    model_scope?: string;
    color_available?: boolean;
    color_unavailable_reason?: string;
    bare?: { xyz?: number[]; xyY?: number[]; srgb?: number[] };
    coated?: { xyz?: number[]; xyY?: number[]; srgb?: number[] };
  };
  analysis_groups?: Record<string, {
    ready: boolean;
    source?: string;
    units?: string;
    reason?: string;
  }>;
}

const ARTIFACT_LABELS: Record<string, string> = {
  material_dispersion: "材料色散",
  layout_uncoated: "裸镜片 2D",
  layout_coated: "镀膜镜片 2D",
  system3d_uncoated: "裸镜片 3D",
  system3d_coated: "镀膜镜片 3D",
  layout_system: "当前系统 2D",
  system3d_system: "当前系统 3D",
  spot_system: "Spot",
  psf_system: "PSF",
  mtf_system: "MTF",
  energy_system: "能量传递：裸表面 / 当前镀膜",
  detector_system: "探测器：裸表面 / 当前镀膜",
  ghost_stray_system: "NSQ 鬼像与杂散光对照",
  spectrum_color_system: "光谱探测与颜色响应",
  branch_system: "反射 / 透射接收功率",
};

const ARTIFACT_GUIDANCE: Record<string, string> = {
  spot_system: "看像面上的光斑大小、形状和偏心：越集中越清晰，拉长或偏心通常提示像差或离焦。",
  psf_system: "看一个理想点经过系统后的扩散：峰值越集中，点扩散越小，细节越不容易被模糊。",
  mtf_system: "看不同空间频率下的对比度保留：曲线越高，镜头保留细节的能力越强。",
};

const SYSTEM_FAMILY_LABELS: Record<string, { title: string; subtitle: string }> = {
  imaging: { title: "Optiland · 成像系统分析", subtitle: "像面辐照度 · 鬼像与杂散光 · Spot / PSF / MTF" },
  spectral: { title: "Optiland · 光谱系统分析", subtitle: "探测器响应 · 光谱通量 · 颜色结果" },
  reflector: { title: "Optiland · 单镜反射分析", subtitle: "反射光路 · 接收功率" },
  beamsplitter: { title: "Optiland · 双支路分光", subtitle: "反射支路 · 透射支路" },
  thermal: { title: "Optiland · 热辐射系统分析", subtitle: "光谱通量 · 吸收与发射" },
  grating: { title: "Optiland · 光栅系统分析", subtitle: "耦合光强 · 光谱响应" },
  baseline: { title: "Optiland · 系统分析", subtitle: "系统能量与探测器结果" },
};

function artifactUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
}

function metric(value: number | undefined, digits = 4): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";
}

function engineeringApplication(draft: DesignDraft, family: string, result: OptilandComparison | null) {
  const goal = draft.engineering_application?.goal;
  const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
  const percent = (value: number) => `${(value * 100).toFixed(2)}%`;
  const change = (before: number, after: number) => {
    const delta = (after - before) * 100;
    return `${percent(before)} 变为 ${percent(after)}，${Math.abs(delta) < 0.005 ? "基本不变" : `${delta > 0 ? "增加" : "减少"} ${Math.abs(delta).toFixed(2)} 个百分点`}`;
  };
  if (family === "reflector") {
    const before = result?.branch_analysis?.bare?.reflected_flux;
    const after = result?.branch_analysis?.coated.reflected_flux;
    return { place: "单个平面反射镜的反射面（当前为单镜基线）。", goal: goal ?? "提高目标波长的反射能量，减少未反射损失。", effect: finite(before) && finite(after) ? `相同条件下，反射接收比例从 ${change(before, after)}；不代表激光腔反馈。` : "尚无可用的单镜对照结果。" };
  }
  if (family === "beamsplitter") {
    const branch = result?.branch_analysis?.coated;
    return { place: "双接收通道之间的零厚度等效分光面。", goal: goal ?? "将入射光分配给反射、透射两个通道。", effect: branch && finite(branch.reflected_flux) && finite(branch.transmitted_flux) ? `入射 1 W 时，反射通道接收 ${metric(branch.reflected_flux)} W，透射通道接收 ${metric(branch.transmitted_flux)} W；是否满足目标需结合指定分光比。` : "尚无可用的双通道结果。" };
  }
  if (family === "spectral") return { place: "探测器前的平行滤光窗口入口面。", goal: goal ?? "选择所需波段，控制进入探测器的光谱。", effect: "现有光谱通量描述膜系响应；尚不足以判断完整光谱相机的通道隔离或成像性能。" };
  if (family !== "imaging") return { place: "当前案例的应用场景仍待匹配系统验证。", goal: goal ?? "比较膜系在目标波段的作用。", effect: "尚无匹配的工程系统结果，不判定目标已达成。" };
  const template = draft.system_template ?? "single_lens_imaging";
  const lens = ["single_lens_imaging", "camera_lens_coverglass", "wide_angle_window"].includes(template) ? "单透镜成像镜头" : ["phone_camera_module", "complex_camera_lens"].includes(template) ? "三片透镜教学镜头组" : "两片透镜教学镜头组";
  const before = result?.metrics?.bare_relative_throughput;
  const after = result?.metrics?.coated_relative_throughput;
  return { place: `${lens}的第一入射表面；其余表面为裸界面。`, goal: goal ?? "降低前表面反射损耗，让更多光到达像面。", effect: result?.analysis_groups?.energy?.ready && finite(before) && finite(after) ? `当前像面通光量从 ${change(before, after)}；该变化不代表几何像差得到修正。` : "尚无可用的镀膜与裸表面对照结果。" };
}

function ResultImage({ artifactKey, path }: { artifactKey: string; path: string }) {
  return (
    <div className="overflow-hidden rounded-md border bg-card">
      <div className="flex items-center justify-between gap-2 border-b px-2.5 py-2 text-xs font-medium">
        <span>{ARTIFACT_LABELS[artifactKey]}</span>
        <Button asChild variant="ghost" size="icon" className="size-7" title="在新窗口打开">
          <a href={artifactUrl(path)} target="_blank" rel="noreferrer"><ExternalLink className="size-3.5" /></a>
        </Button>
      </div>
      <a href={artifactUrl(path)} target="_blank" rel="noreferrer">
        <img src={artifactUrl(path)} alt={ARTIFACT_LABELS[artifactKey]} className="max-h-[440px] w-full object-contain" loading="lazy" />
      </a>
    </div>
  );
}

export function OptilandPanel({ draft }: { draft: DesignDraft }) {
  const [comparison, setComparison] = useState<OptilandComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [calculatedDraftKey, setCalculatedDraftKey] = useState<string | null>(null);
  const optilandEnabled = draft.optiland?.enabled !== false;
  const currentDraftKey = useMemo(() => JSON.stringify(draft), [draft]);
  const resultIsStale = comparison !== null && calculatedDraftKey !== currentDraftKey;
  const systemFamily = draft.system_template === "dual_path_beamsplitter" ? "beamsplitter" : comparison?.system_family ?? draft.optiland?.system_family ?? "imaging";
  const familyLabel = SYSTEM_FAMILY_LABELS[systemFamily] ?? SYSTEM_FAMILY_LABELS.baseline;
  const application = engineeringApplication(draft, systemFamily, comparison);
  const observables = draft.optiland?.observables ?? ["throughput", "detector_irradiance", "ghost", "stray_light", "spectral_response", "color_response"];
  const showEnergy = ["imaging", "reflector", "thermal", "grating", "baseline"].includes(systemFamily) && observables.includes("throughput");
  const showDetector = ["imaging", "spectral", "reflector", "grating", "baseline"].includes(systemFamily) && observables.includes("detector_irradiance");
  const showGhost = systemFamily === "imaging" && (observables.includes("ghost") || observables.includes("stray_light"));
  const showSpectrum = ["spectral", "reflector", "thermal", "grating"].includes(systemFamily) && (observables.includes("spectral_response") || observables.includes("color_response"));

  async function recalculate() {
    if (loading || !optilandEnabled) return;
    const requestDraftKey = currentDraftKey;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/optiland/system`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ draft }),
      });
      const payload = (await response.json()) as OptilandComparison;
      if (!response.ok) throw new Error(payload.error ?? `Optiland 请求失败：${response.status}`);
      setComparison(payload);
      setCalculatedDraftKey(requestDraftKey);
    } catch (cause) {
      setComparison({ available: false, ready: false, error: cause instanceof Error ? cause.message : "Optiland 请求失败" });
      setCalculatedDraftKey(requestDraftKey);
    } finally {
      setLoading(false);
    }
  }

  const artifacts = useMemo(
    () => Object.entries(comparison?.artifacts ?? {}).filter(([, path]) => /\.png(?:[?#]|$)/i.test(path)),
    [comparison],
  );
  const artifactMap = Object.fromEntries(artifacts);
  const secondaryArtifacts = ["spot_system", "psf_system", "mtf_system"]
    .map((key) => [key, artifactMap[key]] as const)
    .filter((entry): entry is readonly [string, string] => systemFamily === "imaging" && Boolean(entry[1]));

  // Pure thin-film cases intentionally do not expose an empty system panel.
  if (!optilandEnabled) return null;

  return (
    <Card className="rounded-md border-primary/20 shadow-none">
      <button type="button" className="flex w-full items-center justify-between gap-3 p-3 text-left" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
          <div className="flex items-center gap-2">
            <ScanSearch className="size-4 text-primary" />
            <div>
              <CardTitle className="text-sm">{familyLabel.title}</CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">{familyLabel.subtitle}</p>
            </div>
          </div>
          <ChevronDown className={`size-4 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open ? <CardContent className="space-y-3 p-3 pt-0">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-muted/20 px-3 py-2.5">
            <p className="text-xs text-muted-foreground">
              {loading ? "正在计算当前膜系" : comparison === null ? "尚未计算 Optiland 系统结果" : resultIsStale ? "膜系已修改，当前显示的是上次计算结果" : "当前结果与膜系一致"}
            </p>
            <Button type="button" variant="outline" size="sm" disabled={loading} onClick={() => void recalculate()}>
              {loading ? <Loader2 className="animate-spin" /> : <RefreshCw />}
              重新计算 Optiland
            </Button>
          </div>
          {resultIsStale && !loading ? <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-2.5 text-xs text-amber-700 dark:text-amber-300">参数已经变化。下方结果仅供参考，点击“重新计算 Optiland”更新。</div> : null}
          {loading && comparison === null ? (
            <div className="flex items-center gap-2 rounded-md border border-dashed p-3 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />正在生成 Optiland 对照结果…</div>
          ) : comparison === null ? (
            <div className="rounded-md border border-dashed p-4 text-center text-xs text-muted-foreground">展开面板不会启动后台计算。请在需要系统图和分析结果时手动计算。</div>
          ) : !comparison?.available ? (
            <div className="flex gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs leading-5 text-amber-700 dark:text-amber-300"><AlertCircle className="mt-0.5 size-4 shrink-0" /><span>{comparison?.error ?? "Optiland 当前不可用"}</span></div>
          ) : (
            <>
              <details className="rounded-md border bg-muted/20">
                <summary className="cursor-pointer list-none px-3 py-2.5 text-xs font-medium">工程应用</summary>
                <div className="grid gap-1.5 border-t px-3 py-2.5 text-[11px] leading-5 text-muted-foreground">
                  <p><span className="font-medium text-foreground">用在哪里：</span>{application.place}</p>
                  <p><span className="font-medium text-foreground">解决什么：</span>{application.goal}</p>
                  <p><span className="font-medium text-foreground">实际效果：</span>{application.effect}</p>
                  {comparison.analysis_conditions ? <p>计算条件：{metric(comparison.analysis_conditions.wavelength_nm, 1)} nm · {comparison.branch_analysis ? "入射角" : "视场"} {metric(comparison.analysis_conditions.field_deg, 1)}°</p> : null}
                  {comparison.sampling?.converged === false ? <p>光谱加密尚未收敛，窄峰位置与峰值需进一步复核。</p> : null}
                </div>
              </details>
              <div className="grid gap-3 lg:grid-cols-2">
                {["layout_system", "system3d_system"].map((key) => {
                  const path = artifactMap[key];
                  if (!path) return null;
                  return (
                    <div key={key} className="overflow-hidden rounded-md border bg-card">
                      <div className="flex items-center justify-between gap-2 border-b px-2.5 py-2 text-xs font-medium">
                        <span>{ARTIFACT_LABELS[key]}</span>
                        <Button asChild variant="ghost" size="icon" className="size-7" title="在新窗口打开">
                          <a href={artifactUrl(path)} target="_blank" rel="noreferrer"><ExternalLink className="size-3.5" /></a>
                        </Button>
                      </div>
                      <img src={artifactUrl(path)} alt={ARTIFACT_LABELS[key]} className="max-h-[420px] w-full object-contain" />
                    </div>
                  );
                })}
              </div>
              <div className="grid gap-2">
                {comparison.branch_analysis ? <details className="rounded-md border">
                  <summary className="cursor-pointer p-3 text-sm font-medium">支路功率与验证</summary>
                  <div className="space-y-2 border-t p-3 text-xs">
                    <p>反射接收：{metric(comparison.branch_analysis.coated.reflected_flux)} W{comparison.branch_analysis.coated.transmitted_flux !== null ? ` · 透射接收：${metric(comparison.branch_analysis.coated.transmitted_flux)} W` : ""}</p>
                    <p>计入未接收损失后的功率残差：{metric(comparison.branch_analysis.coated.ledger.accounted_residual, 8)} W</p>
                    {artifactMap.branch_system ? <ResultImage artifactKey="branch_system" path={artifactMap.branch_system} /> : null}
                  </div>
                </details> : null}
                {showEnergy && !comparison.branch_analysis ? <Card className="rounded-md border shadow-none">
                  <details>
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-3 text-sm font-medium">
                      <span className="flex items-center gap-2"><Activity className="size-4 text-primary" />能量传递</span>
                      <span className="flex items-center gap-2 text-xs font-normal text-muted-foreground"><span>系统通光量 · 光线强度</span><ChevronDown className="size-4" /></span>
                    </summary>
                    <div className="space-y-3 border-t p-3">
                      <p className="text-xs leading-5 text-muted-foreground">比较裸表面与当前膜系从入射到接收面的能量变化。</p>
                      <div className="grid gap-2 sm:grid-cols-3">
                        <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">裸表面 Throughput</p><p className="mt-1 font-semibold">{metric(comparison.metrics?.bare_relative_throughput)}</p></div>
                        <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">当前镀膜 Throughput</p><p className="mt-1 font-semibold">{metric(comparison.metrics?.coated_relative_throughput)}</p></div>
                        <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">通光量变化</p><p className="mt-1 font-semibold">{metric(comparison.metrics?.throughput_gain)}</p></div>
                      </div>
                      {artifactMap.energy_system ? <ResultImage artifactKey="energy_system" path={artifactMap.energy_system} /> : <p className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">当前结果尚未生成能量传递图。</p>}
                    </div>
                  </details>
                </Card> : null}

                {showDetector && !comparison.branch_analysis ? <Card className="rounded-md border shadow-none">
                  <details>
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-3 text-sm font-medium">
                      <span className="flex items-center gap-2"><Gauge className="size-4 text-primary" />探测器结果</span>
                      <span className="flex items-center gap-2 text-xs font-normal text-muted-foreground"><span>像面辐照度</span><ChevronDown className="size-4" /></span>
                    </summary>
                    <div className="space-y-3 border-t p-3">
                      <p className="text-xs leading-5 text-muted-foreground">基于 Optiland 像面光线坐标和真实光线权重形成相对辐照度图。当前单位为相对量，不冒充 NSQ 探测器的绝对 W/mm²。</p>
                      <div className="grid gap-2 sm:grid-cols-3">
                        <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">裸表面接收能量</p><p className="mt-1 font-semibold">{metric(comparison.metrics?.bare_detector_relative_energy)}</p></div>
                        <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">当前镀膜接收能量</p><p className="mt-1 font-semibold">{metric(comparison.metrics?.coated_detector_relative_energy)}</p></div>
                        <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">峰值相对辐照度</p><p className="mt-1 font-semibold">{metric(comparison.metrics?.coated_detector_peak_relative_irradiance)}</p></div>
                      </div>
                      {artifactMap.detector_system ? <ResultImage artifactKey="detector_system" path={artifactMap.detector_system} /> : <p className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">当前结果尚未生成探测器图。</p>}
                    </div>
                  </details>
                </Card> : null}

                {showGhost ? <Card className="rounded-md border shadow-none">
                  <details>
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-3 text-sm font-medium">
                      <span className="flex items-center gap-2"><Ghost className="size-4 text-primary" />鬼像与杂散光</span>
                      <span className="flex items-center gap-2 text-xs font-normal text-muted-foreground"><span>{comparison.analysis_groups?.ghost_stray?.ready ? "结果可用" : "待接入 NSQ"}</span><ChevronDown className="size-4" /></span>
                    </summary>
                    <div className="space-y-3 border-t p-3">
                      {comparison.analysis_groups?.ghost_stray?.ready ? <>
                        <p className="text-xs leading-5 text-muted-foreground">使用当前已调焦镜头的逐面几何和材料，按实际反射事件区分直接光与鬼像。</p>
                        <div className="grid gap-2 sm:grid-cols-3">
                          <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">裸表面鬼像功率</p><p className="mt-1 font-semibold">{metric((comparison.metrics?.bare_ghost_power_fraction ?? NaN) * 100, 4)}%</p></div>
                          <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">当前镀膜鬼像功率</p><p className="mt-1 font-semibold">{metric((comparison.metrics?.coated_ghost_power_fraction ?? NaN) * 100, 4)}%</p></div>
                          <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">{(comparison.metrics?.ghost_suppression_ratio ?? 0) >= 0 ? "鬼像抑制率" : "鬼像增加率"}</p><p className="mt-1 font-semibold">{metric(Math.abs(comparison.metrics?.ghost_suppression_ratio ?? NaN) * 100, 2)}%</p></div>
                        </div>
                        {artifactMap.ghost_stray_system ? <ResultImage artifactKey="ghost_stray_system" path={artifactMap.ghost_stray_system} /> : null}
                        <p className="rounded-md bg-muted/30 p-2 text-[11px] leading-5 text-muted-foreground">{comparison.ghost_stray?.model_scope} 采样 {comparison.ghost_stray?.coated?.ray_count} 条光线；鬼像功率标准误差 {metric(comparison.ghost_stray?.coated?.ghost_flux_standard_error, 7)} W。</p>
                      </> : <p className="text-xs leading-5 text-muted-foreground">当前系统暂不适用经过验证的 NSQ 场景，因此不显示推测性鬼像功率。</p>}
                    </div>
                  </details>
                </Card> : null}

                {showSpectrum && !comparison.branch_analysis ? <Card className="rounded-md border shadow-none">
                  <details>
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-3 text-sm font-medium">
                      <span className="flex items-center gap-2"><Palette className="size-4 text-primary" />光谱与颜色</span>
                      <span className="flex items-center gap-2 text-xs font-normal text-muted-foreground"><span>{comparison.analysis_groups?.spectrum_color?.ready ? "结果可用" : "待接入光谱探测器"}</span><ChevronDown className="size-4" /></span>
                    </summary>
                    <div className="space-y-3 border-t p-3">
                      {comparison.analysis_groups?.spectrum_color?.ready ? <>
                        <p className="text-xs leading-5 text-muted-foreground">当前膜系 T(λ) 输入 Optiland 光谱探测器完成波长分箱，再由 Optiland 色度模块计算 CIE 1931、xyY 与 sRGB。</p>
                        <div className="grid gap-2 sm:grid-cols-3">
                          <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">裸表面光谱通量</p><p className="mt-1 font-semibold">{metric(comparison.metrics?.bare_spectral_detector_flux)}</p></div>
                          <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">当前镀膜光谱通量</p><p className="mt-1 font-semibold">{metric(comparison.metrics?.coated_spectral_detector_flux)}</p></div>
                          <div className="rounded-md border p-2.5"><p className="text-[11px] text-muted-foreground">光谱通量增益</p><p className="mt-1 font-semibold">{metric(comparison.metrics?.spectral_detector_gain)}</p></div>
                        </div>
                        {artifactMap.spectrum_color_system ? <ResultImage artifactKey="spectrum_color_system" path={artifactMap.spectrum_color_system} /> : null}
                        <p className="rounded-md bg-muted/30 p-2 text-[11px] leading-5 text-muted-foreground">光谱探测器能量守恒误差 {metric(comparison.metrics?.spectral_flux_conservation_error, 8)}；{comparison.spectrum_color?.color_available === false ? comparison.spectrum_color.color_unavailable_reason : "颜色结果采用 CIE 1931 2° 标准观察者与 D65 光源。"}</p>
                      </> : <p className="text-xs leading-5 text-muted-foreground">当前系统暂不具备有效光谱覆盖，因此不生成 CIE 或 sRGB 结果。</p>}
                    </div>
                  </details>
                </Card> : null}

                {secondaryArtifacts.length ? <Card className="rounded-md border shadow-none">
                  <details>
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-3 text-sm font-medium">
                      <span>高级系统分析</span>
                      <span className="flex items-center gap-2 text-xs font-normal text-muted-foreground"><span>Spot · PSF · MTF</span><ChevronDown className="size-4" /></span>
                    </summary>
                    <div className="grid gap-3 border-t p-3">
                      <p className="rounded-md bg-muted/30 p-2.5 text-xs leading-5 text-muted-foreground">用于区分能量性能与成像像质：镀膜可能显著提高 Throughput，同时归一化 PSF / MTF 基本不变。</p>
                      {secondaryArtifacts.map(([key, path]) => <div key={key} className="space-y-2"><p className="text-xs leading-5 text-muted-foreground">{ARTIFACT_GUIDANCE[key]}</p><ResultImage artifactKey={key} path={path} /></div>)}
                    </div>
                  </details>
                </Card> : null}
              </div>
            </>
          )}
        </CardContent> : null}
    </Card>
  );
}
