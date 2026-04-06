from __future__ import annotations

from typing import Any

from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError
from app.services.basaltpass_client import BasaltPassClient


def _admin_role_codes() -> set[str]:
    return {
        item.strip().lower()
        for item in settings.basalt_tenant_admin_role_codes.split(",")
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


async def is_tenant_admin(user: Any, client: BasaltPassClient) -> bool:
    basalt_user_id = getattr(user, "basalt_user_id", None)
    if not basalt_user_id:
        return False
    tenant_id = str(getattr(user, "basalt_tenant_id", "") or "") or None

    candidate_codes = _admin_role_codes()
    if not candidate_codes:
        return False

    permissions_payload = await client.s2s_get_user_permissions(str(basalt_user_id), tenant_id=tenant_id)
    role_codes = _extract_role_codes(permissions_payload)
    if role_codes.intersection(candidate_codes):
        return True

    roles_payload = await client.s2s_get_user_roles(str(basalt_user_id), tenant_id=tenant_id)
    role_codes.update(_extract_role_codes(roles_payload))
    return bool(role_codes.intersection(candidate_codes))


async def assert_admin_access(
    request: Request,
    x_admin_token: str | None,
    user: Any,
    client: BasaltPassClient,
) -> None:
    if x_admin_token and x_admin_token == settings.admin_token:
        return

    if user and await is_tenant_admin(user, client):
        return

    raise AppError("admin_unauthorized", "invalid admin token", request.state.request_id, 403)
