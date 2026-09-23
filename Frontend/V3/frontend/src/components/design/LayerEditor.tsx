import { CopyPlus, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LayerRow } from "@/components/design/LayerRow";
import type { DesignLayer, MaterialOption } from "@/types/design";

interface LayerEditorProps {
  layers: DesignLayer[];
  materials: MaterialOption[];
  onChange: (layers: DesignLayer[]) => void;
}

function newId(): string {
  return `layer-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function LayerEditor({ layers, materials, onChange }: LayerEditorProps) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [periodCount, setPeriodCount] = useState(2);
  function replace(index: number, layer: DesignLayer) {
    onChange(layers.map((item, itemIndex) => (itemIndex === index ? layer : item)));
  }

  function move(index: number, offset: -1 | 1) {
    const next = [...layers];
    const target = index + offset;
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  }

  function duplicate(index: number) {
    const next = [...layers];
    next.splice(index + 1, 0, { ...layers[index], id: newId() });
    onChange(next);
  }

  function dropAt(targetIndex: number) {
    if (dragIndex === null || dragIndex === targetIndex) return;
    const next = [...layers];
    const [moved] = next.splice(dragIndex, 1);
    next.splice(targetIndex, 0, moved);
    setDragIndex(null);
    onChange(next);
  }

  function copyPeriod() {
    const count = Math.max(2, Math.min(20, Math.round(periodCount)));
    const copies = Array.from({ length: count - 1 }, () => layers.map((layer) => ({ ...layer, id: newId() })));
    onChange([...layers, ...copies.flat()]);
  }

  return (
    <div className="flex flex-col gap-2">
      {layers.map((layer, index) => (
        <LayerRow
          key={layer.id}
          layer={layer}
          index={index}
          count={layers.length}
          materials={materials}
          onChange={(value) => replace(index, value)}
          onMove={(offset) => move(index, offset)}
          onDuplicate={() => duplicate(index)}
          onDelete={() => onChange(layers.filter((_, itemIndex) => itemIndex !== index))}
          onDragStart={() => setDragIndex(index)}
          onDrop={() => dropAt(index)}
        />
      ))}
      <div className="flex items-center gap-2">
        <Input
          aria-label="周期复制次数"
          type="number"
          min={2}
          max={20}
          step={1}
          value={periodCount}
          onChange={(event) => setPeriodCount(Number(event.target.value))}
          className="w-20"
        />
        <Button type="button" variant="outline" className="flex-1" disabled={layers.length === 0 || layers.length * periodCount > 200} onClick={copyPeriod}>
          <CopyPlus /> 复制整个膜系为周期
        </Button>
      </div>
      <Button
        type="button"
        variant="outline"
        className="mt-1 w-full border-dashed"
        disabled={materials.length === 0 || layers.length >= 200}
        onClick={() =>
          onChange([
            ...layers,
            { id: newId(), material_id: materials.find((item) => item.material_id === "SiO2")?.material_id ?? materials[0].material_id, thickness_nm: 100, enabled: true },
          ])
        }
      >
        <Plus /> 添加膜层
      </Button>
    </div>
  );
}
