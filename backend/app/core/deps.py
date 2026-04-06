from typing import Any, AsyncGenerator, List
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.api_token import ApiToken
from app.core.security import hash_api_token
from app.core.time import utc_now
from app.services.basaltpass_client import BasaltPassClient


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
    try:
        payload = decode_access_token(token)
    except Exception:
        raise AppError("auth_invalid", "invalid token", request.state.request_id, 401)
    user_id = payload.get("sub")
    if not user_id:
        raise AppError("auth_invalid", "invalid token", request.state.request_id, 401)
    user = await db.get(User, user_id)
    if not user or user.status != "active":
        raise AppError("auth_invalid", "invalid user", request.state.request_id, 401)
    return user


async def get_optional_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except Exception:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await db.get(User, user_id)
    if not user or user.status != "active":
        return None
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


def _extract_code_set(payload: Any) -> set[str]:
    values: list[Any] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("permission_codes"), list):
            values.extend(payload.get("permission_codes") or [])
        if isinstance(payload.get("role_codes"), list):
            values.extend(payload.get("role_codes") or [])
        if isinstance(payload.get("roles"), list):
            values.extend(payload.get("roles") or [])
        if isinstance(payload.get("permissions"), list):
            values.extend(payload.get("permissions") or [])
    elif isinstance(payload, list):
        values = payload

    codes: set[str] = set()
    for item in values:
        if isinstance(item, str):
            code = item.strip().lower()
            if code:
                codes.add(code)
            continue
        if isinstance(item, dict):
            code = str(item.get("code") or item.get("name") or "").strip().lower()
            if code:
                codes.add(code)
    return codes


def _has_required_code(codes: set[str], required: str) -> bool:
    if required in codes:
        return True

    suffix = f".{required}"
    for code in codes:
        if code.endswith(suffix):
            return True
    return False


def permission(required_code: str):
    required = required_code.strip().lower()

    async def _dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        client: BasaltPassClient = Depends(BasaltPassClient),
    ) -> None:
        if not settings.basalt_rbac_enforce:
            return

        basalt_user_id = (current_user.basalt_user_id or "").strip()
        if not basalt_user_id:
            if settings.basalt_rbac_strict_user_binding:
                raise AppError("rbac_user_unbound", "user is not bound to basalt account", request.state.request_id, 403)
            return

        tenant_id = (current_user.basalt_tenant_id or settings.basalt_default_tenant_id or "").strip() or None
        payload = await client.s2s_get_user_permissions(basalt_user_id, tenant_id=tenant_id)
        if isinstance(payload, dict) and "error" in payload:
            raise AppError("rbac_upstream_error", "failed to fetch user permissions", request.state.request_id, 502)
        if not _has_required_code(_extract_code_set(payload), required):
            raise AppError("permission_denied", f"missing permission: {required_code}", request.state.request_id, 403)

    return _dependency


def role(required_code: str):
    required = required_code.strip().lower()

    async def _dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        client: BasaltPassClient = Depends(BasaltPassClient),
    ) -> None:
        if not settings.basalt_rbac_enforce:
            return

        basalt_user_id = (current_user.basalt_user_id or "").strip()
        if not basalt_user_id:
            if settings.basalt_rbac_strict_user_binding:
                raise AppError("rbac_user_unbound", "user is not bound to basalt account", request.state.request_id, 403)
            return

        tenant_id = (current_user.basalt_tenant_id or settings.basalt_default_tenant_id or "").strip() or None
        payload = await client.s2s_get_user_roles(basalt_user_id, tenant_id=tenant_id)
        if isinstance(payload, dict) and "error" in payload:
            raise AppError("rbac_upstream_error", "failed to fetch user roles", request.state.request_id, 502)
        if not _has_required_code(_extract_code_set(payload), required):
            raise AppError("role_denied", f"missing role: {required_code}", request.state.request_id, 403)

    return _dependency


def token_permission(required_code: str):
    required = required_code.strip().lower()

    async def _dependency(
        request: Request,
        token: ApiToken = Depends(get_bearer_token),
        db: AsyncSession = Depends(get_db),
        client: BasaltPassClient = Depends(BasaltPassClient),
    ) -> None:
        if not settings.basalt_rbac_enforce:
            return

        user = await db.get(User, token.user_id)
        if not user:
            return

        basalt_user_id = (user.basalt_user_id or "").strip()
        if not basalt_user_id:
            if settings.basalt_rbac_strict_user_binding:
                raise AppError("rbac_user_unbound", "user is not bound to basalt account", request.state.request_id, 403)
            return

        tenant_id = (user.basalt_tenant_id or settings.basalt_default_tenant_id or "").strip() or None
        try:
            payload = await client.s2s_get_user_permissions(basalt_user_id, tenant_id=tenant_id)
        except ValueError:
            return
        if isinstance(payload, dict) and "error" in payload:
            raise AppError("rbac_upstream_error", "failed to fetch user permissions", request.state.request_id, 502)
        if not _has_required_code(_extract_code_set(payload), required):
            raise AppError("permission_denied", f"missing permission: {required_code}", request.state.request_id, 403)

    return _dependency

