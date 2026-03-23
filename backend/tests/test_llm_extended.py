from __future__ import annotations

import os
from types import SimpleNamespace

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.deps import get_bearer_token, get_db
from app.db.models.model import Model
from app.db.models.provider_key import ProviderKey
from app.main import create_app


class _FakeRedis:
    async def aclose(self):
        return None


def _fake_token():
    return SimpleNamespace(user_id="user-llm", id="token-llm", scopes=["llm"])


def _mk_candidate(provider_key):
    return SimpleNamespace(
        provider_key=provider_key,
        mpk=SimpleNamespace(quota_unit="requests", quota_rules={"minute": 100}),
    )


@pytest.mark.asyncio
async def test_llm_model_missing_returns_404(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_bearer_token] = _fake_token
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/chat/completions",
            json={"model": "missing", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_llm_insufficient_balance_and_no_candidates(db_session, monkeypatch):
    app = create_app()
    model = Model(name="llm-m1", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 1})
    db_session.add(model)
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_bearer_token] = _fake_token
    monkeypatch.setattr("app.api.v1.llm.get_redis", lambda: _FakeRedis())
    transport = ASGITransport(app=app)

    async def _raise_balance(*args, **kwargs):
        raise ValueError("insufficient_balance")

    monkeypatch.setattr("app.api.v1.llm.authorize_usage", _raise_balance)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        insufficient = await client.post(
            "/v1/chat/completions",
            json={"model": "llm-m1", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert insufficient.status_code == 402

    usage = SimpleNamespace(id="u-1", status="started", user_id="user-llm", estimated_cost_credits=1)
    called = {"settled": False}

    async def _authorize_ok(*args, **kwargs):
        return usage

    async def _settle(*args, **kwargs):
        called["settled"] = True

    monkeypatch.setattr("app.api.v1.llm.authorize_usage", _authorize_ok)
    async def _no_candidates(db, model_id):
        return []

    monkeypatch.setattr("app.api.v1.llm.get_candidates", _no_candidates)
    monkeypatch.setattr("app.api.v1.llm.settle_usage", _settle)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        no_cap = await client.post(
            "/v1/chat/completions",
            json={"model": "llm-m1", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert no_cap.status_code == 503
        assert called["settled"] is True


@pytest.mark.asyncio
async def test_llm_success_and_upstream_failures(db_session, monkeypatch):
    app = create_app()
    model = Model(name="llm-m2", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 1})
    pkey = ProviderKey(provider="openai", key_name="http://upstream", secret_ref="OPENAI_TEST_KEY", enabled=True, health_state="healthy")
    db_session.add_all([model, pkey])
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_bearer_token] = _fake_token
    monkeypatch.setattr("app.api.v1.llm.get_redis", lambda: _FakeRedis())
    async def _reserve(*args, **kwargs):
        return True

    monkeypatch.setattr("app.api.v1.llm.try_reserve", _reserve)

    usage = SimpleNamespace(
        id="u-2",
        status="started",
        user_id="user-llm",
        estimated_cost_credits=1,
        upstream_provider=None,
        upstream_key_id=None,
    )

    async def _authorize_ok(*args, **kwargs):
        return usage

    async def _settle(*args, **kwargs):
        return None

    monkeypatch.setattr("app.api.v1.llm.authorize_usage", _authorize_ok)
    monkeypatch.setattr("app.api.v1.llm.settle_usage", _settle)
    async def _candidates(db, model_id):
        return [_mk_candidate(pkey)]

    monkeypatch.setattr("app.api.v1.llm.get_candidates", _candidates)

    async def _chat_ok(self, payload, api_key, base_url):
        assert base_url == "http://upstream"
        return (
            {"id": "cmpl-1", "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]},
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    monkeypatch.setattr("app.api.v1.llm.OpenAICompatAdapter.chat_completions", _chat_ok)
    os.environ["OPENAI_TEST_KEY"] = "sk-test"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        success = await client.post(
            "/v1/chat/completions",
            json={"model": "llm-m2", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert success.status_code == 200
        assert success.json()["usage"]["total_tokens"] == 2

    req = httpx.Request("POST", "http://test")
    resp = httpx.Response(401, request=req)
    status_exc = httpx.HTTPStatusError("boom", request=req, response=resp)

    async def _chat_status_error(self, payload, api_key, base_url):
        raise status_exc

    def _normalize_non_retry(self, exc):
        return {"code": "auth_failed", "retryable": False, "cooldown_seconds": 1}

    monkeypatch.setattr("app.api.v1.llm.OpenAICompatAdapter.chat_completions", _chat_status_error)
    monkeypatch.setattr("app.api.v1.llm.OpenAICompatAdapter.normalize_error", _normalize_non_retry)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        failed = await client.post(
            "/v1/chat/completions",
            json={"model": "llm-m2", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert failed.status_code == 502

    async def _chat_exception(self, payload, api_key, base_url):
        raise RuntimeError("network")

    def _normalize_retry(self, exc):
        return {"code": "upstream_error", "retryable": True, "cooldown_seconds": 1}

    monkeypatch.setattr("app.api.v1.llm.OpenAICompatAdapter.chat_completions", _chat_exception)
    monkeypatch.setattr("app.api.v1.llm.OpenAICompatAdapter.normalize_error", _normalize_retry)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        failed2 = await client.post(
            "/v1/chat/completions",
            json={"model": "llm-m2", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert failed2.status_code == 502

