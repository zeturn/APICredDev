from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.services.admin_access import assert_admin_access
from app.services.basaltpass_client import BasaltPassClient
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["basalt"])


@dataclass(frozen=True)
class ProxyRouteSpec:
    method: str
    apicred_path: str
    basalt_path: str
    admin_only: bool = False


def get_basalt_client() -> BasaltPassClient:
    return BasaltPassClient()


async def _require_admin_access(
    request: Request,
    authorization: str | None = Header(default=None),
    x_admin_authorization: str | None = Header(default=None, alias="X-Admin-Authorization"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    db: AsyncSession = Depends(get_db),
    client: BasaltPassClient = Depends(get_basalt_client),
) -> None:
    await assert_admin_access(
        request=request,
        authorization=authorization,
        x_admin_authorization=x_admin_authorization,
        x_admin_token=x_admin_token,
        db=db,
        client=client,
    )


def _extract_codes(payload: Any) -> set[str]:
    values: list[Any] = []
    if isinstance(payload, list):
        values = payload
    elif isinstance(payload, dict):
        for key in ("permissions", "roles", "permission_codes", "role_codes"):
            raw = payload.get(key)
            if isinstance(raw, list):
                values.extend(raw)

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


def _has_required_permission(codes: set[str], required: str) -> bool:
    if required in codes:
        return True
    required_suffix = f".{required}"
    for code in codes:
        if code.endswith(required_suffix):
            return True
    return False


def _build_user_permission_dependency(required_code: str):
    required = required_code.strip().lower()

    async def _dependency(
        request: Request,
        client: BasaltPassClient = Depends(get_basalt_client),
        user=Depends(get_current_user),
    ) -> None:
        if not settings.basalt_rbac_enforce:
            return

        basalt_user_id = (getattr(user, "basalt_user_id", None) or "").strip()
        if not basalt_user_id:
            raise AppError("rbac_user_unbound", "user is not linked to BasaltPass", request.state.request_id, 403)

        tenant_id = (getattr(user, "basalt_tenant_id", None) or settings.basalt_default_tenant_id or "").strip() or None
        try:
            payload = await client.s2s_get_user_permissions(basalt_user_id, tenant_id=tenant_id)
        except ValueError:
            return

        if not _has_required_permission(_extract_codes(payload), required):
            raise AppError("permission_denied", f"missing permission: {required_code}", request.state.request_id, 403)

    return _dependency


def _extract_body(payload: Any) -> Any:
    if payload in (None, "", b""):
        return None
    if isinstance(payload, (dict, list)):
        return payload
    return {"raw": str(payload)}


async def _proxy_request(
    request: Request,
    client: BasaltPassClient,
    spec: ProxyRouteSpec,
    user_context: dict[str, str] | None = None,
) -> JSONResponse:
    body = None
    if request.method.upper() not in {"GET", "DELETE"}:
        try:
            body = _extract_body(await request.json())
        except Exception:
            body = None

    upstream_path = spec.basalt_path
    for key, value in request.path_params.items():
        upstream_path = upstream_path.replace(f"{{{key}}}", str(value))

    response = await client.proxy(
        method=spec.method,
        upstream_path=upstream_path,
        query=dict(request.query_params),
        body=body,
        headers=user_context,
    )
    return JSONResponse(
        status_code=response.status_code,
        content={
            "upstream_status": response.status_code,
            "upstream_path": upstream_path,
            "data": response.payload,
        },
    )


def _build_user_handler(spec: ProxyRouteSpec):
    async def _handler(
        request: Request,
        client: BasaltPassClient = Depends(get_basalt_client),
        user=Depends(get_current_user),
        x_basalt_access_token: str | None = Header(default=None),
    ) -> JSONResponse:
        basalt_user_id = str(getattr(user, "basalt_user_id", "") or "").strip()
        route_user_id = str(request.path_params.get("user_id") or "").strip()
        if route_user_id and (not basalt_user_id or route_user_id != basalt_user_id):
            raise AppError("forbidden_user_scope", "user scope mismatch", request.state.request_id, 403)
        headers: dict[str, str] = {
            "X-APICRED-USER-ID": str(user.id),
            "X-APICRED-USER-EMAIL": str(user.email),
            "X-APICRED-BASALT-USER-ID": basalt_user_id,
        }
        if x_basalt_access_token:
            headers["Authorization"] = f"Bearer {x_basalt_access_token}"
        return await _proxy_request(request, client, spec, headers)

    return _handler


def _build_admin_handler(spec: ProxyRouteSpec):
    async def _handler(
        request: Request,
        _: None = Depends(_require_admin_access),
        client: BasaltPassClient = Depends(get_basalt_client),
    ) -> JSONResponse:
        return await _proxy_request(request, client, spec)

    return _handler


def _get_basalt_identity(user: Any, request: Request) -> tuple[str, str | None]:
    basalt_user_id = getattr(user, "basalt_user_id", None)
    if not basalt_user_id:
        raise AppError("basalt_identity_missing", "current user is not linked to BasaltPass", request.state.request_id, 400)
    return str(basalt_user_id), (str(getattr(user, "basalt_tenant_id", "")) or None)


@router.get("/basalt/tenant-hint")
async def basalt_tenant_hint(
    request: Request,
    client: BasaltPassClient = Depends(get_basalt_client),
    user=Depends(get_current_user),
) -> JSONResponse:
    if not getattr(user, "basalt_user_id", None):
        raise AppError("basalt_identity_missing", "current user is not linked to BasaltPass", request.state.request_id, 400)

    try:
        s2s_me = await client.s2s_get_me()
    except ValueError as exc:
        raise AppError("s2s_config_missing", str(exc), request.state.request_id, 500)

    tenant_code = None
    tenant_id = None
    if isinstance(s2s_me, dict):
        tenant_code = (s2s_me.get("tenant_code") or "").strip() or None
        tenant_id = s2s_me.get("tenant_id")

    return JSONResponse(
        content={
            "data": {
                "tenant_code": tenant_code,
                "tenant_id": tenant_id,
            }
        }
    )


@router.get("/basalt/debug/context")
async def basalt_debug_context(
    request: Request,
    client: BasaltPassClient = Depends(get_basalt_client),
    user=Depends(get_current_user),
) -> JSONResponse:
    if not settings.debug_endpoints_enabled:
        raise AppError("debug_endpoint_disabled", "debug endpoints are disabled", request.state.request_id, 403)

    basalt_user_id = getattr(user, "basalt_user_id", None)
    basalt_tenant_id = getattr(user, "basalt_tenant_id", None)
    s2s_configured = bool(settings.basalt_s2s_client_id and settings.basalt_s2s_client_secret)

    s2s_me = None
    s2s_error = None
    if s2s_configured:
        try:
            s2s_me = await client.s2s_get_me()
        except ValueError as exc:
            s2s_error = str(exc)
        except Exception as exc:
            s2s_error = str(exc)

    return JSONResponse(
        content={
            "data": {
                "apicred_user_id": str(user.id),
                "apicred_email": str(user.email),
                "basalt_user_id": basalt_user_id,
                "basalt_tenant_id": basalt_tenant_id,
                "s2s_configured": s2s_configured,
                "s2s_me": s2s_me,
                "s2s_error": s2s_error,
            }
        }
    )


@router.get("/basalt/permissions")
async def basalt_permissions(
    request: Request,
    client: BasaltPassClient = Depends(get_basalt_client),
    user=Depends(get_current_user),
) -> JSONResponse:
    basalt_user_id, tenant_id = _get_basalt_identity(user, request)
    try:
        data = await client.s2s_get_user_permissions(basalt_user_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise AppError("s2s_config_missing", str(exc), request.state.request_id, 500)
    return JSONResponse(content={"data": data})


@router.get("/basalt/roles")
async def basalt_roles(
    request: Request,
    client: BasaltPassClient = Depends(get_basalt_client),
    user=Depends(get_current_user),
) -> JSONResponse:
    basalt_user_id, tenant_id = _get_basalt_identity(user, request)
    try:
        data = await client.s2s_get_user_roles(basalt_user_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise AppError("s2s_config_missing", str(exc), request.state.request_id, 500)
    return JSONResponse(content={"data": data})


@router.get("/basalt/wallet/balance")
async def basalt_wallet_balance(
    request: Request,
    currency: str = "CNY",
    limit: int = 20,
    client: BasaltPassClient = Depends(get_basalt_client),
    user=Depends(get_current_user),
) -> JSONResponse:
    basalt_user_id, tenant_id = _get_basalt_identity(user, request)
    try:
        data = await client.s2s_get_user_wallet(
            basalt_user_id,
            currency=currency,
            limit=limit,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise AppError("s2s_config_missing", str(exc), request.state.request_id, 500)
    if not isinstance(data, dict):
        return JSONResponse(content={"data": data})
    return JSONResponse(
        content={
            "data": {
                "wallet_id": data.get("wallet_id"),
                "currency": data.get("currency"),
                "balance": data.get("balance"),
            }
        }
    )


@router.get("/basalt/wallet/history")
async def basalt_wallet_history(
    request: Request,
    currency: str = "CNY",
    limit: int = 20,
    client: BasaltPassClient = Depends(get_basalt_client),
    user=Depends(get_current_user),
) -> JSONResponse:
    basalt_user_id, tenant_id = _get_basalt_identity(user, request)
    try:
        data = await client.s2s_get_user_wallet(
            basalt_user_id,
            currency=currency,
            limit=limit,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise AppError("s2s_config_missing", str(exc), request.state.request_id, 500)
    transactions = data.get("transactions", []) if isinstance(data, dict) else []
    return JSONResponse(content={"data": {"transactions": transactions}})


USER_PROXY_SPECS: list[ProxyRouteSpec] = [
    ProxyRouteSpec("GET", "/basalt/health", "/api/v1/health"),
    ProxyRouteSpec("POST", "/basalt/auth/login", "/api/v1/auth/login"),
    ProxyRouteSpec("POST", "/basalt/auth/refresh", "/api/v1/auth/refresh"),
    ProxyRouteSpec("GET", "/basalt/auth/oauth/{provider}/login", "/api/v1/auth/oauth/{provider}/login"),
    ProxyRouteSpec("GET", "/basalt/auth/oauth/{provider}/callback", "/api/v1/auth/oauth/{provider}/callback"),
    ProxyRouteSpec("POST", "/basalt/security/2fa/setup", "/api/v1/security/2fa/setup"),
    ProxyRouteSpec("POST", "/basalt/security/2fa/verify", "/api/v1/security/2fa/verify"),
    ProxyRouteSpec("GET", "/basalt/apps", "/api/v1/user/apps"),
    ProxyRouteSpec("GET", "/basalt/apps/{app_id}/permissions", "/api/v1/tenant/apps/{app_id}/permissions"),
    ProxyRouteSpec("GET", "/basalt/apps/{app_id}/roles", "/api/v1/tenant/apps/{app_id}/roles"),
    ProxyRouteSpec("POST", "/basalt/wallet/recharge", "/api/v1/wallet/recharge"),
    ProxyRouteSpec("POST", "/basalt/wallet/withdraw", "/api/v1/wallet/withdraw"),
    ProxyRouteSpec("GET", "/basalt/user/profile", "/api/v1/user/profile"),
    ProxyRouteSpec("PUT", "/basalt/user/profile", "/api/v1/user/profile"),
    ProxyRouteSpec("GET", "/basalt/user/tenants", "/api/v1/user/tenants"),
    ProxyRouteSpec("GET", "/basalt/notifications", "/api/v1/notifications/"),
    ProxyRouteSpec("PUT", "/basalt/notifications/{id}/read", "/api/v1/notifications/{id}/read"),
    ProxyRouteSpec("GET", "/basalt/subscriptions", "/api/v1/subscriptions/"),
    ProxyRouteSpec("POST", "/basalt/subscriptions/checkout", "/api/v1/subscriptions/checkout"),
    ProxyRouteSpec("GET", "/basalt/orders", "/api/v1/orders/"),
    ProxyRouteSpec("POST", "/basalt/orders", "/api/v1/orders/"),
    ProxyRouteSpec("GET", "/basalt/orders/{id}", "/api/v1/orders/{id}"),
    ProxyRouteSpec("POST", "/basalt/usage/records", "/api/v1/usage/records"),
    ProxyRouteSpec("GET", "/basalt/passkey/list", "/api/v1/passkey/list"),
    ProxyRouteSpec("POST", "/basalt/passkey/register/begin", "/api/v1/passkey/register/begin"),
    ProxyRouteSpec("POST", "/basalt/passkey/register/finish", "/api/v1/passkey/register/finish"),
]

ADMIN_PROXY_SPECS: list[ProxyRouteSpec] = [
    ProxyRouteSpec("GET", "/admin/basalt/dashboard/stats", "/api/v1/admin/dashboard/stats", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/dashboard/activities", "/api/v1/admin/dashboard/activities", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/apps", "/api/v1/admin/apps/", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/apps", "/api/v1/admin/apps/", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/apps/{id}", "/api/v1/admin/apps/{id}", admin_only=True),
    ProxyRouteSpec("PUT", "/admin/basalt/apps/{id}", "/api/v1/admin/apps/{id}", admin_only=True),
    ProxyRouteSpec("DELETE", "/admin/basalt/apps/{id}", "/api/v1/admin/apps/{id}", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/apps/{id}/stats", "/api/v1/admin/apps/{id}/stats", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/apps/{app_id}/users", "/api/v1/admin/apps/{app_id}/users", admin_only=True),
    ProxyRouteSpec("PUT", "/admin/basalt/apps/{app_id}/users/{user_id}/status", "/api/v1/admin/apps/{app_id}/users/{user_id}/status", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/users", "/api/v1/admin/users/", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/users", "/api/v1/admin/users/", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/users/{id}", "/api/v1/admin/users/{id}", admin_only=True),
    ProxyRouteSpec("PUT", "/admin/basalt/users/{id}", "/api/v1/admin/users/{id}", admin_only=True),
    ProxyRouteSpec("DELETE", "/admin/basalt/users/{id}", "/api/v1/admin/users/{id}", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/users/{id}/ban", "/api/v1/admin/users/{id}/ban", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/users/{id}/wallets", "/api/v1/admin/users/{id}/wallets", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/users/stats", "/api/v1/admin/users/stats", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/roles", "/api/v1/admin/roles", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/roles", "/api/v1/admin/roles", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/roles/{id}/permissions", "/api/v1/admin/roles/{id}/permissions", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/roles/{id}/permissions", "/api/v1/admin/roles/{id}/permissions", admin_only=True),
    ProxyRouteSpec("DELETE", "/admin/basalt/roles/{id}/permissions/{permission_id}", "/api/v1/admin/roles/{id}/permissions/{permission_id}", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/permissions", "/api/v1/admin/permissions/", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/permissions", "/api/v1/admin/permissions/", admin_only=True),
    ProxyRouteSpec("PUT", "/admin/basalt/permissions/{id}", "/api/v1/admin/permissions/{id}", admin_only=True),
    ProxyRouteSpec("DELETE", "/admin/basalt/permissions/{id}", "/api/v1/admin/permissions/{id}", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/wallets", "/api/v1/admin/wallets/", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/wallets/{id}/adjust", "/api/v1/admin/wallets/{id}/adjust", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/wallets/{id}/freeze", "/api/v1/admin/wallets/{id}/freeze", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/wallets/{id}/unfreeze", "/api/v1/admin/wallets/{id}/unfreeze", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/wallets/{id}/transactions", "/api/v1/admin/wallets/{id}/transactions", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/wallets/stats", "/api/v1/admin/wallets/stats", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/tenants", "/api/v1/admin/tenants/", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/tenants", "/api/v1/admin/tenants/", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/tenants/{id}", "/api/v1/admin/tenants/{id}", admin_only=True),
    ProxyRouteSpec("PUT", "/admin/basalt/tenants/{id}", "/api/v1/admin/tenants/{id}", admin_only=True),
    ProxyRouteSpec("DELETE", "/admin/basalt/tenants/{id}", "/api/v1/admin/tenants/{id}", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/tenants/{id}/users", "/api/v1/admin/tenants/{id}/users", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/tenants/stats", "/api/v1/admin/tenants/stats", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/subscriptions", "/api/v1/admin/subscriptions/", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/subscriptions/{id}", "/api/v1/admin/subscriptions/{id}", admin_only=True),
    ProxyRouteSpec("PUT", "/admin/basalt/subscriptions/{id}/cancel", "/api/v1/admin/subscriptions/{id}/cancel", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/logs", "/api/v1/admin/logs", admin_only=True),
    ProxyRouteSpec("GET", "/admin/basalt/notifications", "/api/v1/admin/notifications/", admin_only=True),
    ProxyRouteSpec("POST", "/admin/basalt/notifications", "/api/v1/admin/notifications/", admin_only=True),
    ProxyRouteSpec("DELETE", "/admin/basalt/notifications/{id}", "/api/v1/admin/notifications/{id}", admin_only=True),
]

for _spec in USER_PROXY_SPECS:
    _permission_code = "read" if _spec.method.upper() == "GET" else "write"
    router.add_api_route(
        _spec.apicred_path,
        endpoint=_build_user_handler(_spec),
        methods=[_spec.method],
        dependencies=[Depends(_build_user_permission_dependency(_permission_code))],
        name=f"user_proxy_{_spec.method.lower()}_{_spec.apicred_path}",
    )

for _spec in ADMIN_PROXY_SPECS:
    router.add_api_route(
        _spec.apicred_path,
        endpoint=_build_admin_handler(_spec),
        methods=[_spec.method],
        name=f"admin_proxy_{_spec.method.lower()}_{_spec.apicred_path}",
    )

