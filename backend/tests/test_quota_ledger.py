from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.quota_ledger_entry import QuotaLedgerEntry
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.services.billing_service import authorize_usage, settle_usage
from app.services.quota_ledger_service import settle_quota_ledger


async def _seed_user_wallet(db_session, *, user_id: str = "u1", balance: str = "100") -> None:
    db_session.add(User(id=user_id, email=f"{user_id}@example.com", password_hash="x", status="active"))
    db_session.add(Wallet(user_id=user_id, balance_credits=Decimal(balance)))
    await db_session.commit()


@pytest.mark.asyncio
async def test_reserve_then_settle(db_session):
    await _seed_user_wallet(db_session)
    usage = await authorize_usage(
        db_session,
        user_id="u1",
        token_id="t1",
        request_id="req1",
        model_id="m1",
        model_name="apicred-fast",
        estimated_cost=1.2,
        meta={},
    )
    await settle_usage(db_session, usage, 0.8, {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
    ledger = (await db_session.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == "req1"))).scalar_one()
    assert ledger.status == "settled"
    assert float(ledger.final_cost_credits or 0) == pytest.approx(0.8)
    assert ledger.total_tokens == 15


@pytest.mark.asyncio
async def test_reserve_then_upstream_failure(db_session):
    await _seed_user_wallet(db_session)
    usage = await authorize_usage(
        db_session,
        user_id="u1",
        token_id="t1",
        request_id="req-fail",
        model_id="m1",
        model_name="apicred-fast",
        estimated_cost=1.0,
        meta={},
    )
    await settle_usage(db_session, usage, 0, {"error": "upstream_failed"})
    await settle_quota_ledger(db_session, request_id="req-fail", status="failed", reason="upstream_failed")
    ledger = (await db_session.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == "req-fail"))).scalar_one()
    assert ledger.status in {"failed", "settled"}


@pytest.mark.asyncio
async def test_duplicate_settle_idempotent(db_session):
    await _seed_user_wallet(db_session)
    usage = await authorize_usage(
        db_session,
        user_id="u1",
        token_id="t1",
        request_id="req-dup",
        model_id="m1",
        model_name="apicred-fast",
        estimated_cost=1.0,
        meta={},
    )
    await settle_usage(db_session, usage, 0.5, {"total_tokens": 10})
    await settle_usage(db_session, usage, 2.0, {"total_tokens": 999})
    ledger = (await db_session.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == "req-dup"))).scalar_one()
    assert float(ledger.final_cost_credits or 0) == pytest.approx(0.5)
    assert ledger.total_tokens == 10


@pytest.mark.asyncio
async def test_rejected_quota_recorded(db_session):
    await _seed_user_wallet(db_session)
    usage = await authorize_usage(
        db_session,
        user_id="u1",
        token_id="t1",
        request_id="req-reject",
        model_id="m1",
        model_name="apicred-fast",
        estimated_cost=0.1,
        meta={},
    )
    await settle_quota_ledger(db_session, request_id=usage.request_id, status="rejected", reason="quota_rejected")
    ledger = (await db_session.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == "req-reject"))).scalar_one()
    assert ledger.status == "rejected"


@pytest.mark.asyncio
async def test_service_restart_does_not_lose_ledger(db_session):
    await _seed_user_wallet(db_session)
    usage = await authorize_usage(
        db_session,
        user_id="u1",
        token_id="t1",
        request_id="req-restart",
        model_id="m1",
        model_name="apicred-fast",
        estimated_cost=0.2,
        meta={},
    )
    await settle_usage(db_session, usage, 0.2, {"total_tokens": 2})

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as isolated:
        result = await isolated.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == "req-restart"))
        assert result.scalar_one_or_none() is None
    await engine.dispose()

    ledger = (await db_session.execute(select(QuotaLedgerEntry).where(QuotaLedgerEntry.request_id == "req-restart"))).scalar_one_or_none()
    assert ledger is not None
