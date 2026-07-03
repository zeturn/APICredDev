from decimal import Decimal

import pytest

from app.db.models.access_policy import AccessPolicy
from app.db.models.usage_session import UsageSession
from app.db.models.user import User
from app.services.policy_service import enforce_pre_authorize_policy, enforce_provider_policy


async def _seed_user(db_session):
    db_session.add(User(id="u1", email="u1@example.com", password_hash="x", status="active", basalt_tenant_id="t1"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_global_model_block(db_session):
    await _seed_user(db_session)
    db_session.add(AccessPolicy(scope_type="global", name="g", enabled=True, blocked_public_models_json=["blocked-model"]))
    await db_session.commit()
    ok, err, _ = await enforce_pre_authorize_policy(
        db_session, user_id="u1", token_id="tk1", public_model="blocked-model", estimated_tokens=10, estimated_cost_credits=1
    )
    assert not ok
    assert err == "policy_model_blocked"


@pytest.mark.asyncio
async def test_user_allowlist(db_session):
    await _seed_user(db_session)
    db_session.add(AccessPolicy(scope_type="user", scope_id="u1", name="u", enabled=True, allowed_public_models_json=["allowed-model"]))
    await db_session.commit()
    ok, err, _ = await enforce_pre_authorize_policy(
        db_session, user_id="u1", token_id="tk1", public_model="other-model", estimated_tokens=10, estimated_cost_credits=1
    )
    assert not ok
    assert err == "policy_model_not_allowed"


@pytest.mark.asyncio
async def test_token_provider_block_and_deny_wins(db_session):
    await _seed_user(db_session)
    db_session.add(AccessPolicy(scope_type="global", name="allow", enabled=True, allowed_providers_json=["openai"]))
    db_session.add(AccessPolicy(scope_type="token", scope_id="tk1", name="deny", enabled=True, blocked_providers_json=["openai"]))
    await db_session.commit()
    _, _, resolved = await enforce_pre_authorize_policy(
        db_session, user_id="u1", token_id="tk1", public_model="m", estimated_tokens=10, estimated_cost_credits=1
    )
    provider_ok, provider_err = enforce_provider_policy(resolved, "openai")
    assert not provider_ok
    assert provider_err == "policy_provider_blocked"


@pytest.mark.asyncio
async def test_daily_cost_cap_and_token_cap(db_session):
    await _seed_user(db_session)
    db_session.add(
        AccessPolicy(scope_type="token", scope_id="tk1", name="caps", enabled=True, max_cost_credits_per_day=Decimal("5"), max_tokens_per_day=100)
    )
    db_session.add(
        UsageSession(
            id="s1",
            user_id="u1",
            token_id="tk1",
            request_id="r1",
            model_id="m",
            model_name="m",
            status="completed",
            estimated_cost_credits=1,
            final_cost_credits=4.5,
            total_tokens=95,
        )
    )
    await db_session.commit()
    ok, err, _ = await enforce_pre_authorize_policy(
        db_session, user_id="u1", token_id="tk1", public_model="m", estimated_tokens=10, estimated_cost_credits=1
    )
    assert not ok
    assert err in {"policy_cost_per_day_exceeded", "policy_tokens_per_day_exceeded"}


@pytest.mark.asyncio
async def test_disabled_policy_ignored(db_session):
    await _seed_user(db_session)
    db_session.add(AccessPolicy(scope_type="global", name="disabled", enabled=False, blocked_public_models_json=["m"]))
    await db_session.commit()
    ok, err, _ = await enforce_pre_authorize_policy(
        db_session, user_id="u1", token_id="tk1", public_model="m", estimated_tokens=1, estimated_cost_credits=0.1
    )
    assert ok
    assert err is None
