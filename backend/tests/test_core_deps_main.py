from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core import deps
from app.core.deps import CrossAppBearerToken, get_bearer_token, get_current_user, require_scopes, get_db
from app.core.security import create_access_token, generate_api_token, hash_api_token
from app.db.models.api_token import ApiToken
from app.db.models.user import User
from app.core.config import settings
from app.main import create_app


@pytest.mark.asyncio
async def test_get_current_user_and_bearer_token_branches(db_session):
    request = SimpleNamespace(state=SimpleNamespace(request_id=uuid4()))

    with pytest.raises(Exception):
        await get_current_user(request, authorization=None, db=db_session)

    bad_token = create_access_token("")
    with pytest.raises(Exception):
        await get_current_user(request, authorization=f"Bearer {bad_token}", db=db_session)

    user = User(email="deps-user@example.com", password_hash="x", status="inactive")
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(user.id)
    with pytest.raises(Exception):
        await get_current_user(request, authorization=f"Bearer {token}", db=db_session)

    user.status = "active"
    await db_session.commit()
    ok = await get_current_user(request, authorization=f"Bearer {token}", db=db_session)
    assert ok.id == user.id

    with pytest.raises(Exception):
        await get_bearer_token(request, authorization=None, db=db_session)
    with pytest.raises(Exception):
        await get_bearer_token(request, authorization="Bearer missing", db=db_session)

    raw = generate_api_token()
    api_token = ApiToken(user_id=user.id, name="deps", scopes=["llm"], token_hash=hash_api_token(raw), status="active")
    db_session.add(api_token)
    await db_session.commit()
    found = await get_bearer_token(request, authorization=f"Bearer {raw}", db=db_session)
    assert found.id == api_token.id

    await require_scopes(["llm"], found, request)
    with pytest.raises(Exception):
        await require_scopes(["billing"], found, request)
    with pytest.raises(Exception):
        await require_scopes(["billing"], found, None)


@pytest.mark.asyncio
async def test_get_bearer_token_accepts_basalt_cross_app_token(monkeypatch, db_session):
    request = SimpleNamespace(state=SimpleNamespace(request_id=uuid4()))

    class _FakeBasaltClient:
        async def introspect_oauth_token(self, token):
            assert token == "bp_xat_valid"
            return {
                "active": True,
                "client_id": "apicred-client",
                "aud": "apicred-client",
                "sub": "basalt-sub-1",
                "username": "cross-app@example.com",
                "tenant_id": "tenant-1",
                "scope": "llm,apicred.read",
                "act": {"client_id": "araneae-client"},
            }

    monkeypatch.setattr(deps, "BasaltPassClient", lambda: _FakeBasaltClient())
    monkeypatch.setattr(settings, "basalt_oauth_client_id", "apicred-client")
    monkeypatch.setattr(settings, "basalt_oauth_client_secret", "apicred-secret")

    token = await get_bearer_token(request, authorization="Bearer bp_xat_valid", db=db_session)

    assert isinstance(token, CrossAppBearerToken)
    assert token.id.startswith("basalt:xat:")
    assert token.scopes == ["llm", "apicred.read"]
    assert token.basalt_actor == {"client_id": "araneae-client"}

    user = await db_session.get(User, token.user_id)
    assert user.email == "cross-app@example.com"
    assert user.basalt_user_id == "basalt-sub-1"
    assert user.basalt_tenant_id == "tenant-1"
    await require_scopes(["llm"], token, request)


@pytest.mark.asyncio
async def test_get_bearer_token_rejects_cross_app_token_for_other_client(monkeypatch, db_session):
    request = SimpleNamespace(state=SimpleNamespace(request_id=uuid4()))

    class _FakeBasaltClient:
        async def introspect_oauth_token(self, token):
            return {
                "active": True,
                "client_id": "other-client",
                "aud": "other-client",
                "sub": "basalt-sub-1",
                "username": "cross-app@example.com",
                "scope": "llm",
            }

    monkeypatch.setattr(deps, "BasaltPassClient", lambda: _FakeBasaltClient())
    monkeypatch.setattr(settings, "basalt_oauth_client_id", "apicred-client")
    monkeypatch.setattr(settings, "basalt_oauth_client_secret", "apicred-secret")

    with pytest.raises(Exception):
        await get_bearer_token(request, authorization="Bearer bp_xat_wrong_aud", db=db_session)


@pytest.mark.asyncio
async def test_main_startup_runs_tables_and_admin(monkeypatch, db_session):
    calls = {
        "admin": False,
        "brands": False,
        "providers": False,
        "models": False,
        "routes": False,
        "bootstrap_credential": False,
        "bootstrap_openrouter_credential": False,
    }

    class _SessionCtx:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def _ensure_admin_user(db):
        calls["admin"] = True

    async def _ensure_default_brands(db):
        calls["brands"] = True

    async def _ensure_default_providers(db):
        calls["providers"] = True

    async def _ensure_default_models(db):
        calls["models"] = True

    async def _ensure_default_routes(db):
        calls["routes"] = True

    async def _ensure_bootstrap_openai_credential(db):
        calls["bootstrap_credential"] = True

    async def _ensure_bootstrap_openrouter_credential(db):
        calls["bootstrap_openrouter_credential"] = True

    monkeypatch.setattr("app.main.SessionLocal", lambda: _SessionCtx())
    monkeypatch.setattr("app.main.ensure_admin_user", _ensure_admin_user)
    monkeypatch.setattr("app.main.ensure_default_brands", _ensure_default_brands)
    monkeypatch.setattr("app.main.ensure_default_providers", _ensure_default_providers)
    monkeypatch.setattr("app.main.ensure_default_models", _ensure_default_models)
    monkeypatch.setattr("app.main.ensure_default_routes", _ensure_default_routes)
    monkeypatch.setattr("app.main.ensure_bootstrap_openai_credential", _ensure_bootstrap_openai_credential)
    monkeypatch.setattr("app.main.ensure_bootstrap_openrouter_credential", _ensure_bootstrap_openrouter_credential)
    monkeypatch.setattr(settings, "startup_create_tables_enabled", False)
    monkeypatch.setattr(settings, "startup_schema_compat_enabled", False)
    monkeypatch.setattr(settings, "startup_bootstrap_enabled", True)

    app = create_app()
    async with app.router.lifespan_context(app):
        pass

    assert calls["admin"] is True
    assert calls["brands"] is True
    assert calls["providers"] is True
    assert calls["models"] is True
    assert calls["routes"] is True
    assert calls["bootstrap_credential"] is True
    assert calls["bootstrap_openrouter_credential"] is True


@pytest.mark.asyncio
async def test_get_db_generator(monkeypatch):
    class _SessionCtx:
        async def __aenter__(self):
            return "db"

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(deps, "SessionLocal", lambda: _SessionCtx())
    gen = get_db()
    value = await gen.__anext__()
    assert value == "db"
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()

