import os
from collections import defaultdict

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.api.v1.basalt import get_basalt_client
from app.api.v1 import basalt as basalt_module
from app.core.config import settings
from app.core.deps import get_db
from app.main import create_app
from app.services.auth_service import register_user, login_user


class FakeBasaltClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def proxy(self, method: str, upstream_path: str, *, query=None, body=None, headers=None):
        self.calls.append(
            {
                "method": method,
                "upstream_path": upstream_path,
                "query": query or {},
                "body": body,
                "headers": headers or {},
            }
        )
        return type(
            "Resp",
            (),
            {
                "status_code": 200,
                "payload": {"ok": True, "path": upstream_path, "method": method},
            },
        )()

    async def s2s_get_user_permissions(self, user_id: str, tenant_id: str | None = None):
        self.calls.append({"method": "S2S_PERMISSIONS", "user_id": user_id, "tenant_id": tenant_id})
        return {"permission_codes": ["entry.read"], "role_codes": ["member"]}

    async def s2s_get_user_roles(self, user_id: str, tenant_id: str | None = None):
        self.calls.append({"method": "S2S_ROLES", "user_id": user_id, "tenant_id": tenant_id})
        return {"roles": [{"code": "member"}]}

    async def s2s_get_user_wallet(self, user_id: str, currency: str, limit: int = 20, tenant_id: str | None = None):
        self.calls.append(
            {
                "method": "S2S_WALLET",
                "user_id": user_id,
                "tenant_id": tenant_id,
                "currency": currency,
                "limit": limit,
            }
        )
        return {
            "wallet_id": 9,
            "currency": currency,
            "balance": 12345,
            "transactions": [{"id": 1}, {"id": 2}],
        }

    async def s2s_get_me(self):
        self.calls.append({"method": "S2S_ME"})
        return {"client_id": "test-client", "tenant_id": 123, "scopes": ["s2s.rbac.read", "s2s.wallet.read"]}


@pytest.mark.asyncio
async def test_basalt_proxy_user_and_admin_routes(db_session):
    app = create_app()
    fake = FakeBasaltClient()

    async def _override_db():
        yield db_session

    def _override_basalt():
        return fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_basalt_client] = _override_basalt

    user = await register_user(db_session, "proxy-user@example.com", "pass")
    user.basalt_user_id = "bp-user-1"
    user.basalt_tenant_id = "bp-tenant-1"
    await db_session.commit()
    token = await login_user(db_session, "proxy-user@example.com", "pass")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_resp = await client.get(
            "/v1/basalt/wallet/balance",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert user_resp.status_code == 200
        assert user_resp.json()["data"]["balance"] == 12345

        admin_resp = await client.get(
            "/v1/admin/basalt/users",
            headers={"X-Admin-Token": settings.admin_token},
        )
        assert admin_resp.status_code == 200
        assert admin_resp.json()["data"]["path"] == "/api/v1/admin/users/"

    assert len(fake.calls) == 2
    assert fake.calls[0]["method"] == "S2S_WALLET"
    assert fake.calls[0]["user_id"] == "bp-user-1"
    assert fake.calls[1]["upstream_path"] == "/api/v1/admin/users/"


@pytest.mark.asyncio
async def test_basalt_proxy_route_counts_exceed_requirements(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    route_counts = defaultdict(int)
    for route in app.router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        method_count = len([m for m in methods if m in {"GET", "POST", "PUT", "PATCH", "DELETE"}])
        if path.startswith("/v1/admin"):
            route_counts["admin"] += method_count
        elif path.startswith("/v1"):
            route_counts["business"] += method_count

    assert route_counts["admin"] >= 25
    assert route_counts["business"] >= 25
    assert route_counts["admin"] + route_counts["business"] >= 50


@pytest.mark.asyncio
async def test_basalt_admin_requires_valid_admin_token(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bad = await client.get("/v1/admin/basalt/users", headers={"X-Admin-Token": "bad-token"})
        assert bad.status_code == 403
        assert bad.json()["error"]["code"] == "admin_unauthorized"


@pytest.mark.asyncio
async def test_basalt_proxy_forwards_custom_basalt_token_and_path_params(db_session):
    app = create_app()
    fake = FakeBasaltClient()

    async def _override_db():
        yield db_session

    def _override_basalt():
        return fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_basalt_client] = _override_basalt

    user = await register_user(db_session, "path-user@example.com", "pass")
    user.basalt_user_id = "bp-user-path"
    await db_session.commit()
    token = await login_user(db_session, "path-user@example.com", "pass")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/basalt/users/u-001/permissions",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Basalt-Access-Token": "token-from-client",
            },
        )
        assert resp.status_code == 200

    last_call = fake.calls[-1]
    assert last_call["upstream_path"] == "/api/v1/s2s/users/u-001/permissions"
    assert last_call["headers"]["Authorization"] == "Bearer token-from-client"


