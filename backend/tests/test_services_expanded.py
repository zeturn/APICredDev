from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.config import settings
from app.core.secrets import decrypt_secret, encrypt_secret
from app.core.time import format_bucket
from app.db.models.model import Model
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.provider_key import ProviderKey
from app.db.models.usage_session import UsageSession
from app.db.models.user import User
from app.schemas.common import ErrorInfo, ErrorResponse
from app.services import admin_service, token_service, usage_service
from app.services.bootstrap import ensure_admin_user, ensure_default_brands, ensure_default_models, ensure_default_providers, ensure_default_provider_keys
from app.services.providers.anthropic import AnthropicAdapter
from app.services.providers.base import ProviderAdapter
from app.services.providers.factory import get_provider_adapter
from app.services.providers.gemini import GeminiAdapter
from app.services.providers.openai_compat import OpenAICompatAdapter
from app.services.providers.stubs import StubAdapter
from app.services.quota_service import try_reserve
from app.services.routing_service import get_candidates


def test_time_and_common_schema():
    dt = datetime(2026, 2, 16, 9, 8, 7, tzinfo=timezone.utc)
    assert format_bucket(dt, "minute") == "202602160908"
    assert format_bucket(dt, "hour") == "2026021609"
    assert format_bucket(dt, "day") == "20260216"
    assert format_bucket(dt, "month") == "202602"
    with pytest.raises(ValueError):
        format_bucket(dt, "year")

    err = ErrorResponse(error=ErrorInfo(code="bad", message="m", request_id="rid"))
    assert err.error.code == "bad"


class _TestBaseAdapter(ProviderAdapter):
    async def chat_completions(self, payload, api_key, base_url):
        return await super().chat_completions(payload, api_key, base_url)

    def normalize_error(self, exception_or_response):
        return super().normalize_error(exception_or_response)


@pytest.mark.asyncio
async def test_provider_base_and_stub_and_usage_cost():
    adapter = _TestBaseAdapter()
    with pytest.raises(NotImplementedError):
        await adapter.chat_completions({}, "k", "u")
    with pytest.raises(NotImplementedError):
        adapter.normalize_error(Exception("x"))

    stub = StubAdapter()
    data, usage = await stub.chat_completions({}, "k", "u")
    assert data["id"] == "stub"
    assert usage["total_tokens"] == 2
    assert stub.normalize_error(Exception("x"))["retryable"] is False

    model_token = Model(name="m-token", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 2})
    model_req = Model(name="m-req", category="llm", enabled=True, multiplier=1.5, pricing={"unit": "request", "price": 3})
    model_segments = Model(
        name="m-segments",
        category="llm",
        enabled=True,
        multiplier=1,
        pricing={"mode": "token_segments", "input_per_million": 2.5, "cached_input_per_million": 0.25, "output_per_million": 15},
    )
    model_tiered = Model(
        name="m-tiered",
        category="llm",
        enabled=True,
        multiplier=1,
        pricing={
            "mode": "token_segments",
            "input_per_million": 2,
            "output_per_million": 12,
            "tiers": [
                {"max_input_tokens": 200000, "input_per_million": 2, "output_per_million": 12},
                {"min_input_tokens": 200001, "input_per_million": 4, "output_per_million": 18},
            ],
        },
    )
    assert usage_service.estimate_tokens([{"content": "hello"}], 10) >= 10
    assert usage_service.calculate_cost(model_token, 1500, 1) == 4.0
    assert usage_service.calculate_cost(model_req, 10, 2) == 9.0
    assert usage_service.calculate_cost(model_segments, total_tokens=3000, prompt_tokens=2000, completion_tokens=1000) == 0.02
    assert usage_service.calculate_cost(model_segments, total_tokens=3000, prompt_tokens=2000, completion_tokens=1000, cached_input_tokens=1000) == 0.01775
    assert usage_service.calculate_cost(model_tiered, total_tokens=201000, prompt_tokens=201000, completion_tokens=1000) == pytest.approx(0.822)


