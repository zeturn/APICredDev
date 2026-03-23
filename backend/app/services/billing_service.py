import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.db.models.wallet import Wallet
from app.db.models.ledger import LedgerEntry
from app.db.models.usage_session import UsageSession
from app.db.models.recharge_code import RechargeCode
from app.db.models.stripe_event import StripeEvent


async def get_wallet(db: AsyncSession, user_id: str) -> Wallet:
    wallet = await db.get(Wallet, user_id)
    if not wallet:
        wallet = Wallet(user_id=user_id, balance_credits=Decimal("0"))
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
    return wallet


async def list_ledger(db: AsyncSession, user_id: str, limit: int = 50) -> list[LedgerEntry]:
    result = await db.execute(
        select(LedgerEntry)
        .where(LedgerEntry.user_id == user_id)
        .order_by(LedgerEntry.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def authorize_usage(
    db: AsyncSession,
    user_id: str,
    token_id: str,
    request_id: str,
    model_id: str,
    estimated_cost: float,
    meta: dict,
) -> UsageSession:
    wallet = await get_wallet(db, user_id)
    estimated = Decimal(str(estimated_cost))
    if wallet.balance_credits < estimated:
        raise ValueError("insufficient_balance")
    usage_id = str(uuid.uuid4())
    usage = UsageSession(
        id=usage_id,
        user_id=user_id,
        token_id=token_id,
        request_id=request_id,
        model_id=model_id,
        status="started",
        estimated_cost_credits=estimated,
    )
    ledger = LedgerEntry(
        user_id=user_id,
        entry_type="pending_debit",
        amount_credits=-estimated,
        status="pending",
        ref_type="usage_session",
        ref_id=usage_id,
        meta=meta,
    )
    wallet.balance_credits -= estimated
    wallet.updated_at = utc_now()
    db.add(usage)
    db.add(ledger)
    await db.commit()
    await db.refresh(usage)
    return usage


async def settle_usage(
    db: AsyncSession,
    usage: UsageSession,
    final_cost: float,
    usage_meta: dict,
) -> None:
    if usage.status == "completed":
        return
    wallet = await get_wallet(db, usage.user_id)
    result = await db.execute(
        select(LedgerEntry)
        .where(LedgerEntry.ref_type == "usage_session")
        .where(LedgerEntry.ref_id == usage.id)
        .where(LedgerEntry.entry_type == "pending_debit")
    )
    pending = result.scalar_one_or_none()
    if pending and pending.status != "settled":
        pending.status = "settled"
    final = Decimal(str(final_cost))
    estimated = Decimal(str(usage.estimated_cost_credits))
    diff = final - estimated
    if diff != 0:
        adjustment = LedgerEntry(
            user_id=usage.user_id,
            entry_type="adjustment",
            amount_credits=-diff,
            status="settled",
            ref_type="usage_session",
            ref_id=usage.id,
            meta={"reason": "settle_adjust"},
        )
        wallet.balance_credits -= diff
        wallet.updated_at = utc_now()
        db.add(adjustment)
    usage.final_cost_credits = final
    usage.usage = usage_meta
    usage.status = "completed"
    usage.completed_at = utc_now()
    await db.commit()


async def redeem_code(db: AsyncSession, user_id: str, code_hash: str) -> Wallet:
    result = await db.execute(select(RechargeCode).where(RechargeCode.code_hash == code_hash))
    code = result.scalar_one_or_none()
    if not code or code.status != "unused":
        raise ValueError("invalid_code")
    wallet = await get_wallet(db, user_id)
    code.status = "used"
    code.used_by_user_id = user_id
    code.used_at = utc_now()
    amount = Decimal(str(code.amount_credits))
    ledger = LedgerEntry(
        user_id=user_id,
        entry_type="credit",
        amount_credits=amount,
        status="settled",
        ref_type="recharge_code",
        ref_id=code.id,
        meta={},
    )
    wallet.balance_credits += amount
    wallet.updated_at = utc_now()
    db.add(ledger)
    await db.commit()
    return wallet


async def record_stripe_event(
    db: AsyncSession,
    event_id: str,
    event_type: str,
    user_id: str,
    amount_credits: float,
    meta: dict,
) -> None:
    exists = await db.get(StripeEvent, event_id)
    if exists:
        return
    event = StripeEvent(event_id=event_id, type=event_type, meta=meta)
    wallet = await get_wallet(db, user_id)
    amount = Decimal(str(amount_credits))
    ledger = LedgerEntry(
        user_id=user_id,
        entry_type="credit",
        amount_credits=amount,
        status="settled",
        ref_type="stripe_event",
        ref_id=event_id,
        meta=meta,
    )
    wallet.balance_credits += amount
    wallet.updated_at = utc_now()
    db.add(event)
    db.add(ledger)
    await db.commit()

