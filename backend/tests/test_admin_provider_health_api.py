import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import admin as admin_module
from app.core.deps import get_db
from app.core.secrets import encrypt_secret
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.main import create_app


async def _seed_provider_data(db_session):
    provider = Provider(name="OpenAI", slug="openai", enabled=True)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    endpoint = ProviderEndpoint(provider_id=provider.id, slug="main", display_name="OpenAI Main", base_url="https://api.openai.com", enabled=True, health_state="healthy")
    db_session.add(endpoint)
    public_model = PublicModel(slug="apicred-fast", display_name="apicred-fast", category="llm", enabled=True, pricing={"mode": "free"}, multiplier=1)
    upstream = UpstreamModel(provider_id=provider.id, upstream_name="gpt-4o-mini", display_name="gpt-4o-mini", capabilities={}, default_pricing={}, enabled=True)
    db_session.add_all([public_model, upstream])
    await db_session.commit()
    await db_session.refresh(public_model)
    await db_session.refresh(upstream)
    credential = ProviderCredential(provider_endpoint_id=endpoint.id, display_name="main", secret_encrypted=encrypt_secret("sk-old"), enabled=True, health_state="healthy")
    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)
    route = ModelRoute(public_model_id=public_model.id, upstream_model_id=upstream.id, provider_credential_id=credential.id, enabled=True, priority=1, weight=1, quota_unit="requests", quota_rules={})
    db_session.add(route)
    await db_session.commit()
    return credential, route


@pytest.mark.asyncio
async def test_admin_provider_health_api(db_session, monkeypatch):
    credential, route = await _seed_provider_data(db_session)
    app = create_app()

    async def _override_db():
        yield db_session

    async def _allow_admin():
        return None

    async def _fake_check(db, credential_id):
        return {"credential_id": credential_id, "ok": True}

    monkeypatch.setattr(admin_module, "check_credential_health", _fake_check)
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[admin_module.require_admin_access] = _allow_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/admin/provider-health")
        assert health.status_code == 200
        assert health.json()["items"][0]["credential_id"] == credential.id

        check = await client.post(f"/v1/admin/provider-credentials/{credential.id}/health-check")
        assert check.status_code == 200
        assert check.json()["ok"] is True

        disable = await client.post(f"/v1/admin/provider-credentials/{credential.id}/disable")
        assert disable.status_code == 200
        assert disable.json()["enabled"] is False

        enable = await client.post(f"/v1/admin/provider-credentials/{credential.id}/enable")
        assert enable.status_code == 200
        assert enable.json()["enabled"] is True

        rotate = await client.post(f"/v1/admin/provider-credentials/{credential.id}/rotate-secret", json={"secret": "sk-new-value"})
        assert rotate.status_code == 200
        assert rotate.json()["rotated"] is True

        effective = await client.get(f"/v1/admin/model-routes/{route.id}/effective-status")
        assert effective.status_code == 200
        assert "effective_enabled" in effective.json()
