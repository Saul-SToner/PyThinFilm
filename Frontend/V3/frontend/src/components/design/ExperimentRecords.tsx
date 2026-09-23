import { RotateCcw, Save, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { ExperimentRecord } from "@/types/design";

interface ExperimentRecordsProps {
  records: ExperimentRecord[];
  selectedIds: string[];
  recordName: string;
  quantity: "R" | "T" | "A";
  canSave: boolean;
  onRecordNameChange: (value: string) => void;
  onSave: () => void;
  onToggleCompare: (id: string) => void;
  onRestore: (record: ExperimentRecord) => void;
  onDelete: (id: string) => void;
  onQuantityChange: (value: "R" | "T" | "A") => void;
}
export function ExperimentRecords(props: ExperimentRecordsProps) {
  return <Card className="rounded-md shadow-sm"><CardHeader className="flex flex-row items-center justify-between p-4 pb-2"><CardTitle className="text-sm">实验记录与曲线比较</CardTitle><div className="flex items-center gap-2"><span className="text-xs text-muted-foreground">历史比较量</span><Select className="h-8 w-20" value={props.quantity} onChange={(event) => props.onQuantityChange(event.target.value as "R" | "T" | "A")}><option value="R">R</option><option value="T">T</option><option value="A">A</option></Select></div></CardHeader><CardContent className="space-y-3 p-4 pt-0"><div className="flex gap-2"><Input value={props.recordName} placeholder={`实验记录 ${props.records.length + 1}`} onChange={(event) => props.onRecordNameChange(event.target.value)} /><Button disabled={!props.canSave} onClick={props.onSave}><Save />保存当前结果</Button></div>{props.records.length === 0 ? <div className="rounded-md border border-dashed p-5 text-center text-xs text-muted-foreground">尚无记录。改变一个变量并保存，随后即可叠加比较。</div> : <div className="space-y-2">{props.records.map((record) => { const selected = props.selectedIds.includes(record.id); return <div key={record.id} className={`flex items-center gap-3 rounded-md border px-3 py-2 ${selected ? "border-primary/50 bg-primary/5" : ""}`}><input type="checkbox" checked={selected} aria-label={`比较 ${record.name}`} onChange={() => props.onToggleCompare(record.id)} /><div className="min-w-0 flex-1"><p className="truncate text-xs font-medium">{record.name}</p><p className="truncate text-[10px] text-muted-foreground">{new Date(record.created_at).toLocaleString("zh-CN")} · {record.result.summary.layer_count}层 · {record.result.summary.total_thickness_nm.toFixed(1)} nm</p></div><Button size="icon" variant="ghost" className="size-7" title="恢复此膜系" onClick={() => props.onRestore(record)}><RotateCcw className="size-3.5" /></Button><Button size="icon" variant="ghost" className="size-7 text-destructive" title="删除记录" onClick={() => props.onDelete(record.id)}><Trash2 className="size-3.5" /></Button></div>; })}</div>}<p className="text-[10px] text-muted-foreground">最多保存8条记录，同时比较3条历史曲线。数据仅保存在本机。</p></CardContent></Card>;
}
