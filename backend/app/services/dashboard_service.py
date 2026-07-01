from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.public_model import PublicModel
from app.db.models.usage_session import UsageSession
from app.db.models.user import User


def _usage_value(usage: dict | None, key: str) -> int:
    if not usage or not isinstance(usage, dict):
        return 0
    value = usage.get(key) or 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


async def get_user_usage_summary(db: AsyncSession, user_id: str) -> dict:
    model_rows = await db.execute(select(PublicModel.id, PublicModel.slug))
    model_name_map = {row.id: row.slug for row in model_rows.all()}

    recent_result = await db.execute(
        select(UsageSession)
        .where(UsageSession.user_id == user_id)
        .order_by(UsageSession.created_at.desc())
        .limit(20)
    )
    recent_sessions = []
    for session in recent_result.scalars().all():
        usage = session.usage or {}
        recent_sessions.append(
            {
                "id": session.id,
                "request_id": session.request_id,
                "model_id": session.model_id,
                "model_name": model_name_map.get(session.model_id, session.model_id),
                "status": session.status,
                "provider": session.upstream_provider,
                "final_cost_credits": float(session.final_cost_credits or 0),
                "prompt_tokens": _usage_value(usage, "prompt_tokens"),
                "completion_tokens": _usage_value(usage, "completion_tokens"),
                "total_tokens": _usage_value(usage, "total_tokens"),
                "created_at": session.created_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            }
        )

    grouped_result = await db.execute(
        select(
            UsageSession.model_id,
            func.count(UsageSession.id).label("requests"),
            func.coalesce(func.sum(UsageSession.final_cost_credits), 0).label("used_credits"),
        )
        .where(UsageSession.user_id == user_id, UsageSession.status == "completed")
        .group_by(UsageSession.model_id)
        .order_by(func.coalesce(func.sum(UsageSession.final_cost_credits), 0).desc())
    )
    by_model = [
        {
            "model_id": row.model_id,
            "model_name": model_name_map.get(row.model_id, row.model_id),
            "requests": int(row.requests or 0),
            "used_credits": float(row.used_credits or 0),
        }
        for row in grouped_result.all()
    ]
    return {"recent_sessions": recent_sessions, "by_model": by_model}


async def get_admin_usage_summary(db: AsyncSession) -> dict:
    model_rows = await db.execute(select(PublicModel.id, PublicModel.slug))
    model_name_map = {row.id: row.slug for row in model_rows.all()}

    user_rows = await db.execute(select(User.id, User.email))
    user_email_map = {row.id: row.email for row in user_rows.all()}

    provider_rows = await db.execute(
        select(ProviderCredential.id, Provider.slug, ProviderEndpoint.slug.label("endpoint_slug"), ProviderCredential.display_name)
        .join(ProviderEndpoint, ProviderEndpoint.id == ProviderCredential.provider_endpoint_id)
        .join(Provider, Provider.id == ProviderEndpoint.provider_id)
    )
    provider_map = {
        row.id: {"provider": row.slug, "endpoint": row.endpoint_slug, "credential_name": row.display_name}
        for row in provider_rows.all()
    }

    recent_result = await db.execute(select(UsageSession).order_by(UsageSession.created_at.desc()).limit(30))
    recent_sessions = []
    for session in recent_result.scalars().all():
        usage = session.usage or {}
        provider_info = provider_map.get(session.upstream_credential_id or "", {})
        recent_sessions.append(
            {
                "id": session.id,
                "request_id": session.request_id,
                "user_id": session.user_id,
                "user_email": user_email_map.get(session.user_id, session.user_id),
                "model_id": session.model_id,
                "model_name": model_name_map.get(session.model_id, session.model_id),
                "status": session.status,
                "provider": session.upstream_provider or provider_info.get("provider"),
                "endpoint": provider_info.get("endpoint"),
                "credential_name": provider_info.get("credential_name"),
                "final_cost_credits": float(session.final_cost_credits or 0),
                "total_tokens": _usage_value(usage, "total_tokens"),
                "created_at": session.created_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            }
        )

    by_model_result = await db.execute(
        select(
            UsageSession.model_id,
            func.count(UsageSession.id).label("requests"),
            func.coalesce(func.sum(UsageSession.final_cost_credits), 0).label("used_credits"),
        )
        .where(UsageSession.status == "completed")
        .group_by(UsageSession.model_id)
        .order_by(func.coalesce(func.sum(UsageSession.final_cost_credits), 0).desc())
    )
    by_model = [
        {
            "model_id": row.model_id,
            "model_name": model_name_map.get(row.model_id, row.model_id),
            "requests": int(row.requests or 0),
            "used_credits": float(row.used_credits or 0),
        }
        for row in by_model_result.all()
    ]

    by_provider_result = await db.execute(
        select(
            UsageSession.upstream_provider,
            func.count(UsageSession.id).label("requests"),
            func.coalesce(func.sum(UsageSession.final_cost_credits), 0).label("used_credits"),
        )
        .where(UsageSession.status == "completed")
        .group_by(UsageSession.upstream_provider)
        .order_by(func.coalesce(func.sum(UsageSession.final_cost_credits), 0).desc())
    )
    by_provider = [
        {
            "provider": row.upstream_provider or "unknown",
            "requests": int(row.requests or 0),
            "used_credits": float(row.used_credits or 0),
        }
        for row in by_provider_result.all()
    ]

    return {
        "recent_sessions": recent_sessions,
        "by_model": by_model,
        "by_provider": by_provider,
    }
