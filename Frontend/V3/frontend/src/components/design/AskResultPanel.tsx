import { useEffect, useRef, useState } from "react";
import { ChevronDown, Copy, Loader2, Send, Sparkles, Square, X } from "lucide-react";

import { askAboutResult } from "@/api/thinfilmClient";
import { Button } from "@/components/ui/button";
import { MarkdownContent } from "@/components/design/MarkdownContent";
import type { DesignDraft, DesignSimulationResult } from "@/types/design";

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  status?: "streaming" | "done" | "stopped" | "error";
  thoughtOpen?: boolean;
};

interface AskResultPanelProps {
  draft: DesignDraft;
  result: DesignSimulationResult | null;
  ready: boolean;
  onClose: () => void;
}

const SUGGESTIONS = ["这次光谱最值得观察什么？", "当前反射谷为什么出现在这个波长？", "改变膜层厚度后，结果可能怎样变化？"];

export function AskResultPanel({ draft, result, ready, onClose }: AskResultPanelProps) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const controller = useRef<AbortController | null>(null);
  const nextId = useRef(0);
  const listEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    controller.current?.abort();
    setBusy(false);
    setMessages([]);
    setError("");
  }, [result?.request_id]);

  useEffect(() => () => { controller.current?.abort(); }, []);
  useEffect(() => { listEnd.current?.scrollIntoView({ block: "end" }); }, [messages, busy]);
  useEffect(() => {
    if (!ready) {
      controller.current?.abort();
      controller.current = null;
      setBusy(false);
      setMessages((current) => current.map((message) => message.status === "streaming" ? { ...message, status: "stopped" } : message));
    }
  }, [ready]);

  function stopGeneration() {
    controller.current?.abort();
    controller.current = null;
    setBusy(false);
    setMessages((current) => current.map((message) => message.status === "streaming" ? { ...message, status: "stopped" } : message));
  }

  async function submit(text: string) {
    const currentQuestion = text.trim();
    if (!currentQuestion || !result || !ready || busy) return;
    const history: Array<{ role: "user" | "assistant"; content: string }> = [];
    for (let index = 0; index < messages.length - 1; index++) {
      if (messages[index].role === "user" && messages[index + 1].role === "assistant" && messages[index + 1].status === "done") {
        history.push({ role: "user", content: messages[index].content }, { role: "assistant", content: messages[index + 1].content });
      }
    }
    const userId = ++nextId.current;
    const assistantId = ++nextId.current;
    const nextController = new AbortController();
    controller.current = nextController;
    setQuestion("");
    setError("");
    setBusy(true);
    setMessages((current) => [...current,
      { id: userId, role: "user", content: currentQuestion },
      { id: assistantId, role: "assistant", content: "", reasoning: "", status: "streaming", thoughtOpen: true },
    ]);

    let reasoning = "";
    let content = "";
    let frame: number | null = null;
    let autoCollapse = false;
    const flush = () => {
      frame = null;
      setMessages((current) => current.map((message) => message.id === assistantId
        ? { ...message, reasoning, content, thoughtOpen: autoCollapse ? false : message.thoughtOpen }
        : message));
      autoCollapse = false;
    };
    try {
      await askAboutResult(currentQuestion, draft, result, history, (event) => {
        if (nextController.signal.aborted) return;
        if (event.type === "reasoning") reasoning += event.text;
        if (event.type === "content") {
          if (!content) autoCollapse = true;
          content += event.text;
        }
        if (event.type !== "done" && frame === null) frame = window.requestAnimationFrame(flush);
      }, nextController.signal);
      if (!nextController.signal.aborted) {
        if (frame !== null) window.cancelAnimationFrame(frame);
        flush();
        setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, status: "done", thoughtOpen: false } : message));
      }
    } catch (cause) {
      if (!nextController.signal.aborted) {
        if (frame !== null) window.cancelAnimationFrame(frame);
        flush();
        setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, status: "error" } : message));
        setError(cause instanceof Error ? cause.message : "问答请求失败，请稍后重试。");
      }
    } finally {
      if (controller.current === nextController) controller.current = null;
      if (!nextController.signal.aborted) setBusy(false);
    }
  }

  async function copyAnswer(message: ChatMessage) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedId(message.id);
    } catch {
      setError("复制失败，请手动选择文本。");
    }
  }

  return (
    <aside aria-label="本次结果 AI 问答" className="absolute inset-y-0 right-0 z-30 flex w-full max-w-[560px] flex-col border-l bg-background shadow-2xl">
      <div className="flex items-center justify-between border-b px-5 py-3">
        <div><h2 className="flex items-center gap-2 text-sm font-semibold"><Sparkles className="size-4 text-primary" />问问本次结果</h2><p className="mt-1 text-[11px] text-muted-foreground">DeepSeek-V4-Flash · 结合当前膜系与仿真数据</p></div>
        <Button type="button" size="icon" variant="ghost" aria-label="关闭 AI 问答" onClick={onClose}><X className="size-4" /></Button>
      </div>
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5">
        {!ready ? <p className="rounded-md border p-3 text-sm text-muted-foreground">请等待当前参数计算完成，再提问本次结果。</p> : null}
        {ready && messages.length === 0 ? <div className="space-y-3"><p className="text-sm text-muted-foreground">可以从当前光谱、指标或物理规律开始：</p>{SUGGESTIONS.map((item) => <button key={item} type="button" onClick={() => void submit(item)} className="block w-full rounded-lg border p-3 text-left text-sm transition-colors hover:bg-muted">{item}</button>)}</div> : null}
        {messages.map((message) => message.role === "user"
          ? <div key={message.id} className="ml-10 rounded-2xl rounded-br-md bg-primary/10 px-4 py-3 text-sm leading-6 whitespace-pre-wrap">{message.content}</div>
          : <div key={message.id} className="space-y-3 text-sm">
              {message.reasoning ? <div className="rounded-lg border bg-muted/30">
                <button type="button" className="flex w-full items-center justify-between px-3 py-2 text-left text-xs text-muted-foreground" aria-expanded={Boolean(message.thoughtOpen)} onClick={() => setMessages((current) => current.map((item) => item.id === message.id ? { ...item, thoughtOpen: !item.thoughtOpen } : item))}>
                  <span className="flex items-center gap-2">{message.status === "streaming" && !message.content ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}{message.status === "streaming" && !message.content ? "思考中…" : "已思考"}</span>
                  <ChevronDown className={`size-3.5 transition-transform ${message.thoughtOpen ? "rotate-180" : ""}`} />
                </button>
                {message.thoughtOpen ? <div className="max-h-60 overflow-y-auto border-t px-3 py-3 text-xs leading-5 text-muted-foreground"><MarkdownContent content={message.reasoning} muted /></div> : null}
              </div> : null}
              {message.content ? <MarkdownContent content={message.content} /> : message.status === "streaming" ? <p role="status" className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="size-4 animate-spin" />{message.reasoning ? "正在组织回答…" : "正在思考…"}</p> : null}
              {message.status === "stopped" ? <p className="text-xs text-muted-foreground">已停止生成</p> : null}
              {message.status === "done" && message.content ? <button type="button" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" onClick={() => void copyAnswer(message)}><Copy className="size-3.5" />{copiedId === message.id ? "已复制" : "复制回复"}</button> : null}
            </div>)}
        {error ? <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">{error}</p> : null}
        <div ref={listEnd} />
      </div>
      <form className="space-y-2 border-t bg-card/70 p-4" onSubmit={(event) => { event.preventDefault(); void submit(question); }}>
        <label htmlFor="ask-result-question" className="sr-only">输入关于本次结果的问题</label>
        <textarea id="ask-result-question" value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submit(question); } }} maxLength={1500} rows={3} placeholder="例如：为什么 550 nm 附近出现反射谷？" className="w-full resize-none rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
        <div className="flex items-center justify-between gap-2"><p className="text-[10px] text-muted-foreground">AI 解读仅供教学参考，以计算结果为准。</p>{busy ? <Button type="button" size="sm" variant="outline" onClick={stopGeneration}><Square className="size-3.5" />停止</Button> : <Button type="submit" size="sm" disabled={!ready || !question.trim()}><Send className="size-4" />发送</Button>}</div>
      </form>
    </aside>
  );
}
