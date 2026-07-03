from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.time import utc_now
from app.db.models.audit_llm_message import AuditLLMMessage
from app.db.models.usage_session import UsageSession
from app.db.models.user import User
from app.services.audit_service import purge_expired_audit_messages, record_request_messages, soft_delete_user_conversation


async def _seed_usage(db_session):
    db_session.add(User(id="u1", email="u1@example.com", password_hash="x", status="active"))
    usage = UsageSession(
        id="s1",
        user_id="u1",
        token_id="t1",
        request_id="req-audit",
        model_id="m1",
        model_name="m1",
        status="started",
        estimated_cost_credits=0,
    )
    db_session.add(usage)
    await db_session.commit()
    await db_session.refresh(usage)
    return usage


@pytest.mark.asyncio
async def test_secret_redacted_before_storage(db_session, monkeypatch):
    monkeypatch.setattr(settings, "audit_redaction_enabled", True)
    monkeypatch.setattr(settings, "audit_store_message_content", True)
    monkeypatch.setattr(settings, "audit_hash_content", False)
    usage = await _seed_usage(db_session)
    await record_request_messages(
        db_session,
        usage,
        [{"role": "user", "content": "token sk-1234567890abcdefghijkl and email a@b.com"}],
    )
    message = (await db_session.execute(select(AuditLLMMessage))).scalar_one()
    assert "[REDACTED]" in (message.content or "")
    assert "sk-1234567890abcdefghijkl" not in (message.content or "")


@pytest.mark.asyncio
async def test_hash_mode_stores_hash_not_content(db_session, monkeypatch):
    monkeypatch.setattr(settings, "audit_redaction_enabled", True)
    monkeypatch.setattr(settings, "audit_hash_content", True)
    monkeypatch.setattr(settings, "audit_store_message_content", True)
    usage = await _seed_usage(db_session)
    await record_request_messages(db_session, usage, [{"role": "user", "content": "hello world"}])
    message = (await db_session.execute(select(AuditLLMMessage))).scalar_one()
    assert message.content is None
    assert message.content_hash
    assert message.content_preview == "hello world"


@pytest.mark.asyncio
async def test_retention_expires_at_set_and_purge(db_session, monkeypatch):
    monkeypatch.setattr(settings, "audit_retention_days", 1)
    monkeypatch.setattr(settings, "audit_hash_content", False)
    monkeypatch.setattr(settings, "audit_store_message_content", True)
    usage = await _seed_usage(db_session)
    await record_request_messages(db_session, usage, [{"role": "user", "content": "keep"}])
    message = (await db_session.execute(select(AuditLLMMessage))).scalar_one()
    assert message.retention_expires_at is not None

    message.retention_expires_at = utc_now() - timedelta(days=1)
    await db_session.commit()
    dry = await purge_expired_audit_messages(db_session, dry_run=True)
    assert dry["expired_count"] == 1
    actual = await purge_expired_audit_messages(db_session, dry_run=False)
    assert actual["deleted_count"] == 1
    assert (await db_session.execute(select(AuditLLMMessage))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_user_soft_delete_still_works(db_session, monkeypatch):
    monkeypatch.setattr(settings, "audit_hash_content", False)
    usage = await _seed_usage(db_session)
    await record_request_messages(db_session, usage, [{"role": "user", "content": "hello"}])
    deleted = await soft_delete_user_conversation(db_session, "u1", "s1")
    assert deleted == 1
    message = (await db_session.execute(select(AuditLLMMessage))).scalar_one()
    assert message.user_deleted_at is not None