@pytest.mark.asyncio
async def test_openai_compat_adapter(monkeypatch):
    class _Resp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [], "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers):
            assert url.endswith("/v1/chat/completions")
            assert headers["Authorization"].startswith("Bearer ")
            return _Resp()

    monkeypatch.setattr("app.services.providers.openai_compat.httpx.AsyncClient", lambda *a, **k: _Client())
    adapter = OpenAICompatAdapter()
    _, usage = await adapter.chat_completions({"model": "x"}, "key", "http://base")
    assert usage["total_tokens"] == 3

    req = httpx.Request("POST", "http://test")
    for code, expected in ((401, "auth_failed"), (429, "rate_limited"), (500, "upstream_error")):
        resp = httpx.Response(code, request=req)
        exc = httpx.HTTPStatusError("boom", request=req, response=resp)
        assert adapter.normalize_error(exc)["code"] == expected
    assert adapter.normalize_error(Exception("net"))["code"] == "network_error"


@pytest.mark.asyncio
async def test_openai_compat_adapter_native_stream(monkeypatch):
    chunks = [
        'data: {"id":"cmpl-stream","choices":[{"delta":{"role":"assistant","content":"hel"},"index":0,"finish_reason":null}]}',
        'data: {"id":"cmpl-stream","choices":[{"delta":{"content":"lo"},"index":0,"finish_reason":null}]}',
        'data: {"id":"cmpl-stream","choices":[{"delta":{},"index":0,"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":3,"total_tokens":5}}',
        "data: [DONE]",
    ]

    class _Resp:
        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            for chunk in chunks:
                yield chunk

    class _StreamCtx:
        async def __aenter__(self):
            return _Resp()

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class _Client:
        def stream(self, method, url, json, headers):
            assert method == "POST"
            assert url.endswith("/v1/chat/completions")
            assert json["stream"] is True
            assert json["stream_options"]["include_usage"] is True
            assert headers["Authorization"] == "Bearer key"
            return _StreamCtx()

        async def aclose(self):
            return None

    monkeypatch.setattr("app.services.providers.openai_compat.httpx.AsyncClient", lambda *a, **k: _Client())

    adapter = OpenAICompatAdapter()
    result = await adapter.stream_chat_completions({"model": "x", "messages": [{"role": "user", "content": "hi"}]}, "key", "http://base")
    seen = []
    async for chunk in result.iterator:
        seen.append(chunk)
    raw, usage = await result.finalize()

    assert any("hel" in chunk for chunk in seen)
    assert any("[DONE]" in chunk for chunk in seen)
    assert raw["choices"][0]["message"]["content"] == "hello"
    assert raw["choices"][0]["finish_reason"] == "stop"
    assert usage["total_tokens"] == 5


