"""Small deployable AI gateway; keep the provider key on the owner's server."""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .ai_qa import AskResultRequest, prepare_result_request, stream_result_answer


app = FastAPI(title="PythonFilm AI Gateway")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST"], allow_headers=["Content-Type"])

_lock = threading.Lock()
_recent: dict[str, deque[float]] = defaultdict(deque)
_daily_count = 0
_daily_start = time.time()


def _check_limit(client_ip: str) -> None:
    global _daily_count, _daily_start
    now = time.time()
    daily_limit = max(1, int(os.environ.get("THINFILM_AI_DAILY_REQUEST_LIMIT", "500")))
    with _lock:
        if now - _daily_start >= 86400:
            _daily_start, _daily_count = now, 0
        recent = _recent[client_ip]
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if len(recent) >= 12 or _daily_count >= daily_limit:
            raise HTTPException(status_code=429, detail="AI 问答已达到调用上限，请稍后重试。")
        recent.append(now)
        _daily_count += 1


@app.post("/api/ai/ask-result")
def ask_result(request: AskResultRequest, http_request: Request) -> StreamingResponse:
    _check_limit(http_request.client.host if http_request.client else "unknown")
    outgoing = prepare_result_request(request)
    return StreamingResponse(stream_result_answer(outgoing), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
