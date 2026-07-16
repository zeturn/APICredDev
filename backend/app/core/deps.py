from dataclasses import dataclass
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
from app.services.auth_service import get_or_create_oauth_user


@dataclass
class CrossAppBearerToken:
    id: str
    user_id: str
    name: str
    scopes: list[str]
    status: str = "active"
    last_used_at: Any = None
    basalt_client_id: str | None = None
    basalt_tenant_id: str | None = None
    basalt_actor: Any = None
    principal_type: str = "user"
    principal_id: str | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif request.cookies.get(settings.auth_cookie_name):
        token = request.cookies.get(settings.auth_cookie_name)

    if not token:
        raise AppError("auth_missing", "missing bearer token", request.state.request_id, 401)

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
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    else:
        token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        return None
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
) -> ApiToken | CrossAppBearerToken:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("token_missing", "missing api token", request.state.request_id, 401)
    raw = authorization.split(" ", 1)[1]
    if raw.startswith("bp_xat_"):
        return await _get_cross_app_bearer_token(request, raw, db)

    token_hash = hash_api_token(raw)
    result = await db.execute(select(ApiToken).where(ApiToken.token_hash == token_hash))
    token = result.scalar_one_or_none()
    if not token or token.status != "active":
        raise AppError("token_invalid", "invalid api token", request.state.request_id, 401)
    token.last_used_at = utc_now()
    await db.commit()
    return token


def _split_scope_string(scope: Any) -> list[str]:
    if not isinstance(scope, str):
        return []
    return [part for part in scope.replace(",", " ").split() if part]


def _extract_introspection_email(payload: dict[str, Any]) -> str | None:
    for key in ("email", "username", "preferred_username"):
        value = payload.get(key)
        if isinstance(value, str) and "@" in value:
            return value.strip().lower()
    return None


async def _get_cross_app_bearer_token(
    request: Request,
    raw: str,
    db: AsyncSession,
) -> CrossAppBearerToken:
    client = BasaltPassClient()
    try:
        payload = await client.introspect_oauth_token(raw)
    except ValueError:
        raise AppError("cross_app_config_missing", "Basalt OAuth client credentials are not configured", request.state.request_id, 500)

    if not isinstance(payload, dict) or payload.get("error"):
        raise AppError("token_invalid", "invalid cross-app token", request.state.request_id, 401)
    if payload.get("active") is not True:
        raise AppError("token_invalid", "inactive cross-app token", request.state.request_id, 401)

    client_id = str(payload.get("client_id") or "")
    audience = str(payload.get("aud") or "")
    expected_client_id = settings.basalt_oauth_client_id
    if expected_client_id and expected_client_id not in {client_id, audience}:
        raise AppError("token_invalid", "cross-app token is not issued for APICred", request.state.request_id, 403)

    scopes = _split_scope_string(payload.get("scope"))
    subject = str(payload.get("sub") or "").strip()
    email = _extract_introspection_email(payload)
    if not subject or not email:
        raise AppError("token_invalid", "cross-app token is missing user identity", request.state.request_id, 401)

    tenant_id = str(payload.get("tenant_id") or "").strip() or None

    subject_type = str(payload.get("subject_type") or "user").strip().lower()
    actor = payload.get("act") if isinstance(payload.get("act"), dict) else {}
    if subject_type == "app":
        principal_id = str(actor.get("app_id") or payload.get("app_id") or "").strip()
        if not principal_id:
            raise AppError("token_invalid", "cross-app token is missing app identity", request.state.request_id, 401)
        principal_type = "app"
    else:
        principal_type = "user"
        principal_id = subject

    user = await get_or_create_oauth_user(
        db,
        email=email,
        basalt_user_id=subject,
        basalt_tenant_id=tenant_id,
    )
    token_id = f"basalt:xat:{hash_api_token(raw)[:32]}"
    return CrossAppBearerToken(
        id=token_id,
        user_id=user.id,
        name="BasaltPass Cross-App Trust",
        scopes=scopes,
        last_used_at=utc_now(),
        basalt_client_id=client_id or None,
        basalt_tenant_id=tenant_id,
        basalt_actor=payload.get("act"),
        principal_type=principal_type,
        principal_id=principal_id,
    )


async def require_scopes(required: List[str], token: ApiToken | CrossAppBearerToken, request: Request | None = None) -> None:
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
            raise AppError("rbac_user_unbound", "user is not bound to basalt account", request.state.request_id, 403)

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
            raise AppError("rbac_user_unbound", "user is not bound to basalt account", request.state.request_id, 403)

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
        token: ApiToken | CrossAppBearerToken = Depends(get_bearer_token),
        db: AsyncSession = Depends(get_db),
        client: BasaltPassClient = Depends(BasaltPassClient),
    ) -> None:
        if not settings.basalt_rbac_enforce:
            return
        if isinstance(token, CrossAppBearerToken):
            return

        user = await db.get(User, token.user_id)
        if not user:
            return

        basalt_user_id = (user.basalt_user_id or "").strip()
        if not basalt_user_id:
            raise AppError("rbac_user_unbound", "user is not bound to basalt account", request.state.request_id, 403)

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

