import httpx
import pytest

from app.services.providers.gemini import GeminiAdapter


class _Resp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            req = httpx.Request("POST", "https://example.com")
            raise httpx.HTTPStatusError("err", request=req, response=httpx.Response(self.status_code, request=req))

    def json(self):
        return self._payload


class _StreamResp:
    status_code = 200

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        lines = [
            'data: {"responseId":"r1","candidates":[{"content":{"parts":[{"text":"hel"}]},"finishReason":null}]}',
            'data: {"responseId":"r1","candidates":[{"content":{"parts":[{"text":"lo"}]},"finishReason":"STOP"}],"usageMetadata":{"promptTokenCount":2,"candidatesTokenCount":3,"totalTokenCount":5}}',
        ]
        for line in lines:
            yield line


class _StreamCtx:
    async def __aenter__(self):
        return _StreamResp()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Client:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return _Resp(
            payload={
                "responseId": "r1",
                "candidates": [{"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 2, "totalTokenCount": 3},
            }
        )

    def stream(self, *args, **kwargs):
        return _StreamCtx()

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_gemini_contract_success_usage_and_stream(monkeypatch):
    monkeypatch.setattr("app.services.providers.gemini.httpx.AsyncClient", _Client)
    adapter = GeminiAdapter()
    raw, usage = await adapter.chat_completions({"model": "gemini-1.5", "messages": [{"role": "user", "content": "x"}]}, "k", "https://generativelanguage.googleapis.com")
    assert raw["choices"][0]["message"]["content"] == "ok"
    assert usage["total_tokens"] == 3

    stream = await adapter.stream_chat_completions({"model": "gemini-1.5", "messages": [{"role": "user", "content": "x"}]}, "k", "https://generativelanguage.googleapis.com")
    chunks = []
    async for chunk in stream.iterator:
        chunks.append(chunk)
    raw_stream, usage_stream = await stream.finalize()
    assert any("[DONE]" in c for c in chunks)
    assert raw_stream["choices"][0]["message"]["content"] == "hello"
    assert usage_stream["total_tokens"] == 5


def test_gemini_contract_error_normalization():
    adapter = GeminiAdapter()
    req = httpx.Request("POST", "https://x")
    assert adapter.normalize_error(httpx.TimeoutException("timeout"))["code"] == "timeout"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(401, request=req)))["code"] == "auth_failed"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(429, request=req)))["code"] == "rate_limited"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(400, request=req)))["code"] == "request_error"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(503, request=req)))["code"] == "upstream_error"
