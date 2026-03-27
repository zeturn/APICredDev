from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.model import Model
from app.db.models.provider_key import ProviderKey
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.user import User
from app.db.models.usage_session import UsageSession
from app.db.models.wallet import Wallet


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


async def upsert_provider_key(db: AsyncSession, payload: dict) -> ProviderKey:
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


async def list_model_provider_keys(db: AsyncSession) -> list[ModelProviderKey]:
    result = await db.execute(select(ModelProviderKey))
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

