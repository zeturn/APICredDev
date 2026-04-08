import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.config import settings
from app.core.deps import get_db
from app.core.url_safety import normalize_upstream_base_url
from app.main import create_app


@pytest.mark.asyncio
async def test_local_auth_disabled_for_browser_requests(db_session):
    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/auth/register",
            json={"email": "browser-user@example.com", "password": "pass"},
            headers={"User-Agent": "Mozilla/5.0"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "local_auth_disabled"


@pytest.mark.asyncio
async def test_cli_local_auth_requires_matching_shared_secret(db_session, monkeypatch):
    monkeypatch.setattr(settings, "allow_local_password_auth", False)
    monkeypatch.setattr(settings, "allow_test_cli_local_auth", True)
    monkeypatch.setattr(settings, "test_cli_auth_secret", "cli-secret")

    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.post(
            "/v1/auth/register",
            json={"email": "cli-denied@example.com", "password": "pass"},
            headers={"X-APICRED-Client": "cli", "X-APICRED-CLI-Auth": "bad"},
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "local_auth_disabled"

        ok_register = await client.post(
            "/v1/auth/register",
            json={"email": "cli-ok@example.com", "password": "pass"},
            headers={"X-APICRED-Client": "cli", "X-APICRED-CLI-Auth": "cli-secret"},
        )
        assert ok_register.status_code == 200

        ok_login = await client.post(
            "/v1/auth/login",
            json={"email": "cli-ok@example.com", "password": "pass"},
            headers={"X-APICRED-Client": "cli", "X-APICRED-CLI-Auth": "cli-secret"},
        )
        assert ok_login.status_code == 200
        assert isinstance(ok_login.json().get("access_token"), str)
        assert ok_login.json()["access_token"]


def test_normalize_upstream_base_url_rejects_dangerous_schemes():
    with pytest.raises(ValueError):
        normalize_upstream_base_url("file:///etc/passwd")

    with pytest.raises(ValueError):
        normalize_upstream_base_url("ftp://example.com")

    assert normalize_upstream_base_url("https://api.example.com/") == "https://api.example.com"
