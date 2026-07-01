from datetime import timedelta
import random

import pytest
from redis.asyncio import Redis

from app.core.config import settings
from app.core.secrets import encrypt_secret
from app.core.time import utc_now
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.services.quota_service import try_reserve
from app.services.routing_service import get_route_candidates


async def _route_fixture(db_session, slug: str, credentials: list[tuple[str, int, int, dict | None]]):
    provider = Provider(slug=f"provider-{slug}", name=f"Provider {slug}", default_base_url="https://example.com", enabled=True)
    public_model = PublicModel(slug=slug, display_name=slug, category="llm", enabled=True, multiplier=1, pricing={"unit": "request", "price": 1})
    db_session.add_all([provider, public_model])
    await db_session.commit()
    await db_session.refresh(provider)
    await db_session.refresh(public_model)

    upstream_model = UpstreamModel(
        provider_id=provider.id,
        upstream_name=f"{slug}-upstream",
        display_name=f"{slug} upstream",
        capabilities={},
        default_pricing={},
        enabled=True,
    )
    db_session.add(upstream_model)
    await db_session.commit()
    await db_session.refresh(upstream_model)

    created_credentials = {}
    for name, priority, weight, quota_rules in credentials:
        credential = ProviderCredential(
            provider_id=provider.id,
            display_name=name,
            secret_encrypted=encrypt_secret(name),
            secret_last4=name[-4:],
            enabled=True,
            health_state="healthy",
        )
        db_session.add(credential)
        await db_session.commit()
        await db_session.refresh(credential)
        db_session.add(
            ModelRoute(
                public_model_id=public_model.id,
                upstream_model_id=upstream_model.id,
                provider_credential_id=credential.id,
                enabled=True,
                priority=priority,
                weight=weight,
                quota_unit="requests",
                quota_rules=quota_rules or {},
            )
        )
        created_credentials[name] = credential
    await db_session.commit()
    return public_model, created_credentials


@pytest.mark.asyncio
async def test_keypool_rotation(db_session):
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.ping()
    except Exception:
        await redis.aclose()
        pytest.skip("redis not available")

    public_model, credentials = await _route_fixture(
        db_session,
        "gpt5",
        [("b", 1, 1, {"day": 5}), ("a", 2, 1, {"day": 5}), ("d", 3, 1, {"day": 5}), ("c", 4, 1, {"day": 5})],
    )

    selected = []
    for _ in range(6):
        picked = None
        for candidate in await get_route_candidates(db_session, public_model.id):
            ok = await try_reserve(redis, candidate.credential.id, public_model.id, 1, candidate.route.quota_rules or {})
            if ok:
                picked = candidate.credential.id
                break
        selected.append(picked)

    first_credential_id = credentials["b"].id
    assert selected[:5].count(first_credential_id) == 5
    assert selected[5] == credentials["a"].id

    await redis.aclose()


@pytest.mark.asyncio
async def test_multi_window_switch(db_session):
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.ping()
    except Exception:
        await redis.aclose()
        pytest.skip("redis not available")

    public_model, credentials = await _route_fixture(
        db_session,
        "gpt5-mini",
        [("first", 1, 1, {"minute": 2, "day": 100}), ("second", 2, 1, {"minute": 100, "day": 100})],
    )

    selected = []
    for _ in range(3):
        picked = None
        for candidate in await get_route_candidates(db_session, public_model.id):
            ok = await try_reserve(redis, candidate.credential.id, public_model.id, 1, candidate.route.quota_rules or {})
            if ok:
                picked = candidate.credential.id
                break
        selected.append(picked)
    assert selected == [credentials["first"].id, credentials["first"].id, credentials["second"].id]

    await redis.aclose()


@pytest.mark.asyncio
async def test_cooldown_skips_credential(db_session):
    public_model, credentials = await _route_fixture(db_session, "gpt5-cool", [("cool", 1, 1, {"day": 5})])
    credentials["cool"].cooldown_until = utc_now() + timedelta(seconds=120)
    await db_session.commit()

    assert await get_route_candidates(db_session, public_model.id) == []


@pytest.mark.asyncio
async def test_weighted_selection_prefers_higher_weight_same_priority(db_session):
    random.seed(7)
    public_model, credentials = await _route_fixture(db_session, "gpt5-weighted", [("low", 1, 1, None), ("high", 1, 9, None)])

    first_picks = {credentials["low"].id: 0, credentials["high"].id: 0}
    for _ in range(200):
        candidates = await get_route_candidates(db_session, public_model.id)
        first_picks[candidates[0].credential.id] += 1

    assert first_picks[credentials["high"].id] > first_picks[credentials["low"].id]


@pytest.mark.asyncio
async def test_weighted_selection_keeps_priority_tiers(db_session):
    random.seed(9)
    public_model, credentials = await _route_fixture(db_session, "gpt5-priority-weight", [("p1a", 1, 1, None), ("p1b", 1, 5, None), ("p2", 2, 100, None)])

    candidates = await get_route_candidates(db_session, public_model.id)
    assert {candidates[0].credential.id, candidates[1].credential.id} == {credentials["p1a"].id, credentials["p1b"].id}
    assert candidates[2].credential.id == credentials["p2"].id
