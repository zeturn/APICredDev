from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets import decrypt_secret
from app.db.models.brand import Brand
from app.db.models.model import Model
from app.db.models.provider import Provider
from app.db.models.provider_key import ProviderKey
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.user import User
from app.db.models.usage_session import UsageSession
from app.db.models.wallet import Wallet
from app.services.providers.factory import OPENAI_COMPAT_PROVIDERS
from app.services.providers.presets import get_provider_default_base_url
from app.core.secrets import encrypt_secret


async def list_brands(db: AsyncSession) -> list[Brand]:
    result = await db.execute(select(Brand).order_by(Brand.name.asc()))
    return list(result.scalars().all())


async def upsert_brand(db: AsyncSession, payload: dict) -> Brand:
    item_id = payload.get("id")
    if item_id:
        brand = await db.get(Brand, item_id)
    else:
        brand = None
    if not brand:
        brand = Brand(**payload)
        db.add(brand)
    else:
        for k, v in payload.items():
            setattr(brand, k, v)
    await db.commit()
    await db.refresh(brand)
    return brand


async def list_providers(db: AsyncSession) -> list[Provider]:
    result = await db.execute(select(Provider).order_by(Provider.name.asc()))
    return list(result.scalars().all())


async def upsert_provider(db: AsyncSession, payload: dict) -> Provider:
    item_id = payload.get("id")
    if item_id:
        provider = await db.get(Provider, item_id)
    else:
        provider = None
    if not provider:
        provider = Provider(**payload)
        db.add(provider)
    else:
        for k, v in payload.items():
            setattr(provider, k, v)
    await db.commit()
    await db.refresh(provider)
    return provider


async def list_models(db: AsyncSession) -> list[Model]:
    result = await db.execute(select(Model))
    return list(result.scalars().all())


async def upsert_model(db: AsyncSession, payload: dict) -> Model:
    model_id = payload.get("id")
    if model_id:
        model = await db.get(Model, model_id)
    else:
        model = None
    if not model:
        model = Model(**payload)
        db.add(model)
    else:
        for k, v in payload.items():
            setattr(model, k, v)
    await db.commit()
    await db.refresh(model)
    return model


async def list_provider_keys(db: AsyncSession) -> list[ProviderKey]:
    result = await db.execute(select(ProviderKey))
    return list(result.scalars().all())


async def get_provider_key(db: AsyncSession, provider_key_id: str) -> ProviderKey | None:
    return await db.get(ProviderKey, provider_key_id)


async def upsert_provider_key(db: AsyncSession, payload: dict) -> ProviderKey:
    provider_id = payload.get("provider_id")
    if provider_id:
        provider = await db.get(Provider, provider_id)
        if provider:
            payload["provider"] = provider.slug
    api_key = (payload.pop("api_key", None) or "").strip()
    secret_ref = (payload.get("secret_ref") or "").strip()
    if api_key:
        payload["secret_encrypted"] = encrypt_secret(api_key)
        payload["secret_last4"] = api_key[-4:]
        payload["secret_ref"] = ""
    else:
        payload["secret_ref"] = secret_ref
    item_id = payload.get("id")
    if item_id:
        pkey = await db.get(ProviderKey, item_id)
    else:
        pkey = None
    if not pkey:
        pkey = ProviderKey(**payload)
        db.add(pkey)
    else:
        for k, v in payload.items():
            setattr(pkey, k, v)
    await db.commit()
    await db.refresh(pkey)
    return pkey


async def validate_provider_key(db: AsyncSession, provider_key_id: str) -> dict:
    provider_key = await db.get(ProviderKey, provider_key_id)
    if not provider_key:
        raise ValueError("provider_key_not_found")

    provider = await db.get(Provider, provider_key.provider_id) if provider_key.provider_id else None
    base_url = (provider_key.key_name or "").strip() or (getattr(provider, "default_base_url", None) or "").strip() or get_provider_default_base_url(provider_key.provider) or ""
    api_key = decrypt_secret(provider_key.secret_encrypted) if provider_key.secret_encrypted else ""
    if not api_key and provider_key.secret_ref:
        return {"ok": False, "provider": provider_key.provider, "base_url": base_url, "message": "legacy secret_ref requires environment variable"}
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


