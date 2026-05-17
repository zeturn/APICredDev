import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.deps import get_db
from app.core.config import settings
from app.main import create_app
from app.services.auth_service import get_or_create_oauth_user


@pytest.mark.asyncio
async def test_oauth_helper_and_get_or_create_user(db_session):
    u1 = await get_or_create_oauth_user(
        db_session,
        "oauth@example.com",
        basalt_user_id="bp-user-1",
        basalt_tenant_id="tenant-1",
    )
    u2 = await get_or_create_oauth_user(db_session, "oauth@example.com", basalt_user_id="bp-user-1")
    assert u1.id == u2.id
    assert u2.status == "active"
    assert u2.basalt_user_id == "bp-user-1"
    assert u2.basalt_tenant_id == "tenant-1"


@pytest.mark.asyncio
async def test_basalt_oauth_login_redirect_and_callback_success(db_session, monkeypatch):
    monkeypatch.setattr(settings, "basalt_oauth_client_id", "apicred-test")
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    class _Resp:
        def __init__(self, status_code: int, payload: dict, text: str = ""):
            self.status_code = status_code
            self._payload = payload
            self.text = text

        def json(self):
            return self._payload

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, data=None):
            assert "/api/v1/oauth/token" in url
            assert data["code_verifier"]
            return _Resp(
                200,
                {
                    "access_token": "access-token",
                },
            )

        async def get(self, url, headers=None):
            assert "/api/v1/oauth/userinfo" in url
            return _Resp(
                200,
                {"sub": "bp-user-123", "tid": "bp-tenant-1", "email": "oauth-callback@example.com"},
            )

    monkeypatch.setattr("app.api.v1.auth.httpx.AsyncClient", lambda *a, **k: _Client())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_redirect = await client.get("/v1/auth/basalt/oauth/google/login?next=/workspace/dashboard", follow_redirects=False)
        assert login_redirect.status_code in (302, 307)
        assert "/api/v1/oauth/authorize" in login_redirect.headers["location"]
        assert "nonce=" in login_redirect.headers["location"]

        state_cookie = login_redirect.cookies.get("apicred_basalt_oauth_state")
        assert state_cookie
        callback = await client.get(
            f"/v1/auth/basalt/oauth/google/callback?code=abc&state={state_cookie}",
            follow_redirects=False,
        )
        assert callback.status_code in (302, 307)
        location = callback.headers["location"]
        assert location.endswith("/workspace/dashboard")
        assert "token=" not in location
        assert "source=basaltpass" not in location


@pytest.mark.asyncio
async def test_basalt_oauth_callback_failure_paths(db_session, monkeypatch):
    monkeypatch.setattr(settings, "basalt_oauth_client_id", "apicred-test")
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)

    class _Resp:
        def __init__(self, status_code: int, payload: dict, text: str = ""):
            self.status_code = status_code
            self._payload = payload
            self.text = text

        def json(self):
            return self._payload

    class _ClientBadToken:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, data=None):
            return _Resp(400, {"error": "bad"}, text="bad token exchange")

        async def get(self, url, headers=None):
            return _Resp(200, {})

    class _ClientNoEmail:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, data=None):
            return _Resp(200, {"access_token": "good"})

        async def get(self, url, headers=None):
            return _Resp(200, {"sub": "bp-user-1"})

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bad_state = await client.get("/v1/auth/basalt/oauth/google/callback?code=abc&state=invalid")
        assert bad_state.status_code == 400

    monkeypatch.setattr("app.api.v1.auth.httpx.AsyncClient", lambda *a, **k: _ClientBadToken())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_redirect = await client.get("/v1/auth/basalt/login", follow_redirects=False)
        state_cookie = login_redirect.cookies.get("apicred_basalt_oauth_state")
        bad_token = await client.get(
            f"/v1/auth/basalt/callback?code=abc&state={state_cookie}",
            follow_redirects=False,
        )
        assert bad_token.status_code == 502

    monkeypatch.setattr("app.api.v1.auth.httpx.AsyncClient", lambda *a, **k: _ClientNoEmail())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_redirect = await client.get("/v1/auth/basalt/login", follow_redirects=False)
        state_cookie = login_redirect.cookies.get("apicred_basalt_oauth_state")
        no_email = await client.get(
            f"/v1/auth/basalt/callback?code=abc&state={state_cookie}",
            follow_redirects=False,
        )
        assert no_email.status_code == 400
