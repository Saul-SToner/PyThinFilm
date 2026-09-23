import { ArrowDown, ArrowUp, Copy, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { DesignLayer, MaterialOption } from "@/types/design";

interface LayerRowProps {
  layer: DesignLayer;
  index: number;
  count: number;
  materials: MaterialOption[];
  onChange: (layer: DesignLayer) => void;
  onMove: (offset: -1 | 1) => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onDragStart: () => void;
  onDrop: () => void;
}

export function LayerRow({ layer, index, count, materials, onChange, onMove, onDuplicate, onDelete, onDragStart, onDrop }: LayerRowProps) {
  const material = materials.find((item) => item.material_id === layer.material_id);
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragOver={(event) => event.preventDefault()}
      onDrop={onDrop}
      className={`cursor-grab rounded-md border p-3 transition active:cursor-grabbing ${layer.enabled ? "bg-card" : "bg-muted/40 opacity-70"}`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex size-6 items-center justify-center rounded bg-primary/10 text-xs font-semibold text-primary">
            {index + 1}
          </span>
          <span className="text-xs font-medium">膜层 {index + 1}</span>
        </div>
        <Switch checked={layer.enabled} onCheckedChange={(enabled) => onChange({ ...layer, enabled })} />
      </div>
      <div className="grid grid-cols-[1fr_108px] gap-2">
        <Select
          aria-label={`膜层 ${index + 1} 材料`}
          value={layer.material_id}
          onChange={(event) => onChange({ ...layer, material_id: event.target.value })}
        >
          {materials.map((material) => (
            <option key={material.material_id} value={material.material_id}>
              {material.display_name_zh}
            </option>
          ))}
        </Select>
        <div className="relative">
          <Input
            aria-label={`膜层 ${index + 1} 厚度`}
            type="number"
            min={0.01}
            step={1}
            className="pr-8"
            value={Number.isFinite(layer.thickness_nm) ? layer.thickness_nm : ""}
            onChange={(event) => onChange({ ...layer, thickness_nm: Number(event.target.value) })}
          />
          <span className="pointer-events-none absolute right-2 top-2.5 text-[10px] text-muted-foreground">nm</span>
        </div>
      </div>
      {material ? (
        <details className="mt-2 rounded-md border bg-muted/20 px-2 py-1.5 text-[11px] text-muted-foreground">
          <summary className="cursor-pointer font-medium text-foreground">查看材料属性</summary>
          <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
            <span>类别：{material.category}</span>
            <span>数据：Real n,k</span>
            <span>n(550 nm)：{material.n_at_550nm.toFixed(3)}</span>
            <span>k(550 nm)：{material.k_at_550nm.toFixed(3)}</span>
            <span className="col-span-2">有效范围：{material.lambda_min_nm.toFixed(0)}–{material.lambda_max_nm.toFixed(0)} nm</span>
          </div>
        </details>
      ) : null}
      <div className="mt-2 flex justify-end gap-1">
        <Button variant="ghost" size="icon" className="size-7" disabled={index === 0} title="上移" onClick={() => onMove(-1)}>
          <ArrowUp className="size-3.5" />
        </Button>
        <Button variant="ghost" size="icon" className="size-7" disabled={index === count - 1} title="下移" onClick={() => onMove(1)}>
          <ArrowDown className="size-3.5" />
        </Button>
        <Button variant="ghost" size="icon" className="size-7" title="复制" onClick={onDuplicate}>
          <Copy className="size-3.5" />
        </Button>
        <Button variant="ghost" size="icon" className="size-7 text-destructive" disabled={count === 1} title="删除" onClick={onDelete}>
          <Trash2 className="size-3.5" />
        </Button>
      </div>
    </div>
  );
}
