import { Button } from "@/components/ui/button";

export type PowerQuantity = "all" | "R" | "T" | "A";

export function preferredPowerQuantity(caseId: string): PowerQuantity {
  if (/^(fp_|narrowband_filter|app_wdm_filter)/.test(caseId)) return "T";
  if (/^(absorbing_|pdrc_)/.test(caseId)) return "A";
  if (caseId === "neutral_beamsplitter") return "all";
  return "R";
}

const OPTIONS: Array<{ value: PowerQuantity; label: string }> = [
  { value: "all", label: "总览" },
  { value: "R", label: "反射 R" },
  { value: "T", label: "透射 T" },
  { value: "A", label: "吸收 A" },
];

export function powerAxisDomain(values: number[]): [number, number] {
  const finite = values.filter(Number.isFinite);
  if (!finite.length) return [0, 1];
  const minimum = Math.max(0, Math.min(...finite));
  const maximum = Math.min(1, Math.max(...finite));
  const spread = Math.max(maximum - minimum, 0.01);
  const step = 10 ** Math.floor(Math.log10(spread / 4));
  const padding = Math.max(spread * 0.12, step);
  const lower = Math.max(0, Math.floor((minimum - padding) / step) * step);
  const upper = Math.min(1, Math.ceil((maximum + padding) / step) * step);
  return lower < upper ? [lower, upper] : [0, 1];
}

export function formatPowerTick(value: number, domain: [number, number]): string {
  const spanPercent = (domain[1] - domain[0]) * 100;
  const digits = spanPercent < 1 ? 3 : spanPercent < 10 ? 2 : 1;
  return `${(value * 100).toFixed(digits)}%`;
}

export function PowerSpectrumControls({ value, onChange, values = [] }: { value: PowerQuantity; onChange: (value: PowerQuantity) => void; values?: number[] }) {
  const finite = values.filter(Number.isFinite);
  const maximum = finite.length ? Math.max(...finite) : null;
  const minimum = finite.length ? Math.min(...finite) : null;
  const note = value === "all" ? "共用 0–100% 纵轴"
    : maximum !== null && maximum <= 1e-8 ? "该量在当前波段近似为零"
    : maximum !== null && minimum !== null && maximum - minimum < 1e-6 ? "该量在当前波段几乎不变"
    : "纵轴显示实际数值的局部范围";
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div role="group" aria-label="光谱观察量" className="inline-flex rounded-md border bg-muted/50 p-0.5">
        {OPTIONS.map((option) => (
          <Button key={option.value} type="button" size="sm" variant={value === option.value ? "secondary" : "ghost"}
            aria-pressed={value === option.value} onClick={() => onChange(option.value)}
            className="h-7 rounded-sm px-2 text-xs whitespace-nowrap">
            {option.label}
          </Button>
        ))}
      </div>
      <span className="text-[11px] text-muted-foreground">{note}</span>
    </div>
  );
}