def test_basalt_helper_functions():
    client = get_basalt_client()
    assert client.base_url.startswith("http")
    assert basalt_module._extract_body(None) is None
    assert basalt_module._extract_body("") is None
    assert basalt_module._extract_body({"a": 1}) == {"a": 1}
    assert basalt_module._extract_body(["a"]) == ["a"]
    assert basalt_module._extract_body("raw-body") == {"raw": "raw-body"}


@pytest.mark.asyncio
async def test_basalt_permissions_requires_basalt_identity(db_session):
    app = create_app()
    fake = FakeBasaltClient()

    async def _override_db():
        yield db_session

    def _override_basalt():
        return fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_basalt_client] = _override_basalt

    await register_user(db_session, "identity-user@example.com", "pass")
    token = await login_user(db_session, "identity-user@example.com", "pass")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/v1/basalt/permissions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "basalt_identity_missing"


@pytest.mark.asyncio
async def test_basalt_debug_context_returns_link_and_s2s_info(db_session):
    app = create_app()
    fake = FakeBasaltClient()

    async def _override_db():
        yield db_session

    def _override_basalt():
        return fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_basalt_client] = _override_basalt

    old_s2s_id = settings.basalt_s2s_client_id
    old_s2s_secret = settings.basalt_s2s_client_secret
    old_debug_flag = settings.debug_endpoints_enabled
    settings.basalt_s2s_client_id = "s2s-id"
    settings.basalt_s2s_client_secret = "s2s-secret"
    settings.debug_endpoints_enabled = True

    try:
        user = await register_user(db_session, "debug-user@example.com", "pass")
        user.basalt_user_id = "bp-debug-user"
        user.basalt_tenant_id = "bp-debug-tenant"
        await db_session.commit()
        token = await login_user(db_session, "debug-user@example.com", "pass")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/v1/basalt/debug/context",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            payload = resp.json()["data"]
            assert payload["basalt_user_id"] == "bp-debug-user"
            assert payload["basalt_tenant_id"] == "bp-debug-tenant"
            assert payload["s2s_configured"] is True
            assert payload["s2s_me"]["client_id"] == "test-client"
    finally:
        settings.basalt_s2s_client_id = old_s2s_id
        settings.basalt_s2s_client_secret = old_s2s_secret
        settings.debug_endpoints_enabled = old_debug_flag


@pytest.mark.asyncio
async def test_basalt_debug_context_disabled(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    old_debug_flag = settings.debug_endpoints_enabled
    settings.debug_endpoints_enabled = False
    try:
        await register_user(db_session, "debug-disabled@example.com", "pass")
        token = await login_user(db_session, "debug-disabled@example.com", "pass")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/v1/basalt/debug/context",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
            assert resp.json()["error"]["code"] == "debug_endpoint_disabled"
    finally:
        settings.debug_endpoints_enabled = old_debug_flag


@pytest.mark.asyncio
async def test_basalt_proxy_handles_non_json_body_as_none(db_session):
    app = create_app()
    fake = FakeBasaltClient()

    async def _override_db():
        yield db_session

    def _override_basalt():
        return fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_basalt_client] = _override_basalt

    await register_user(db_session, "body-user@example.com", "pass")
    token = await login_user(db_session, "body-user@example.com", "pass")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/basalt/wallet/recharge",
            content="not-json",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/plain",
            },
        )
        assert resp.status_code == 200

    assert fake.calls[-1]["body"] is None

