import random
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timezone

from app.core.time import utc_now
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.upstream_model import UpstreamModel


@dataclass
class ModelRouteCandidate:
    route: ModelRoute
    upstream_model: UpstreamModel
    provider: Provider
    endpoint: ProviderEndpoint | None
    credential: ProviderCredential | None


def _candidate_weight(item) -> int:
    return int(getattr(item.route, "weight", 0) or 0)


def _weighted_shuffle(group: list) -> list:
    positives = [item for item in group if _candidate_weight(item) > 0]
    zeros = [item for item in group if _candidate_weight(item) <= 0]
    ordered: list[ModelRouteCandidate] = []

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


def _is_available_endpoint(endpoint: ProviderEndpoint | None) -> bool:
    if endpoint is None:
        return True
    if not endpoint.enabled or endpoint.health_state == "disabled":
        return False
    if endpoint.cooldown_until:
        cooldown = endpoint.cooldown_until
        if cooldown.tzinfo is None:
            cooldown = cooldown.replace(tzinfo=timezone.utc)
        if cooldown > utc_now():
            return False
    return True


async def get_route_candidates(db: AsyncSession, public_model_id: str) -> list[ModelRouteCandidate]:
    result = await db.execute(
        select(ModelRoute, UpstreamModel, Provider, ProviderEndpoint, ProviderCredential)
        .join(UpstreamModel, UpstreamModel.id == ModelRoute.upstream_model_id)
        .join(Provider, Provider.id == UpstreamModel.provider_id)
        .outerjoin(ProviderCredential, ProviderCredential.id == ModelRoute.provider_credential_id)
        .outerjoin(ProviderEndpoint, ProviderEndpoint.id == ProviderCredential.provider_endpoint_id)
        .where(ModelRoute.public_model_id == public_model_id)
        .where(ModelRoute.enabled.is_(True))
        .where(UpstreamModel.enabled.is_(True))
        .where(Provider.enabled.is_(True))
        .order_by(asc(ModelRoute.priority), asc(ModelRoute.id))
    )
    rows = result.all()
    grouped: dict[int, list[ModelRouteCandidate]] = defaultdict(list)
    for route, upstream_model, provider, endpoint, credential in rows:
        if not _is_available_endpoint(endpoint) or not _is_available_credential(credential):
            continue
        grouped[route.priority].append(ModelRouteCandidate(route, upstream_model, provider, endpoint, credential))

    candidates: list[ModelRouteCandidate] = []
    for priority in sorted(grouped):
        candidates.extend(_weighted_shuffle(grouped[priority]))
    return candidates

