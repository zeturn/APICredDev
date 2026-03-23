from typing import AsyncGenerator, List
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.api_token import ApiToken
from app.core.security import hash_api_token
from app.core.time import utc_now


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("auth_missing", "missing bearer token", request.state.request_id, 401)
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AppError("auth_invalid", "invalid token", request.state.request_id, 401)
    user = await db.get(User, user_id)
    if not user or user.status != "active":
        raise AppError("auth_invalid", "invalid user", request.state.request_id, 401)
    return user


async def get_bearer_token(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiToken:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("token_missing", "missing api token", request.state.request_id, 401)
    raw = authorization.split(" ", 1)[1]
    token_hash = hash_api_token(raw)
    result = await db.execute(select(ApiToken).where(ApiToken.token_hash == token_hash))
    token = result.scalar_one_or_none()
    if not token or token.status != "active":
        raise AppError("token_invalid", "invalid api token", request.state.request_id, 401)
    token.last_used_at = utc_now()
    await db.commit()
    return token


async def require_scopes(required: List[str], token: ApiToken, request: Request | None = None) -> None:
    scopes = set(token.scopes or [])
    for scope in required:
        if scope not in scopes:
            request_id = request.state.request_id if request else UUID(int=0)
            raise AppError("scope_missing", "missing scope", request_id, 403)

