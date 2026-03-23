from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.model import Model
from app.db.models.provider_key import ProviderKey
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.user import User
from app.db.models.usage_session import UsageSession


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
    result = await db.execute(select(User))
    return list(result.scalars().all())


async def list_usage_sessions(db: AsyncSession) -> list[UsageSession]:
    result = await db.execute(select(UsageSession))
    return list(result.scalars().all())

