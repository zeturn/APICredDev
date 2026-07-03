from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.db.models.access_policy import AccessPolicy
from app.db.models.usage_session import UsageSession
from app.db.models.user import User

SCOPE_PRIORITY = {"global": 0, "tenant": 1, "user": 2, "token": 3}


@dataclass
class PolicyContext:
    user_id: str
    token_id: str
    tenant_id: str | None


@dataclass
class ResolvedPolicy:
    allowed_models: set[str]
    blocked_models: set[str]
    allowed_providers: set[str]
    blocked_providers: set[str]
    max_requests_per_minute: int | None
    max_requests_per_day: int | None
    max_tokens_per_day: int | None
    max_cost_credits_per_day: Decimal | None
    max_cost_credits_per_month: Decimal | None


def _as_decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _merge_limit(current: tuple[int, int | float | Decimal] | None, candidate_scope: str, candidate_value):
    if candidate_value in (None, ""):
        return current
    rank = SCOPE_PRIORITY.get(candidate_scope, -1)
    if current is None or rank > current[0]:
        return (rank, candidate_value)
    return current


def _normalize_set(items) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item).strip().lower() for item in items if str(item).strip()}


async def _load_policy_context(db: AsyncSession, *, user_id: str, token_id: str) -> PolicyContext:
    user = await db.get(User, user_id)
    tenant_id = str(user.basalt_tenant_id).strip() if user and user.basalt_tenant_id else None
    return PolicyContext(user_id=user_id, token_id=token_id, tenant_id=tenant_id)


async def resolve_policy(db: AsyncSession, *, user_id: str, token_id: str) -> ResolvedPolicy:
    ctx = await _load_policy_context(db, user_id=user_id, token_id=token_id)
    query = select(AccessPolicy).where(AccessPolicy.enabled.is_(True))
    policies = list((await db.execute(query)).scalars().all())

    applicable: list[AccessPolicy] = []
    for policy in policies:
        scope = (policy.scope_type or "").strip().lower()
        scope_id = str(policy.scope_id or "").strip()
        if scope == "global":
            applicable.append(policy)
        elif scope == "tenant" and ctx.tenant_id and scope_id == ctx.tenant_id:
            applicable.append(policy)
        elif scope == "user" and scope_id == ctx.user_id:
            applicable.append(policy)
        elif scope == "token" and scope_id == ctx.token_id:
            applicable.append(policy)

    allowed_models = set()
    blocked_models = set()
    allowed_providers = set()
    blocked_providers = set()

    max_requests_per_minute = None
    max_requests_per_day = None
    max_tokens_per_day = None
    max_cost_credits_per_day = None
    max_cost_credits_per_month = None

    for policy in applicable:
        scope = (policy.scope_type or "").strip().lower()
        allowed_models |= _normalize_set(policy.allowed_public_models_json)
        blocked_models |= _normalize_set(policy.blocked_public_models_json)
        allowed_providers |= _normalize_set(policy.allowed_providers_json)
        blocked_providers |= _normalize_set(policy.blocked_providers_json)
        max_requests_per_minute = _merge_limit(max_requests_per_minute, scope, policy.max_requests_per_minute)
        max_requests_per_day = _merge_limit(max_requests_per_day, scope, policy.max_requests_per_day)
        max_tokens_per_day = _merge_limit(max_tokens_per_day, scope, policy.max_tokens_per_day)
        max_cost_credits_per_day = _merge_limit(max_cost_credits_per_day, scope, policy.max_cost_credits_per_day)
        max_cost_credits_per_month = _merge_limit(max_cost_credits_per_month, scope, policy.max_cost_credits_per_month)

    return ResolvedPolicy(
        allowed_models=allowed_models,
        blocked_models=blocked_models,
        allowed_providers=allowed_providers,
        blocked_providers=blocked_providers,
        max_requests_per_minute=max_requests_per_minute[1] if max_requests_per_minute else None,
        max_requests_per_day=max_requests_per_day[1] if max_requests_per_day else None,
        max_tokens_per_day=max_tokens_per_day[1] if max_tokens_per_day else None,
        max_cost_credits_per_day=_as_decimal(max_cost_credits_per_day[1]) if max_cost_credits_per_day else None,
        max_cost_credits_per_month=_as_decimal(max_cost_credits_per_month[1]) if max_cost_credits_per_month else None,
    )


async def _usage_agg(db: AsyncSession, *, user_id: str, token_id: str, since) -> dict:
    result = await db.execute(
        select(
            func.count(UsageSession.id),
            func.coalesce(func.sum(UsageSession.total_tokens), 0),
            func.coalesce(func.sum(UsageSession.final_cost_credits), 0),
        ).where(
            and_(
                UsageSession.user_id == user_id,
                UsageSession.token_id == token_id,
                UsageSession.created_at >= since,
            )
        )
    )
    requests, tokens, cost = result.one()
    return {"requests": int(requests or 0), "tokens": int(tokens or 0), "cost": _as_decimal(cost)}


async def enforce_pre_authorize_policy(
    db: AsyncSession,
    *,
    user_id: str,
    token_id: str,
    public_model: str,
    estimated_tokens: int,
    estimated_cost_credits: float,
) -> tuple[bool, str | None, ResolvedPolicy]:
    policy = await resolve_policy(db, user_id=user_id, token_id=token_id)
    model_slug = (public_model or "").strip().lower()

    if model_slug in policy.blocked_models:
        return False, "policy_model_blocked", policy
    if policy.allowed_models and model_slug not in policy.allowed_models:
        return False, "policy_model_not_allowed", policy

    now = utc_now()
    if policy.max_requests_per_minute is not None:
        usage_min = await _usage_agg(db, user_id=user_id, token_id=token_id, since=now - timedelta(minutes=1))
        if usage_min["requests"] + 1 > int(policy.max_requests_per_minute):
            return False, "policy_requests_per_minute_exceeded", policy
    if policy.max_requests_per_day is not None:
        usage_day = await _usage_agg(db, user_id=user_id, token_id=token_id, since=now - timedelta(days=1))
        if usage_day["requests"] + 1 > int(policy.max_requests_per_day):
            return False, "policy_requests_per_day_exceeded", policy
    if policy.max_tokens_per_day is not None:
        usage_day = await _usage_agg(db, user_id=user_id, token_id=token_id, since=now - timedelta(days=1))
        if usage_day["tokens"] + int(estimated_tokens or 0) > int(policy.max_tokens_per_day):
            return False, "policy_tokens_per_day_exceeded", policy
    if policy.max_cost_credits_per_day is not None:
        usage_day = await _usage_agg(db, user_id=user_id, token_id=token_id, since=now - timedelta(days=1))
        if usage_day["cost"] + _as_decimal(estimated_cost_credits) > policy.max_cost_credits_per_day:
            return False, "policy_cost_per_day_exceeded", policy
    if policy.max_cost_credits_per_month is not None:
        usage_month = await _usage_agg(db, user_id=user_id, token_id=token_id, since=now - timedelta(days=31))
        if usage_month["cost"] + _as_decimal(estimated_cost_credits) > policy.max_cost_credits_per_month:
            return False, "policy_cost_per_month_exceeded", policy
    return True, None, policy


def enforce_provider_policy(policy: ResolvedPolicy, provider_slug: str) -> tuple[bool, str | None]:
    provider = (provider_slug or "").strip().lower()
    if provider in policy.blocked_providers:
        return False, "policy_provider_blocked"
    if policy.allowed_providers and provider not in policy.allowed_providers:
        return False, "policy_provider_not_allowed"
    return True, None
