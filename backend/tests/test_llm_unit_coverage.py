from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.api.v1 import llm as llm_module
from app.core.secrets import encrypt_secret
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
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


def test_openai_compat_5xx_is_retryable_without_credential_cooldown():
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


async def _noop(*args, **kwargs):
    return None


async def _true(*args, **kwargs):
    return True


async def _create_route(db_session, slug="llm-unit", provider_slug="openai", upstream_name="gpt-test"):
    provider = Provider(slug=provider_slug, name=provider_slug, default_base_url="http://base", enabled=True)
    public_model = PublicModel(slug=slug, display_name=slug, category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 1})
    db_session.add_all([provider, public_model])
    await db_session.commit()
    await db_session.refresh(provider)
    await db_session.refresh(public_model)

    upstream_model = UpstreamModel(provider_id=provider.id, upstream_name=upstream_name, display_name=upstream_name, capabilities={}, default_pricing={}, enabled=True)
    credential = ProviderCredential(provider_id=provider.id, display_name="cred", secret_encrypted=encrypt_secret("sk-unit"), secret_last4="unit", enabled=True, health_state="healthy")
    db_session.add_all([upstream_model, credential])
    await db_session.commit()
    await db_session.refresh(upstream_model)
    await db_session.refresh(credential)

    route = ModelRoute(
        public_model_id=public_model.id,
        upstream_model_id=upstream_model.id,
        provider_credential_id=credential.id,
        enabled=True,
        priority=1,
        weight=1,
        quota_unit="requests",
        quota_rules={},
    )
    db_session.add(route)
    await db_session.commit()
    await db_session.refresh(route)
    return public_model, credential, route


@pytest.mark.asyncio
async def test_llm_unit_model_missing(db_session, monkeypatch):
    monkeypatch.setattr(llm_module, "require_scopes", _noop)
    payload = ChatCompletionRequest(model="missing", messages=[{"role": "user", "content": "x"}])
    with pytest.raises(Exception):
        await llm_module.chat_completions(_req(), payload, db_session, _token())


@pytest.mark.asyncio
async def test_llm_unit_insufficient_and_no_candidates(db_session, monkeypatch):
    await _create_route(db_session, slug="llm-unit-1")

    async def _raise_balance(*args, **kwargs):
        raise ValueError("insufficient_balance")

    monkeypatch.setattr(llm_module, "require_scopes", _noop)
    monkeypatch.setattr(llm_module, "authorize_usage", _raise_balance)
    payload = ChatCompletionRequest(model="llm-unit-1", messages=[{"role": "user", "content": "hello"}])
    with pytest.raises(Exception):
        await llm_module.chat_completions(_req(), payload, db_session, _token())

    usage = SimpleNamespace(id="usage-1", status="started", user_id="u-llm", estimated_cost_credits=1)

    async def _authorize(*args, **kwargs):
        return usage

    monkeypatch.setattr(llm_module, "authorize_usage", _authorize)
    async def _no_candidates(*args, **kwargs):
        return []

    monkeypatch.setattr(llm_module, "get_route_candidates", _no_candidates)
    monkeypatch.setattr(llm_module, "settle_usage", _noop)
    with pytest.raises(Exception):
        await llm_module.chat_completions(_req(), payload, db_session, _token())


@pytest.mark.asyncio
async def test_llm_unit_success_uses_public_route_and_credential(db_session, monkeypatch):
    _, _, _ = await _create_route(db_session, slug="llm-unit-2", upstream_name="gpt-upstream")
    usage = SimpleNamespace(id="usage-2", status="started", user_id="u-llm", estimated_cost_credits=1, upstream_provider=None, upstream_credential_id=None)
    fake_redis = _FakeRedis()

    async def _chat(payload, api_key, base_url):
        assert payload["model"] == "gpt-upstream"
        assert api_key == "sk-unit"
        assert base_url == "http://base"
        return (
            {"id": "cmpl-unit", "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]},
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    async def _authorize(*args, **kwargs):
        return usage

    monkeypatch.setattr(llm_module, "require_scopes", _noop)
    monkeypatch.setattr(llm_module, "authorize_usage", _authorize)
    monkeypatch.setattr(llm_module, "settle_usage", _noop)
    monkeypatch.setattr(llm_module, "try_reserve", _true)
    monkeypatch.setattr(llm_module, "get_redis", lambda: fake_redis)
    monkeypatch.setattr(llm_module, "get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat))

    resp = await llm_module.chat_completions(_req(), ChatCompletionRequest(model="llm-unit-2", messages=[{"role": "user", "content": "hello"}]), db_session, _token())
    assert resp.id == "cmpl-unit"
    assert fake_redis.closed is True


@pytest.mark.asyncio
async def test_llm_unit_http_error_disables_credential(db_session, monkeypatch):
    _, credential, _ = await _create_route(db_session, slug="llm-unit-3")
    usage = SimpleNamespace(id="usage-3", status="started", user_id="u-llm", estimated_cost_credits=1, upstream_provider=None, upstream_credential_id=None)

    req = httpx.Request("POST", "http://test")
    exc = httpx.HTTPStatusError("boom", request=req, response=httpx.Response(401, request=req))

    async def _chat_http(payload, api_key, base_url):
        raise exc

    async def _authorize(*args, **kwargs):
        return usage

    monkeypatch.setattr(llm_module, "require_scopes", _noop)
    monkeypatch.setattr(llm_module, "authorize_usage", _authorize)
    monkeypatch.setattr(llm_module, "settle_usage", _noop)
    monkeypatch.setattr(llm_module, "try_reserve", _true)
    monkeypatch.setattr(llm_module, "get_redis", lambda: _FakeRedis())
    monkeypatch.setattr(llm_module, "get_provider_adapter", lambda provider: _Adapter(chat_impl=_chat_http, normalize_impl=lambda err: {"code": "auth_failed", "retryable": False, "cooldown_seconds": 0}))

    with pytest.raises(Exception):
        await llm_module.chat_completions(_req(), ChatCompletionRequest(model="llm-unit-3", messages=[{"role": "user", "content": "hello"}]), db_session, _token())
    assert credential.health_state == "disabled"
