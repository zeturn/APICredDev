import asyncio
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.brand import Brand
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.db.models.user import User
from app.db.models.usage_session import UsageSession
from app.db.models.wallet import Wallet
from app.services.basaltpass_client import BasaltPassClient
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


async def list_provider_endpoints(db: AsyncSession) -> list[ProviderEndpoint]:
    result = await db.execute(select(ProviderEndpoint).order_by(ProviderEndpoint.display_name.asc()))
    return list(result.scalars().all())


async def upsert_provider_endpoint(db: AsyncSession, payload: dict) -> ProviderEndpoint:
    item_id = payload.get("id")
    item = await db.get(ProviderEndpoint, item_id) if item_id else None
    if not item:
        item = ProviderEndpoint(**payload)
        db.add(item)
    else:
        for key, value in payload.items():
            setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def list_public_models(db: AsyncSession) -> list[PublicModel]:
    result = await db.execute(select(PublicModel).order_by(PublicModel.slug.asc()))
    return list(result.scalars().all())


async def upsert_public_model(db: AsyncSession, payload: dict) -> PublicModel:
    item_id = payload.get("id")
    item = await db.get(PublicModel, item_id) if item_id else None
    if not item:
        item = PublicModel(**payload)
        db.add(item)
    else:
        for key, value in payload.items():
            setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def list_upstream_models(db: AsyncSession) -> list[UpstreamModel]:
    result = await db.execute(select(UpstreamModel).order_by(UpstreamModel.upstream_name.asc()))
    return list(result.scalars().all())


async def upsert_upstream_model(db: AsyncSession, payload: dict) -> UpstreamModel:
    item_id = payload.get("id")
    item = await db.get(UpstreamModel, item_id) if item_id else None
    if not item:
        item = UpstreamModel(**payload)
        db.add(item)
    else:
        for key, value in payload.items():
            setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def list_provider_credentials(db: AsyncSession) -> list[ProviderCredential]:
    result = await db.execute(select(ProviderCredential).order_by(ProviderCredential.display_name.asc()))
    return list(result.scalars().all())


async def upsert_provider_credential(db: AsyncSession, payload: dict) -> ProviderCredential:
    credential_secret = (payload.pop("credential_secret", None) or payload.pop("api_key", None) or "").strip()
    if credential_secret:
        payload["secret_encrypted"] = encrypt_secret(credential_secret)
        payload["secret_last4"] = credential_secret[-4:]
    item_id = payload.get("id")
    item = await db.get(ProviderCredential, item_id) if item_id else None
    if not item:
        item = ProviderCredential(**payload)
        db.add(item)
    else:
        for key, value in payload.items():
            setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def list_model_routes(db: AsyncSession) -> list[ModelRoute]:
    result = await db.execute(select(ModelRoute).order_by(ModelRoute.priority.asc(), ModelRoute.weight.desc()))
    return list(result.scalars().all())


async def upsert_model_route(db: AsyncSession, payload: dict) -> ModelRoute:
    item_id = payload.get("id")
    item = await db.get(ModelRoute, item_id) if item_id else None
    if not item:
        item = ModelRoute(**payload)
        db.add(item)
    else:
        for key, value in payload.items():
            setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


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
    total_models = int((await db.execute(select(func.count()).select_from(PublicModel))).scalar() or 0)
    enabled_models = int((await db.execute(select(func.count()).select_from(PublicModel).where(PublicModel.enabled.is_(True)))).scalar() or 0)
    provider_credentials = int((await db.execute(select(func.count()).select_from(ProviderCredential))).scalar() or 0)
    enabled_provider_credentials = int((await db.execute(select(func.count()).select_from(ProviderCredential).where(ProviderCredential.enabled.is_(True)))).scalar() or 0)
    provider_endpoints = int((await db.execute(select(func.count()).select_from(ProviderEndpoint))).scalar() or 0)
    enabled_provider_endpoints = int((await db.execute(select(func.count()).select_from(ProviderEndpoint).where(ProviderEndpoint.enabled.is_(True)))).scalar() or 0)
    model_routes = int((await db.execute(select(func.count()).select_from(ModelRoute))).scalar() or 0)
    upstream_models = int((await db.execute(select(func.count()).select_from(UpstreamModel))).scalar() or 0)
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
        "public_models": total_models,
        "upstream_models": upstream_models,
        "provider_endpoints": provider_endpoints,
        "enabled_provider_endpoints": enabled_provider_endpoints,
        "provider_credentials": provider_credentials,
        "enabled_provider_credentials": enabled_provider_credentials,
        "model_routes": model_routes,
        "usage_sessions": usage_sessions,
        "completed_usage_sessions": completed_usage_sessions,
        "total_usage_credits": float(total_usage_credits),
        "total_remaining_credits": float(total_remaining_credits),
    }


async def list_usage_sessions(db: AsyncSession) -> list[UsageSession]:
    result = await db.execute(select(UsageSession))
    return list(result.scalars().all())


async def list_user_chat_sessions(db: AsyncSession, user_id: str, limit: int = 50) -> list[dict]:
    result = await db.execute(
        select(UsageSession)
        .where(UsageSession.user_id == user_id)
        .order_by(UsageSession.created_at.desc())
        .limit(limit)
    )
    sessions = list(result.scalars().all())
    return [
        {
            "id": item.id,
            "request_id": item.request_id,
            "user_id": item.user_id,
            "model_name": item.model_name,
            "upstream_provider": item.upstream_provider,
            "status": item.status,
            "request_messages": item.request_messages or [],
            "request_text": item.request_text,
            "response_text": item.response_text,
            "prompt_tokens": item.prompt_tokens,
            "completion_tokens": item.completion_tokens,
            "total_tokens": item.total_tokens,
            "final_cost_credits": float(item.final_cost_credits or 0),
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        }
        for item in sessions
    ]


