from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.deps import get_bearer_token, get_db
from app.core.secrets import encrypt_secret
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
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


class _Adapter:
    def __init__(self, chat_impl=None):
        self._chat_impl = chat_impl

    async def chat_completions(self, payload, api_key, base_url):
        return await self._chat_impl(payload, api_key, base_url)

    async def stream_chat_completions(self, payload, api_key, base_url):
        raw, usage = await self._chat_impl(payload, api_key, base_url)

        async def _iterator():
            yield f"data: {json.dumps({'id': raw['id'], 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': raw['choices'][0]['message']['content']}, 'finish_reason': None}]})}\n\n"
            yield "data: [DONE]\n\n"

        async def _finalize():
            return raw, usage

        return SimpleNamespace(iterator=_iterator(), finalize=_finalize)

    def normalize_error(self, exc):
        return {"code": "upstream_error", "retryable": True, "cooldown_seconds": 1}


@pytest.mark.asyncio
async def test_llm_routes_public_model_to_upstream_model(db_session, monkeypatch):
    app = create_app()
    provider = Provider(name="OpenAI", slug="openai", default_base_url="https://api.openai.com", enabled=True)
    public_model = PublicModel(slug="apicred-fast", display_name="APICred Fast", category="llm", pricing={"mode": "free"}, enabled=True)
    db_session.add_all([provider, public_model])
    await db_session.commit()
    await db_session.refresh(provider)
    await db_session.refresh(public_model)
    endpoint = ProviderEndpoint(provider_id=provider.id, slug="default", display_name="OpenAI Default", base_url="https://api.openai.com", enabled=True, health_state="healthy")
    db_session.add(endpoint)
    await db_session.commit()
    await db_session.refresh(endpoint)

    upstream_model = UpstreamModel(provider_id=provider.id, upstream_name="gpt-4o-mini", display_name="GPT-4o mini", context_window=128000, capabilities={"chat": True}, default_pricing={}, enabled=True)
    credential = ProviderCredential(provider_endpoint_id=endpoint.id, display_name="openai-main-key", secret_encrypted=encrypt_secret("sk-route"), secret_last4="oute", enabled=True, health_state="healthy")
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
    monkeypatch.setattr("app.api.v1.llm.authorize_usage", lambda *args, **kwargs: _await(SimpleNamespace(id="usage-route", status="started", user_id="user-llm", estimated_cost_credits=0, upstream_provider=None, upstream_credential_id=None)))
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
        resp = await client.post("/v1/chat/completions", json={"model": "apicred-fast", "messages": [{"role": "user", "content": "hello"}]})
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
        resp = await client.post("/v1/chat/completions", json={"model": "missing", "messages": [{"role": "user", "content": "hi"}]})
        assert resp.status_code == 404
