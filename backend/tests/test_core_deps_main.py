from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core import deps
from app.core.deps import get_bearer_token, get_current_user, require_scopes, get_db
from app.core.security import create_access_token, generate_api_token, hash_api_token
from app.db.models.api_token import ApiToken
from app.db.models.user import User
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
async def test_main_startup_runs_tables_and_admin(monkeypatch, db_session):
    calls = {"run_sync": False, "admin": False}

    class _BeginCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def run_sync(self, fn):
            calls["run_sync"] = True
            return None

    class _SessionCtx:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def _ensure_admin_user(db):
        calls["admin"] = True

    monkeypatch.setattr("app.main.engine", SimpleNamespace(begin=lambda: _BeginCtx()))
    monkeypatch.setattr("app.main.SessionLocal", lambda: _SessionCtx())
    monkeypatch.setattr("app.main.ensure_admin_user", _ensure_admin_user)

    app = create_app()
    for startup in app.router.on_startup:
        await startup()

    assert calls["run_sync"] is True
    assert calls["admin"] is True


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

