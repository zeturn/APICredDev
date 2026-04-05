import random
from collections import defaultdict

from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timezone

from app.core.time import utc_now
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.provider_key import ProviderKey
class RoutingResult:
    def __init__(self, provider_key: ProviderKey, mpk: ModelProviderKey):
        self.provider_key = provider_key
        self.mpk = mpk


def _weighted_shuffle(group: list[RoutingResult]) -> list[RoutingResult]:
    positives = [item for item in group if (item.mpk.weight or 0) > 0]
    zeros = [item for item in group if (item.mpk.weight or 0) <= 0]
    ordered: list[RoutingResult] = []

    remaining = positives[:]
    while remaining:
        total_weight = sum(item.mpk.weight for item in remaining if item.mpk.weight > 0)
        if total_weight <= 0:
            break
        pick = random.uniform(0, total_weight)
        cursor = 0.0
        selected_index = 0
        for index, item in enumerate(remaining):
            cursor += float(item.mpk.weight)
            if pick <= cursor:
                selected_index = index
                break
        ordered.append(remaining.pop(selected_index))

    ordered.extend(zeros)
    return ordered


async def get_candidates(db: AsyncSession, model_id: str) -> list[RoutingResult]:
    result = await db.execute(
        select(ModelProviderKey, ProviderKey)
        .join(ProviderKey, ProviderKey.id == ModelProviderKey.provider_key_id)
        .where(ModelProviderKey.model_id == model_id)
        .where(ModelProviderKey.enabled.is_(True))
        .where(ProviderKey.enabled.is_(True))
        .order_by(asc(ModelProviderKey.priority), asc(ModelProviderKey.id))
    )
    rows = result.all()
    now = utc_now()
    grouped: dict[int, list[RoutingResult]] = defaultdict(list)
    for mpk, pkey in rows:
        if pkey.health_state == "disabled":
            continue
        if pkey.cooldown_until:
            cooldown = pkey.cooldown_until
            if cooldown.tzinfo is None:
                cooldown = cooldown.replace(tzinfo=timezone.utc)
            if cooldown > now:
                continue
        grouped[mpk.priority].append(RoutingResult(pkey, mpk))

    candidates: list[RoutingResult] = []
    for priority in sorted(grouped):
        candidates.extend(_weighted_shuffle(grouped[priority]))
    return candidates

