from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.url_safety import normalize_upstream_base_url
from app.db.models.provider_endpoint import ProviderEndpoint


async def list_provider_endpoints(db: AsyncSession) -> list[ProviderEndpoint]:
    result = await db.execute(select(ProviderEndpoint).order_by(ProviderEndpoint.display_name.asc()))
    return list(result.scalars().all())


async def get_provider_endpoint(db: AsyncSession, endpoint_id: str) -> ProviderEndpoint | None:
    return await db.get(ProviderEndpoint, endpoint_id)


async def upsert_provider_endpoint(db: AsyncSession, payload: dict) -> ProviderEndpoint:
    payload["base_url"] = normalize_upstream_base_url(payload.get("base_url"))
    item_id = payload.get("id")
    if item_id:
        endpoint = await db.get(ProviderEndpoint, item_id)
    else:
        endpoint = None
    if not endpoint:
        endpoint = ProviderEndpoint(**payload)
        db.add(endpoint)
    else:
        for key, value in payload.items():
            setattr(endpoint, key, value)
    await db.commit()
    await db.refresh(endpoint)
    return endpoint
