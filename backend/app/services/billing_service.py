from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import utc_now
from app.db.models.ledger import LedgerEntry
from app.db.models.recharge_code import RechargeCode
from app.db.models.stripe_event import StripeEvent
from app.db.models.usage_session import UsageSession
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.services.basaltpass_client import BasaltPassClient


@dataclass
class WalletSnapshot:
    balance_credits: Decimal
    updated_at: datetime


def _as_decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


def _credit_to_smallest(amount_credits: Decimal) -> int:
    scale = max(int(settings.basalt_credit_scale or 1), 1)
    smallest = (amount_credits * Decimal(scale)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(smallest)


def _smallest_to_credit(amount_smallest: int | float | str) -> Decimal:
    scale = max(int(settings.basalt_credit_scale or 1), 1)
    return _as_decimal(amount_smallest) / Decimal(scale)


def _is_remote_wallet_enabled(user: User | None) -> bool:
    return bool(
        user
        and getattr(user, "basalt_user_id", None)
        and settings.basalt_s2s_client_id
        and settings.basalt_s2s_client_secret
    )


def _extract_remote_error(payload: object) -> str:
    if not isinstance(payload, dict):
        return "remote wallet request failed"
    err = payload.get("error")
    if not isinstance(err, dict):
        return "remote wallet request failed"

    message = err.get("message")
    if isinstance(message, str) and message:
        return message

    details = err.get("details")
    if isinstance(details, dict):
        detail_error = details.get("error")
        if isinstance(detail_error, dict):
            detail_message = detail_error.get("message")
            if isinstance(detail_message, str) and detail_message:
                return detail_message
        details_message = details.get("message")
        if isinstance(details_message, str) and details_message:
            return details_message

    return "remote wallet request failed"


async def _get_local_wallet(db: AsyncSession, user_id: str) -> Wallet:
    wallet = await db.get(Wallet, user_id)
    if not wallet:
        wallet = Wallet(user_id=user_id, balance_credits=Decimal("0"), updated_at=utc_now())
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
    return wallet


async def _fetch_remote_credit_balance(user: User) -> Decimal:
    client = BasaltPassClient()
    payload = await client.s2s_get_user_wallet(
        user_id=str(user.basalt_user_id),
        currency=settings.basalt_credit_currency,
        limit=1,
        tenant_id=str(user.basalt_tenant_id) if user.basalt_tenant_id else None,
    )
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(_extract_remote_error(payload))
    if not isinstance(payload, dict):
        raise RuntimeError("invalid remote wallet response")
    return _smallest_to_credit(payload.get("balance") or 0)


async def _sync_local_wallet_from_remote(db: AsyncSession, user: User | None, wallet: Wallet) -> Decimal | None:
    if not _is_remote_wallet_enabled(user):
        return None
    remote_balance = await _fetch_remote_credit_balance(user)
    wallet.balance_credits = remote_balance
    wallet.updated_at = utc_now()
    return remote_balance


async def _adjust_remote_credit(user: User, delta: Decimal, reference: str) -> None:
    if delta == 0:
        return

    amount_smallest = abs(_credit_to_smallest(delta))
    if amount_smallest == 0:
        return

    operation = "increase" if delta > 0 else "decrease"
    client = BasaltPassClient()
    payload = await client.s2s_adjust_user_wallet(
        user_id=str(user.basalt_user_id),
        currency=settings.basalt_credit_currency,
        operation=operation,
        amount=amount_smallest,
        reference=reference,
        tenant_id=str(user.basalt_tenant_id) if user.basalt_tenant_id else None,
    )

    if isinstance(payload, dict) and payload.get("error"):
        message = _extract_remote_error(payload)
        if "insufficient" in message.lower():
            raise ValueError("insufficient_balance")
        raise RuntimeError(message)


async def list_ledger(db: AsyncSession, user_id: str, limit: int = 50) -> list[LedgerEntry]:
    result = await db.execute(
        select(LedgerEntry)
        .where(LedgerEntry.user_id == user_id)
        .order_by(LedgerEntry.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_wallet(db: AsyncSession, user_id: str) -> WalletSnapshot:
    user = await db.get(User, user_id)
    wallet = await _get_local_wallet(db, user_id)

    if _is_remote_wallet_enabled(user):
        await _sync_local_wallet_from_remote(db, user, wallet)
        await _sync_local_wallet_from_remote(db, user, wallet)
        await db.commit()
        await db.refresh(wallet)

    return WalletSnapshot(
        balance_credits=_as_decimal(wallet.balance_credits),
        updated_at=wallet.updated_at,
    )


async def authorize_usage(
    db: AsyncSession,
    user_id: str,
    token_id: str,
    request_id: str,
    model_id: str,
    estimated_cost: float,
    meta: dict,
    model_name: str | None = None,
    request_messages: list[dict] | None = None,
    request_text: str | None = None,
) -> UsageSession:
    estimated = Decimal(str(estimated_cost))
    user = await db.get(User, user_id)
    wallet = await _get_local_wallet(db, user_id)

    if _is_remote_wallet_enabled(user):
        before_balance = await _sync_local_wallet_from_remote(db, user, wallet)
        if _as_decimal(before_balance) < estimated:
            raise ValueError("insufficient_balance")
        await _adjust_remote_credit(user, -estimated, f"apicred:usage_pending:{request_id}")
        await _sync_local_wallet_from_remote(db, user, wallet)
    else:
        local_balance = _as_decimal(wallet.balance_credits)
        if local_balance < estimated:
            raise ValueError("insufficient_balance")
        wallet.balance_credits = local_balance - estimated

    usage_id = str(uuid.uuid4())
    usage = UsageSession(
        id=usage_id,
        user_id=user_id,
        token_id=token_id,
        request_id=request_id,
        model_id=model_id,
        model_name=model_name,
        status="started",
        estimated_cost_credits=estimated,
        request_messages=request_messages or [],
        request_text=request_text,
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
    response_text: str | None = None,
) -> None:
    if usage.status == "completed":
        return

    result = await db.execute(
        select(LedgerEntry)
        .where(LedgerEntry.ref_type == "usage_session")
        .where(LedgerEntry.ref_id == usage.id)
        .where(LedgerEntry.entry_type == "pending_debit")
    )
    pending = result.scalar_one_or_none()
    if pending and pending.status != "settled":
        pending.status = "settled"

    user = await db.get(User, usage.user_id)
    wallet = await _get_local_wallet(db, usage.user_id)

    final = Decimal(str(final_cost))
    estimated = Decimal(str(usage.estimated_cost_credits))
    diff = final - estimated

    if _is_remote_wallet_enabled(user):
        await _sync_local_wallet_from_remote(db, user, wallet)

    if diff != 0:
        if _is_remote_wallet_enabled(user):
            await _adjust_remote_credit(user, -diff, f"apicred:usage_settle:{usage.id}")
        adjustment = LedgerEntry(
            user_id=usage.user_id,
            entry_type="adjustment",
            amount_credits=-diff,
            status="settled",
            ref_type="usage_session",
            ref_id=usage.id,
            meta={"reason": "settle_adjust"},
        )
        if _is_remote_wallet_enabled(user):
            await _sync_local_wallet_from_remote(db, user, wallet)
        else:
            wallet.balance_credits = _as_decimal(wallet.balance_credits) - diff
            wallet.updated_at = utc_now()
        db.add(adjustment)
    elif _is_remote_wallet_enabled(user):
        await _sync_local_wallet_from_remote(db, user, wallet)

    usage.final_cost_credits = final
    usage.prompt_tokens = int((usage_meta or {}).get("prompt_tokens", 0) or 0)
    usage.completion_tokens = int((usage_meta or {}).get("completion_tokens", 0) or 0)
    usage.total_tokens = int((usage_meta or {}).get("total_tokens", 0) or 0)
    usage.response_text = response_text
    usage.usage = usage_meta
    usage.status = "completed"
    usage.completed_at = utc_now()
    await db.commit()


async def redeem_code(db: AsyncSession, user_id: str, code_hash: str) -> WalletSnapshot:
    result = await db.execute(select(RechargeCode).where(RechargeCode.code_hash == code_hash))
    code = result.scalar_one_or_none()
    if not code or code.status != "unused":
        raise ValueError("invalid_code")

    amount = Decimal(str(code.amount_credits))
    user = await db.get(User, user_id)
    wallet = await _get_local_wallet(db, user_id)

    if _is_remote_wallet_enabled(user):
        await _sync_local_wallet_from_remote(db, user, wallet)
        await _adjust_remote_credit(user, amount, f"apicred:recharge_code:{code.id}")
        await _sync_local_wallet_from_remote(db, user, wallet)

    code.status = "used"
    code.used_by_user_id = user_id
    code.used_at = utc_now()

    ledger = LedgerEntry(
        user_id=user_id,
        entry_type="credit",
        amount_credits=amount,
        status="settled",
        ref_type="recharge_code",
        ref_id=code.id,
        meta={},
    )
    if not _is_remote_wallet_enabled(user):
        wallet.balance_credits = _as_decimal(wallet.balance_credits) + amount
        wallet.updated_at = utc_now()
    db.add(ledger)
    await db.commit()
    await db.refresh(wallet)

    return WalletSnapshot(
        balance_credits=_as_decimal(wallet.balance_credits),
        updated_at=wallet.updated_at,
    )


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

    amount = Decimal(str(amount_credits))
    user = await db.get(User, user_id)
    wallet = await _get_local_wallet(db, user_id)

    if _is_remote_wallet_enabled(user):
        await _sync_local_wallet_from_remote(db, user, wallet)
        await _adjust_remote_credit(user, amount, f"apicred:stripe:{event_id}")
        await _sync_local_wallet_from_remote(db, user, wallet)

    event = StripeEvent(event_id=event_id, type=event_type, meta=meta)
    ledger = LedgerEntry(
        user_id=user_id,
        entry_type="credit",
        amount_credits=amount,
        status="settled",
        ref_type="stripe_event",
        ref_id=event_id,
        meta=meta,
    )
    if not _is_remote_wallet_enabled(user):
        wallet.balance_credits = _as_decimal(wallet.balance_credits) + amount
        wallet.updated_at = utc_now()
    db.add(event)
    db.add(ledger)
    await db.commit()

