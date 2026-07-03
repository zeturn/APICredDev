from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets import encrypt_secret
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.services.provider_health_service import run_provider_health_check


async def list_provider_health(db: AsyncSession) -> dict:
    rows = (
        await db.execute(
            select(ProviderCredential, ProviderEndpoint, Provider)
            .join(ProviderEndpoint, ProviderEndpoint.id == ProviderCredential.provider_endpoint_id)
            .join(Provider, Provider.id == ProviderEndpoint.provider_id)
            .order_by(Provider.slug.asc(), ProviderEndpoint.slug.asc(), ProviderCredential.display_name.asc())
        )
    ).all()
    items = []
    for credential, endpoint, provider in rows:
        routes_count = int(
            (
                await db.execute(
                    select(func.count()).select_from(ModelRoute).where(ModelRoute.provider_credential_id == credential.id)
                )
            ).scalar()
            or 0
        )
        items.append(
            {
                "provider": provider.slug,
                "endpoint": endpoint.display_name,
                "credential_id": credential.id,
                "credential_name": credential.display_name,
                "enabled": bool(credential.enabled),
                "health_state": credential.health_state,
                "cooldown_until": credential.cooldown_until.isoformat() if credential.cooldown_until else None,
                "last_checked_at": credential.last_checked_at.isoformat() if credential.last_checked_at else None,
                "last_success_at": credential.last_success_at.isoformat() if credential.last_success_at else None,
                "last_failure_at": credential.last_failure_at.isoformat() if credential.last_failure_at else None,
                "last_error_code": credential.last_error_code,
                "consecutive_failures": int(credential.consecutive_failures or 0),
                "routes_count": routes_count,
                "quota_status": {"minute": "unknown", "hour": "unknown", "day": "unknown"},
            }
        )
    return {"items": items}


async def set_credential_enabled(db: AsyncSession, credential_id: str, enabled: bool) -> ProviderCredential:
    credential = await db.get(ProviderCredential, credential_id)
    if not credential:
        raise ValueError("provider_credential_not_found")
    credential.enabled = enabled
    if not enabled:
        credential.health_state = "disabled"
    elif credential.health_state == "disabled":
        credential.health_state = "healthy"
    await db.commit()
    await db.refresh(credential)
    return credential


async def rotate_credential_secret(db: AsyncSession, credential_id: str, new_secret: str) -> ProviderCredential:
    credential = await db.get(ProviderCredential, credential_id)
    if not credential:
        raise ValueError("provider_credential_not_found")
    secret = str(new_secret or "").strip()
    if not secret:
        raise ValueError("secret_required")
    credential.secret_encrypted = encrypt_secret(secret)
    credential.secret_last4 = secret[-4:]
    await db.commit()
    await db.refresh(credential)
    return credential


async def model_route_effective_status(db: AsyncSession, route_id: str) -> dict:
    route = await db.get(ModelRoute, route_id)
    if not route:
        raise ValueError("route_not_found")
    credential = await db.get(ProviderCredential, route.provider_credential_id) if route.provider_credential_id else None
    endpoint = await db.get(ProviderEndpoint, credential.provider_endpoint_id) if credential else None
    effective_enabled = bool(route.enabled and (credential.enabled if credential else True) and (endpoint.enabled if endpoint else True))
    blockers = []
    if not route.enabled:
        blockers.append("route_disabled")
    if credential and not credential.enabled:
        blockers.append("credential_disabled")
    if endpoint and not endpoint.enabled:
        blockers.append("endpoint_disabled")
    if credential and credential.health_state == "disabled":
        blockers.append("credential_health_disabled")
    return {
        "route_id": route.id,
        "effective_enabled": effective_enabled,
        "blockers": blockers,
        "route_enabled": route.enabled,
        "credential_enabled": credential.enabled if credential else None,
        "credential_health_state": credential.health_state if credential else None,
        "endpoint_enabled": endpoint.enabled if endpoint else None,
        "endpoint_health_state": endpoint.health_state if endpoint else None,
    }


async def check_credential_health(db: AsyncSession, credential_id: str) -> dict:
    credential = await db.get(ProviderCredential, credential_id)
    if not credential:
        raise ValueError("provider_credential_not_found")
    return await run_provider_health_check(db, credential)
