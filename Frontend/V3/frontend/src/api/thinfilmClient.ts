import type { DesignDraft, DesignSimulationResult, MaterialOption } from "@/types/design";

const browserApiHost = window.location.hostname || "127.0.0.1";
export const API_BASE_URL = window.thinfilmDesktop?.apiBaseUrl ?? `http://${browserApiHost}:8122`;
const AI_API_BASE_URL = import.meta.env.VITE_AI_API_BASE_URL || API_BASE_URL;

async function responseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `请求失败：${response.status}`);
  }
  return (await response.json()) as T;
}
export async function listMaterials(signal?: AbortSignal): Promise<MaterialOption[]> {
  return responseJson<MaterialOption[]>(await fetch(`${API_BASE_URL}/api/materials`, { signal }));
}

export async function simulateDesign(
  draft: DesignDraft,
  requestId: string,
  signal?: AbortSignal,
): Promise<DesignSimulationResult> {
  return responseJson<DesignSimulationResult>(
    await fetch(`${API_BASE_URL}/api/designs/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...draft, request_id: requestId }),
      signal,
    }),
  );
}

export type AskResultStreamEvent =
  | { type: "reasoning" | "content"; text: string }
  | { type: "done" };

export async function askAboutResult(
  question: string,
  draft: DesignDraft,
  result: DesignSimulationResult,
  history: Array<{ role: "user" | "assistant"; content: string }>,
  onEvent: (event: AskResultStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const stride = Math.max(1, Math.ceil(result.series.wavelength_nm.length / 30));
  const spectrumSamples = result.series.wavelength_nm.flatMap((wavelength, index) =>
    index % stride === 0 || index === result.series.wavelength_nm.length - 1
      ? [{ wavelength_nm: wavelength, R: result.series.R[index], T: result.series.T[index], A: result.series.A[index] }]
      : [],
  );
  const response = await fetch(`${AI_API_BASE_URL}/api/ai/ask-result`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      history: history.slice(-8),
      design: {
        incident_material_id: draft.incident_material_id,
        substrate_material_id: draft.substrate_material_id,
        layers: draft.layers.filter((layer) => layer.enabled),
        spectrum: draft.spectrum,
        angle_deg: draft.angle_deg,
        polarization: draft.polarization,
        probe_wavelength_nm: draft.probe_wavelength_nm,
      },
      result: {
        request_id: result.request_id,
        summary: result.summary,
        metrics: result.metrics,
        field: { wavelength_nm: result.field.wavelength_nm, peak_E2: result.field.peak_E2, peak_z_nm: result.field.peak_z_nm, R: result.field.R, T: result.field.T, A: result.field.A },
        phase: { probe: result.phase.probe, explanations: result.phase.explanations },
        warnings: result.warnings,
        solver: result.solver,
        spectrum_samples: spectrumSamples,
      },
    }),
    signal,
  });
  if (!response.ok) {
    await responseJson<unknown>(response);
    return;
  }
  if (!response.body) throw new Error("浏览器不支持流式回复。");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let done = false;
  try {
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const kind = frame.match(/^event: (\w+)/m)?.[1];
        const raw = frame.split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart()).join("\n");
        if (kind && raw) {
          const data = JSON.parse(raw) as { text?: string; message?: string };
          if (kind === "reasoning" || kind === "content") onEvent({ type: kind, text: data.text ?? "" });
          else if (kind === "error") throw new Error(data.message ?? "AI 服务暂时不可用。");
          else if (kind === "done") { done = true; onEvent({ type: "done" }); }
        }
        boundary = buffer.indexOf("\n\n");
      }
    }
    if (!done && !signal?.aborted) throw new Error("AI 回复意外中断，请重试。");
  } finally {
    reader.releaseLock();
  }
}