async def list_api_supported_models(db: AsyncSession) -> list[dict]:
    routes_rows = await db.execute(
        select(ModelRoute, PublicModel, UpstreamModel, Provider, ProviderEndpoint, ProviderCredential)
        .join(PublicModel, PublicModel.id == ModelRoute.public_model_id)
        .join(UpstreamModel, UpstreamModel.id == ModelRoute.upstream_model_id)
        .join(Provider, Provider.id == UpstreamModel.provider_id)
        .outerjoin(ProviderCredential, ProviderCredential.id == ModelRoute.provider_credential_id)
        .outerjoin(ProviderEndpoint, ProviderEndpoint.id == ProviderCredential.provider_endpoint_id)
        .order_by(Provider.slug.asc(), ProviderEndpoint.slug.asc(), ProviderCredential.display_name.asc(), ModelRoute.priority.asc(), ModelRoute.weight.desc())
    )
    route_rows = routes_rows.all()
    if not route_rows:
        return []

    grouped: dict[str, dict] = {}
    for route, public_model, upstream_model, provider, endpoint, credential in route_rows:
        credential_key = credential.id if credential else f"route:{route.id}"
        base_url = route.base_url_override or (endpoint.base_url if endpoint else None)
        item = grouped.setdefault(
            credential_key,
            {
                "api_id": credential.id if credential else None,
                "provider": provider.slug,
                "provider_name": provider.name,
                "endpoint_id": endpoint.id if endpoint else None,
                "endpoint_slug": endpoint.slug if endpoint else None,
                "endpoint_name": endpoint.display_name if endpoint else None,
                "enabled": bool((credential.enabled if credential else True) and (endpoint.enabled if endpoint else True) and provider.enabled),
                "health_state": credential.health_state if credential else (endpoint.health_state if endpoint else "healthy"),
                "base_url": base_url,
                "credential_name": credential.display_name if credential else None,
                "supported_models": [],
            },
        )
        item["supported_models"].append(
            {
                "model_id": public_model.id,
                "model_name": public_model.slug,
                "display_name": public_model.display_name,
                "upstream_model_id": upstream_model.id,
                "upstream_model": upstream_model.upstream_name,
                "enabled": bool(route.enabled and public_model.enabled and upstream_model.enabled),
                "priority": route.priority,
                "weight": route.weight,
                "base_url": base_url,
            }
        )

    return list(grouped.values())


def _smallest_to_credit(amount_smallest: int | float | str | None) -> Decimal:
    scale = max(int(settings.basalt_credit_scale or 1), 1)
    return Decimal(str(amount_smallest or 0)) / Decimal(scale)


async def sync_wallets_from_basalt(
    db: AsyncSession,
    user_id: str | None = None,
    dry_run: bool = False,
) -> dict:
    query = select(User).where(User.basalt_user_id.is_not(None))
    if user_id:
        query = query.where(User.id == user_id)
    rows = await db.execute(query.order_by(User.created_at.desc()))
    users = list(rows.scalars().all())

    client = BasaltPassClient()
    synced = 0
    failed = 0
    skipped = 0
    errors: list[dict] = []

    active_tasks = []
    semaphore = asyncio.Semaphore(10)

    async def fetch_wallet(user: User):
        async with semaphore:
            basalt_user_id = (user.basalt_user_id or "").strip()
            tenant_id = (user.basalt_tenant_id or "").strip() or None
            try:
                payload = await client.s2s_get_user_wallet(
                    user_id=basalt_user_id,
                    currency=settings.basalt_credit_currency,
                    limit=1,
                    tenant_id=tenant_id,
                )
                return user, payload
            except Exception as e:
                return user, {"error": str(e)}

    for user in users:
        if not (user.basalt_user_id or "").strip():
            skipped += 1
            continue
        active_tasks.append(fetch_wallet(user))

    if not active_tasks:
        return {
            "total": len(users),
            "synced": synced,
            "failed": failed,
            "skipped": skipped,
            "dry_run": dry_run,
            "errors": errors,
        }

    results = await asyncio.gather(*active_tasks)

    user_ids = [res[0].id for res in results if isinstance(res[1], dict) and not res[1].get("error")]
    wallets_map = {}
    if user_ids and not dry_run:
        wallets_res = await db.execute(select(Wallet).where(Wallet.user_id.in_(user_ids)))
        wallets_map = {w.user_id: w for w in wallets_res.scalars().all()}

    for user, payload in results:
        if isinstance(payload, dict) and payload.get("error"):
            failed += 1
            errors.append(
                {
                    "user_id": user.id,
                    "email": user.email,
                    "error": payload.get("error"),
                }
            )
            continue

        if not isinstance(payload, dict):
            failed += 1
            errors.append(
                {
                    "user_id": user.id,
                    "email": user.email,
                    "error": "invalid_response",
                }
            )
            continue

        remote_balance = _smallest_to_credit(payload.get("balance"))
        if dry_run:
            synced += 1
            continue

        wallet = wallets_map.get(user.id)
        if not wallet:
            wallet = Wallet(user_id=user.id, balance_credits=remote_balance)
            db.add(wallet)
        else:
            wallet.balance_credits = remote_balance
        synced += 1

    if not dry_run:
        await db.commit()

    return {
        "total": len(users),
        "synced": synced,
        "failed": failed,
        "skipped": skipped,
        "dry_run": dry_run,
        "errors": errors,
    }