@pytest.mark.asyncio
async def test_anthropic_and_gemini_adapters_and_factory(monkeypatch):
    class _AnthropicResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "id": "msg_123",
                "content": [{"type": "text", "text": "hello from claude"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 5, "output_tokens": 7},
            }

    class _GeminiResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "responseId": "resp-1",
                "candidates": [
                    {
                        "content": {"parts": [{"text": "hello from gemini"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 4, "totalTokenCount": 7},
            }

    class _AnthropicClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers):
            assert url.endswith("/v1/messages")
            assert headers["x-api-key"] == "claude-key"
            assert json["system"] == "sys"
            return _AnthropicResp()

    class _GeminiClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, params, json, headers):
            assert url.endswith("/v1beta/models/gemini-2.5-pro:generateContent")
            assert params["key"] == "gem-key"
            assert json["systemInstruction"]["parts"][0]["text"] == "sys"
            return _GeminiResp()

    anthropic = AnthropicAdapter()
    gemini = GeminiAdapter()

    monkeypatch.setattr("app.services.providers.anthropic.httpx.AsyncClient", lambda *a, **k: _AnthropicClient())
    raw_a, usage_a = await anthropic.chat_completions(
        {"model": "claude-3-7-sonnet", "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]},
        "claude-key",
        "https://api.anthropic.com",
    )
    assert raw_a["choices"][0]["message"]["content"] == "hello from claude"
    assert usage_a["total_tokens"] == 12

    monkeypatch.setattr("app.services.providers.gemini.httpx.AsyncClient", lambda *a, **k: _GeminiClient())
    raw_g, usage_g = await gemini.chat_completions(
        {"model": "gemini-2.5-pro", "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]},
        "gem-key",
        "https://generativelanguage.googleapis.com",
    )
    assert raw_g["choices"][0]["message"]["content"] == "hello from gemini"
    assert usage_g["total_tokens"] == 7

    assert isinstance(get_provider_adapter("openai"), OpenAICompatAdapter)
    assert isinstance(get_provider_adapter("deepseek"), OpenAICompatAdapter)
    assert isinstance(get_provider_adapter("anthropic"), AnthropicAdapter)
    assert isinstance(get_provider_adapter("gemini"), GeminiAdapter)
    assert isinstance(get_provider_adapter("stub"), StubAdapter)


@pytest.mark.asyncio
async def test_anthropic_and_gemini_native_stream(monkeypatch):
    anthropic_lines = [
        'event: message_start',
        'data: {"type":"message_start","message":{"id":"msg_1","usage":{"input_tokens":4,"output_tokens":1}}}',
        'event: content_block_delta',
        'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}',
        'event: content_block_delta',
        'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" world"}}',
        'event: message_delta',
        'data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":6}}',
        'event: message_stop',
        'data: {"type":"message_stop"}',
    ]

    gemini_lines = [
        'data: {"responseId":"resp-2","candidates":[{"content":{"parts":[{"text":"Hi"}]}}]}',
        'data: {"responseId":"resp-2","candidates":[{"content":{"parts":[{"text":" there"}]},"finishReason":"STOP"}],"usageMetadata":{"promptTokenCount":2,"candidatesTokenCount":3,"totalTokenCount":5}}',
    ]

    class _Resp:
        def __init__(self, lines):
            self._lines = lines

        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            for line in self._lines:
                yield line

    class _StreamCtx:
        def __init__(self, response):
            self._response = response

        async def __aenter__(self):
            return self._response

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class _AnthropicClient:
        def stream(self, method, url, json, headers):
            assert method == "POST"
            assert url.endswith("/v1/messages")
            assert json["stream"] is True
            assert headers["x-api-key"] == "claude-key"
            return _StreamCtx(_Resp(anthropic_lines))

        async def aclose(self):
            return None

    class _GeminiClient:
        def stream(self, method, url, params, json, headers):
            assert method == "POST"
            assert url.endswith(":streamGenerateContent")
            assert params["key"] == "gem-key"
            assert params["alt"] == "sse"
            return _StreamCtx(_Resp(gemini_lines))

        async def aclose(self):
            return None

    monkeypatch.setattr("app.services.providers.anthropic.httpx.AsyncClient", lambda *a, **k: _AnthropicClient())
    anthropic = AnthropicAdapter()
    a_stream = await anthropic.stream_chat_completions(
        {"model": "claude-sonnet", "messages": [{"role": "user", "content": "hi"}]},
        "claude-key",
        "https://api.anthropic.com",
    )
    a_seen = []
    async for chunk in a_stream.iterator:
        a_seen.append(chunk)
    a_raw, a_usage = await a_stream.finalize()
    assert any("Hello" in chunk for chunk in a_seen)
    assert any("[DONE]" in chunk for chunk in a_seen)
    assert a_raw["choices"][0]["message"]["content"] == "Hello world"
    assert a_raw["choices"][0]["finish_reason"] == "end_turn"
    assert a_usage["total_tokens"] == 10

    monkeypatch.setattr("app.services.providers.gemini.httpx.AsyncClient", lambda *a, **k: _GeminiClient())
    gemini = GeminiAdapter()
    g_stream = await gemini.stream_chat_completions(
        {"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "hi"}]},
        "gem-key",
        "https://generativelanguage.googleapis.com",
    )
    g_seen = []
    async for chunk in g_stream.iterator:
        g_seen.append(chunk)
    g_raw, g_usage = await g_stream.finalize()
    assert any("Hi" in chunk for chunk in g_seen)
    assert any("[DONE]" in chunk for chunk in g_seen)
    assert g_raw["choices"][0]["message"]["content"] == "Hi there"
    assert g_raw["choices"][0]["finish_reason"] == "STOP"
    assert g_usage["total_tokens"] == 5


@pytest.mark.asyncio
async def test_quota_try_reserve_and_redis_client(monkeypatch):
    class _FakeRedis:
        def __init__(self):
            self.calls = []

        async def eval(self, script, key_count, *args):
            self.calls.append((script, key_count, args))
            return 1

    fake = _FakeRedis()
    ok = await try_reserve(fake, "pk", "m1", 3, {"minute": 10, "hour": 20, "day": 30, "month": 40})
    assert ok is True
    assert fake.calls and fake.calls[0][1] == 4
    ok2 = await try_reserve(fake, "pk", "m1", 1, {"minute": None, "hour": 1, "day": 1, "month": 1})
    assert ok2 is True

    called = {}

    class _DummyRedis:
        pass

    def _from_url(url, decode_responses):
        called["url"] = url
        called["decode"] = decode_responses
        return _DummyRedis()

    monkeypatch.setattr("app.redis.client.Redis.from_url", _from_url)
    from app.redis.client import get_redis

    obj = get_redis()
    assert isinstance(obj, _DummyRedis)
    assert called["url"] == settings.redis_url
    assert called["decode"] is True


@pytest.mark.asyncio
async def test_admin_token_routing_and_bootstrap_services(db_session):
    await ensure_admin_user(db_session)
    await ensure_admin_user(db_session)
    await ensure_default_brands(db_session)
    await ensure_default_brands(db_session)
    await ensure_default_providers(db_session)
    await ensure_default_providers(db_session)
    await ensure_default_provider_keys(db_session)
    await ensure_default_provider_keys(db_session)
    await ensure_default_models(db_session)
    await ensure_default_models(db_session)
    users = await admin_service.list_users(db_session)
    assert any(u["email"] == settings.admin_email for u in users)
    brands = await admin_service.list_brands(db_session)
    openai_brand = next((b for b in brands if b.slug == "openai"), None)
    assert openai_brand is not None
    provider_keys = await admin_service.list_provider_keys(db_session)
    assert provider_keys == []
    models = await admin_service.list_models(db_session)
    assert any(m.name == "gpt-5.4" for m in models)
    assert any(m.name == "gemini-3.1-pro-preview" for m in models)
    assert any(m.name == "claude-sonnet-4.6" for m in models)

    model = await admin_service.upsert_model(
        db_session,
        {"name": "model-a", "brand_id": openai_brand.id, "category": "llm", "enabled": True, "multiplier": 1.0, "pricing": {"unit": "1k_tokens", "price": 1}},
    )
    model2 = await admin_service.upsert_model(
        db_session,
        {"id": model.id, "name": "model-a", "brand_id": openai_brand.id, "category": "llm", "enabled": False, "multiplier": 2.0, "pricing": {"unit": "request", "price": 3}},
    )
    assert model2.enabled is False
    assert len(await admin_service.list_models(db_session)) >= 1

    pkey = await admin_service.upsert_provider_key(
        db_session,
        {
            "provider": "openai",
            "key_name": "base",
            "api_key": "sk-test-openai-1234",
            "enabled": True,
            "health_state": "healthy",
            "cooldown_until": None,
        },
    )
    pkey2 = await admin_service.upsert_provider_key(
        db_session,
        {
            "id": pkey.id,
            "provider": "openai",
            "key_name": "base-2",
            "api_key": "sk-test-openai-9876",
            "enabled": True,
            "health_state": "healthy",
            "cooldown_until": None,
        },
    )
    assert pkey2.key_name == "base-2"
    assert pkey2.secret_last4 == "9876"
    assert decrypt_secret(pkey2.secret_encrypted) == "sk-test-openai-9876"
    assert len(await admin_service.list_provider_keys(db_session)) >= 1

    class _Resp:
        def __init__(self, status_code=200, payload=None):
            self.status_code = status_code
            self._payload = payload or {"data": [{"id": "m1"}]}
            self.headers = {"content-type": "application/json"}

        def json(self):
            return self._payload

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None, params=None):
            assert url.endswith("/v1/models")
            assert headers["Authorization"].startswith("Bearer ")
            return _Resp()

    from app.services import admin_service as admin_service_module

    admin_service_module.httpx.AsyncClient = lambda timeout=20: _Client()
    validation = await admin_service.validate_provider_key(db_session, pkey2.id)
    assert validation["ok"] is True
    assert validation["model_count"] == 1

    mpk = await admin_service.upsert_model_provider_key(
        db_session,
        {
            "model_id": model.id,
            "provider_key_id": pkey.id,
            "enabled": True,
            "priority": 1,
            "quota_unit": "requests",
            "quota_rules": {"minute": 100},
        },
    )
    mpk2 = await admin_service.upsert_model_provider_key(
        db_session,
        {
            "id": mpk.id,
            "model_id": model.id,
            "provider_key_id": pkey.id,
            "enabled": False,
            "priority": 2,
            "quota_unit": "tokens",
            "quota_rules": {"minute": 200},
        },
    )
    assert mpk2.priority == 2
    assert len(await admin_service.list_model_provider_keys(db_session)) >= 1

    us = UsageSession(
        user_id=users[0]["id"],
        token_id="t1",
        request_id="r1",
        model_id=model.id,
        status="completed",
        estimated_cost_credits=1,
        final_cost_credits=1,
        usage={},
    )
    db_session.add(us)
    await db_session.commit()
    assert len(await admin_service.list_usage_sessions(db_session)) >= 1

    user = User(email="token-user@example.com", password_hash="x", status="active")
    db_session.add(user)
    await db_session.commit()
    token, raw = await token_service.create_token(db_session, user.id, "sdk", ["llm"])
    assert raw
    assert len(await token_service.list_tokens(db_session, user.id)) == 1
    await token_service.revoke_token(db_session, user.id, token.id)
    with pytest.raises(ValueError):
        await token_service.revoke_token(db_session, "other", token.id)


@pytest.mark.asyncio
async def test_routing_service_branches(db_session):
    model = Model(name="route-model", category="llm", enabled=True, multiplier=1, pricing={})
    db_session.add(model)
    await db_session.commit()

    p_disabled = ProviderKey(provider="x", key_name="a", secret_encrypted=encrypt_secret("A"), secret_last4="A", enabled=True, health_state="disabled")
    p_cool = ProviderKey(
        provider="x",
        key_name="b",
        secret_encrypted=encrypt_secret("B"),
        secret_last4="B",
        enabled=True,
        health_state="healthy",
        cooldown_until=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    p_ok = ProviderKey(provider="x", key_name="c", secret_encrypted=encrypt_secret("C"), secret_last4="C", enabled=True, health_state="healthy", cooldown_until=datetime.now(timezone.utc) - timedelta(minutes=1))
    db_session.add_all([p_disabled, p_cool, p_ok])
    await db_session.commit()

    db_session.add_all(
        [
            ModelProviderKey(model_id=model.id, provider_key_id=p_disabled.id, enabled=True, priority=1, quota_unit="requests", quota_rules={}),
            ModelProviderKey(model_id=model.id, provider_key_id=p_cool.id, enabled=True, priority=2, quota_unit="requests", quota_rules={}),
            ModelProviderKey(model_id=model.id, provider_key_id=p_ok.id, enabled=True, priority=3, quota_unit="requests", quota_rules={}),
        ]
    )
    await db_session.commit()

    candidates = await get_candidates(db_session, model.id)
    assert len(candidates) == 1
    assert candidates[0].provider_key.id == p_ok.id

