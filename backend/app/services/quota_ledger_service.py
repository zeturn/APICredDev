from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.db.models.quota_ledger_entry import QuotaLedgerEntry
from app.db.models.usage_session import UsageSession

SETTLED_STATUSES = {"settled", "rejected", "released", "failed"}


def _as_decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


async def reserve_quota_ledger_for_usage(
    db: AsyncSession,
    *,
    usage_session_id: str,
    request_id: str,
    user_id: str,
    token_id: str,
    public_model_id: str,
    public_model_name: str | None,
    estimated_cost_credits: float,
    metadata_json: dict[str, Any] | None = None,
) -> QuotaLedgerEntry:
    existing = (
        await db.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == request_id))
    ).scalar_one_or_none()
    if existing:
        return existing
    entry = QuotaLedgerEntry(
        usage_session_id=usage_session_id,
        request_id=request_id,
        user_id=user_id,
        token_id=token_id,
        public_model_id=public_model_id,
        public_model_name=public_model_name,
        estimated_cost_credits=_as_decimal(estimated_cost_credits),
        status="reserved",
        metadata_json=metadata_json or {},
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def mark_quota_reservation(
    db: AsyncSession,
    *,
    request_id: str,
    provider: str,
    upstream_model: str,
    provider_credential_id: str,
    quota_unit: str,
    reserved_delta: int,
) -> None:
    entry = (await db.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == request_id))).scalar_one_or_none()
    if not entry:
        return
    if entry.status in SETTLED_STATUSES:
        return
    entry.provider = provider
    entry.upstream_model = upstream_model
    entry.provider_credential_id = provider_credential_id
    entry.quota_unit = quota_unit
    entry.reserved_delta = int(reserved_delta or 0)
    await db.commit()


async def settle_quota_ledger(
    db: AsyncSession,
    *,
    request_id: str,
    status: str,
    final_cost_credits: float | None = None,
    reason: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    metadata_patch: dict[str, Any] | None = None,
) -> None:
    entry = (await db.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == request_id))).scalar_one_or_none()
    if not entry:
        return
    if entry.status in SETTLED_STATUSES:
        return
    entry.status = status
    entry.reason = reason
    entry.settled_at = utc_now()
    if final_cost_credits is not None:
        entry.final_cost_credits = _as_decimal(final_cost_credits)
    entry.prompt_tokens = int(prompt_tokens or 0)
    entry.completion_tokens = int(completion_tokens or 0)
    entry.total_tokens = int(total_tokens or 0)
    if metadata_patch:
        merged = dict(entry.metadata_json or {})
        merged.update(metadata_patch)
        entry.metadata_json = merged
    await db.commit()


def _date_filter(column, date_from: str | None, date_to: str | None):
    conditions = []
    if date_from:
        conditions.append(column >= date_from)
    if date_to:
        conditions.append(column <= date_to)
    return conditions


