import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import admin as admin_module
from app.core.deps import get_db
from app.main import create_app


@pytest.mark.asyncio
async def test_access_policy_api_crud_and_toggle(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    async def _allow_admin():
        return None

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[admin_module.require_admin_access] = _allow_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/v1/admin/policies",
            json={"scope_type": "global", "name": "global-policy", "enabled": True, "blocked_public_models_json": ["x"]},
        )
        assert created.status_code == 200
        policy_id = created.json()["id"]

        listed = await client.get("/v1/admin/policies")
        assert listed.status_code == 200
        assert any(item["id"] == policy_id for item in listed.json())

        fetched = await client.get(f"/v1/admin/policies/{policy_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "global-policy"

        updated = await client.put(f"/v1/admin/policies/{policy_id}", json={"name": "global-policy-v2"})
        assert updated.status_code == 200
        assert updated.json()["name"] == "global-policy-v2"

        disabled = await client.post(f"/v1/admin/policies/{policy_id}/disable")
        assert disabled.status_code == 200
        assert disabled.json()["enabled"] is False

        enabled = await client.post(f"/v1/admin/policies/{policy_id}/enable")
        assert enabled.status_code == 200
        assert enabled.json()["enabled"] is True

        deleted = await client.delete(f"/v1/admin/policies/{policy_id}")
        assert deleted.status_code == 200
        assert deleted.json()["ok"] is True
