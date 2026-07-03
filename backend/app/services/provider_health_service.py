from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets import decrypt_secret
from app.core.time import utc_now
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.services.providers.factory import OPENAI_COMPAT_PROVIDERS


def _health_probe_request(provider_slug: str, base_url: str, api_key: str) -> dict[str, Any]:
    provider = (provider_slug or "").strip().lower()
    if provider in OPENAI_COMPAT_PROVIDERS:
        return {
            "method": "GET",
            "url": base_url.rstrip("/") + "/v1/models",
            "headers": {"Authorization": f"Bearer {api_key}"},
            "json": None,
            "params": None,
        }
    if provider in {"anthropic", "claude"}:
        return {
            "method": "GET",
            "url": base_url.rstrip("/") + "/v1/models",
            "headers": {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            "json": None,
            "params": None,
        }
    if provider in {"gemini", "google", "google_ai", "googleai"}:
        return {
            "method": "GET",
            "url": base_url.rstrip("/") + "/v1beta/models",
            "headers": {},
            "json": None,
            "params": {"key": api_key},
        }
    return {
        "method": "GET",
        "url": base_url.rstrip("/") + "/health",
        "headers": {"Authorization": f"Bearer {api_key}"},
        "json": None,
        "params": None,
    }


async def run_provider_health_check(db: AsyncSession, credential: ProviderCredential) -> dict[str, Any]:
    endpoint = await db.get(ProviderEndpoint, credential.provider_endpoint_id)
    provider = await db.get(Provider, endpoint.provider_id) if endpoint else None
    if not endpoint or not provider:
        raise ValueError("provider_or_endpoint_missing")
    api_key = decrypt_secret(credential.secret_encrypted)
    probe = _health_probe_request(provider.slug, endpoint.base_url, api_key)

    now = utc_now()
    credential.last_checked_at = now
    ok = False
    error_code = ""
    error_message = ""
    status_code = 0
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(
                probe["method"],
                probe["url"],
                headers=probe["headers"],
                json=probe["json"],
                params=probe["params"],
            )
            status_code = int(response.status_code)
            response.raise_for_status()
            ok = True
    except Exception as exc:
        error_message = str(exc)[:500]
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = int(exc.response.status_code)
        if status_code in (401, 403):
            error_code = "auth_failed"
        elif status_code == 429:
            error_code = "rate_limited"
        elif status_code >= 500:
            error_code = "upstream_error"
        else:
            error_code = "request_error"

    if ok:
        credential.health_state = "healthy"
        credential.last_success_at = now
        credential.last_error_code = None
        credential.last_error_message = None
        credential.consecutive_failures = 0
    else:
        credential.health_state = "disabled" if error_code == "auth_failed" else "cooldown"
        credential.last_failure_at = now
        credential.last_error_code = error_code
        credential.last_error_message = error_message
        credential.consecutive_failures = int(credential.consecutive_failures or 0) + 1

    await db.commit()
    return {
        "credential_id": credential.id,
        "provider": provider.slug,
        "endpoint": endpoint.base_url,
        "ok": ok,
        "health_state": credential.health_state,
        "last_checked_at": credential.last_checked_at.isoformat() if credential.last_checked_at else None,
        "last_success_at": credential.last_success_at.isoformat() if credential.last_success_at else None,
        "last_failure_at": credential.last_failure_at.isoformat() if credential.last_failure_at else None,
        "last_error_code": credential.last_error_code,
        "consecutive_failures": int(credential.consecutive_failures or 0),
    }


async def health_check_by_id(db: AsyncSession, credential_id: str) -> dict[str, Any]:
    credential = await db.get(ProviderCredential, credential_id)
    if not credential:
        raise ValueError("credential_not_found")
    return await run_provider_health_check(db, credential)


async def health_check_all(db: AsyncSession, provider_slug: str | None = None) -> list[dict[str, Any]]:
    query = select(ProviderCredential).order_by(ProviderCredential.created_at.asc())
    rows = list((await db.execute(query)).scalars().all())
    results = []
    for credential in rows:
        endpoint = await db.get(ProviderEndpoint, credential.provider_endpoint_id)
        provider = await db.get(Provider, endpoint.provider_id) if endpoint else None
        if provider_slug and provider and provider.slug != provider_slug:
            continue
        if not credential.secret_encrypted:
            continue
        results.append(await run_provider_health_check(db, credential))
    return results
