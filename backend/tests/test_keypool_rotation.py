import pytest
from redis.asyncio import Redis
import random

from app.core.config import settings
from app.db.models.model import Model
from app.db.models.provider_key import ProviderKey
from app.db.models.model_provider_key import ModelProviderKey
from app.services.routing_service import get_candidates
from app.services.quota_service import try_reserve
from app.core.time import utc_now
from datetime import timedelta


@pytest.mark.asyncio
async def test_keypool_rotation(db_session):
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.ping()
    except Exception:
        await redis.aclose()
        pytest.skip("redis not available")

    model = Model(name="gpt5", category="llm", enabled=True, multiplier=1, pricing={"unit": "request", "price": 1})
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    keys = {}
    for name in ["b", "a", "d", "c"]:
        pkey = ProviderKey(provider="openai_compat", key_name="https://example.com", secret_ref="K", enabled=True)
        db_session.add(pkey)
        await db_session.commit()
        await db_session.refresh(pkey)
        keys[name] = pkey

    priorities = {"b": 1, "a": 2, "d": 3, "c": 4}
    for name, pkey in keys.items():
        mpk = ModelProviderKey(
            model_id=model.id,
            provider_key_id=pkey.id,
            enabled=True,
            priority=priorities[name],
            quota_unit="requests",
            quota_rules={"day": 5},
        )
        db_session.add(mpk)
    await db_session.commit()

    selected = []
    for _ in range(6):
        candidates = await get_candidates(db_session, model.id)
        picked = None
        for candidate in candidates:
            ok = await try_reserve(redis, candidate.provider_key.id, model.id, 1, candidate.mpk.quota_rules or {})
            if ok:
                picked = candidate.provider_key.id
                break
        selected.append(picked)

    first_key_id = keys["b"].id
    assert selected[:5].count(first_key_id) == 5
    assert selected[5] == keys["a"].id

    await redis.aclose()


@pytest.mark.asyncio
async def test_multi_window_switch(db_session):
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.ping()
    except Exception:
        await redis.aclose()
        pytest.skip("redis not available")

    model = Model(name="gpt5-mini", category="llm", enabled=True, multiplier=1, pricing={"unit": "request", "price": 1})
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    pkey = ProviderKey(provider="openai_compat", key_name="https://example.com", secret_ref="K", enabled=True)
    pkey2 = ProviderKey(provider="openai_compat", key_name="https://example.com", secret_ref="K2", enabled=True)
    db_session.add_all([pkey, pkey2])
    await db_session.commit()
    await db_session.refresh(pkey)
    await db_session.refresh(pkey2)

    mpk1 = ModelProviderKey(
        model_id=model.id,
        provider_key_id=pkey.id,
        enabled=True,
        priority=1,
        quota_unit="requests",
        quota_rules={"minute": 2, "day": 100},
    )
    mpk2 = ModelProviderKey(
        model_id=model.id,
        provider_key_id=pkey2.id,
        enabled=True,
        priority=2,
        quota_unit="requests",
        quota_rules={"minute": 100, "day": 100},
    )
    db_session.add_all([mpk1, mpk2])
    await db_session.commit()

    selected = []
    for _ in range(3):
        candidates = await get_candidates(db_session, model.id)
        picked = None
        for candidate in candidates:
            ok = await try_reserve(redis, candidate.provider_key.id, model.id, 1, candidate.mpk.quota_rules or {})
            if ok:
                picked = candidate.provider_key.id
                break
        selected.append(picked)
    assert selected[0] == pkey.id
    assert selected[1] == pkey.id
    assert selected[2] == pkey2.id

    await redis.aclose()


@pytest.mark.asyncio
async def test_cooldown_skips_key(db_session):
    model = Model(name="gpt5-cool", category="llm", enabled=True, multiplier=1, pricing={"unit": "request", "price": 1})
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    pkey = ProviderKey(provider="openai_compat", key_name="https://example.com", secret_ref="K", enabled=True)
    pkey.cooldown_until = utc_now() + timedelta(seconds=120)
    db_session.add(pkey)
    await db_session.commit()
    await db_session.refresh(pkey)

    mpk = ModelProviderKey(
        model_id=model.id,
        provider_key_id=pkey.id,
        enabled=True,
        priority=1,
        quota_unit="requests",
        quota_rules={"day": 5},
    )
    db_session.add(mpk)
    await db_session.commit()

    candidates = await get_candidates(db_session, model.id)
    assert len(candidates) == 0


@pytest.mark.asyncio
async def test_weighted_selection_prefers_higher_weight_same_priority(db_session):
    random.seed(7)

    model = Model(name="gpt5-weighted", category="llm", enabled=True, multiplier=1, pricing={"unit": "request", "price": 1})
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    low_key = ProviderKey(provider="openai", key_name="https://example.com", secret_ref="LOW", enabled=True, health_state="healthy")
    high_key = ProviderKey(provider="openai", key_name="https://example.com", secret_ref="HIGH", enabled=True, health_state="healthy")
    db_session.add_all([low_key, high_key])
    await db_session.commit()
    await db_session.refresh(low_key)
    await db_session.refresh(high_key)

    db_session.add_all(
        [
            ModelProviderKey(model_id=model.id, provider_key_id=low_key.id, enabled=True, priority=1, weight=1, quota_unit="requests", quota_rules={}),
            ModelProviderKey(model_id=model.id, provider_key_id=high_key.id, enabled=True, priority=1, weight=9, quota_unit="requests", quota_rules={}),
        ]
    )
    await db_session.commit()

    first_picks = {low_key.id: 0, high_key.id: 0}
    for _ in range(200):
        candidates = await get_candidates(db_session, model.id)
        first_picks[candidates[0].provider_key.id] += 1

    assert first_picks[high_key.id] > first_picks[low_key.id]


@pytest.mark.asyncio
async def test_weighted_selection_keeps_priority_tiers(db_session):
    random.seed(9)

    model = Model(name="gpt5-priority-weight", category="llm", enabled=True, multiplier=1, pricing={"unit": "request", "price": 1})
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    p1_a = ProviderKey(provider="openai", key_name="https://example.com", secret_ref="P1A", enabled=True, health_state="healthy")
    p1_b = ProviderKey(provider="openai", key_name="https://example.com", secret_ref="P1B", enabled=True, health_state="healthy")
    p2 = ProviderKey(provider="openai", key_name="https://example.com", secret_ref="P2", enabled=True, health_state="healthy")
    db_session.add_all([p1_a, p1_b, p2])
    await db_session.commit()
    await db_session.refresh(p1_a)
    await db_session.refresh(p1_b)
    await db_session.refresh(p2)

    db_session.add_all(
        [
            ModelProviderKey(model_id=model.id, provider_key_id=p1_a.id, enabled=True, priority=1, weight=1, quota_unit="requests", quota_rules={}),
            ModelProviderKey(model_id=model.id, provider_key_id=p1_b.id, enabled=True, priority=1, weight=5, quota_unit="requests", quota_rules={}),
            ModelProviderKey(model_id=model.id, provider_key_id=p2.id, enabled=True, priority=2, weight=100, quota_unit="requests", quota_rules={}),
        ]
    )
    await db_session.commit()

    candidates = await get_candidates(db_session, model.id)
    assert {candidates[0].provider_key.id, candidates[1].provider_key.id} == {p1_a.id, p1_b.id}
    assert candidates[2].provider_key.id == p2.id

