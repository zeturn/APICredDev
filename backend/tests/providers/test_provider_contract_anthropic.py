import json

import httpx
import pytest

from app.services.providers.anthropic import AnthropicAdapter


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
            "event: message_start",
            'data: {"message":{"id":"msg1","usage":{"input_tokens":2,"output_tokens":0}}}',
            "event: content_block_delta",
            'data: {"delta":{"type":"text_delta","text":"hi"}}',
            "event: message_delta",
            'data: {"delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":4}}',
            "event: message_stop",
            "data: {}",
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
                "id": "msg1",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 1, "output_tokens": 2},
                "stop_reason": "end_turn",
            }
        )

    def stream(self, *args, **kwargs):
        return _StreamCtx()

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_anthropic_contract_success_usage_and_stream(monkeypatch):
    monkeypatch.setattr("app.services.providers.anthropic.httpx.AsyncClient", _Client)
    adapter = AnthropicAdapter()
    raw, usage = await adapter.chat_completions({"model": "claude", "messages": [{"role": "user", "content": "x"}]}, "k", "https://api.anthropic.com")
    assert raw["choices"][0]["message"]["content"] == "ok"
    assert usage["total_tokens"] == 3

    stream = await adapter.stream_chat_completions({"model": "claude", "messages": [{"role": "user", "content": "x"}]}, "k", "https://api.anthropic.com")
    chunks = []
    async for chunk in stream.iterator:
        chunks.append(chunk)
    raw_stream, usage_stream = await stream.finalize()
    assert any("[DONE]" in c for c in chunks)
    assert raw_stream["choices"][0]["message"]["content"] == "hi"
    assert usage_stream["total_tokens"] == 6


def test_anthropic_contract_error_normalization():
    adapter = AnthropicAdapter()
    req = httpx.Request("POST", "https://x")
    assert adapter.normalize_error(httpx.TimeoutException("timeout"))["code"] == "timeout"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(401, request=req)))["code"] == "auth_failed"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(429, request=req)))["code"] == "rate_limited"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(400, request=req)))["code"] == "request_error"
    assert adapter.normalize_error(httpx.HTTPStatusError("x", request=req, response=httpx.Response(503, request=req)))["code"] == "upstream_error"
