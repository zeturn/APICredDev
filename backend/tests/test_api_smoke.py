import hashlib
import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.config import settings
from app.core.deps import get_db
from app.db.models.model import Model
from app.db.models.recharge_code import RechargeCode
from app.db.models.usage_session import UsageSession
from app.main import create_app


@pytest.mark.asyncio
async def test_api_smoke(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

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

        # me
        me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me.status_code == 200

        # create model for list
        model = Model(name="gpt5", category="llm", enabled=True, multiplier=1, pricing={"unit": "1k_tokens", "price": 10})
        db_session.add(model)
        await db_session.commit()

        # models
        models_resp = await client.get("/v1/models")
        assert models_resp.status_code == 200

        # wallet/ledger
        wallet = await client.get("/v1/billing/wallet", headers={"Authorization": f"Bearer {access_token}"})
        assert wallet.status_code == 200
        summary = await client.get("/v1/billing/summary", headers={"Authorization": f"Bearer {access_token}"})
        assert summary.status_code == 200

        # redeem
        code_plain = "CODE123"
        code_hash = hashlib.sha256(code_plain.encode("utf-8")).hexdigest()
        code = RechargeCode(code_hash=code_hash, amount_credits=50)
        db_session.add(code)
        await db_session.commit()
        redeem = await client.post("/v1/billing/redeem", json={"code": code_plain}, headers={"Authorization": f"Bearer {access_token}"})
        assert redeem.status_code == 200

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
        assert time_resp.status_code == 200
        weather_resp = await client.get("/v1/weather")
        assert weather_resp.status_code == 501
        fx_resp = await client.get("/v1/fx")
        assert fx_resp.status_code == 501

        # admin endpoints
        admin_headers = {"X-Admin-Token": settings.admin_token}
        admin_models = await client.get("/v1/admin/models", headers=admin_headers)
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

