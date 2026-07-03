import json

import httpx
import pytest

from app.services.providers.openai_compat import OpenAICompatAdapter


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)
        self.is_error = status_code >= 400

    def raise_for_status(self):
        if self.status_code >= 400:
            req = httpx.Request("POST", "https://example.com")
            raise httpx.HTTPStatusError("err", request=req, response=httpx.Response(self.status_code, request=req, text=self.text))

    def json(self):
        return self._payload


class _FakeStreamResponse:
    def __init__(self, lines):
        self.status_code = 200
        self._lines = lines
        self.is_error = False

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self):
        return b""


class _FakeStreamCtx:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return _FakeResponse(
            payload={
                "id": "chatcmpl-1",
                "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            }
        )

    def stream(self, *args, **kwargs):
        lines = [
            'data: {"id":"chatcmpl-2","choices":[{"delta":{"role":"assistant","content":"he"},"finish_reason":null}]}',
            'data: {"id":"chatcmpl-2","choices":[{"delta":{"content":"llo"},"finish_reason":"stop"}],"usage":{"prompt_tokens":4,"completion_tokens":3,"total_tokens":7}}',
            "data: [DONE]",
        ]
        return _FakeStreamCtx(_FakeStreamResponse(lines))

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_openai_contract_success_shape_and_usage(monkeypatch):
    monkeypatch.setattr("app.services.providers.openai_compat.httpx.AsyncClient", _FakeClient)
    adapter = OpenAICompatAdapter()
    raw, usage = await adapter.chat_completions({"model": "gpt-4o", "messages": []}, "sk", "https://api.openai.com")
    assert raw["choices"][0]["message"]["content"] == "ok"
    assert usage["total_tokens"] == 5


def test_openai_contract_error_normalization():
    adapter = OpenAICompatAdapter()
    req = httpx.Request("POST", "https://x")
    assert adapter.normalize_error(httpx.TimeoutException("timeout")).get("code") == "timeout"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(401, request=req)))["code"] == "auth_failed"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(429, request=req)))["code"] == "rate_limited"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(400, request=req)))["code"] == "request_error"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(500, request=req)))["code"] == "upstream_error"


@pytest.mark.asyncio
async def test_openai_contract_streaming_finalize(monkeypatch):
    monkeypatch.setattr("app.services.providers.openai_compat.httpx.AsyncClient", _FakeClient)
    adapter = OpenAICompatAdapter()
    stream = await adapter.stream_chat_completions({"model": "gpt-4o", "messages": []}, "sk", "https://api.openai.com")
    chunks = []
    async for chunk in stream.iterator:
        chunks.append(chunk)
    raw, usage = await stream.finalize()
    assert any("[DONE]" in chunk for chunk in chunks)
    assert raw["choices"][0]["message"]["content"] == "hello"
    assert usage["total_tokens"] == 7
