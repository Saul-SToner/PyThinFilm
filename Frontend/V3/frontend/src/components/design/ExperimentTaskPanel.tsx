import { BookOpen, CheckCircle2, Circle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type { ExperimentTask } from "@/components/design/experimentTasks";

interface ExperimentTaskPanelProps {
  tasks: ExperimentTask[];
  task: ExperimentTask;
  completedSteps: boolean[];
  prediction: string;
  conclusion: string;
  onSelect: (taskId: string) => void;
  onLoad: () => void;
  onToggleStep: (index: number) => void;
  onPredictionChange: (value: string) => void;
  onConclusionChange: (value: string) => void;
}

export function ExperimentTaskPanel(props: ExperimentTaskPanelProps) {
  const completed = props.completedSteps.filter(Boolean).length;
  const progress = Math.round((completed / props.task.steps.length) * 100);
  return (
    <Card className="rounded-md border-primary/25 shadow-none">
      <CardHeader className="p-3 pb-2">
        <div className="flex items-center justify-between gap-2"><CardTitle className="flex items-center gap-2 text-sm"><BookOpen className="size-4 text-primary" />实验任务</CardTitle><span className="rounded bg-primary/10 px-2 py-0.5 text-[10px] text-primary">{props.task.stage}</span></div>
      </CardHeader>
      <CardContent className="space-y-3 p-3 pt-0">
        <Select value={props.task.id} onChange={(event) => props.onSelect(event.target.value)}>{props.tasks.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</Select>
        <div className="rounded-md bg-muted/60 p-3"><p className="text-xs font-semibold">探究问题</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{props.task.question}</p></div>
        <div><p className="mb-1 text-[11px] font-semibold">教学目标</p><ul className="space-y-1 text-xs text-muted-foreground">{props.task.objectives.map((objective) => <li key={objective}>· {objective}</li>)}</ul></div>
        <div><div className="mb-1 flex justify-between text-[11px] text-muted-foreground"><span>实验进度</span><span>{completed}/{props.task.steps.length} · {progress}%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} /></div></div>
        <div className="space-y-1">
          {props.task.steps.map((step, index) => <button key={step} type="button" className="flex w-full items-start gap-2 rounded px-1 py-1 text-left text-xs hover:bg-muted" onClick={() => props.onToggleStep(index)}>{props.completedSteps[index] ? <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-primary" /> : <Circle className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />}<span className={props.completedSteps[index] ? "text-muted-foreground line-through" : ""}>{step}</span></button>)}
        </div>
        <Button variant="outline" size="sm" className="w-full" onClick={props.onLoad}>载入任务起始膜系</Button>
        <div className="space-y-1.5"><Label className="text-xs">实验前预测</Label><textarea className="min-h-16 w-full resize-y rounded-md border bg-background px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-ring" placeholder="先写下你的预测，再修改参数……" value={props.prediction} onChange={(event) => props.onPredictionChange(event.target.value)} /></div>
        <div className="space-y-1.5"><Label className="text-xs">实验结论</Label><textarea className="min-h-16 w-full resize-y rounded-md border bg-background px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-ring" placeholder={props.task.prompts.join("；")} value={props.conclusion} onChange={(event) => props.onConclusionChange(event.target.value)} /></div>
      </CardContent>
    </Card>
  );
}
