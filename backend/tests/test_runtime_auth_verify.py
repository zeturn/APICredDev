import pytest

from app.api.v1 import auth
from app.api.v1.auth import RuntimeAuthVerifyRequest, runtime_auth_verify
from app.core.errors import AppError
from app.core.security import hash_api_token
from app.db.models.api_token import ApiToken
from app.db.models.user import User


class Request:
    class State:
        request_id = "req-test"

    state = State()


@pytest.mark.asyncio
async def test_runtime_auth_verify_accepts_active_api_token(db_session):
    user = User(id="user-1", email="u@example.com", password_hash="x", status="active")
    token = ApiToken(user_id=user.id, name="docode", token_hash=hash_api_token("raw-token"), scopes=["llm"], status="active")
    db_session.add(user)
    db_session.add(token)
    await db_session.commit()

    result = await runtime_auth_verify(RuntimeAuthVerifyRequest(access_token="raw-token"), Request(), db_session)

    assert result["allowed"] is True
    assert result["active"] is True
    assert result["user_id"] == "user-1"
    assert result["scopes"] == ["llm"]


@pytest.mark.asyncio
async def test_runtime_auth_verify_rejects_missing_or_unknown_token(db_session):
    missing = await runtime_auth_verify(RuntimeAuthVerifyRequest(), Request(), db_session)
    unknown = await runtime_auth_verify(RuntimeAuthVerifyRequest(access_token="missing-token"), Request(), db_session)

    assert missing["allowed"] is False
    assert missing["reason"] == "token_missing"
    assert unknown["allowed"] is False
    assert unknown["reason"] == "token_invalid"


@pytest.mark.asyncio
async def test_runtime_auth_verify_returns_denied_for_invalid_cross_app_token(db_session, monkeypatch):
    async def fail_introspection(request, raw, db):
        raise AppError("token_invalid", "invalid cross-app token", request.state.request_id, 401)

    monkeypatch.setattr(auth, "_get_cross_app_bearer_token", fail_introspection)

    result = await runtime_auth_verify(RuntimeAuthVerifyRequest(access_token="bp_xat_bad"), Request(), db_session)

    assert result["allowed"] is False
    assert result["active"] is False
    assert result["reason"] == "token_invalid"
