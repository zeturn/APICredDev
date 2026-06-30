from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.api.v1 import llm as llm_module
from app.core.secrets import encrypt_secret
from app.db.models.model import Model
from app.db.models.provider_key import ProviderKey
from app.schemas.llm import ChatCompletionRequest
from app.services.providers.openai_compat import OpenAICompatAdapter


class _FakeRedis:
    def __init__(self):
        self.closed = False

    async def aclose(self):
        self.closed = True


class _Adapter:
    def __init__(self, chat_impl=None, normalize_impl=None):
        self._chat_impl = chat_impl
        self._normalize_impl = normalize_impl or (lambda exc: {"code": "upstream_error", "retryable": True, "cooldown_seconds": 1})

    async def chat_completions(self, payload, api_key, base_url):
        return await self._chat_impl(payload, api_key, base_url)

    def normalize_error(self, exc):
        return self._normalize_impl(exc)


def test_openai_compat_5xx_is_retryable_without_key_cooldown():
    req = httpx.Request("POST", "http://upstream/v1/chat/completions")
    exc = httpx.HTTPStatusError("bad gateway", request=req, response=httpx.Response(502, request=req, text="bad gateway"))

    info = OpenAICompatAdapter().normalize_error(exc)

    assert info["code"] == "upstream_error"
    assert info["retryable"] is True
    assert info["cooldown_seconds"] == 0


def _req():
    return SimpleNamespace(state=SimpleNamespace(request_id=uuid4()))


def _token():
    return SimpleNamespace(user_id="u-llm", id="t-llm", scopes=["llm"])


@pytest.mark.asyncio
async def test_llm_unit_model_missing(db_session, monkeypatch):
    async def _require_scopes(required, token, request):
        return None

    monkeypatch.setattr(llm_module, "require_scopes", _require_scopes)
    payload = ChatCompletionRequest(model="missing", messages=[{"role": "user", "content": "x"}])
    with pytest.raises(Exception):
        await llm_module.chat_completions(_req(), payload, db_session, _token())


@pytest.mark.asyncio
async def test_llm_unit_insufficient_and_no_candidates(db_session, monkeypatch):
    model = Model(name="llm-unit-1", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 1})
    db_session.add(model)
    await db_session.commit()

    async def _require_scopes(required, token, request):
        return None

    async def _raise_balance(*args, **kwargs):
        raise ValueError("insufficient_balance")

    monkeypatch.setattr(llm_module, "require_scopes", _require_scopes)
    monkeypatch.setattr(llm_module, "authorize_usage", _raise_balance)
    payload = ChatCompletionRequest(model="llm-unit-1", messages=[{"role": "user", "content": "hello"}])
    with pytest.raises(Exception):
        await llm_module.chat_completions(_req(), payload, db_session, _token())

    usage = SimpleNamespace(id="usage-1", status="started", user_id="u-llm", estimated_cost_credits=1)

    async def _authorize(*args, **kwargs):
        return usage

    async def _candidates(*args, **kwargs):
        return []

    async def _settle(*args, **kwargs):
        return None

    monkeypatch.setattr(llm_module, "authorize_usage", _authorize)
    monkeypatch.setattr(llm_module, "get_candidates", _candidates)
    monkeypatch.setattr(llm_module, "settle_usage", _settle)
    with pytest.raises(Exception):
        await llm_module.chat_completions(_req(), payload, db_session, _token())


