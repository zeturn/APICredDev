from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import llm as llm_module
from app.core.deps import get_bearer_token, get_db
from app.core.config import settings
from app.db.models.access_policy import AccessPolicy
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.db.models.user import User
from app.main import create_app


@pytest.mark.asyncio
async def test_policy_violation_returns_clear_error(db_session, monkeypatch):
    db_session.add(User(id="u1", email="u1@example.com", password_hash="x", status="active", basalt_tenant_id="t1"))
    provider = Provider(name="OpenAI", slug="openai", enabled=True)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    endpoint = ProviderEndpoint(provider_id=provider.id, slug="main", display_name="main", base_url="https://api.openai.com", enabled=True, health_state="healthy")
    model = PublicModel(slug="apicred-fast", display_name="apicred-fast", category="llm", enabled=True, pricing={"mode": "free"}, multiplier=1)
    upstream = UpstreamModel(provider_id=provider.id, upstream_name="gpt-4o-mini", display_name="gpt-4o-mini", capabilities={}, default_pricing={}, enabled=True)
    db_session.add_all([endpoint, model, upstream])
    await db_session.commit()
    await db_session.refresh(endpoint)
    await db_session.refresh(model)
    await db_session.refresh(upstream)
    credential = ProviderCredential(provider_endpoint_id=endpoint.id, display_name="c1", enabled=True, health_state="healthy")
    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)
    db_session.add(ModelRoute(public_model_id=model.id, upstream_model_id=upstream.id, provider_credential_id=credential.id, enabled=True, priority=1, weight=1, quota_unit="requests", quota_rules={}))
    db_session.add(AccessPolicy(scope_type="global", name="block", enabled=True, blocked_public_models_json=["apicred-fast"]))
    await db_session.commit()

    app = create_app()

    async def _override_db():
        yield db_session

    async def _token():
        return SimpleNamespace(user_id="u1", id="t1", scopes=["llm", "user_console"])

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(llm_module, "require_scopes", _noop)
    monkeypatch.setattr(settings, "basalt_rbac_enforce", False)
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_bearer_token] = _token

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/chat/completions", json={"model": "apicred-fast", "messages": [{"role": "user", "content": "hello"}]})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "policy_violation"