async def list_quota_usage(
    db: AsyncSession,
    *,
    user_id: str | None = None,
    token_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    query = select(UsageSession).order_by(UsageSession.created_at.desc()).limit(min(max(limit, 1), 1000))
    conditions = []
    if user_id:
        conditions.append(UsageSession.user_id == user_id)
    if token_id:
        conditions.append(UsageSession.token_id == token_id)
    if provider:
        conditions.append(UsageSession.upstream_provider == provider)
    if model:
        conditions.append(UsageSession.model_name == model)
    if status:
        conditions.append(UsageSession.status == status)
    conditions.extend(_date_filter(UsageSession.created_at, date_from, date_to))
    if conditions:
        query = query.where(and_(*conditions))
    rows = list((await db.execute(query)).scalars().all())
    return [
        {
            "id": row.id,
            "request_id": row.request_id,
            "user_id": row.user_id,
            "token_id": row.token_id,
            "model_id": row.model_id,
            "model_name": row.model_name,
            "provider": row.upstream_provider,
            "provider_credential_id": row.upstream_credential_id,
            "status": row.status,
            "estimated_cost_credits": float(row.estimated_cost_credits or 0),
            "final_cost_credits": float(row.final_cost_credits or 0),
            "prompt_tokens": int(row.prompt_tokens or 0),
            "completion_tokens": int(row.completion_tokens or 0),
            "total_tokens": int(row.total_tokens or 0),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
        for row in rows
    ]


async def list_quota_ledger(
    db: AsyncSession,
    *,
    user_id: str | None = None,
    token_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    query = select(QuotaLedgerEntry).order_by(QuotaLedgerEntry.created_at.desc()).limit(min(max(limit, 1), 1000))
    conditions = []
    if user_id:
        conditions.append(QuotaLedgerEntry.user_id == user_id)
    if token_id:
        conditions.append(QuotaLedgerEntry.token_id == token_id)
    if provider:
        conditions.append(QuotaLedgerEntry.provider == provider)
    if model:
        conditions.append(QuotaLedgerEntry.public_model_name == model)
    if status:
        conditions.append(QuotaLedgerEntry.status == status)
    conditions.extend(_date_filter(QuotaLedgerEntry.created_at, date_from, date_to))
    if conditions:
        query = query.where(and_(*conditions))
    rows = list((await db.execute(query)).scalars().all())
    return [
        {
            "id": row.id,
            "usage_session_id": row.usage_session_id,
            "request_id": row.request_id,
            "user_id": row.user_id,
            "token_id": row.token_id,
            "public_model_id": row.public_model_id,
            "public_model_name": row.public_model_name,
            "provider": row.provider,
            "upstream_model": row.upstream_model,
            "provider_credential_id": row.provider_credential_id,
            "quota_unit": row.quota_unit,
            "reserved_delta": int(row.reserved_delta or 0),
            "prompt_tokens": int(row.prompt_tokens or 0),
            "completion_tokens": int(row.completion_tokens or 0),
            "total_tokens": int(row.total_tokens or 0),
            "estimated_cost_credits": float(row.estimated_cost_credits or 0),
            "final_cost_credits": float(row.final_cost_credits or 0),
            "status": row.status,
            "reason": row.reason,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "settled_at": row.settled_at.isoformat() if row.settled_at else None,
            "metadata_json": row.metadata_json or {},
        }
        for row in rows
    ]


async def reconcile_quota_ledger(db: AsyncSession, *, dry_run: bool = True) -> dict[str, Any]:
    now = utc_now()
    stale_before = now - timedelta(minutes=30)
    issues: list[dict[str, Any]] = []

    stale_started = list(
        (
            await db.execute(
                select(UsageSession).where(UsageSession.status == "started", UsageSession.created_at < stale_before)
            )
        ).scalars().all()
    )
    for row in stale_started:
        issues.append({"type": "started_usage_session_too_old", "usage_session_id": row.id, "request_id": row.request_id})

    reserved_not_settled = list(
        (
            await db.execute(
                select(QuotaLedgerEntry).where(
                    QuotaLedgerEntry.status == "reserved",
                    QuotaLedgerEntry.created_at < stale_before,
                )
            )
        ).scalars().all()
    )
    for row in reserved_not_settled:
        issues.append({"type": "reserved_not_settled", "quota_ledger_id": row.id, "request_id": row.request_id})
        if not dry_run:
            row.status = "released"
            row.reason = "reconcile_stale_reserved"
            row.settled_at = now

    completed_rows = list(
        (await db.execute(select(UsageSession).where(UsageSession.status == "completed"))).scalars().all()
    )
    for usage in completed_rows:
        ledger = (
            await db.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == usage.request_id))
        ).scalar_one_or_none()
        if not ledger:
            issues.append({"type": "usage_completed_but_ledger_missing", "usage_session_id": usage.id, "request_id": usage.request_id})
            continue
        if ledger.status == "rejected":
            issues.append({"type": "ledger_rejected_but_usage_completed", "quota_ledger_id": ledger.id, "request_id": usage.request_id})

    if not dry_run:
        await db.commit()

    return {
        "dry_run": dry_run,
        "issue_count": len(issues),
        "issues": issues,
        "summary": {
            "started_usage_session_too_old": sum(1 for item in issues if item["type"] == "started_usage_session_too_old"),
            "reserved_not_settled": sum(1 for item in issues if item["type"] == "reserved_not_settled"),
            "usage_completed_but_ledger_missing": sum(1 for item in issues if item["type"] == "usage_completed_but_ledger_missing"),
            "ledger_rejected_but_usage_completed": sum(1 for item in issues if item["type"] == "ledger_rejected_but_usage_completed"),
        },
    }
