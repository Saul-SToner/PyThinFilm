import io
import json

import pytest
from fastapi import HTTPException

from app import ai_qa


def _request():
    return {
        "question": "为什么反射率降低？",
        "design": {"layers": [{"material_id": "MgF2", "thickness_nm": 100}], "angle_deg": 0},
        "result": {"request_id": "design-3", "summary": {"mean_R": 0.04}, "spectrum_samples": [{"wavelength_nm": 550, "R": 0.02}]},
    }


def test_ask_result_requires_admin_key(monkeypatch):
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        ai_qa.prepare_result_request(ai_qa.AskResultRequest(**_request()))
    assert exc_info.value.status_code == 503
    assert "管理员" in exc_info.value.detail


def test_ask_result_reads_backend_dotenv(monkeypatch):
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    paths = []

    def fake_dotenv_values(path):
        paths.append(path)
        return {"SILICONFLOW_API_KEY": "file-test-key"}

    monkeypatch.setattr(ai_qa, "dotenv_values", fake_dotenv_values)
    assert ai_qa._api_key() == "file-test-key"
    assert paths == [ai_qa.Path(ai_qa.__file__).resolve().parents[1] / ".env"]
    monkeypatch.setenv("SILICONFLOW_API_KEY", "environment-test-key")
    assert ai_qa._api_key() == "environment-test-key"
    assert len(paths) == 1


def test_ask_result_forwards_current_context_without_leaking_key(monkeypatch):
    monkeypatch.setenv("SILICONFLOW_API_KEY", "private-test-key")
    sent = {}

    def fake_urlopen(request, timeout):
        sent["url"] = request.full_url
        sent["headers"] = request.headers
        sent["body"] = json.loads(request.data)
        sent["timeout"] = timeout
        chunks = [
            {"choices": [{"delta": {"reasoning_content": "先检查反射率。"}}]},
            {"choices": [{"delta": {"content": "**当前** 550 nm "}}]},
            {"choices": [{"delta": {"content": "反射率为 2%。"}}]},
        ]
        lines = "".join(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
        return io.BytesIO(lines.encode("utf-8"))

    monkeypatch.setattr(ai_qa, "urlopen", fake_urlopen)
    request = ai_qa.AskResultRequest(**_request(), history=[{"role": "user", "content": "上个问题"}, {"role": "assistant", "content": "上个回答"}])
    events = list(ai_qa.stream_result_answer(ai_qa.prepare_result_request(request)))
    assert 'event: reasoning\ndata: {"text": "先检查反射率。"}' in events[0]
    assert 'event: content\ndata: {"text": "**当前** 550 nm "}' in events[1]
    assert events[-1].startswith("event: done")
    assert sent["body"]["model"] == "deepseek-ai/DeepSeek-V4-Flash"
    assert sent["body"]["stream"] is True
    assert sent["body"]["enable_thinking"] is True
    assert "design-3" in sent["body"]["messages"][1]["content"]
    assert sent["body"]["messages"][-3:-1] == [{"role": "user", "content": "上个问题"}, {"role": "assistant", "content": "上个回答"}]
    assert sent["headers"]["Authorization"] == "Bearer private-test-key"
    assert "private-test-key" not in "".join(events)


def test_stream_reports_provider_failure_without_exposing_response(monkeypatch):
    from urllib.error import HTTPError

    def fail_urlopen(request, timeout):
        raise HTTPError(request.full_url, 401, "private-test-key", {}, None)

    monkeypatch.setattr(ai_qa, "urlopen", fail_urlopen)
    outgoing = ai_qa.Request(ai_qa.SILICONFLOW_URL)
    events = list(ai_qa.stream_result_answer(outgoing))
    assert len(events) == 1
    assert events[0].startswith("event: error")
    assert "鉴权失败" in events[0]
    assert "private-test-key" not in events[0]
