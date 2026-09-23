import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Beaker, BookOpen, CheckCircle2, FlaskConical, Layers3, Loader2, Menu, RotateCcw, Sparkles, Wrench } from "lucide-react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

import { listMaterials, simulateDesign } from "@/api/thinfilmClient";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LayerEditor } from "@/components/design/LayerEditor";
import { ExperimentRecords } from "@/components/design/ExperimentRecords";
import { ExperimentTaskPanel } from "@/components/design/ExperimentTaskPanel";
import { cloneDesign, EXPERIMENT_TASKS } from "@/components/design/experimentTasks";
import { SpectralMetricsPanel } from "@/components/design/SpectralMetricsPanel";
import { PhysicsInsightPanel } from "@/components/design/PhysicsInsightPanel";
import { PowerSpectrumControls, formatPowerTick, powerAxisDomain, type PowerQuantity } from "@/components/design/PowerSpectrumControls";
import { OptilandPanel } from "@/components/optiland/OptilandPanel";
import { LayerStructure3D } from "@/components/three/LayerStructure3D";
import type { DesignDraft, DesignSimulationResult, ExperimentRecord, MaterialOption } from "@/types/design";

const AskResultPanel = lazy(() => import("@/components/design/AskResultPanel").then((module) => ({ default: module.AskResultPanel })));

const INITIAL_DESIGN: DesignDraft = {
  schema_version: "1.0",
  solver: "tmmcore",
  incident_material_id: "Air",
  substrate_material_id: "N-BK7",
  layers: [
    { id: "layer-1", material_id: "MgF2", thickness_nm: 99.6, enabled: true },
    { id: "layer-2", material_id: "TiO2", thickness_nm: 62, enabled: true },
  ],
  spectrum: { start_nm: 450, stop_nm: 800, points: 351 },
  angle_deg: 0,
  polarization: "p",
  out_of_range_policy: "error",
  probe_wavelength_nm: 550,
  experiment_task_id: "single-layer-ar",
};

interface DesignWorkbenchProps {
  onOpenCases: () => void;
  initialDraft?: DesignDraft;
}

const RECORDS_STORAGE_KEY = "pythinfilm-v1-experiment-records";
const DESIGNS_STORAGE_KEY = "pythinfilm-v1-saved-designs";
const COMPARISON_COLORS = ["#a855f7", "#ec4899", "#84cc16"];

interface SavedDesign {
  id: string;
  name: string;
  saved_at: string;
  draft: DesignDraft;
}

function loadRecords(): ExperimentRecord[] {
  try {
    const raw = window.localStorage.getItem(RECORDS_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ExperimentRecord[]).slice(0, 8) : [];
  } catch {
    return [];
  }
}

function loadSavedDesigns(): SavedDesign[] {
  try {
    const raw = window.localStorage.getItem(DESIGNS_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SavedDesign[]).slice(0, 20) : [];
  } catch {
    return [];
  }
}

function format(value: number, digits = 4) {
  return Number.isFinite(value) ? value.toLocaleString("zh-CN", { maximumFractionDigits: digits }) : "—";
}

