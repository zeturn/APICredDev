from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.config import settings
from app.core.time import format_bucket
from app.db.models.model import Model
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.provider_key import ProviderKey
from app.db.models.usage_session import UsageSession
from app.db.models.user import User
from app.schemas.common import ErrorInfo, ErrorResponse
from app.services import admin_service, token_service, usage_service
from app.services.bootstrap import ensure_admin_user
from app.services.providers.base import ProviderAdapter
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
    assert usage_service.estimate_tokens([{"content": "hello"}], 10) >= 10
    assert usage_service.calculate_cost(model_token, 1500, 1) == 4.0
    assert usage_service.calculate_cost(model_req, 10, 2) == 9.0


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
    users = await admin_service.list_users(db_session)
    assert any(u.email == settings.admin_email for u in users)

    model = await admin_service.upsert_model(
        db_session,
        {"name": "model-a", "category": "llm", "enabled": True, "multiplier": 1.0, "pricing": {"unit": "1k_tokens", "price": 1}},
    )
    model2 = await admin_service.upsert_model(
        db_session,
        {"id": model.id, "name": "model-a", "category": "llm", "enabled": False, "multiplier": 2.0, "pricing": {"unit": "request", "price": 3}},
    )
    assert model2.enabled is False
    assert len(await admin_service.list_models(db_session)) >= 1

    pkey = await admin_service.upsert_provider_key(
        db_session,
        {
            "provider": "openai",
            "key_name": "base",
            "secret_ref": "OPENAI_KEY",
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
            "secret_ref": "OPENAI_KEY",
            "enabled": True,
            "health_state": "healthy",
            "cooldown_until": None,
        },
    )
    assert pkey2.key_name == "base-2"
    assert len(await admin_service.list_provider_keys(db_session)) >= 1

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
        user_id=users[0].id,
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

    p_disabled = ProviderKey(provider="x", key_name="a", secret_ref="A", enabled=True, health_state="disabled")
    p_cool = ProviderKey(
        provider="x",
        key_name="b",
        secret_ref="B",
        enabled=True,
        health_state="healthy",
        cooldown_until=datetime.now() + timedelta(minutes=30),
    )
    p_ok = ProviderKey(provider="x", key_name="c", secret_ref="C", enabled=True, health_state="healthy", cooldown_until=datetime.now(timezone.utc) - timedelta(minutes=1))
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

