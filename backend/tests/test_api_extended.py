import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.deps import get_db
from app.api.v1.admin import get_basalt_client
from app.api.v1.auth import get_basalt_client as get_auth_basalt_client
from app.db.models.model import Model
from app.db.models.provider_key import ProviderKey
from app.db.models.user import User
from app.main import create_app
from app.services.auth_service import register_user, login_user
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
async def test_auth_and_tokens_and_billing_and_models_branches(db_session, monkeypatch):
    app = create_app()
    monkeypatch.setattr("app.services.billing_service.BasaltPassClient", _TenantAdminBasaltClient)

    async def _override_db():
        yield db_session

    def _override_basalt_client():
        return _TenantAdminBasaltClient()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[BasaltPassClient] = _override_basalt_client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/v1/auth/register", json={"email": "api-ext@example.com", "password": "pass"})
        assert reg.status_code == 200

        dup = await client.post("/v1/auth/register", json={"email": "api-ext@example.com", "password": "pass"})
        assert dup.status_code == 400
        assert dup.json()["error"]["code"] == "email_exists"

        bad_login = await client.post("/v1/auth/login", json={"email": "api-ext@example.com", "password": "bad"})
        assert bad_login.status_code == 401

        login = await client.post("/v1/auth/login", json={"email": "api-ext@example.com", "password": "pass"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        bound_user = await db_session.get(User, reg.json()["id"])
        bound_user.basalt_user_id = "bp-ext-user"
        bound_user.basalt_tenant_id = "bp-ext-tenant"
        await db_session.commit()

        me = await client.get("/v1/auth/me", headers=headers)
        assert me.status_code == 200

        create_tok = await client.post("/v1/tokens", json={"name": "t-ext", "scopes": ["llm"]}, headers=headers)
        assert create_tok.status_code == 200
        token_id = create_tok.json()["id"]

        list_tok = await client.get("/v1/tokens", headers=headers)
        assert list_tok.status_code == 200
        assert len(list_tok.json()) >= 1

        deleted = await client.delete(f"/v1/tokens/{token_id}", headers=headers)
        assert deleted.status_code == 200
        missing_del = await client.delete("/v1/tokens/not-found", headers=headers)
        assert missing_del.status_code == 404

        wallet = await client.get("/v1/billing/wallet", headers=headers)
        assert wallet.status_code == 200
        ledger = await client.get("/v1/billing/ledger", headers=headers)
        assert ledger.status_code == 200

        invalid_redeem = await client.post("/v1/billing/redeem", json={"code": "missing"}, headers=headers)
        assert invalid_redeem.status_code == 400

        enabled = Model(name="m-enabled", category="llm", enabled=True, multiplier=1, pricing={})
        disabled = Model(name="m-disabled", category="llm", enabled=False, multiplier=1, pricing={})
        db_session.add_all([enabled, disabled])
        await db_session.commit()
        model_resp = await client.get("/v1/models", headers=headers)
        assert model_resp.status_code == 200
        names = [m["name"] for m in model_resp.json()]
        assert "m-enabled" in names
        assert "m-disabled" not in names


@pytest.mark.asyncio
async def test_cookie_auth_login_me_logout_flow(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    def _override_basalt_client():
        return _TenantAdminBasaltClient()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[BasaltPassClient] = _override_basalt_client
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/v1/auth/register", json={"email": "cookie-auth@example.com", "password": "pass"})
        assert reg.status_code == 200

        login = await client.post("/v1/auth/login", json={"email": "cookie-auth@example.com", "password": "pass"})
        assert login.status_code == 200
        assert "set-cookie" in {k.lower(): v for k, v in login.headers.items()}

        bound_user = await db_session.get(User, reg.json()["id"])
        bound_user.basalt_user_id = "bp-cookie-user"
        bound_user.basalt_tenant_id = "bp-cookie-tenant"
        await db_session.commit()

        me_with_cookie = await client.get("/v1/auth/me")
        assert me_with_cookie.status_code == 200
        assert me_with_cookie.json()["email"] == "cookie-auth@example.com"

        logout = await client.post("/v1/auth/logout")
        assert logout.status_code == 200

        me_after_logout = await client.get("/v1/auth/me")
        assert me_after_logout.status_code == 401


@pytest.mark.asyncio
async def test_admin_routes_and_stripe_webhook_branches(db_session, monkeypatch):
    app = create_app()

    async def _override_db():
        yield db_session

    def _override_basalt_client():
        return _TenantAdminBasaltClient()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_basalt_client] = _override_basalt_client
    app.dependency_overrides[get_auth_basalt_client] = _override_basalt_client
    app.dependency_overrides[BasaltPassClient] = _override_basalt_client
    transport = ASGITransport(app=app)

    admin_user = await register_user(db_session, "admin-ext@example.com", "pass")
    admin_user.basalt_user_id = "bp-admin-ext"
    admin_user.basalt_tenant_id = "bp-tenant-ext"
    await db_session.commit()
    admin_user_token = await login_user(db_session, "admin-ext@example.com", "pass")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.get("/v1/admin/models")
        assert unauthorized.status_code == 401

        admin_token_resp = await client.get("/v1/auth/admin-token", headers={"Authorization": f"Bearer {admin_user_token}"})
        assert admin_token_resp.status_code == 200
        admin_access_token = admin_token_resp.json()["admin_access_token"]
        admin_headers = {"X-Admin-Authorization": f"Bearer {admin_access_token}"}
        model_payload = {
            "name": "admin-model",
            "category": "llm",
            "enabled": True,
            "multiplier": 1.2,
            "pricing": {"unit": "1k_tokens", "price": 1},
        }
        model_upsert = await client.post("/v1/admin/models", json=model_payload, headers=admin_headers)
        assert model_upsert.status_code == 200
        model_id = model_upsert.json()["id"]

        model_update = dict(model_payload)
        model_update["id"] = model_id
        model_update["enabled"] = False
        updated = await client.post("/v1/admin/models", json=model_update, headers=admin_headers)
        assert updated.status_code == 200

        list_models = await client.get("/v1/admin/models", headers=admin_headers)
        assert list_models.status_code == 200

        pkey_payload = {
            "provider": "openai",
            "key_name": "k1",
            "api_key": "sk-test",
            "enabled": True,
            "health_state": "healthy",
            "cooldown_until": None,
        }
        pkey_upsert = await client.post("/v1/admin/provider-keys", json=pkey_payload, headers=admin_headers)
        assert pkey_upsert.status_code == 200
        pkey_id = pkey_upsert.json()["id"]
        pkey_payload["id"] = pkey_id
        await client.post("/v1/admin/provider-keys", json=pkey_payload, headers=admin_headers)
        pkey_list = await client.get("/v1/admin/provider-keys", headers=admin_headers)
        assert pkey_list.status_code == 200

        mpk_payload = {
            "model_id": model_id,
            "provider_key_id": pkey_id,
            "enabled": True,
            "priority": 1,
            "quota_unit": "requests",
            "quota_rules": {"minute": 100},
        }
        mpk_upsert = await client.post("/v1/admin/model-provider-keys", json=mpk_payload, headers=admin_headers)
        assert mpk_upsert.status_code == 200
        mpk_payload["id"] = mpk_upsert.json()["id"]
        await client.post("/v1/admin/model-provider-keys", json=mpk_payload, headers=admin_headers)
        mpk_list = await client.get("/v1/admin/model-provider-keys", headers=admin_headers)
        assert mpk_list.status_code == 200

        users_resp = await client.get("/v1/admin/users", headers=admin_headers)
        usage_resp = await client.get("/v1/admin/usage-sessions", headers=admin_headers)
        assert users_resp.status_code == 200
        assert usage_resp.status_code == 200

        stripe_disabled = await client.post("/v1/billing/stripe/webhook", content=b"{}")
        assert stripe_disabled.status_code == 410


@pytest.mark.asyncio
async def test_admin_routes_allow_tenant_admin_jwt(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    def _override_basalt_client():
        return _TenantAdminBasaltClient()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_basalt_client] = _override_basalt_client
    app.dependency_overrides[get_auth_basalt_client] = _override_basalt_client
    app.dependency_overrides[BasaltPassClient] = _override_basalt_client

    user = await register_user(db_session, "tenant-admin-api@example.com", "pass")
    user.basalt_user_id = "bp-user-admin"
    user.basalt_tenant_id = "bp-tenant-admin"
    await db_session.commit()
    token = await login_user(db_session, "tenant-admin-api@example.com", "pass")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token_resp = await client.get("/v1/auth/admin-token", headers={"Authorization": f"Bearer {token}"})
        assert admin_token_resp.status_code == 200
        admin_access_token = admin_token_resp.json()["admin_access_token"]
        resp = await client.get(
            "/v1/admin/models",
            headers={"X-Admin-Authorization": f"Bearer {admin_access_token}"},
        )
        assert resp.status_code == 200