export function DesignWorkbench({ onOpenCases, initialDraft }: DesignWorkbenchProps) {
  const [draft, setDraft] = useState<DesignDraft>(INITIAL_DESIGN);
  const [materials, setMaterials] = useState<MaterialOption[]>([]);
  const [result, setResult] = useState<DesignSimulationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState(EXPERIMENT_TASKS[0].id);
  const [completedSteps, setCompletedSteps] = useState<boolean[]>(() => EXPERIMENT_TASKS[0].steps.map(() => false));
  const [prediction, setPrediction] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [records, setRecords] = useState<ExperimentRecord[]>(loadRecords);
  const [savedDesigns, setSavedDesigns] = useState<SavedDesign[]>(loadSavedDesigns);
  const [designName, setDesignName] = useState("");
  const [selectedDesignId, setSelectedDesignId] = useState("");
  const [viewMode, setViewMode] = useState<"engineering" | "teaching">("engineering");
  const [analysisTab, setAnalysisTab] = useState("overview");
  const [showAskResult, setShowAskResult] = useState(false);
  const [powerQuantity, setPowerQuantity] = useState<PowerQuantity>("R");
  const [inspectedMaterialId, setInspectedMaterialId] = useState("MgF2");
  const [showProjectSidebar, setShowProjectSidebar] = useState(false);
  const [showStackSidebar, setShowStackSidebar] = useState(true);
  const [workbenchWidth, setWorkbenchWidth] = useState(1000);
  const workbenchRef = useRef<HTMLElement>(null);
  const [selectedRecordIds, setSelectedRecordIds] = useState<string[]>([]);
  const [comparisonQuantity, setComparisonQuantity] = useState<"R" | "T" | "A">("R");
  const [recordName, setRecordName] = useState("");
  const sequence = useRef(0);
  const panelWidth = Math.max(workbenchWidth, 1000);
  const projectMinSize = Math.max(18, 280 / panelWidth * 100);
  const stackMinSize = Math.max(24, 340 / panelWidth * 100);
  const selectedTask = EXPERIMENT_TASKS.find((task) => task.id === selectedTaskId) ?? EXPERIMENT_TASKS[0];
  const resultMatchesDraft = Boolean(result &&
    result.design.incident_material_id === draft.incident_material_id &&
    result.design.substrate_material_id === draft.substrate_material_id &&
    result.design.angle_deg === draft.angle_deg &&
    result.design.polarization === draft.polarization &&
    result.design.spectrum.start_nm === draft.spectrum.start_nm &&
    result.design.spectrum.stop_nm === draft.spectrum.stop_nm &&
    result.design.spectrum.points === draft.spectrum.points &&
    result.design.layers.length === draft.layers.length &&
    result.design.layers.every((layer, index) => layer.id === draft.layers[index]?.id && layer.material_id === draft.layers[index]?.material_id && layer.thickness_nm === draft.layers[index]?.thickness_nm && layer.enabled === draft.layers[index]?.enabled));
  const inspectedMaterial = materials.find((item) => item.material_id === inspectedMaterialId) ?? materials[0];
  const usedMaterialIds = useMemo(
    () => new Set([draft.incident_material_id, draft.substrate_material_id, ...draft.layers.filter((layer) => layer.enabled).map((layer) => layer.material_id)]),
    [draft],
  );
  const rangeWarnings = useMemo(
    () => materials.filter((material) => usedMaterialIds.has(material.material_id) && (draft.spectrum.start_nm < material.lambda_min_nm || draft.spectrum.stop_nm > material.lambda_max_nm)),
    [draft.spectrum.start_nm, draft.spectrum.stop_nm, materials, usedMaterialIds],
  );

  useEffect(() => {
    const element = workbenchRef.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setWorkbenchWidth(element.clientWidth));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    listMaterials(controller.signal)
      .then(setMaterials)
      .catch((cause) => {
        if (!(cause instanceof DOMException && cause.name === "AbortError")) {
          setError(cause instanceof Error ? cause.message : "材料目录加载失败");
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!initialDraft) return;
    setDraft(cloneDesign(initialDraft));
    setResult(null);
    setError(null);
    setAnalysisTab("overview");
    setPowerQuantity(/spectral|filter|wdm|sensor_prefilter/.test(initialDraft.system_template ?? "") ? "T" : "R");
    setPrediction("");
    setConclusion("");
  }, [initialDraft]);

  useEffect(() => {
    if (materials.length === 0) return;
    const current = ++sequence.current;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      simulateDesign(draft, `design-${current}`, controller.signal)
        .then((data) => {
          if (current === sequence.current) setResult(data);
        })
        .catch((cause) => {
          if (current === sequence.current && !(cause instanceof DOMException && cause.name === "AbortError")) {
            setResult(null);
            setError(cause instanceof Error ? cause.message : "自由膜系仿真失败");
          }
        })
        .finally(() => {
          if (current === sequence.current) setLoading(false);
        });
    }, 350);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [draft, materials.length]);

  useEffect(() => {
    try {
      window.localStorage.setItem(RECORDS_STORAGE_KEY, JSON.stringify(records));
    } catch {
      setError("实验记录无法写入本机存储，请删除部分历史记录后重试。");
    }
  }, [records]);

  useEffect(() => {
    try {
      window.localStorage.setItem(DESIGNS_STORAGE_KEY, JSON.stringify(savedDesigns));
    } catch {
      setError("设计无法写入本机存储，请删除部分旧设计后重试。");
    }
  }, [savedDesigns]);

  const selectedRecords = useMemo(
    () => selectedRecordIds.map((id) => records.find((record) => record.id === id)).filter((record): record is ExperimentRecord => Boolean(record)),
    [records, selectedRecordIds],
  );

  const chartRows = useMemo(
    () => {
      const rows = new Map<string, Record<string, number>>();
      const add = (wavelength: number, values: Record<string, number>) => {
        const key = wavelength.toFixed(6);
        rows.set(key, { ...(rows.get(key) ?? { wavelength_nm: wavelength }), ...values });
      };
      result?.series.wavelength_nm.forEach((wavelength, index) => add(wavelength, { R: result.series.R[index], T: result.series.T[index], A: result.series.A[index] }));
      selectedRecords.forEach((record) => record.result.series.wavelength_nm.forEach((wavelength, index) => add(wavelength, { [`history_${record.id}`]: record.result.series[comparisonQuantity][index] })));
      return [...rows.values()].sort((left, right) => left.wavelength_nm - right.wavelength_nm);
    },
    [comparisonQuantity, result, selectedRecords],
  );
  const showHistory = powerQuantity === "all" || powerQuantity === comparisonQuantity;
  const powerDomain = powerQuantity === "all" ? [0, 1] as [number, number] : powerAxisDomain([
    ...chartRows.map((row) => row[powerQuantity]).filter((value): value is number => typeof value === "number"),
    ...(showHistory ? selectedRecords.flatMap((record) => record.result.series[comparisonQuantity]) : []),
  ]);

  const patchDraft = (value: Partial<DesignDraft>) => setDraft((current) => ({ ...current, ...value }));

  function selectTask(taskId: string) {
    const task = EXPERIMENT_TASKS.find((item) => item.id === taskId);
    if (!task) return;
    setSelectedTaskId(taskId);
    setCompletedSteps(task.steps.map(() => false));
    setPrediction("");
    setConclusion("");
    setSelectedRecordIds([]);
    setDraft((current) => ({ ...current, experiment_task_id: taskId }));
  }

  function loadTaskDesign() {
    setDraft(cloneDesign(selectedTask.starterDesign));
    setResult(null);
  }

  function saveCurrentResult() {
    if (!result) return;
    const id = `record-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const record: ExperimentRecord = {
      id,
      name: recordName.trim() || `实验记录 ${records.length + 1}`,
      created_at: new Date().toISOString(),
      task_id: selectedTaskId,
      prediction,
      conclusion,
      draft: cloneDesign(draft),
      result: JSON.parse(JSON.stringify(result)) as DesignSimulationResult,
    };
    setRecords((current) => [record, ...current].slice(0, 8));
    setRecordName("");
  }

  function saveDesign() {
    const name = designName.trim() || `膜系设计 ${savedDesigns.length + 1}`;
    const entry: SavedDesign = {
      id: `design-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      name,
      saved_at: new Date().toISOString(),
      draft: cloneDesign(draft),
    };
    setSavedDesigns((current) => [entry, ...current].slice(0, 20));
    setSelectedDesignId(entry.id);
    setDesignName("");
  }

  function loadDesign(id: string) {
    const entry = savedDesigns.find((item) => item.id === id);
    if (!entry) return;
    setDraft(cloneDesign(entry.draft));
    setSelectedDesignId(id);
  }

  function deleteDesign() {
    if (!selectedDesignId) return;
    setSavedDesigns((current) => current.filter((item) => item.id !== selectedDesignId));
    setSelectedDesignId("");
  }

  function toggleComparison(id: string) {
    setSelectedRecordIds((current) => {
      if (current.includes(id)) return current.filter((item) => item !== id);
      return current.length >= 3 ? current : [...current, id];
    });
  }

  function restoreRecord(record: ExperimentRecord) {
    const restored = cloneDesign(record.draft);
    setDraft({
      ...restored,
      experiment_task_id: record.task_id,
      probe_wavelength_nm: restored.probe_wavelength_nm ?? (restored.spectrum.start_nm + restored.spectrum.stop_nm) / 2,
    });
    setSelectedTaskId(record.task_id);
    const task = EXPERIMENT_TASKS.find((item) => item.id === record.task_id) ?? EXPERIMENT_TASKS[0];
    setCompletedSteps(task.steps.map(() => false));
    setPrediction(record.prediction);
    setConclusion(record.conclusion);
  }

  return (
    <main ref={workbenchRef} className="relative flex h-screen min-h-0 flex-col bg-muted/30 text-foreground">
      <header className="flex min-h-16 shrink-0 items-center justify-between gap-4 border-b bg-card/95 px-5 py-2 backdrop-blur">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground"><FlaskConical className="size-5" /></div>
          <div>
            <h1 className="truncate text-lg font-semibold tracking-tight">PythonFilm</h1>
            <p className="text-xs text-muted-foreground">项目建模 · 材料管理 · 膜系编辑 · 结果分析</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button className="whitespace-nowrap px-2 text-xs" variant={showProjectSidebar ? "secondary" : "ghost"} size="sm" aria-pressed={showProjectSidebar} onClick={() => setShowProjectSidebar((value) => !value)}><Menu />项目侧栏</Button>
          <Button className="whitespace-nowrap px-2 text-xs" variant={showStackSidebar ? "secondary" : "ghost"} size="sm" aria-pressed={showStackSidebar} onClick={() => setShowStackSidebar((value) => !value)}><Layers3 />膜系侧栏</Button>
          <div className="flex rounded-md border bg-background p-0.5">
            <Button className="whitespace-nowrap px-2 text-xs" variant={viewMode === "engineering" ? "default" : "ghost"} size="sm" onClick={() => { setViewMode("engineering"); setAnalysisTab("overview"); }}><Wrench />工程视图</Button>
            <Button className="whitespace-nowrap px-2 text-xs" variant={viewMode === "teaching" ? "default" : "ghost"} size="sm" onClick={() => { setViewMode("teaching"); setAnalysisTab("overview"); }}><BookOpen />教学视图</Button>
          </div>
          <Input aria-label="设计名称" placeholder="设计名称" value={designName} onChange={(event) => setDesignName(event.target.value)} className="hidden w-32 lg:block" />
          <Button className="whitespace-nowrap px-2 text-xs" variant="outline" size="sm" onClick={saveDesign}>保存设计</Button>
          <Select aria-label="加载本地设计" value={selectedDesignId} onChange={(event) => loadDesign(event.target.value)} className="hidden max-w-40 lg:block">
            <option value="">加载设计…</option>
            {savedDesigns.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </Select>
          <Button className="whitespace-nowrap px-2 text-xs" variant="ghost" size="sm" disabled={!selectedDesignId} onClick={deleteDesign}>删除</Button>
          <Button className="whitespace-nowrap px-2 text-xs" variant="outline" size="sm" onClick={() => setDraft(INITIAL_DESIGN)}><RotateCcw />重置</Button>
          <Button className="whitespace-nowrap px-2 text-xs" variant="outline" size="sm" onClick={onOpenCases}><Beaker />教学案例库</Button>
        </div>
      </header>

      <div className="grid shrink-0 grid-cols-4 border-b bg-background text-xs">
        {[
          ["01", "结构", `${draft.layers.filter((item) => item.enabled).length} 层`],
          ["02", "计算", loading ? "进行中" : error ? "需修正" : "已完成"],
          ["03", "分析", result ? "可查看" : "等待结果"],
          ["04", "结论", conclusion.trim() ? "已记录" : "待记录"],
        ].map(([step, label, status]) => <div key={step} className="flex items-center gap-2 border-r px-4 py-2 last:border-r-0"><span className="font-semibold text-primary">{step}</span><span className="font-medium">{label}</span><span className="truncate text-muted-foreground">{status}</span></div>)}
      </div>

      <PanelGroup direction="horizontal" className="min-h-0 min-w-[1000px] flex-1">
        {showProjectSidebar ? <><Panel id="project-panel" order={1} defaultSize={Math.max(24, projectMinSize)} minSize={projectMinSize} maxSize={34} className="min-w-[280px] bg-background">
          <ScrollArea className="h-full border-r bg-card/45">
            <section className="flex flex-col gap-4 p-4">
              <div><h2 className="text-sm font-semibold">项目与材料</h2><p className="text-xs text-muted-foreground">定义任务、边界介质和材料数据</p></div>
              {viewMode === "teaching" ? <ExperimentTaskPanel
                tasks={EXPERIMENT_TASKS}
                task={selectedTask}
                completedSteps={completedSteps}
                prediction={prediction}
                conclusion={conclusion}
                onSelect={selectTask}
                onLoad={loadTaskDesign}
                onToggleStep={(index) => setCompletedSteps((current) => current.map((value, itemIndex) => itemIndex === index ? !value : value))}
                onPredictionChange={setPrediction}
                onConclusionChange={setConclusion}
              /> : null}
              <Card className="rounded-md shadow-none">
                <CardHeader className="p-3 pb-2"><CardTitle className="text-sm">边界介质</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-2 gap-3 p-3 pt-0">
                  <div className="space-y-1.5"><Label>入射介质</Label><Select value={draft.incident_material_id} onChange={(e) => patchDraft({ incident_material_id: e.target.value })}>{materials.map((item) => <option key={item.material_id} value={item.material_id}>{item.display_name_zh}</option>)}</Select></div>
                  <div className="space-y-1.5"><Label>基底</Label><Select value={draft.substrate_material_id} onChange={(e) => patchDraft({ substrate_material_id: e.target.value })}>{materials.map((item) => <option key={item.material_id} value={item.material_id}>{item.display_name_zh}</option>)}</Select></div>
                </CardContent>
              </Card>

              <Card className="rounded-md shadow-none">
                <CardHeader className="p-3 pb-2"><CardTitle className="text-sm">材料检查器</CardTitle></CardHeader>
                <CardContent className="space-y-3 p-3 pt-0">
                  <Select value={inspectedMaterial?.material_id ?? ""} onChange={(event) => setInspectedMaterialId(event.target.value)}>{materials.map((item) => <option key={item.material_id} value={item.material_id}>{item.display_name_zh}</option>)}</Select>
                  {inspectedMaterial ? <details className="rounded-md border bg-muted/20 p-2 text-xs"><summary className="cursor-pointer font-medium">查看材料属性</summary><div className="mt-3 grid grid-cols-2 gap-2"><span className="text-muted-foreground">类别</span><span>{inspectedMaterial.category}</span><span className="text-muted-foreground">n(550 nm)</span><span>{format(inspectedMaterial.n_at_550nm, 4)}</span><span className="text-muted-foreground">k(550 nm)</span><span>{format(inspectedMaterial.k_at_550nm, 4)}</span><span className="text-muted-foreground">有效范围</span><span>{format(inspectedMaterial.lambda_min_nm, 0)}–{format(inspectedMaterial.lambda_max_nm, 0)} nm</span><span className="text-muted-foreground">数据来源</span><span>Real n,k</span></div></details> : null}
                </CardContent>
              </Card>

              <Card className="rounded-md shadow-none">
                <CardHeader className="p-3 pb-2"><CardTitle className="text-sm">扫描条件</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-2 gap-3 p-3 pt-0">
                  <div className="space-y-1.5"><Label>起始波长 / nm</Label><Input type="number" value={draft.spectrum.start_nm} onChange={(e) => patchDraft({ spectrum: { ...draft.spectrum, start_nm: Number(e.target.value) } })} /></div>
                  <div className="space-y-1.5"><Label>终止波长 / nm</Label><Input type="number" value={draft.spectrum.stop_nm} onChange={(e) => patchDraft({ spectrum: { ...draft.spectrum, stop_nm: Number(e.target.value) } })} /></div>
                  <div className="space-y-1.5"><Label>采样点</Label><Input type="number" min={2} max={5000} value={draft.spectrum.points} onChange={(e) => patchDraft({ spectrum: { ...draft.spectrum, points: Number(e.target.value) } })} /></div>
                  <div className="space-y-1.5"><Label>入射角 / °</Label><Input type="number" min={0} max={89.9} value={draft.angle_deg} onChange={(e) => patchDraft({ angle_deg: Number(e.target.value) })} /></div>
                  <div className="space-y-1.5"><Label>场探针波长 / nm</Label><Input type="number" min={draft.spectrum.start_nm} max={draft.spectrum.stop_nm} value={draft.probe_wavelength_nm ?? (draft.spectrum.start_nm + draft.spectrum.stop_nm) / 2} onChange={(e) => patchDraft({ probe_wavelength_nm: Number(e.target.value) })} /></div>
                  <div className="space-y-1.5"><Label>偏振</Label><Select value={draft.polarization} onChange={(e) => patchDraft({ polarization: e.target.value as "s" | "p" })}><option value="p">p 偏振</option><option value="s">s 偏振</option></Select></div>
                  <div className="space-y-1.5"><Label>越界策略</Label><Select value={draft.out_of_range_policy} onChange={(e) => patchDraft({ out_of_range_policy: e.target.value as "error" | "clip" })}><option value="error">阻止计算</option><option value="clip">边界裁剪</option></Select></div>
                </CardContent>
              </Card>
              {rangeWarnings.map((material) => <div key={material.material_id} className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300">{material.display_name_zh} 数据范围为 {format(material.lambda_min_nm, 0)}–{format(material.lambda_max_nm, 0)} nm，当前扫描范围已越界。</div>)}
            </section>
          </ScrollArea>
        </Panel>
        <PanelResizeHandle id="project-resize-handle" className="resize-handle" /></> : null}
        {showStackSidebar ? <><Panel id="stack-panel" order={2} defaultSize={Math.max(32, stackMinSize)} minSize={stackMinSize} className="min-w-[340px] bg-background">
          <ScrollArea className="h-full border-r bg-card/30">
            <section className="flex flex-col gap-4 p-4">
              <div><h2 className="text-sm font-semibold">膜系建模</h2><p className="text-xs text-muted-foreground">按入射方向编辑层序并检查三维结构</p></div>
              <Card className="rounded-md shadow-none">
                <CardHeader className="flex flex-row items-center justify-between p-3 pb-2"><CardTitle className="text-sm">膜系编辑</CardTitle><span className="text-xs text-muted-foreground">{draft.layers.filter((item) => item.enabled).length} 层启用</span></CardHeader>
                <CardContent className="p-3 pt-0"><LayerEditor layers={draft.layers} materials={materials} onChange={(layers) => patchDraft({ layers })} /></CardContent>
              </Card>
              <Card className="overflow-hidden rounded-md bg-[#09131f] shadow-sm">
                <div className="flex items-center justify-between border-b border-white/10 px-4 py-3 text-white"><span className="text-sm font-medium">三维膜层结构</span><span className="text-[10px] text-slate-400">左键旋转 · 右键平移 · 滚轮缩放</span></div>
                <LayerStructure3D layers={draft.layers} materials={materials} className="h-[360px] w-full" />
              </Card>
            </section>
          </ScrollArea>
        </Panel>
        <PanelResizeHandle id="stack-resize-handle" className="resize-handle" /></> : null}
        <Panel id="analysis-panel" order={3} minSize={34}>
          <ScrollArea className="h-full">
            <section className="flex flex-col gap-4 p-5">
              <div className="flex items-center justify-between gap-3"><div><h2 className="text-sm font-semibold">分析结果</h2><p className="text-xs text-muted-foreground">光谱、性能指标与物理解释</p></div><Button type="button" size="sm" variant="outline" aria-label="问问本次结果" onClick={() => setShowAskResult(true)}><Sparkles className="size-4" />问问本次结果</Button></div>
              <OptilandPanel draft={draft} />
              <div className="flex items-center justify-between rounded-md border bg-card px-4 py-3 shadow-sm">
                <div><h2 className="font-semibold">设计响应</h2></div>
                <div className="flex items-center gap-2 text-xs">
                  {loading ? <><Loader2 className="size-4 animate-spin text-primary" />计算中</> : error ? <><AlertCircle className="size-4 text-destructive" />需要修正</> : <><CheckCircle2 className="size-4 text-emerald-600" />已同步</>}
                </div>
              </div>

              {error ? <div className="flex gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"><AlertCircle className="mt-0.5 size-4 shrink-0" /><span>{error}</span></div> : null}
              {result?.warnings.map((warning) => <div key={warning} className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300">{warning}</div>)}

              <Tabs value={analysisTab} onValueChange={setAnalysisTab}>
                <TabsList className="w-full justify-start rounded-md">
                  <TabsTrigger value="overview">{viewMode === "teaching" ? "① 结果概览" : "概览"}</TabsTrigger>
                  <TabsTrigger value="spectrum">{viewMode === "teaching" ? "② 观察光谱" : "光谱"}</TabsTrigger>
                  <TabsTrigger value="physics">{viewMode === "teaching" ? "③ 解释规律" : "相位与场"}</TabsTrigger>
                  {viewMode === "teaching" ? <TabsTrigger value="experiment">④ 实验记录</TabsTrigger> : null}
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Card className="rounded-md"><CardContent className="p-4"><p className="text-xs text-muted-foreground">总厚度</p><p className="mt-1 text-xl font-semibold">{format(result?.summary.total_thickness_nm ?? NaN, 2)} <span className="text-xs font-normal text-muted-foreground">nm</span></p></CardContent></Card>
                    <Card className="rounded-md"><CardContent className="p-4"><p className="text-xs text-muted-foreground">平均反射率</p><p className="mt-1 text-xl font-semibold">{format((result?.summary.mean_R ?? NaN) * 100, 2)} <span className="text-xs font-normal text-muted-foreground">%</span></p></CardContent></Card>
                    <Card className="rounded-md"><CardContent className="p-4"><p className="text-xs text-muted-foreground">能量残差</p><p className="mt-1 text-xl font-semibold">{format(result?.summary.max_energy_residue ?? NaN, 8)}</p></CardContent></Card>
                  </div>
                  <SpectralMetricsPanel result={result} />
                </TabsContent>

                <TabsContent value="spectrum">
                  <Card className="rounded-md shadow-sm">
                    <CardHeader className="p-4 pb-0"><CardTitle className="text-sm">R / T / A 光谱</CardTitle></CardHeader>
                    <CardContent className="space-y-2 p-4">
                      <PowerSpectrumControls value={powerQuantity} onChange={setPowerQuantity} values={powerQuantity === "all" ? [] : chartRows.map((row) => row[powerQuantity]).filter((value): value is number => typeof value === "number")} />
                      {selectedRecords.length > 0 && !showHistory ? <p className="text-[11px] text-muted-foreground">历史记录当前对比 {comparisonQuantity}；切换到相同观察量或总览后显示。</p> : null}
                      <div className="h-[440px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={chartRows} margin={{ top: 8, right: 20, bottom: 30, left: 8 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                            <XAxis dataKey="wavelength_nm" type="number" domain={["dataMin", "dataMax"]} height={50} label={{ value: "波长 (nm)", position: "insideBottom", offset: -8 }} />
                            <YAxis domain={powerDomain} width={68} tickFormatter={(value) => formatPowerTick(Number(value), powerDomain)} label={{ value: "功率比例", angle: -90, position: "insideLeft" }} />
                            <Tooltip formatter={(value, name) => [`${(Number(value) * 100).toFixed(3)}%`, String(name)]} labelFormatter={(value) => `${format(Number(value), 2)} nm`} />
                            <Legend verticalAlign="top" align="center" height={44} wrapperStyle={{ lineHeight: "20px", paddingBottom: 8 }} />
                            {(powerQuantity === "all" || powerQuantity === "R") && <Line type="monotone" dataKey="R" name="反射 R" stroke="#0f766e" strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />}
                            {(powerQuantity === "all" || powerQuantity === "T") && <Line type="monotone" dataKey="T" name="透射 T" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />}
                            {(powerQuantity === "all" || powerQuantity === "A") && <Line type="monotone" dataKey="A" name="吸收 A" stroke="#d97706" strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />}
                            {showHistory && selectedRecords.map((record, index) => <Line key={record.id} type="monotone" dataKey={`history_${record.id}`} name={`${record.name} ${comparisonQuantity}`} stroke={COMPARISON_COLORS[index]} strokeWidth={1.8} strokeDasharray="6 4" dot={false} connectNulls isAnimationActive={false} />)}
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="physics">
                  <PhysicsInsightPanel result={result} processProgress={Math.round(100 * completedSteps.filter(Boolean).length / selectedTask.steps.length)} hasPrediction={Boolean(prediction.trim())} hasConclusion={Boolean(conclusion.trim())} />
                </TabsContent>

                {viewMode === "teaching" ? <TabsContent value="experiment"><ExperimentRecords records={records} selectedIds={selectedRecordIds} recordName={recordName} quantity={comparisonQuantity} canSave={Boolean(result) && !loading} onRecordNameChange={setRecordName} onSave={saveCurrentResult} onToggleCompare={toggleComparison} onRestore={restoreRecord} onDelete={(id) => { setRecords((current) => current.filter((record) => record.id !== id)); setSelectedRecordIds((current) => current.filter((item) => item !== id)); }} onQuantityChange={setComparisonQuantity} /></TabsContent> : null}
              </Tabs>
            </section>
          </ScrollArea>
        </Panel>
      </PanelGroup>
      {showAskResult ? <Suspense fallback={<div className="absolute inset-y-0 right-0 z-30 w-full max-w-[560px] border-l bg-background p-5 text-sm text-muted-foreground">正在打开问答…</div>}><AskResultPanel draft={draft} result={result} ready={Boolean(resultMatchesDraft && !loading && !error)} onClose={() => setShowAskResult(false)} /></Suspense> : null}
    </main>
  );
}
