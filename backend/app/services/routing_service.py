import random
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timezone

from app.core.time import utc_now
from app.db.models.model_route import ModelRoute
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_key import ProviderKey
from app.db.models.upstream_model import UpstreamModel


class RoutingResult:
    def __init__(self, provider_key: ProviderKey, mpk: ModelProviderKey):
        self.provider_key = provider_key
        self.mpk = mpk


@dataclass
class ModelRouteCandidate:
    route: ModelRoute
    upstream_model: UpstreamModel
    provider: Provider
    credential: ProviderCredential | None


def _candidate_weight(item) -> int:
    route_or_link = getattr(item, "route", None) or getattr(item, "mpk", None)
    return int(getattr(route_or_link, "weight", 0) or 0)


def _weighted_shuffle(group: list) -> list:
    positives = [item for item in group if _candidate_weight(item) > 0]
    zeros = [item for item in group if _candidate_weight(item) <= 0]
    ordered: list[RoutingResult] = []

    remaining = positives[:]
    while remaining:
        total_weight = sum(_candidate_weight(item) for item in remaining if _candidate_weight(item) > 0)
        if total_weight <= 0:
            break
        pick = random.uniform(0, total_weight)
        cursor = 0.0
        selected_index = 0
        for index, item in enumerate(remaining):
            cursor += float(_candidate_weight(item))
            if pick <= cursor:
                selected_index = index
                break
        ordered.append(remaining.pop(selected_index))

    ordered.extend(zeros)
    return ordered


def _is_available_credential(credential: ProviderCredential | None) -> bool:
    if credential is None:
        return True
    if not credential.enabled or credential.health_state == "disabled":
        return False
    if credential.cooldown_until:
        cooldown = credential.cooldown_until
        if cooldown.tzinfo is None:
            cooldown = cooldown.replace(tzinfo=timezone.utc)
        if cooldown > utc_now():
            return False
    return True


async def get_route_candidates(db: AsyncSession, public_model_id: str) -> list[ModelRouteCandidate]:
    result = await db.execute(
        select(ModelRoute, UpstreamModel, Provider, ProviderCredential)
        .join(UpstreamModel, UpstreamModel.id == ModelRoute.upstream_model_id)
        .join(Provider, Provider.id == UpstreamModel.provider_id)
        .outerjoin(ProviderCredential, ProviderCredential.id == ModelRoute.provider_credential_id)
        .where(ModelRoute.public_model_id == public_model_id)
        .where(ModelRoute.enabled.is_(True))
        .where(UpstreamModel.enabled.is_(True))
        .where(Provider.enabled.is_(True))
        .order_by(asc(ModelRoute.priority), asc(ModelRoute.id))
    )
    rows = result.all()
    grouped: dict[int, list[ModelRouteCandidate]] = defaultdict(list)
    for route, upstream_model, provider, credential in rows:
        if not _is_available_credential(credential):
            continue
        grouped[route.priority].append(ModelRouteCandidate(route, upstream_model, provider, credential))

    candidates: list[ModelRouteCandidate] = []
    for priority in sorted(grouped):
        candidates.extend(_weighted_shuffle(grouped[priority]))
    return candidates


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

