import { CheckCircle2, CircleAlert, Gauge, Waves } from "lucide-react";
import { useState } from "react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { DesignSimulationResult } from "@/types/design";

interface PhysicsInsightPanelProps {
  result: DesignSimulationResult | null;
  processProgress: number;
  hasPrediction: boolean;
  hasConclusion: boolean;
}

const BAND_COLORS = ["#0f766e", "#2563eb", "#7c3aed", "#d97706"];

function displayValue(value: number | null) {
  if (value == null) return "不可用";
  if (Math.abs(value) <= 1) return `${(value * 100).toFixed(2)}%`;
  return value.toFixed(2);
}

export function PhysicsInsightPanel({ result, processProgress, hasPrediction, hasConclusion }: PhysicsInsightPanelProps) {
  const [tab, setTab] = useState("field");
  const fieldRows = result?.field.z_nm.map((z_nm, index) => ({ z_nm, E2: result.field.E2[index] })) ?? [];
  const phaseRows = result?.phase.wavelength_nm.map((wavelength_nm, index) => ({
    wavelength_nm,
    reflection: result.phase.reflection_phase_deg[index],
    transmission: result.phase.transmission_phase_deg[index],
  })) ?? [];
  const evaluation = result?.evaluation;
  return (
    <Card className="rounded-md shadow-sm">
      <CardHeader className="p-4 pb-2"><CardTitle className="flex items-center gap-2 text-sm"><Waves className="size-4 text-primary" />V2 物理证据与评价</CardTitle></CardHeader>
      <CardContent className="p-4 pt-0">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="rounded-md"><TabsTrigger value="field">场分布</TabsTrigger><TabsTrigger value="phase">相位解释</TabsTrigger><TabsTrigger value="evaluation">自动评价</TabsTrigger></TabsList>
          <TabsContent value="field">
            {result ? <div className="space-y-3"><div className="flex flex-wrap gap-4 rounded-md bg-muted/40 px-3 py-2 text-xs"><span>探针：<b>{result.field.wavelength_nm.toFixed(1)} nm</b></span><span>峰值 |E|²：<b>{result.field.peak_E2.toFixed(3)}</b></span><span>位置：<b>{result.field.peak_z_nm.toFixed(2)} nm</b></span></div><div className="h-[330px]"><ResponsiveContainer width="100%" height="100%"><AreaChart data={fieldRows} margin={{ top: 8, right: 20, bottom: 26, left: 6 }}><defs><linearGradient id="fieldGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#14b8a6" stopOpacity={0.45} /><stop offset="95%" stopColor="#14b8a6" stopOpacity={0.04} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />{result.field.boundaries.map((boundary, index) => <ReferenceArea key={boundary.layer_id} x1={boundary.start_nm} x2={boundary.stop_nm} fill={BAND_COLORS[index % BAND_COLORS.length]} fillOpacity={0.08} />)}<XAxis dataKey="z_nm" type="number" domain={["dataMin", "dataMax"]} height={46} label={{ value: "位置 z (nm)", position: "insideBottom", offset: -8 }} /><YAxis width={52} label={{ value: "|E|²", angle: -90, position: "insideLeft" }} /><Tooltip formatter={(value) => [Number(value).toFixed(4), "|E|²"]} labelFormatter={(value) => `z = ${Number(value).toFixed(2)} nm`} /><Area type="monotone" dataKey="E2" stroke="#0f766e" strokeWidth={2} fill="url(#fieldGradient)" dot={false} isAnimationActive={false} /></AreaChart></ResponsiveContainer></div><div className="flex flex-wrap gap-2">{result.field.boundaries.map((boundary, index) => <span key={boundary.layer_id} className="rounded border px-2 py-1 text-[10px]" style={{ borderColor: BAND_COLORS[index % BAND_COLORS.length] }}>{index + 1}. {boundary.material_id} · {(boundary.stop_nm - boundary.start_nm).toFixed(1)} nm</span>)}</div></div> : <p className="p-6 text-center text-xs text-muted-foreground">等待有效仿真结果</p>}
          </TabsContent>
          <TabsContent value="phase">
            {result ? <div className="space-y-4"><div className="h-[300px]"><ResponsiveContainer width="100%" height="100%"><LineChart data={phaseRows} margin={{ top: 8, right: 20, bottom: 26, left: 6 }}><CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" /><XAxis dataKey="wavelength_nm" type="number" domain={["dataMin", "dataMax"]} height={46} label={{ value: "波长 (nm)", position: "insideBottom", offset: -8 }} /><YAxis domain={[-180, 180]} width={55} unit="°" /><Tooltip formatter={(value, name) => [`${Number(value).toFixed(2)}°`, name === "reflection" ? "反射相位" : "透射相位"]} labelFormatter={(value) => `${Number(value).toFixed(2)} nm`} /><ReferenceLine x={result.phase.probe.wavelength_nm} stroke="#d97706" strokeDasharray="4 3" /><Line type="monotone" dataKey="reflection" stroke="#7c3aed" strokeWidth={2} dot={false} isAnimationActive={false} /><Line type="monotone" dataKey="transmission" stroke="#2563eb" strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></div><div className="rounded-md border bg-muted/30 p-3 text-xs leading-6">{result.phase.explanations.map((text) => <p key={text}>• {text}</p>)}</div><div className="overflow-auto"><Table><TableHeader><TableRow><TableHead>层</TableHead><TableHead>材料</TableHead><TableHead>光学厚度</TableHead><TableHead>单程相位</TableHead><TableHead>往返相位</TableHead></TableRow></TableHeader><TableBody>{result.phase.layer_phase.map((layer, index) => <TableRow key={layer.layer_id}><TableCell>{index + 1}</TableCell><TableCell>{layer.material_id}</TableCell><TableCell>{layer.optical_thickness_nm.toFixed(2)} nm</TableCell><TableCell>{layer.one_way_phase_deg.toFixed(1)}°</TableCell><TableCell>{layer.round_trip_phase_deg.toFixed(1)}°</TableCell></TableRow>)}</TableBody></Table></div></div> : <p className="p-6 text-center text-xs text-muted-foreground">等待有效仿真结果</p>}
          </TabsContent>
          <TabsContent value="evaluation">
            {evaluation?.status === "available" ? <div className="space-y-4"><div className="grid gap-3 sm:grid-cols-3"><div className="rounded-md border bg-primary/5 p-4"><p className="text-xs text-muted-foreground">物理指标得分</p><p className="mt-1 text-3xl font-semibold text-primary">{evaluation.score}</p></div><div className="rounded-md border p-4"><p className="text-xs text-muted-foreground">实验步骤完成度</p><p className="mt-1 text-3xl font-semibold">{processProgress}%</p></div><div className="rounded-md border p-4"><p className="text-xs text-muted-foreground">科学表达</p><p className="mt-2 text-sm font-medium">预测 {hasPrediction ? "✓" : "○"} · 结论 {hasConclusion ? "✓" : "○"}</p></div></div><div className="space-y-2">{evaluation.criteria.map((criterion) => <div key={criterion.label} className="flex items-center gap-3 rounded-md border px-3 py-2">{criterion.passed ? <CheckCircle2 className="size-4 shrink-0 text-emerald-600" /> : <CircleAlert className="size-4 shrink-0 text-amber-500" />}<div className="min-w-0 flex-1"><p className="text-xs font-medium">{criterion.label}</p><p className="text-[10px] text-muted-foreground">目标：{criterion.target}</p></div><span className="text-sm font-semibold">{displayValue(criterion.value)}</span></div>)}</div><div className="flex gap-2 rounded-md bg-muted/50 p-3 text-xs leading-5"><Gauge className="mt-0.5 size-4 shrink-0 text-primary" /><span>{evaluation.feedback}</span></div><p className="text-[10px] text-muted-foreground">评分只依据透明的物理阈值；步骤、预测和结论单独展示，不用文字长度替代学习质量。</p></div> : <div className="p-6 text-center text-xs text-muted-foreground">{evaluation?.feedback ?? "等待有效仿真结果"}</div>}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
