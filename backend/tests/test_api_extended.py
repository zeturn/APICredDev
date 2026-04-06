import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.config import settings
from app.core.deps import get_db
from app.api.v1.admin import get_basalt_client
from app.db.models.model import Model
from app.db.models.provider_key import ProviderKey
from app.main import create_app
from app.services.auth_service import register_user, login_user


class _TenantAdminBasaltClient:
    async def s2s_get_user_permissions(self, user_id: str, tenant_id: str | None = None):
        return {"permission_codes": ["entry.read"], "role_codes": ["tenant"]}

    async def s2s_get_user_roles(self, user_id: str, tenant_id: str | None = None):
        return {"roles": [{"code": "tenant"}]}


@pytest.mark.asyncio
async def test_auth_and_tokens_and_billing_and_models_branches(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
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
async def test_admin_routes_and_stripe_webhook_branches(db_session, monkeypatch):
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.get("/v1/admin/models")
        assert unauthorized.status_code == 403

        admin_headers = {"X-Admin-Token": settings.admin_token}
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

        # stripe webhook missing signature
        miss_sig = await client.post("/v1/billing/stripe/webhook", content=b"{}")
        assert miss_sig.status_code == 400

        # stripe webhook invalid signature
        def _raise_invalid(payload, signature, secret):
            raise ValueError("invalid")

        monkeypatch.setattr("app.api.v1.stripe_webhook.stripe.Webhook.construct_event", _raise_invalid)
        bad_sig = await client.post("/v1/billing/stripe/webhook", headers={"Stripe-Signature": "bad"}, content=b"{}")
        assert bad_sig.status_code == 400

        # stripe webhook missing user
        monkeypatch.setattr(
            "app.api.v1.stripe_webhook.stripe.Webhook.construct_event",
            lambda payload, signature, secret: {"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {"metadata": {}}}},
        )
        missing_user = await client.post("/v1/billing/stripe/webhook", headers={"Stripe-Signature": "ok"}, content=b"{}")
        assert missing_user.status_code == 400

        recorded = {"called": False}

        async def _record(db, event_id, event_type, user_id, amount_credits, meta):
            recorded["called"] = True
            assert event_id == "evt_2"
            assert event_type == "checkout.session.completed"
            assert user_id == "u-1"
            assert float(amount_credits) == 123.0
            assert "raw" in meta

        monkeypatch.setattr("app.api.v1.stripe_webhook.record_stripe_event", _record)
        monkeypatch.setattr(
            "app.api.v1.stripe_webhook.stripe.Webhook.construct_event",
            lambda payload, signature, secret: {
                "id": "evt_2",
                "type": "checkout.session.completed",
                "data": {"object": {"metadata": {"user_id": "u-1", "amount_credits": "123"}}},
            },
        )
        ok = await client.post(
            "/v1/billing/stripe/webhook",
            headers={"Stripe-Signature": "ok"},
            content=b'{"checkout":"ok"}',
        )
        assert ok.status_code == 200
        assert recorded["called"] is True


@pytest.mark.asyncio
async def test_admin_routes_allow_tenant_admin_bearer(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    def _override_basalt_client():
        return _TenantAdminBasaltClient()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_basalt_client] = _override_basalt_client

    user = await register_user(db_session, "tenant-admin-api@example.com", "pass")
    user.basalt_user_id = "bp-user-admin"
    user.basalt_tenant_id = "bp-tenant-admin"
    await db_session.commit()
    token = await login_user(db_session, "tenant-admin-api@example.com", "pass")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/admin/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

