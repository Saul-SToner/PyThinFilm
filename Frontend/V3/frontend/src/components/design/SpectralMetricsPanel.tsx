import { Activity } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DesignSimulationResult } from "@/types/design";

function percent(value: number) { return `${(value * 100).toFixed(2)}%`; }
function number(value: number | null | undefined, suffix = "") { return value == null ? "不可用" : `${value.toFixed(2)}${suffix}`; }

export function SpectralMetricsPanel({ result }: { result: DesignSimulationResult | null }) {
  const metrics = result?.metrics;
  const items = metrics ? [
    ["最低反射率", `${percent(metrics.R.minimum)}（波长 ${number(metrics.R.minimum_wavelength_nm, " nm")}）`],
    ["最高反射率", `${percent(metrics.R.maximum)}（波长 ${number(metrics.R.maximum_wavelength_nm, " nm")}）`],
    ["最高透射率", `${percent(metrics.T.maximum)}（波长 ${number(metrics.T.maximum_wavelength_nm, " nm")}）`],
    ["中心波长反射率", `${percent(metrics.R.at_center)}（中心 ${number(metrics.center_wavelength_nm, " nm")}）`],
    ["R≥90% 最大带宽", metrics.high_reflection_band ? number(metrics.high_reflection_band.width_nm, " nm") : "未形成"],
    ["主透射峰 FWHM / Q", metrics.transmission_peak_linewidth.status === "available" ? `${number(metrics.transmission_peak_linewidth.fwhm_nm, " nm")} / ${number(metrics.transmission_peak_linewidth.q_factor)}` : "当前波段不可测"],
  ] : [];
  return <Card className="rounded-md shadow-sm"><CardHeader className="p-4 pb-2"><CardTitle className="flex items-center gap-2 text-sm"><Activity className="size-4 text-primary" />光谱指标分析</CardTitle></CardHeader><CardContent className="grid gap-2 p-4 pt-0 sm:grid-cols-2 xl:grid-cols-3">{items.length ? items.map(([label, value]) => <div key={label} className="rounded-md border bg-muted/30 px-3 py-2"><p className="text-[11px] text-muted-foreground">{label}</p><p className="mt-1 text-sm font-semibold">{value}</p></div>) : <p className="text-xs text-muted-foreground">等待有效仿真结果</p>}</CardContent></Card>;
}
