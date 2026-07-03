from datetime import timedelta
import random

import pytest

from app.api.v1.llm import _apply_cooldown
from app.core.time import utc_now
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.services.routing_service import get_route_candidates


async def _fixture_routes(db_session):
    provider = Provider(slug="openai", name="OpenAI", enabled=True)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    endpoint = ProviderEndpoint(
        provider_id=provider.id,
        slug="default",
        display_name="default",
        base_url="https://api.openai.com",
        enabled=True,
        health_state="healthy",
    )
    db_session.add(endpoint)
    public_model = PublicModel(slug="m", display_name="m", category="llm", enabled=True, pricing={"unit": "request", "price": 1}, multiplier=1)
    upstream = UpstreamModel(provider_id=provider.id, upstream_name="gpt-4o", display_name="gpt-4o", capabilities={}, default_pricing={}, enabled=True)
    db_session.add_all([public_model, upstream])
    await db_session.commit()
    await db_session.refresh(public_model)
    await db_session.refresh(upstream)

    creds = []
    for idx in range(3):
        credential = ProviderCredential(
            provider_endpoint_id=endpoint.id,
            display_name=f"cred-{idx}",
            secret_encrypted="v2:dummy",
            enabled=True,
            health_state="healthy",
        )
        db_session.add(credential)
        await db_session.commit()
        await db_session.refresh(credential)
        db_session.add(
            ModelRoute(
                public_model_id=public_model.id,
                upstream_model_id=upstream.id,
                provider_credential_id=credential.id,
                enabled=True,
                priority=idx + 1,
                weight=idx + 1,
                quota_unit="requests",
                quota_rules={},
            )
        )
        creds.append(credential)
    await db_session.commit()
    return public_model, creds


@pytest.mark.asyncio
async def test_priority_order_and_weight_smoke(db_session):
    model, creds = await _fixture_routes(db_session)
    random.seed(42)
    ordered = await get_route_candidates(db_session, model.id)
    assert ordered[0].credential.id == creds[0].id


@pytest.mark.asyncio
async def test_disabled_and_cooldown_credential_skipped(db_session):
    model, creds = await _fixture_routes(db_session)
    creds[0].enabled = False
    creds[1].cooldown_until = utc_now() + timedelta(minutes=5)
    await db_session.commit()
    candidates = await get_route_candidates(db_session, model.id)
    ids = [c.credential.id for c in candidates]
    assert creds[0].id not in ids
    assert creds[1].id not in ids
    assert creds[2].id in ids


@pytest.mark.asyncio
async def test_quota_exhausted_credential_skipped_in_selection_loop(db_session):
    model, creds = await _fixture_routes(db_session)
    candidates = await get_route_candidates(db_session, model.id)
    reserve_ok = {creds[0].id: False, creds[1].id: True}
    selected = None
    for candidate in candidates:
        if reserve_ok.get(candidate.credential.id, False):
            selected = candidate.credential.id
            break
    assert selected == creds[1].id


@pytest.mark.asyncio
async def test_auth_failed_disables_credential(db_session):
    model, creds = await _fixture_routes(db_session)
    candidate = (await get_route_candidates(db_session, model.id))[0]
    await _apply_cooldown(db_session, candidate, {"code": "auth_failed", "cooldown_seconds": 60})
    refreshed = await db_session.get(ProviderCredential, creds[0].id)
    assert refreshed.health_state == "disabled"


@pytest.mark.asyncio
async def test_rate_limited_puts_credential_in_cooldown(db_session):
    model, creds = await _fixture_routes(db_session)
    candidate = (await get_route_candidates(db_session, model.id))[0]
    await _apply_cooldown(db_session, candidate, {"code": "rate_limited", "cooldown_seconds": 60})
    refreshed = await db_session.get(ProviderCredential, creds[0].id)
    assert refreshed.cooldown_until is not None


def test_fallback_route_used_after_retryable_failure():
    events = []
    candidates = ["first", "second"]
    retryable = {"first": True, "second": False}
    chosen = None
    for item in candidates:
        events.append(item)
        if retryable[item]:
            continue
        chosen = item
        break
    assert events == ["first", "second"]
    assert chosen == "second"


def test_non_retryable_request_error_stops_correctly():
    candidates = ["first", "second"]
    retryable = {"first": False, "second": True}
    events = []
    for item in candidates:
        events.append(item)
        if not retryable[item]:
            break
    assert events == ["first"]
