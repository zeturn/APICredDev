import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets import decrypt_secret
from app.core.url_safety import normalize_upstream_base_url
from app.db.models.provider import Provider
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.provider_key import ProviderKey
from app.services.providers.factory import OPENAI_COMPAT_PROVIDERS
from app.services.providers.presets import get_provider_default_base_url


def _is_url_like_base_url(value: str | None) -> bool:
    lowered = (value or "").strip().lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


async def resolve_provider_key_base_url(db: AsyncSession, provider_key: ProviderKey) -> str:
    if provider_key.endpoint_id:
        endpoint = await db.get(ProviderEndpoint, provider_key.endpoint_id)
        if endpoint and endpoint.enabled:
            return normalize_upstream_base_url(endpoint.base_url)

    legacy_key_name = (provider_key.key_name or "").strip()
    if _is_url_like_base_url(legacy_key_name):
        return normalize_upstream_base_url(legacy_key_name)

    provider = await db.get(Provider, provider_key.provider_id) if provider_key.provider_id else None
    provider_default_base_url = (getattr(provider, "default_base_url", None) or "").strip() if provider else ""
    if provider_default_base_url:
        return normalize_upstream_base_url(provider_default_base_url)

    return normalize_upstream_base_url(get_provider_default_base_url(provider_key.provider))


async def validate_provider_key(db: AsyncSession, provider_key_id: str) -> dict:
    provider_key = await db.get(ProviderKey, provider_key_id)
    if not provider_key:
        raise ValueError("provider_key_not_found")

    base_url = await resolve_provider_key_base_url(db, provider_key)
    api_key = decrypt_secret(provider_key.secret_encrypted) if provider_key.secret_encrypted else ""
    if not api_key:
        return {"ok": False, "provider": provider_key.provider, "base_url": base_url, "message": "missing api key"}

    normalized = (provider_key.provider or "").strip().lower()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            if normalized in OPENAI_COMPAT_PROVIDERS:
                resp = await client.get(
                    base_url.rstrip("/") + "/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                ok = resp.status_code < 400
                return {
                    "ok": ok,
                    "provider": provider_key.provider,
                    "base_url": base_url,
                    "status_code": resp.status_code,
                    "model_count": len((payload or {}).get("data", []) or []),
                    "message": "validated" if ok else str(payload),
                }
            if normalized in {"anthropic", "claude"}:
                resp = await client.get(
                    base_url.rstrip("/") + "/v1/models",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                )
                payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                ok = resp.status_code < 400
                return {
                    "ok": ok,
                    "provider": provider_key.provider,
                    "base_url": base_url,
                    "status_code": resp.status_code,
                    "model_count": len((payload or {}).get("data", []) or []),
                    "message": "validated" if ok else str(payload),
                }
            if normalized in {"gemini", "google", "google_ai", "googleai"}:
                resp = await client.get(
                    base_url.rstrip("/") + "/v1beta/models",
                    params={"key": api_key},
                )
                payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                ok = resp.status_code < 400
                return {
                    "ok": ok,
                    "provider": provider_key.provider,
                    "base_url": base_url,
                    "status_code": resp.status_code,
                    "model_count": len((payload or {}).get("models", []) or []),
                    "message": "validated" if ok else str(payload),
                }
    except httpx.RequestError as exc:
        return {"ok": False, "provider": provider_key.provider, "base_url": base_url, "message": str(exc)}

    return {"ok": False, "provider": provider_key.provider, "base_url": base_url, "message": "unsupported provider"}