async def list_model_provider_keys(db: AsyncSession) -> list[ModelProviderKey]:
    result = await db.execute(select(ModelProviderKey))
    return list(result.scalars().all())


async def list_model_provider_keys_by_provider_key(db: AsyncSession, provider_key_id: str) -> list[ModelProviderKey]:
    result = await db.execute(
        select(ModelProviderKey)
        .where(ModelProviderKey.provider_key_id == provider_key_id)
        .order_by(ModelProviderKey.priority.asc(), ModelProviderKey.weight.desc())
    )
    return list(result.scalars().all())


async def upsert_model_provider_key(db: AsyncSession, payload: dict) -> ModelProviderKey:
    item_id = payload.get("id")
    if item_id:
        mpk = await db.get(ModelProviderKey, item_id)
    else:
        mpk = None
    if not mpk:
        mpk = ModelProviderKey(**payload)
        db.add(mpk)
    else:
        for k, v in payload.items():
            setattr(mpk, k, v)
    await db.commit()
    await db.refresh(mpk)
    return mpk


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(
            User.id,
            User.email,
            User.status,
            User.created_at,
            func.coalesce(Wallet.balance_credits, 0).label("balance_credits"),
            func.coalesce(func.sum(UsageSession.final_cost_credits), 0).label("used_credits"),
            func.count(UsageSession.id).label("usage_sessions"),
        )
        .outerjoin(Wallet, Wallet.user_id == User.id)
        .outerjoin(UsageSession, UsageSession.user_id == User.id)
        .group_by(User.id, User.email, User.status, User.created_at, Wallet.balance_credits)
        .order_by(User.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": row.id,
            "email": row.email,
            "status": row.status,
            "created_at": row.created_at,
            "balance_credits": float(row.balance_credits or 0),
            "used_credits": float(row.used_credits or 0),
            "usage_sessions": int(row.usage_sessions or 0),
        }
        for row in rows
    ]


async def update_user_status(db: AsyncSession, user_id: str, status: str) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise ValueError("user_not_found")
    user.status = status
    await db.commit()
    await db.refresh(user)
    return user


async def get_admin_dashboard(db: AsyncSession) -> dict:
    total_users = int((await db.execute(select(func.count()).select_from(User))).scalar() or 0)
    active_users = int((await db.execute(select(func.count()).select_from(User).where(User.status == "active"))).scalar() or 0)
    total_models = int((await db.execute(select(func.count()).select_from(Model))).scalar() or 0)
    enabled_models = int((await db.execute(select(func.count()).select_from(Model).where(Model.enabled.is_(True)))).scalar() or 0)
    provider_keys = int((await db.execute(select(func.count()).select_from(ProviderKey))).scalar() or 0)
    enabled_provider_keys = int((await db.execute(select(func.count()).select_from(ProviderKey).where(ProviderKey.enabled.is_(True)))).scalar() or 0)
    model_provider_links = int((await db.execute(select(func.count()).select_from(ModelProviderKey))).scalar() or 0)
    usage_sessions = int((await db.execute(select(func.count()).select_from(UsageSession))).scalar() or 0)
    completed_usage_sessions = int(
        (await db.execute(select(func.count()).select_from(UsageSession).where(UsageSession.status == "completed"))).scalar() or 0
    )
    total_usage_credits = Decimal(
        str((await db.execute(select(func.coalesce(func.sum(UsageSession.final_cost_credits), 0)).where(UsageSession.status == "completed"))).scalar() or 0)
    )
    total_remaining_credits = Decimal(str((await db.execute(select(func.coalesce(func.sum(Wallet.balance_credits), 0)).select_from(Wallet))).scalar() or 0))

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_models": total_models,
        "enabled_models": enabled_models,
        "provider_keys": provider_keys,
        "enabled_provider_keys": enabled_provider_keys,
        "model_provider_links": model_provider_links,
        "usage_sessions": usage_sessions,
        "completed_usage_sessions": completed_usage_sessions,
        "total_usage_credits": float(total_usage_credits),
        "total_remaining_credits": float(total_remaining_credits),
    }


async def list_usage_sessions(db: AsyncSession) -> list[UsageSession]:
    result = await db.execute(select(UsageSession))
    return list(result.scalars().all())

