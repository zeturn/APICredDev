import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.api.v1.admin import get_basalt_client
from app.api.v1.auth import get_basalt_client as get_auth_basalt_client
from app.core.deps import get_db
from app.db.models.public_model import PublicModel
from app.db.models.user import User
from app.db.models.usage_session import UsageSession
from app.main import create_app
from app.services.basaltpass_client import BasaltPassClient


class _TenantAdminBasaltClient:
    async def s2s_get_user_permissions(self, user_id: str, tenant_id: str | None = None):
        return {"permission_codes": ["user_console", "entry.read"], "role_codes": ["tenant"]}

    async def s2s_get_user_roles(self, user_id: str, tenant_id: str | None = None):
        return {"roles": [{"code": "tenant"}]}

    async def s2s_get_user_wallet(self, user_id: str, currency: str, limit: int = 1, tenant_id: str | None = None):
        return {"balance": 0}

    async def s2s_adjust_user_wallet(
        self,
        user_id: str,
        currency: str,
        operation: str,
        amount: int,
        reference: str,
        tenant_id: str | None = None,
    ):
        return {"ok": True}


@pytest.mark.asyncio
async def test_api_smoke(db_session, monkeypatch):
    app = create_app()
    monkeypatch.setattr("app.services.billing_service.BasaltPassClient", _TenantAdminBasaltClient)

    async def _override_db():
        yield db_session

    def _override_basalt_client():
        return _TenantAdminBasaltClient()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_basalt_client] = _override_basalt_client
    app.dependency_overrides[get_auth_basalt_client] = _override_basalt_client
    app.dependency_overrides[BasaltPassClient] = _override_basalt_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok", "service": "apicred"}

        # register + login
        reg = await client.post("/v1/auth/register", json={"email": "u1@example.com", "password": "pass"})
        assert reg.status_code == 200
        login = await client.post("/v1/auth/login", json={"email": "u1@example.com", "password": "pass"})
        assert login.status_code == 200
        access_token = login.json()["access_token"]

        bound_user = await db_session.get(User, reg.json()["id"])
        bound_user.basalt_user_id = "bp-smoke-user"
        bound_user.basalt_tenant_id = "bp-smoke-tenant"
        await db_session.commit()

        # me
        me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me.status_code == 200

        # create model for list
        model = PublicModel(slug="gpt5", display_name="GPT5", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 10})
        db_session.add(model)
        await db_session.commit()

        # models
        models_resp = await client.get("/v1/models", headers={"Authorization": f"Bearer {access_token}"})
        assert models_resp.status_code == 200

        # wallet/ledger
        wallet = await client.get("/v1/billing/wallet", headers={"Authorization": f"Bearer {access_token}"})
        assert wallet.status_code == 200
        summary = await client.get("/v1/billing/summary", headers={"Authorization": f"Bearer {access_token}"})
        assert summary.status_code == 200

        ledger = await client.get("/v1/billing/ledger", headers={"Authorization": f"Bearer {access_token}"})
        assert ledger.status_code == 200
        usage = await client.get("/v1/billing/usage", headers={"Authorization": f"Bearer {access_token}"})
        assert usage.status_code == 200

        # tokens
        tok = await client.post(
            "/v1/tokens",
            json={"name": "t1", "scopes": ["llm"]},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert tok.status_code == 200
        raw_api_token = tok.json()["token"]

        api_models = await client.get("/v1/models", headers={"Authorization": f"Bearer {raw_api_token}"})
        assert api_models.status_code == 200
        assert any(item["name"] == "gpt5" for item in api_models.json())

        usage_row = UsageSession(
            user_id=me.json()["id"],
            token_id="tok1",
            request_id="req1",
            model_id=model.id,
            status="completed",
            final_cost_credits=2.5,
            upstream_provider="openai",
            usage={"total_tokens": 128},
        )
        db_session.add(usage_row)
        await db_session.commit()

        # chat completions with missing model -> 404
        chat = await client.post(
            "/v1/chat/completions",
            json={"model": "missing", "messages": [{"role": "user", "content": "hi"}]},
            headers={"Authorization": f"Bearer {raw_api_token}"},
        )
        assert chat.status_code == 404

        # data sources
        time_resp = await client.get("/v1/time")
        assert time_resp.status_code == 404
        weather_resp = await client.get("/v1/weather")
        assert weather_resp.status_code == 404
        fx_resp = await client.get("/v1/fx")
        assert fx_resp.status_code == 404

        current_user = await db_session.get(User, me.json()["id"])
        current_user.basalt_user_id = "bp-smoke-admin"
        current_user.basalt_tenant_id = "bp-smoke-tenant"
        await db_session.commit()

        admin_token_resp = await client.get("/v1/auth/admin-token", headers={"Authorization": f"Bearer {access_token}"})
        assert admin_token_resp.status_code == 200
        admin_access_token = admin_token_resp.json()["admin_access_token"]

        # admin endpoints
        admin_headers = {"X-Admin-Authorization": f"Bearer {admin_access_token}"}
        admin_models = await client.get("/v1/admin/public-models", headers=admin_headers)
        assert admin_models.status_code == 200
        admin_dashboard = await client.get("/v1/admin/dashboard", headers=admin_headers)
        assert admin_dashboard.status_code == 200
        admin_presets = await client.get("/v1/admin/provider-presets", headers=admin_headers)
        assert admin_presets.status_code == 200
        assert any(item["provider"] == "openai" for item in admin_presets.json())
        admin_users = await client.get("/v1/admin/users", headers=admin_headers)
        assert admin_users.status_code == 200
        admin_usage = await client.get("/v1/admin/usage-summary", headers=admin_headers)
        assert admin_usage.status_code == 200

