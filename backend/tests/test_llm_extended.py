from __future__ import annotations

import os
import json
from types import SimpleNamespace

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.secrets import encrypt_secret
from app.core.deps import get_bearer_token, get_db
from app.db.models.model_route import ModelRoute
from app.db.models.model import Model
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_key import ProviderKey
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.main import create_app


class _FakeRedis:
    async def aclose(self):
        return None


def _fake_token():
    return SimpleNamespace(user_id="user-llm", id="token-llm", scopes=["llm"])


async def _await(value):
    return value


def _mk_candidate(provider_key):
    return SimpleNamespace(
        provider_key=provider_key,
        mpk=SimpleNamespace(quota_unit="requests", quota_rules={"minute": 100}),
    )


class _Adapter:
    def __init__(self, chat_impl=None, normalize_impl=None):
        self._chat_impl = chat_impl
        self._normalize_impl = normalize_impl or (lambda exc: {"code": "upstream_error", "retryable": True, "cooldown_seconds": 1})

    async def chat_completions(self, payload, api_key, base_url):
        return await self._chat_impl(payload, api_key, base_url)

    async def stream_chat_completions(self, payload, api_key, base_url):
        raw, usage = await self._chat_impl(payload, api_key, base_url)

        async def _iterator():
            first_chunk = {
                "id": raw["id"],
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": raw["choices"][0]["message"]["content"]}, "finish_reason": None}],
            }
            final_chunk = {
                "id": raw["id"],
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {}, "finish_reason": raw["choices"][0].get("finish_reason")}],
            }
            yield f"data: {json.dumps(first_chunk)}\n\n"
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        async def _finalize():
            return raw, usage

        return SimpleNamespace(iterator=_iterator(), finalize=_finalize)

    def normalize_error(self, exc):
        return self._normalize_impl(exc)


@pytest.mark.asyncio
async def test_llm_routes_public_model_to_upstream_model(db_session, monkeypatch):
    app = create_app()
    provider = Provider(name="OpenAI", slug="openai", default_base_url="https://api.openai.com", enabled=True)
    public_model = PublicModel(
        slug="apicred-fast",
        display_name="APICred Fast",
        category="llm",
        pricing={"mode": "free"},
        enabled=True,
    )
    db_session.add_all([provider, public_model])
    await db_session.commit()
    await db_session.refresh(provider)
    await db_session.refresh(public_model)

    upstream_model = UpstreamModel(
        provider_id=provider.id,
        upstream_name="gpt-4o-mini",
        display_name="GPT-4o mini",
        context_window=128000,
        capabilities={"chat": True},
        default_pricing={},
        enabled=True,
    )
    credential = ProviderCredential(
        provider_id=provider.id,
        display_name="openai-main-key",
        secret_encrypted=encrypt_secret("sk-route"),
        secret_last4="oute",
        enabled=True,
        health_state="healthy",
    )
    db_session.add_all([upstream_model, credential])
    await db_session.commit()
    await db_session.refresh(upstream_model)
    await db_session.refresh(credential)
    db_session.add(
        ModelRoute(
            public_model_id=public_model.id,
            upstream_model_id=upstream_model.id,
            provider_credential_id=credential.id,
            base_url_override="https://api.openai.com",
            enabled=True,
            priority=1,
            weight=1,
            quota_unit="requests",
            quota_rules={},
        )
    )
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_bearer_token] = _fake_token
    monkeypatch.setattr("app.api.v1.llm.get_redis", lambda: _FakeRedis())
    monkeypatch.setattr("app.api.v1.llm.try_reserve", lambda *args, **kwargs: _await(True))
    usage = SimpleNamespace(
        id="usage-route",
        status="started",
        user_id="user-llm",
        estimated_cost_credits=0,
        upstream_provider=None,
        upstream_key_id=None,
    )
    monkeypatch.setattr("app.api.v1.llm.authorize_usage", lambda *args, **kwargs: _await(usage))
    monkeypatch.setattr("app.api.v1.llm.settle_usage", lambda *args, **kwargs: _await(None))

    async def _chat_ok(payload, api_key, base_url):
        assert payload["model"] == "gpt-4o-mini"
        assert api_key == "sk-route"
        assert base_url == "https://api.openai.com"
        return (
            {"id": "cmpl-route", "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]},
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    monkeypatch.setattr("app.api.v1.llm.get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat_ok))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/chat/completions",
            json={"model": "apicred-fast", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == "cmpl-route"


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
    pkey = ProviderKey(provider="openai", key_name="http://upstream", secret_encrypted=encrypt_secret("sk-test"), secret_last4="test", enabled=True, health_state="healthy")
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

    async def _chat_ok(payload, api_key, base_url):
        assert base_url == "http://upstream"
        return (
            {"id": "cmpl-1", "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]},
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    monkeypatch.setattr("app.api.v1.llm.get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat_ok))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        success = await client.post(
            "/v1/chat/completions",
            json={"model": "llm-m2", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert success.status_code == 200
        assert success.json()["usage"]["total_tokens"] == 2

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            json={"model": "llm-m2", "stream": True, "messages": [{"role": "user", "content": "hello"}]},
        ) as streamed:
            body = await streamed.aread()
            text = body.decode("utf-8")
            assert streamed.status_code == 200
            assert "text/event-stream" in streamed.headers["content-type"]
            assert '"chat.completion.chunk"' in text
            assert "ok" in text
            assert "[DONE]" in text

    req = httpx.Request("POST", "http://test")
    resp = httpx.Response(401, request=req)
    status_exc = httpx.HTTPStatusError("boom", request=req, response=resp)

    async def _chat_status_error(payload, api_key, base_url):
        raise status_exc

    def _normalize_non_retry(exc):
        return {"code": "auth_failed", "retryable": False, "cooldown_seconds": 1}

    monkeypatch.setattr("app.api.v1.llm.get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat_status_error, normalize_impl=_normalize_non_retry))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        failed = await client.post(
            "/v1/chat/completions",
            json={"model": "llm-m2", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert failed.status_code == 502

    async def _chat_exception(payload, api_key, base_url):
        raise RuntimeError("network")

    def _normalize_retry(exc):
        return {"code": "upstream_error", "retryable": True, "cooldown_seconds": 1}

    monkeypatch.setattr("app.api.v1.llm.get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat_exception, normalize_impl=_normalize_retry))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        failed2 = await client.post(
            "/v1/chat/completions",
            json={"model": "llm-m2", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert failed2.status_code == 502