@pytest.mark.asyncio
async def test_llm_unit_success_and_reserve_continue(db_session, monkeypatch):
    model = Model(name="llm-unit-2", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 1})
    pkey = ProviderKey(provider="openai", key_name="http://base", secret_encrypted=encrypt_secret("sk-unit"), secret_last4="unit", enabled=True, health_state="healthy")
    db_session.add_all([model, pkey])
    await db_session.commit()

    usage = SimpleNamespace(
        id="usage-2",
        status="started",
        user_id="u-llm",
        estimated_cost_credits=1,
        upstream_provider=None,
        upstream_key_id=None,
    )
    fake_redis = _FakeRedis()

    async def _require_scopes(required, token, request):
        return None

    async def _authorize(*args, **kwargs):
        return usage

    async def _settle(*args, **kwargs):
        return None

    candidate = SimpleNamespace(
        provider_key=pkey,
        mpk=SimpleNamespace(quota_unit="requests", quota_rules={"minute": 100}),
    )

    async def _candidates(*args, **kwargs):
        return [candidate]

    reserve_calls = {"count": 0}

    async def _reserve(*args, **kwargs):
        reserve_calls["count"] += 1
        return reserve_calls["count"] >= 1

    async def _chat(payload, api_key, base_url):
        return (
            {"id": "cmpl-unit", "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]},
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    monkeypatch.setattr(llm_module, "require_scopes", _require_scopes)
    monkeypatch.setattr(llm_module, "authorize_usage", _authorize)
    monkeypatch.setattr(llm_module, "settle_usage", _settle)
    monkeypatch.setattr(llm_module, "get_candidates", _candidates)
    monkeypatch.setattr(llm_module, "try_reserve", _reserve)
    monkeypatch.setattr(llm_module, "get_redis", lambda: fake_redis)
    monkeypatch.setattr(llm_module, "get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat))

    payload = ChatCompletionRequest(model="llm-unit-2", messages=[{"role": "user", "content": "hello"}])
    resp = await llm_module.chat_completions(_req(), payload, db_session, _token())
    assert resp.id == "cmpl-unit"
    assert fake_redis.closed is True


@pytest.mark.asyncio
async def test_llm_unit_deepseek_product_model_maps_to_upstream_model(db_session, monkeypatch):
    model = Model(name="deepseek-v4-pro", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 1})
    pkey = ProviderKey(provider="deepseek", key_name="http://deepseek", secret_encrypted=encrypt_secret("sk-deepseek"), secret_last4="seek", enabled=True, health_state="healthy")
    db_session.add_all([model, pkey])
    await db_session.commit()

    usage = SimpleNamespace(
        id="usage-deepseek",
        status="started",
        user_id="u-llm",
        estimated_cost_credits=1,
        upstream_provider=None,
        upstream_key_id=None,
    )
    candidate = SimpleNamespace(
        provider_key=pkey,
        mpk=SimpleNamespace(quota_unit="requests", quota_rules={}),
    )
    seen_payloads = []

    async def _require_scopes(required, token, request):
        return None

    async def _authorize(*args, **kwargs):
        return usage

    async def _settle(*args, **kwargs):
        return None

    async def _candidates(*args, **kwargs):
        return [candidate]

    async def _reserve(*args, **kwargs):
        return True

    async def _chat(payload, api_key, base_url):
        seen_payloads.append(dict(payload))
        return (
            {"id": "cmpl-deepseek", "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]},
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    monkeypatch.setattr(llm_module, "require_scopes", _require_scopes)
    monkeypatch.setattr(llm_module, "authorize_usage", _authorize)
    monkeypatch.setattr(llm_module, "settle_usage", _settle)
    monkeypatch.setattr(llm_module, "get_candidates", _candidates)
    monkeypatch.setattr(llm_module, "try_reserve", _reserve)
    monkeypatch.setattr(llm_module, "get_redis", lambda: _FakeRedis())
    monkeypatch.setattr(llm_module, "get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat))

    payload = ChatCompletionRequest(model="deepseek-v4-pro", messages=[{"role": "user", "content": "hello"}])
    resp = await llm_module.chat_completions(_req(), payload, db_session, _token())

    assert resp.id == "cmpl-deepseek"
    assert seen_payloads[0]["model"] == "deepseek-chat"


@pytest.mark.asyncio
async def test_llm_unit_http_and_generic_errors_and_cooldown(db_session, monkeypatch):
    model = Model(name="llm-unit-3", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 1})
    pkey = ProviderKey(provider="openai", key_name="http://base", secret_encrypted=encrypt_secret("sk-unit-2"), secret_last4="it-2", enabled=True, health_state="healthy")
    db_session.add_all([model, pkey])
    await db_session.commit()

    usage = SimpleNamespace(
        id="usage-3",
        status="started",
        user_id="u-llm",
        estimated_cost_credits=1,
        upstream_provider=None,
        upstream_key_id=None,
    )
    candidate = SimpleNamespace(
        provider_key=pkey,
        mpk=SimpleNamespace(quota_unit="tokens", quota_rules={"minute": 100}),
    )

    async def _require_scopes(required, token, request):
        return None

    async def _authorize(*args, **kwargs):
        return usage

    async def _settle(*args, **kwargs):
        return None

    async def _candidates(*args, **kwargs):
        return [candidate]

    async def _reserve(*args, **kwargs):
        return True

    monkeypatch.setattr(llm_module, "require_scopes", _require_scopes)
    monkeypatch.setattr(llm_module, "authorize_usage", _authorize)
    monkeypatch.setattr(llm_module, "settle_usage", _settle)
    monkeypatch.setattr(llm_module, "get_candidates", _candidates)
    monkeypatch.setattr(llm_module, "try_reserve", _reserve)
    monkeypatch.setattr(llm_module, "get_redis", lambda: _FakeRedis())

    req = httpx.Request("POST", "http://test")
    exc = httpx.HTTPStatusError("boom", request=req, response=httpx.Response(401, request=req))

    async def _chat_http(payload, api_key, base_url):
        raise exc

    def _normalize_http(err):
        return {"code": "auth_failed", "retryable": False, "cooldown_seconds": 0}

    monkeypatch.setattr(llm_module, "get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat_http, normalize_impl=_normalize_http))
    payload = ChatCompletionRequest(model="llm-unit-3", messages=[{"role": "user", "content": "hello"}])
    with pytest.raises(Exception):
        await llm_module.chat_completions(_req(), payload, db_session, _token())
    assert pkey.health_state == "disabled"

    async def _chat_generic(payload, api_key, base_url):
        raise RuntimeError("network")

    def _normalize_generic(err):
        return {"code": "upstream_error", "retryable": True, "cooldown_seconds": 1}

    monkeypatch.setattr(llm_module, "get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat_generic, normalize_impl=_normalize_generic))
    with pytest.raises(Exception):
        await llm_module.chat_completions(_req(), payload, db_session, _token())


@pytest.mark.asyncio
async def test_llm_unit_attempt_limit_and_reserve_continue(db_session, monkeypatch):
    model = Model(name="llm-unit-4", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 1})
    pkey = ProviderKey(provider="openai", key_name="http://base", secret_encrypted=encrypt_secret("sk-unit-3"), secret_last4="it-3", enabled=True, health_state="healthy")
    db_session.add_all([model, pkey])
    await db_session.commit()

    usage = SimpleNamespace(
        id="usage-4",
        status="started",
        user_id="u-llm",
        estimated_cost_credits=1,
        upstream_provider=None,
        upstream_key_id=None,
    )
    candidate = SimpleNamespace(
        provider_key=pkey,
        mpk=SimpleNamespace(quota_unit="requests", quota_rules={"minute": 100}),
    )

    async def _require_scopes(required, token, request):
        return None

    async def _authorize(*args, **kwargs):
        return usage

    async def _settle(*args, **kwargs):
        return None

    async def _candidates(*args, **kwargs):
        return [candidate]

    async def _reserve_false(*args, **kwargs):
        return False

    monkeypatch.setattr(llm_module, "require_scopes", _require_scopes)
    monkeypatch.setattr(llm_module, "authorize_usage", _authorize)
    monkeypatch.setattr(llm_module, "settle_usage", _settle)
    monkeypatch.setattr(llm_module, "get_candidates", _candidates)
    monkeypatch.setattr(llm_module, "try_reserve", _reserve_false)
    monkeypatch.setattr(llm_module, "get_redis", lambda: _FakeRedis())
    with pytest.raises(Exception):
        await llm_module.chat_completions(
            _req(),
            ChatCompletionRequest(model="llm-unit-4", messages=[{"role": "user", "content": "x"}]),
            db_session,
            _token(),
        )

    old_max = llm_module.settings.max_key_attempts
    llm_module.settings.max_key_attempts = 0
    try:
        with pytest.raises(Exception):
            await llm_module.chat_completions(
                _req(),
                ChatCompletionRequest(model="llm-unit-4", messages=[{"role": "user", "content": "x"}]),
                db_session,
                _token(),
            )
    finally:
        llm_module.settings.max_key_attempts = old_max
