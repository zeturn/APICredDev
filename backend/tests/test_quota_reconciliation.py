from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.time import utc_now
from app.db.models.quota_ledger_entry import QuotaLedgerEntry
from app.db.models.usage_session import UsageSession
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.services.quota_ledger_service import reconcile_quota_ledger


@pytest.mark.asyncio
async def test_reconcile_stale_pending_sessions(db_session):
    db_session.add(User(id="u1", email="u1@example.com", password_hash="x", status="active"))
    db_session.add(Wallet(user_id="u1", balance_credits=Decimal("10")))
    db_session.add(
        UsageSession(
            id="s1",
            user_id="u1",
            token_id="t1",
            request_id="req-old",
            model_id="m1",
            model_name="m1",
            status="started",
            estimated_cost_credits=1,
            created_at=utc_now() - timedelta(hours=2),
        )
    )
    db_session.add(
        QuotaLedgerEntry(
            id="q1",
            usage_session_id="s1",
            request_id="req-old",
            user_id="u1",
            token_id="t1",
            public_model_id="m1",
            public_model_name="m1",
            status="reserved",
            created_at=utc_now() - timedelta(hours=2),
            metadata_json={},
        )
    )
    await db_session.commit()

    dry = await reconcile_quota_ledger(db_session, dry_run=True)
    assert dry["summary"]["started_usage_session_too_old"] >= 1
    assert dry["summary"]["reserved_not_settled"] >= 1

    applied = await reconcile_quota_ledger(db_session, dry_run=False)
    assert applied["summary"]["reserved_not_settled"] >= 1
    entry = (await db_session.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.id == "q1"))).scalar_one()
    assert entry.status == "released"


@pytest.mark.asyncio
async def test_reconcile_detects_completed_mismatch(db_session):
    db_session.add(User(id="u2", email="u2@example.com", password_hash="x", status="active"))
    db_session.add(Wallet(user_id="u2", balance_credits=Decimal("10")))
    db_session.add(
        UsageSession(
            id="s2",
            user_id="u2",
            token_id="t2",
            request_id="req-completed-missing",
            model_id="m2",
            model_name="m2",
            status="completed",
            estimated_cost_credits=1,
            final_cost_credits=1,
        )
    )
    db_session.add(
        UsageSession(
            id="s3",
            user_id="u2",
            token_id="t2",
            request_id="req-completed-rejected",
            model_id="m2",
            model_name="m2",
            status="completed",
            estimated_cost_credits=1,
            final_cost_credits=1,
        )
    )
    db_session.add(
        QuotaLedgerEntry(
            id="q3",
            usage_session_id="s3",
            request_id="req-completed-rejected",
            user_id="u2",
            token_id="t2",
            public_model_id="m2",
            public_model_name="m2",
            status="rejected",
            metadata_json={},
        )
    )
    await db_session.commit()
    result = await reconcile_quota_ledger(db_session, dry_run=True)
    assert result["summary"]["usage_completed_but_ledger_missing"] >= 1
    assert result["summary"]["ledger_rejected_but_usage_completed"] >= 1
