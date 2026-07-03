import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import admin as admin_module
from app.core.deps import get_db
from app.db.models.quota_ledger_entry import QuotaLedgerEntry
from app.db.models.usage_session import UsageSession
from app.db.models.user import User
from app.main import create_app


@pytest.mark.asyncio
async def test_admin_usage_analytics_api(db_session):
    db_session.add(User(id="u1", email="u1@example.com", password_hash="x", status="active"))
    db_session.add(
        UsageSession(
            id="s1",
            user_id="u1",
            token_id="t1",
            request_id="r1",
            model_id="m1",
            model_name="apicred-fast",
            status="completed",
            estimated_cost_credits=1,
            final_cost_credits=0.8,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            upstream_provider="openai",
            latency_ms=100,
            upstream_latency_ms=80,
        )
    )
    db_session.add(
        QuotaLedgerEntry(
            id="q1",
            usage_session_id="s1",
            request_id="r1",
            user_id="u1",
            token_id="t1",
            public_model_id="m1",
            public_model_name="apicred-fast",
            provider="openai",
            upstream_model="gpt-4o-mini",
            status="settled",
            reserved_delta=30,
            total_tokens=30,
            final_cost_credits=0.8,
            metadata_json={},
        )
    )
    await db_session.commit()

    app = create_app()

    async def _override_db():
        yield db_session

    async def _allow_admin():
        return None

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[admin_module.require_admin_access] = _allow_admin
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        summary = await client.get("/v1/admin/usage/summary")
        assert summary.status_code == 200
        assert summary.json()["request_count"] >= 1

        timeseries = await client.get("/v1/admin/usage/timeseries")
        assert timeseries.status_code == 200
        assert isinstance(timeseries.json(), list)

        top_users = await client.get("/v1/admin/usage/top-users")
        assert top_users.status_code == 200
        assert len(top_users.json()) >= 1

        by_provider = await client.get("/v1/admin/usage/by-provider")
        assert by_provider.status_code == 200
        assert len(by_provider.json()) >= 1

        by_model = await client.get("/v1/admin/usage/by-model")
        assert by_model.status_code == 200
        assert len(by_model.json()) >= 1

        errors = await client.get("/v1/admin/usage/errors")
        assert errors.status_code == 200
        assert isinstance(errors.json(), list)

        quota = await client.get("/v1/admin/quota/summary")
        assert quota.status_code == 200
        assert quota.json()["entry_count"] >= 1
