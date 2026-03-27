from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.api.v1 import admin as admin_api
from app.api.v1 import auth as auth_api
from app.api.v1 import billing as billing_api
from app.api.v1 import models as models_api
from app.api.v1 import tokens as tokens_api
from app.db.models.ledger import LedgerEntry
from app.db.models.model import Model
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.services.auth_service import login_user, register_user
from app.services.billing_service import authorize_usage, get_wallet, list_ledger


def _req():
    return SimpleNamespace(state=SimpleNamespace(request_id=uuid4()))


@pytest.mark.asyncio
async def test_admin_api_direct_calls(monkeypatch, db_session):
    req = _req()
    token = "dev-admin-token"
    now = SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00+00:00")

    obj = SimpleNamespace(a=1, b=now, _hidden=1)
    assert admin_api._to_dict(obj)["b"] == "2026-01-01T00:00:00+00:00"

    monkeypatch.setattr(admin_api, "list_models", lambda db: [SimpleNamespace(id="m1", created_at=now)])
    monkeypatch.setattr(admin_api, "upsert_model", lambda db, p: SimpleNamespace(id="m2", created_at=now))
    monkeypatch.setattr(admin_api, "list_provider_keys", lambda db: [SimpleNamespace(id="p1", created_at=now)])
    monkeypatch.setattr(admin_api, "list_provider_presets", lambda: [{"provider": "openai", "base_url": "https://api.openai.com"}])
    monkeypatch.setattr(admin_api, "upsert_provider_key", lambda db, p: SimpleNamespace(id="p2", created_at=now))
    monkeypatch.setattr(admin_api, "list_model_provider_keys", lambda db: [SimpleNamespace(id="k1", created_at=now)])
    monkeypatch.setattr(admin_api, "upsert_model_provider_key", lambda db, p: SimpleNamespace(id="k2", created_at=now))
    monkeypatch.setattr(admin_api, "list_users", lambda db: [SimpleNamespace(id="u1", created_at=now)])
    monkeypatch.setattr(admin_api, "list_usage_sessions", lambda db: [SimpleNamespace(id="s1", created_at=now)])

    async def _await(v):
        return v

    for name in (
        "list_models",
        "upsert_model",
        "list_provider_keys",
        "upsert_provider_key",
        "list_model_provider_keys",
        "upsert_model_provider_key",
        "list_users",
        "list_usage_sessions",
    ):
        fn = getattr(admin_api, name)
        monkeypatch.setattr(admin_api, name, (lambda f: (lambda *a, **k: _await(f(*a, **k))))(fn))

    assert await admin_api.admin_models_list(req, token, db_session)
    assert await admin_api.admin_models_upsert(req, SimpleNamespace(model_dump=lambda: {}), token, db_session)
    assert await admin_api.admin_provider_keys_list(req, token, db_session)
    assert await admin_api.admin_provider_presets(req, token)
    assert await admin_api.admin_provider_keys_upsert(req, SimpleNamespace(model_dump=lambda: {}), token, db_session)
    assert await admin_api.admin_model_provider_keys_list(req, token, db_session)
    assert await admin_api.admin_model_provider_keys_upsert(req, SimpleNamespace(model_dump=lambda: {}), token, db_session)
    assert await admin_api.admin_users(req, token, db_session)
    assert await admin_api.admin_usage_sessions(req, token, db_session)


@pytest.mark.asyncio
async def test_auth_tokens_billing_models_direct_calls(monkeypatch, db_session):
    req = _req()
    user = SimpleNamespace(id="u1", email="u@example.com", status="active")

    async def _raise(*args, **kwargs):
        raise ValueError("x")

    monkeypatch.setattr(auth_api, "register_user", _raise)
    with pytest.raises(Exception):
        await auth_api.register(SimpleNamespace(email="a", password="b"), req, db_session)

    monkeypatch.setattr(auth_api, "login_user", _raise)
    with pytest.raises(Exception):
        await auth_api.login(SimpleNamespace(email="a", password="b"), req, db_session)

    async def _token_create(*args, **kwargs):
        return (SimpleNamespace(id="t1", name="n1", scopes=["llm"]), "raw")

    async def _token_list(*args, **kwargs):
        return [SimpleNamespace(id="t1", name="n1", scopes=["llm"], status="active", created_at=SimpleNamespace(isoformat=lambda: "x"), last_used_at=None)]

    monkeypatch.setattr(tokens_api, "create_token", _token_create)
    monkeypatch.setattr(tokens_api, "list_tokens", _token_list)
    monkeypatch.setattr(tokens_api, "revoke_token", _raise)
    created = await tokens_api.create(SimpleNamespace(name="n", scopes=["llm"]), db_session, user)
    assert created.token == "raw"
    listed = await tokens_api.list_all(db_session, user)
    assert listed[0].id == "t1"
    with pytest.raises(Exception):
        await tokens_api.delete("x", req, db_session, user)

    wallet_obj = SimpleNamespace(balance_credits=1, updated_at=SimpleNamespace(isoformat=lambda: "now"))
    ledger_item = SimpleNamespace(
        id="l1",
        entry_type="credit",
        amount_credits=1,
        status="settled",
        ref_type="r",
        ref_id="r1",
        meta={},
        created_at=SimpleNamespace(isoformat=lambda: "ts"),
    )
    monkeypatch.setattr(billing_api, "get_wallet", lambda db, uid: _await(wallet_obj))
    monkeypatch.setattr(billing_api, "list_ledger", lambda db, uid, limit: _await([ledger_item]))
    monkeypatch.setattr(billing_api, "redeem_code", _raise)
    w = await billing_api.wallet(db_session, user)
    assert w.balance_credits == 1
    lg = await billing_api.ledger(db_session, user)
    assert len(lg) == 1
    with pytest.raises(Exception):
        await billing_api.redeem(SimpleNamespace(code="x"), req, db_session, user)

    model = Model(name="md", category="llm", enabled=True, multiplier=1, pricing={})
    db_session.add(model)
    await db_session.commit()
    model_list = await models_api.list_models(db_session)
    assert len(model_list) >= 1


async def _await(v):
    return v


@pytest.mark.asyncio
async def test_auth_and_billing_services_remaining_lines(db_session):
    await register_user(db_session, "svc-user@example.com", "pass")
    with pytest.raises(ValueError):
        await register_user(db_session, "svc-user@example.com", "pass")
    with pytest.raises(ValueError):
        await login_user(db_session, "svc-user@example.com", "bad")

    wallet = await get_wallet(db_session, "wallet-user")
    assert wallet.user_id == "wallet-user"
    ledger_rows = await list_ledger(db_session, "wallet-user", 10)
    assert isinstance(ledger_rows, list)

    u = User(email="authz@example.com", password_hash="x", status="active")
    db_session.add(u)
    await db_session.commit()
    w = Wallet(user_id=u.id, balance_credits=0)
    db_session.add(w)
    await db_session.commit()
    with pytest.raises(ValueError):
        await authorize_usage(db_session, u.id, "t1", "r1", "m1", 5, {})

    db_session.add(
        LedgerEntry(
            user_id=u.id,
            entry_type="credit",
            amount_credits=1,
            status="settled",
            ref_type="x",
            ref_id="y",
            meta={},
        )
    )
    await db_session.commit()
    assert await list_ledger(db_session, u.id, 10)

