from typing import Optional

from sqlalchemy import select, asc
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timezone

from app.core.time import utc_now
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.provider_key import ProviderKey
class RoutingResult:
    def __init__(self, provider_key: ProviderKey, mpk: ModelProviderKey):
        self.provider_key = provider_key
        self.mpk = mpk


async def get_candidates(db: AsyncSession, model_id: str) -> list[RoutingResult]:
    result = await db.execute(
        select(ModelProviderKey, ProviderKey)
        .join(ProviderKey, ProviderKey.id == ModelProviderKey.provider_key_id)
        .where(ModelProviderKey.model_id == model_id)
        .where(ModelProviderKey.enabled.is_(True))
        .where(ProviderKey.enabled.is_(True))
        .order_by(asc(ModelProviderKey.priority))
    )
    rows = result.all()
    now = utc_now()
    candidates: list[RoutingResult] = []
    for mpk, pkey in rows:
        if pkey.health_state == "disabled":
            continue
        if pkey.cooldown_until:
            cooldown = pkey.cooldown_until
            if cooldown.tzinfo is None:
                cooldown = cooldown.replace(tzinfo=timezone.utc)
            if cooldown > now:
                continue
        candidates.append(RoutingResult(pkey, mpk))
    return candidates

