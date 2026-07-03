from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.quota_ledger_entry import QuotaLedgerEntry
from app.db.models.usage_session import UsageSession
from app.db.models.user import User


def _parse_ts(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _as_decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _iso(value):
    return value.isoformat() if value else None


def _filters(from_ts, to_ts, tenant_id, user_id, provider, model):
    conditions = []
    from_value = _parse_ts(from_ts)
    to_value = _parse_ts(to_ts)
    if from_value:
        conditions.append(UsageSession.created_at >= from_value)
    if to_value:
        conditions.append(UsageSession.created_at <= to_value)
    if user_id:
        conditions.append(UsageSession.user_id == user_id)
    if provider:
        conditions.append(UsageSession.upstream_provider == provider)
    if model:
        conditions.append(UsageSession.model_name == model)
    return conditions


async def usage_summary(
    db: AsyncSession, *, from_ts=None, to_ts=None, tenant_id=None, user_id=None, provider=None, model=None
) -> dict:
    query = select(
        func.count(UsageSession.id),
        func.sum(case((UsageSession.status == "completed", 1), else_=0)),
        func.sum(case((UsageSession.status != "completed", 1), else_=0)),
        func.coalesce(func.sum(UsageSession.prompt_tokens), 0),
        func.coalesce(func.sum(UsageSession.completion_tokens), 0),
        func.coalesce(func.sum(UsageSession.total_tokens), 0),
        func.coalesce(func.sum(UsageSession.estimated_cost_credits), 0),
        func.coalesce(func.sum(UsageSession.final_cost_credits), 0),
        func.coalesce(func.avg(UsageSession.latency_ms), 0),
    ).where(and_(*_filters(from_ts, to_ts, tenant_id, user_id, provider, model))) if _filters(from_ts, to_ts, tenant_id, user_id, provider, model) else select(
        func.count(UsageSession.id),
        func.sum(case((UsageSession.status == "completed", 1), else_=0)),
        func.sum(case((UsageSession.status != "completed", 1), else_=0)),
        func.coalesce(func.sum(UsageSession.prompt_tokens), 0),
        func.coalesce(func.sum(UsageSession.completion_tokens), 0),
        func.coalesce(func.sum(UsageSession.total_tokens), 0),
        func.coalesce(func.sum(UsageSession.estimated_cost_credits), 0),
        func.coalesce(func.sum(UsageSession.final_cost_credits), 0),
        func.coalesce(func.avg(UsageSession.latency_ms), 0),
    )
    row = (await db.execute(query)).one()
    request_count = int(row[0] or 0)
    success_count = int(row[1] or 0)
    error_count = int(row[2] or 0)
    return {
        "request_count": request_count,
        "success_count": success_count,
        "error_count": error_count,
        "error_rate": float(error_count / request_count) if request_count else 0.0,
        "prompt_tokens": int(row[3] or 0),
        "completion_tokens": int(row[4] or 0),
        "total_tokens": int(row[5] or 0),
        "estimated_cost_credits": float(_as_decimal(row[6])),
        "final_cost_credits": float(_as_decimal(row[7])),
        "avg_latency_ms": float(row[8] or 0),
    }


async def usage_timeseries(db: AsyncSession, *, from_ts=None, to_ts=None, bucket: str = "hour", user_id=None, provider=None, model=None) -> list[dict]:
    rows = list(
        (
            await db.execute(
                select(UsageSession.created_at, UsageSession.status, UsageSession.total_tokens, UsageSession.final_cost_credits, UsageSession.latency_ms).where(
                    and_(*_filters(from_ts, to_ts, None, user_id, provider, model))
                )
                if _filters(from_ts, to_ts, None, user_id, provider, model)
                else select(UsageSession.created_at, UsageSession.status, UsageSession.total_tokens, UsageSession.final_cost_credits, UsageSession.latency_ms)
            )
        ).all()
    )
    grouped: dict[str, dict] = defaultdict(lambda: {"request_count": 0, "success_count": 0, "error_count": 0, "total_tokens": 0, "final_cost_credits": Decimal("0"), "latencies": []})
    for created_at, status, total_tokens, final_cost, latency in rows:
        if not isinstance(created_at, datetime):
            continue
        if bucket == "minute":
            key = created_at.strftime("%Y-%m-%dT%H:%M:00Z")
        elif bucket == "day":
            key = created_at.strftime("%Y-%m-%d")
        else:
            key = created_at.strftime("%Y-%m-%dT%H:00:00Z")
        item = grouped[key]
        item["request_count"] += 1
        if status == "completed":
            item["success_count"] += 1
        else:
            item["error_count"] += 1
        item["total_tokens"] += int(total_tokens or 0)
        item["final_cost_credits"] += _as_decimal(final_cost)
        if latency is not None:
            item["latencies"].append(int(latency))
    result = []
    for key in sorted(grouped):
        item = grouped[key]
        latencies = sorted(item["latencies"])
        p95 = latencies[int(0.95 * (len(latencies) - 1))] if latencies else None
        result.append(
            {
                "bucket": key,
                "request_count": item["request_count"],
                "success_count": item["success_count"],
                "error_count": item["error_count"],
                "error_rate": float(item["error_count"] / item["request_count"]) if item["request_count"] else 0.0,
                "total_tokens": item["total_tokens"],
                "final_cost_credits": float(item["final_cost_credits"]),
                "avg_latency_ms": float(sum(latencies) / len(latencies)) if latencies else None,
                "p95_latency_ms": p95,
            }
        )
    return result


async def usage_group_by(db: AsyncSession, group: str, *, from_ts=None, to_ts=None, user_id=None, provider=None, model=None, limit: int = 20):
    column = {
        "user": UsageSession.user_id,
        "provider": UsageSession.upstream_provider,
        "model": UsageSession.model_name,
        "error": UsageSession.error_code,
    }[group]
    query = (
        select(
            column.label("k"),
            func.count(UsageSession.id).label("request_count"),
            func.sum(case((UsageSession.status == "completed", 1), else_=0)).label("success_count"),
            func.sum(case((UsageSession.status != "completed", 1), else_=0)).label("error_count"),
            func.coalesce(func.sum(UsageSession.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(UsageSession.final_cost_credits), 0).label("final_cost_credits"),
        )
        .group_by(column)
        .order_by(func.count(UsageSession.id).desc())
        .limit(limit)
    )
    conditions = _filters(from_ts, to_ts, None, user_id, provider, model)
    if conditions:
        query = query.where(and_(*conditions))
    rows = list((await db.execute(query)).all())
    if group == "user":
        users = {u.id: u.email for u in list((await db.execute(select(User.id, User.email))).all())}
    else:
        users = {}
    items = []
    for row in rows:
        request_count = int(row.request_count or 0)
        error_count = int(row.error_count or 0)
        key = row.k or "unknown"
        items.append(
            {
                group: key,
                "label": users.get(key, key) if group == "user" else key,
                "request_count": request_count,
                "success_count": int(row.success_count or 0),
                "error_count": error_count,
                "error_rate": float(error_count / request_count) if request_count else 0.0,
                "total_tokens": int(row.total_tokens or 0),
                "final_cost_credits": float(_as_decimal(row.final_cost_credits)),
            }
        )
    return items


async def quota_summary(db: AsyncSession, *, from_ts=None, to_ts=None, user_id=None, provider=None, model=None) -> dict:
    query = select(
        func.count(QuotaLedgerEntry.id),
        func.sum(case((QuotaLedgerEntry.status == "reserved", 1), else_=0)),
        func.sum(case((QuotaLedgerEntry.status == "settled", 1), else_=0)),
        func.sum(case((QuotaLedgerEntry.status == "rejected", 1), else_=0)),
        func.sum(case((QuotaLedgerEntry.status == "failed", 1), else_=0)),
        func.coalesce(func.sum(QuotaLedgerEntry.reserved_delta), 0),
        func.coalesce(func.sum(QuotaLedgerEntry.total_tokens), 0),
        func.coalesce(func.sum(QuotaLedgerEntry.final_cost_credits), 0),
    )
    conditions = []
    from_value = _parse_ts(from_ts)
    to_value = _parse_ts(to_ts)
    if from_value:
        conditions.append(QuotaLedgerEntry.created_at >= from_value)
    if to_value:
        conditions.append(QuotaLedgerEntry.created_at <= to_value)
    if user_id:
        conditions.append(QuotaLedgerEntry.user_id == user_id)
    if provider:
        conditions.append(QuotaLedgerEntry.provider == provider)
    if model:
        conditions.append(QuotaLedgerEntry.public_model_name == model)
    if conditions:
        query = query.where(and_(*conditions))
    row = (await db.execute(query)).one()
    return {
        "entry_count": int(row[0] or 0),
        "reserved_count": int(row[1] or 0),
        "settled_count": int(row[2] or 0),
        "rejected_count": int(row[3] or 0),
        "failed_count": int(row[4] or 0),
        "reserved_delta": int(row[5] or 0),
        "total_tokens": int(row[6] or 0),
        "final_cost_credits": float(_as_decimal(row[7])),
    }
