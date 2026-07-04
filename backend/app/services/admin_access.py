from __future__ import annotations

from typing import Any

from fastapi import Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import create_admin_access_token, decode_admin_access_token
from app.db.models.user import User
from app.services.basaltpass_client import BasaltPassClient


def _admin_role_codes() -> set[str]:
    return {
        item.strip().lower()
        for item in settings.basalt_tenant_admin_role_codes.split(",")
        if item.strip()
    }


def _admin_permission_codes() -> set[str]:
    return {
        item.strip().lower()
        for item in settings.basalt_admin_permission_codes.split(",")
        if item.strip()
    }


def _extract_role_codes(payload: Any) -> set[str]:
    codes: set[str] = set()
    if not isinstance(payload, dict):
        return codes

    role_codes = payload.get("role_codes")
    if isinstance(role_codes, list):
        for role in role_codes:
            if isinstance(role, str) and role:
                codes.add(role.strip().lower())

    roles = payload.get("roles")
    if isinstance(roles, list):
        for role in roles:
            if isinstance(role, str) and role:
                codes.add(role.strip().lower())
            elif isinstance(role, dict):
                code = role.get("code") or role.get("role_code")
                if isinstance(code, str) and code:
                    codes.add(code.strip().lower())

    return codes


def _extract_permission_codes(payload: Any) -> set[str]:
    codes: set[str] = set()
    if not isinstance(payload, dict):
        return codes

    permission_codes = payload.get("permission_codes")
    if isinstance(permission_codes, list):
        for permission in permission_codes:
            if isinstance(permission, str) and permission:
                codes.add(permission.strip().lower())

    permissions = payload.get("permissions")
    if isinstance(permissions, list):
        for permission in permissions:
            if isinstance(permission, str) and permission:
                codes.add(permission.strip().lower())
            elif isinstance(permission, dict):
                code = permission.get("code") or permission.get("permission_code") or permission.get("permission_key")
                if isinstance(code, str) and code:
                    codes.add(code.strip().lower())

    return codes


def _extract_admin_codes(payload: Any) -> set[str]:
    role_matches = _extract_role_codes(payload).intersection(_admin_role_codes())
    permission_matches = _extract_permission_codes(payload).intersection(_admin_permission_codes())
    return role_matches.union(permission_matches)


async def is_tenant_admin(user: Any, client: BasaltPassClient) -> bool:
    basalt_user_id = getattr(user, "basalt_user_id", None)
    if not basalt_user_id:
        return False
    tenant_id = str(getattr(user, "basalt_tenant_id", "") or "") or None

    if not _admin_role_codes() and not _admin_permission_codes():
        return False

    permissions_payload = await client.s2s_get_user_permissions(str(basalt_user_id), tenant_id=tenant_id)
    admin_codes = _extract_admin_codes(permissions_payload)
    if admin_codes:
        return True

    roles_payload = await client.s2s_get_user_roles(str(basalt_user_id), tenant_id=tenant_id)
    admin_codes.update(_extract_admin_codes(roles_payload))
    return bool(admin_codes)


async def resolve_tenant_admin_role_codes(user: Any, client: BasaltPassClient) -> set[str]:
    basalt_user_id = getattr(user, "basalt_user_id", None)
    if not basalt_user_id:
        return set()
    tenant_id = str(getattr(user, "basalt_tenant_id", "") or "") or None
    if not _admin_role_codes() and not _admin_permission_codes():
        return set()

    permissions_payload = await client.s2s_get_user_permissions(str(basalt_user_id), tenant_id=tenant_id)
    admin_codes = _extract_admin_codes(permissions_payload)

    roles_payload = await client.s2s_get_user_roles(str(basalt_user_id), tenant_id=tenant_id)
    admin_codes.update(_extract_admin_codes(roles_payload))
    return admin_codes


async def issue_admin_access_token(user: Any, client: BasaltPassClient) -> str:
    role_codes = await resolve_tenant_admin_role_codes(user, client)
    if not role_codes:
        raise PermissionError("missing admin role")

    basalt_user_id = str(getattr(user, "basalt_user_id", "") or "").strip()
    if not basalt_user_id:
        raise PermissionError("missing basalt user binding")

    basalt_tenant_id = str(getattr(user, "basalt_tenant_id", "") or "").strip() or None
    return create_admin_access_token(
        subject=str(getattr(user, "id")),
        basalt_user_id=basalt_user_id,
        basalt_tenant_id=basalt_tenant_id,
        admin_roles=sorted(role_codes),
    )


def _extract_bearer_value(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if value.lower().startswith("bearer "):
        token = value.split(" ", 1)[1].strip()
        return token or None
    return None


async def assert_admin_access(
    request: Request,
    authorization: str | None,
    x_admin_authorization: str | None,
    x_admin_token: str | None,
    db: AsyncSession,
    client: BasaltPassClient,
) -> User:
    if x_admin_token:
        raise AppError("admin_token_legacy_disabled", "legacy admin token is disabled", request.state.request_id, 401)

    credential = _extract_bearer_value(x_admin_authorization) or _extract_bearer_value(authorization)
    if not credential:
        raise AppError("admin_auth_missing", "missing admin bearer token", request.state.request_id, 401)

    try:
        claims = decode_admin_access_token(credential)
    except JWTError:
        raise AppError("admin_token_invalid", "invalid admin token", request.state.request_id, 401)
    except Exception:
        raise AppError("admin_token_invalid", "invalid admin token", request.state.request_id, 401)

    if str(claims.get("typ") or "") != "admin_access":
        raise AppError("admin_token_invalid", "invalid admin token type", request.state.request_id, 401)

    user_id = str(claims.get("sub") or "").strip()
    if not user_id:
        raise AppError("admin_token_invalid", "invalid admin token subject", request.state.request_id, 401)

    user = await db.get(User, user_id)
    if not user or user.status != "active":
        raise AppError("admin_unauthorized", "invalid admin user", request.state.request_id, 403)

    token_basalt_user_id = str(claims.get("basalt_user_id") or "").strip()
    token_basalt_tenant_id = str(claims.get("basalt_tenant_id") or "").strip() or None
    user_basalt_user_id = str(getattr(user, "basalt_user_id", "") or "").strip()
    user_basalt_tenant_id = str(getattr(user, "basalt_tenant_id", "") or "").strip() or None

    if not token_basalt_user_id or token_basalt_user_id != user_basalt_user_id:
        raise AppError("admin_token_invalid", "admin binding mismatch", request.state.request_id, 401)
    if token_basalt_tenant_id != user_basalt_tenant_id:
        raise AppError("admin_token_invalid", "admin tenant mismatch", request.state.request_id, 401)

    try:
        live_role_codes = await resolve_tenant_admin_role_codes(user, client)
    except ValueError as exc:
        raise AppError("admin_check_unavailable", str(exc), request.state.request_id, 503)

    if not live_role_codes:
        raise AppError("admin_unauthorized", "missing admin role", request.state.request_id, 403)

    token_role_codes = {
        str(code).strip().lower()
        for code in (claims.get("admin_roles") or [])
        if str(code).strip()
    }
    if token_role_codes and not (token_role_codes.intersection(live_role_codes)):
        raise AppError("admin_token_invalid", "admin role changed", request.state.request_id, 401)

    request.state.admin_user_id = str(user.id)
    request.state.admin_tenant_id = user_basalt_tenant_id
    return user
