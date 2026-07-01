from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.db.models.audit_llm_message import AuditLLMMessage
from app.db.models.usage_session import UsageSession


def _message_content(message: dict[str, Any]) -> str | None:
    content = message.get("content")
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return str(content)


def _message_role(message: dict[str, Any], fallback: str) -> str:
    role = str(message.get("role") or "").strip()
    return role or fallback


async def record_request_messages(
    db: AsyncSession,
    usage_session: UsageSession,
    messages: list[dict[str, Any]],
    *,
    source: str = "request",
) -> None:
    rows = [
        AuditLLMMessage(
            usage_session_id=usage_session.id,
            user_id=usage_session.user_id,
            request_id=usage_session.request_id,
            model_id=usage_session.model_id,
            model_name=usage_session.model_name,
            upstream_provider=usage_session.upstream_provider,
            upstream_credential_id=usage_session.upstream_credential_id,
            source=source,
            role=_message_role(message, "user"),
            content=_message_content(message),
            sequence=index,
            message_metadata={key: value for key, value in message.items() if key not in {"role", "content"}},
        )
        for index, message in enumerate(messages)
    ]
    if rows:
        db.add_all(rows)
        await db.commit()


def extract_response_messages(raw: dict | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    messages: list[dict[str, Any]] = []
    for choice in raw.get("choices", []):
        if not isinstance(choice, dict):
            continue
        message = choice.get("message") or {}
        if not isinstance(message, dict):
            continue
        messages.append(
            {
                "role": message.get("role") or "assistant",
                "content": message.get("content"),
                "finish_reason": choice.get("finish_reason"),
                "choice_index": choice.get("index"),
            }
        )
    return messages


async def record_response_messages(
    db: AsyncSession,
    usage_session: UsageSession,
    messages: list[dict[str, Any]],
) -> None:
    if not messages:
        return
    max_sequence = int(
        (
            await db.execute(
                select(func.coalesce(func.max(AuditLLMMessage.sequence), -1)).where(
                    AuditLLMMessage.usage_session_id == usage_session.id
                )
            )
        ).scalar()
        or -1
    )
    rows = [
        AuditLLMMessage(
            usage_session_id=usage_session.id,
            user_id=usage_session.user_id,
            request_id=usage_session.request_id,
            model_id=usage_session.model_id,
            model_name=usage_session.model_name,
            upstream_provider=usage_session.upstream_provider,
            upstream_credential_id=usage_session.upstream_credential_id,
            source="response",
            role=_message_role(message, "assistant"),
            content=_message_content(message),
            sequence=max_sequence + index + 1,
            message_metadata={key: value for key, value in message.items() if key not in {"role", "content"}},
        )
        for index, message in enumerate(messages)
    ]
    db.add_all(rows)
    await db.commit()


def _message_to_dict(message: AuditLLMMessage, *, include_deleted: bool) -> dict[str, Any]:
    return {
        "id": message.id,
        "usage_session_id": message.usage_session_id,
        "request_id": message.request_id,
        "user_id": message.user_id,
        "model_id": message.model_id,
        "model_name": message.model_name,
        "upstream_provider": message.upstream_provider,
        "upstream_credential_id": message.upstream_credential_id,
        "source": message.source,
        "role": message.role,
        "content": message.content,
        "sequence": message.sequence,
        "metadata": message.message_metadata or {},
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "user_deleted_at": message.user_deleted_at.isoformat() if include_deleted and message.user_deleted_at else None,
    }


async def list_user_audit_conversations(
    db: AsyncSession,
    user_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
    include_user_deleted: bool = False,
) -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    visible_filter = True if include_user_deleted else AuditLLMMessage.user_deleted_at.is_(None)
    session_query = (
        select(
            AuditLLMMessage.usage_session_id,
            func.max(AuditLLMMessage.created_at).label("last_message_at"),
            func.min(AuditLLMMessage.created_at).label("first_message_at"),
            func.count(AuditLLMMessage.id).label("message_count"),
        )
        .where(AuditLLMMessage.user_id == user_id, visible_filter)
        .group_by(AuditLLMMessage.usage_session_id)
    )
    total = int((await db.execute(select(func.count()).select_from(session_query.subquery()))).scalar() or 0)
    session_rows = (
        await db.execute(
            session_query.order_by(func.max(AuditLLMMessage.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    session_ids = [row.usage_session_id for row in session_rows]
    if not session_ids:
        return {"items": [], "page": page, "page_size": page_size, "total": total}

    messages_query = select(AuditLLMMessage).where(AuditLLMMessage.usage_session_id.in_(session_ids))
    if not include_user_deleted:
        messages_query = messages_query.where(AuditLLMMessage.user_deleted_at.is_(None))
    messages = list(
        (
            await db.execute(
                messages_query.order_by(AuditLLMMessage.usage_session_id.asc(), AuditLLMMessage.sequence.asc(), AuditLLMMessage.created_at.asc())
            )
        ).scalars().all()
    )
    messages_by_session: dict[str, list[AuditLLMMessage]] = {}
    for message in messages:
        messages_by_session.setdefault(message.usage_session_id, []).append(message)

    usage_rows = list((await db.execute(select(UsageSession).where(UsageSession.id.in_(session_ids)))).scalars().all())
    usage_by_id = {usage.id: usage for usage in usage_rows}

    items = []
    for row in session_rows:
        usage = usage_by_id.get(row.usage_session_id)
        session_messages = messages_by_session.get(row.usage_session_id, [])
        deleted_for_user = bool(session_messages) and all(message.user_deleted_at is not None for message in session_messages)
        items.append(
            {
                "usage_session_id": row.usage_session_id,
                "request_id": usage.request_id if usage else (session_messages[0].request_id if session_messages else None),
                "user_id": user_id,
                "model_id": usage.model_id if usage else (session_messages[0].model_id if session_messages else None),
                "model_name": usage.model_name if usage else (session_messages[0].model_name if session_messages else None),
                "upstream_provider": usage.upstream_provider if usage else (session_messages[0].upstream_provider if session_messages else None),
                "status": usage.status if usage else None,
                "final_cost_credits": float(usage.final_cost_credits or 0) if usage else 0,
                "total_tokens": int(usage.total_tokens or 0) if usage else 0,
                "created_at": usage.created_at.isoformat() if usage and usage.created_at else row.first_message_at.isoformat(),
                "completed_at": usage.completed_at.isoformat() if usage and usage.completed_at else None,
                "message_count": int(row.message_count or len(session_messages)),
                "deleted_for_user": deleted_for_user,
                "messages": [_message_to_dict(message, include_deleted=include_user_deleted) for message in session_messages],
            }
        )

    return {"items": items, "page": page, "page_size": page_size, "total": total}


async def soft_delete_user_conversation(db: AsyncSession, user_id: str, usage_session_id: str) -> int:
    result = await db.execute(
        update(AuditLLMMessage)
        .where(
            AuditLLMMessage.user_id == user_id,
            AuditLLMMessage.usage_session_id == usage_session_id,
            AuditLLMMessage.user_deleted_at.is_(None),
        )
        .values(user_deleted_at=utc_now())
    )
    await db.commit()
    return int(result.rowcount or 0)
