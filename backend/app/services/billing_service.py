from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
import uuid6

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.credit_units import as_decimal, billable_credits, credits_to_microcredits, microcredits_to_credits
from app.core.time import utc_now
from app.db.models.ledger import LedgerEntry
from app.db.models.usage_session import UsageSession
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.services.basaltpass_client import BasaltPassClient
from app.services.quota_ledger_service import reserve_quota_ledger_for_usage, settle_quota_ledger
from app.services import synavis_client as _synavis


@dataclass
class WalletSnapshot:
    balance_credits: Decimal
    updated_at: datetime


@dataclass(frozen=True)
class RemoteWalletOwner:
    owner_type: str
    owner_id: str
    tenant_id: str | None


def _as_decimal(value: object) -> Decimal:
    return as_decimal(value)


def _credit_to_smallest(amount_credits: Decimal) -> int:
    return credits_to_microcredits(amount_credits, rounding=ROUND_HALF_UP)


def _smallest_to_credit(amount_smallest: int | float | str) -> Decimal:
    return microcredits_to_credits(amount_smallest)


def _remote_wallet_owner(
    user: User | None,
    principal_type: str = "user",
    principal_id: str | None = None,
    tenant_id: str | None = None,
) -> RemoteWalletOwner | None:
    if not settings.basalt_s2s_client_id or not settings.basalt_s2s_client_secret:
        return None
    normalized_type = (principal_type or "user").strip().lower()
    if normalized_type == "app":
        owner_id = (principal_id or "").strip()
        owner_tenant_id = (tenant_id or "").strip() or None
        if owner_id and owner_tenant_id:
            return RemoteWalletOwner("app", owner_id, owner_tenant_id)
        return None
    basalt_user_id = str(getattr(user, "basalt_user_id", "") or "").strip()
    if not basalt_user_id:
        return None
    owner_tenant_id = (tenant_id or str(getattr(user, "basalt_tenant_id", "") or "")).strip() or None
    return RemoteWalletOwner("user", basalt_user_id, owner_tenant_id)


def _is_remote_wallet_enabled(
    user: User | None,
    principal_type: str = "user",
    principal_id: str | None = None,
    tenant_id: str | None = None,
) -> bool:
    return _remote_wallet_owner(user, principal_type, principal_id, tenant_id) is not None


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


async def _fetch_remote_credit_balance(owner: RemoteWalletOwner) -> Decimal:
    client = BasaltPassClient()
    if owner.owner_type == "user":
        payload = await client.s2s_get_user_wallet(
            user_id=owner.owner_id,
            currency=settings.basalt_credit_currency,
            limit=1,
            tenant_id=owner.tenant_id,
        )
    else:
        payload = await client.s2s_get_owner_wallet(
            owner_type=owner.owner_type,
            owner_id=owner.owner_id,
            currency=settings.basalt_credit_currency,
            limit=1,
            tenant_id=owner.tenant_id,
        )
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(_extract_remote_error(payload))
    if not isinstance(payload, dict):
        raise RuntimeError("invalid remote wallet response")
    return _smallest_to_credit(payload.get("balance") or 0)


async def _sync_local_wallet_from_remote(
    db: AsyncSession,
    user: User | None,
    wallet: Wallet,
    principal_type: str = "user",
    principal_id: str | None = None,
    tenant_id: str | None = None,
) -> Decimal | None:
    owner = _remote_wallet_owner(user, principal_type, principal_id, tenant_id)
    if owner is None:
        return None
    remote_balance = await _fetch_remote_credit_balance(owner)
    wallet.balance_credits = remote_balance
    wallet.updated_at = utc_now()
    return remote_balance


async def _adjust_remote_credit(owner: RemoteWalletOwner, delta: Decimal, reference: str) -> None:
    if delta == 0:
        return

    amount_smallest = abs(_credit_to_smallest(delta))
    if amount_smallest == 0:
        return

    operation = "increase" if delta > 0 else "decrease"
    client = BasaltPassClient()
    if owner.owner_type == "user":
        payload = await client.s2s_adjust_user_wallet(
            user_id=owner.owner_id,
            currency=settings.basalt_credit_currency,
            operation=operation,
            amount=amount_smallest,
            reference=reference,
            tenant_id=owner.tenant_id,
        )
    else:
        payload = await client.s2s_adjust_owner_wallet(
            owner_type=owner.owner_type,
            owner_id=owner.owner_id,
            currency=settings.basalt_credit_currency,
            operation=operation,
            amount=amount_smallest,
            reference=reference,
            tenant_id=owner.tenant_id,
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
    principal_type: str = "user",
    principal_id: str | None = None,
    tenant_id: str | None = None,
) -> UsageSession:
    estimated = billable_credits(estimated_cost)
    user = await db.get(User, user_id)
    wallet = await _get_local_wallet(db, user_id)

    normalized_principal_type = (principal_type or "user").strip().lower()
    if normalized_principal_type not in {"user", "app", "tenant", "team"}:
        raise ValueError("invalid_principal")
    effective_principal_id = (principal_id or "").strip() or (
        str(getattr(user, "basalt_user_id", "") or "").strip() if normalized_principal_type == "user" else ""
    ) or user_id
    effective_tenant_id = (tenant_id or str(getattr(user, "basalt_tenant_id", "") or "")).strip() or None
    remote_owner = _remote_wallet_owner(user, normalized_principal_type, effective_principal_id, effective_tenant_id)

    if remote_owner is not None:
        before_balance = await _sync_local_wallet_from_remote(
            db, user, wallet, normalized_principal_type, effective_principal_id, effective_tenant_id
        )
        if _as_decimal(before_balance) < estimated:
            raise ValueError("insufficient_balance")
        await _adjust_remote_credit(remote_owner, -estimated, f"apicred:usage_pending:{request_id}")
        await _sync_local_wallet_from_remote(
            db, user, wallet, normalized_principal_type, effective_principal_id, effective_tenant_id
        )
    else:
        result = await db.execute(
            update(Wallet)
            .where(Wallet.user_id == user_id)
            .where(Wallet.balance_credits >= estimated)
            .values(balance_credits=Wallet.balance_credits - estimated, updated_at=utc_now())
        )
        if result.rowcount == 0:
            raise ValueError("insufficient_balance")

    usage_id = str(uuid6.uuid7())
    usage = UsageSession(
        id=usage_id,
        user_id=user_id,
        principal_type=normalized_principal_type,
        principal_id=effective_principal_id,
        tenant_id=effective_tenant_id,
        app_id=effective_principal_id if normalized_principal_type == "app" else None,
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
        principal_type=normalized_principal_type,
        principal_id=effective_principal_id,
        tenant_id=effective_tenant_id,
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
    await reserve_quota_ledger_for_usage(
        db,
        usage_session_id=usage.id,
        request_id=request_id,
        user_id=user_id,
        token_id=token_id,
        public_model_id=model_id,
        public_model_name=model_name,
        estimated_cost_credits=float(estimated),
        metadata_json=meta,
    )
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

    principal_type = str(getattr(usage, "principal_type", "user") or "user")
    principal_id = str(getattr(usage, "principal_id", "") or "").strip() or None
    tenant_id = str(getattr(usage, "tenant_id", "") or "").strip() or None
    remote_owner = _remote_wallet_owner(user, principal_type, principal_id, tenant_id)

    final = billable_credits(final_cost)
    estimated = Decimal(str(usage.estimated_cost_credits))
    diff = final - estimated

    if remote_owner is not None:
        await _sync_local_wallet_from_remote(db, user, wallet, principal_type, principal_id, tenant_id)

    if diff != 0:
        if remote_owner is not None:
            await _adjust_remote_credit(remote_owner, -diff, f"apicred:usage_settle:{usage.id}")
        adjustment = LedgerEntry(
            user_id=usage.user_id,
            principal_type=principal_type,
            principal_id=principal_id,
            tenant_id=tenant_id,
            entry_type="adjustment",
            amount_credits=-diff,
            status="settled",
            ref_type="usage_session",
            ref_id=usage.id,
            meta={"reason": "settle_adjust"},
        )
        if remote_owner is not None:
            await _sync_local_wallet_from_remote(db, user, wallet, principal_type, principal_id, tenant_id)
        else:
            await db.execute(
                update(Wallet)
                .where(Wallet.user_id == usage.user_id)
                .values(balance_credits=Wallet.balance_credits - diff, updated_at=utc_now())
            )
        db.add(adjustment)
    elif remote_owner is not None:
        await _sync_local_wallet_from_remote(db, user, wallet, principal_type, principal_id, tenant_id)

    usage.final_cost_credits = final
    usage.prompt_tokens = int((usage_meta or {}).get("prompt_tokens", 0) or 0)
    usage.completion_tokens = int((usage_meta or {}).get("completion_tokens", 0) or 0)
    usage.total_tokens = int((usage_meta or {}).get("total_tokens", 0) or 0)
    usage.latency_ms = int((usage_meta or {}).get("latency_ms", 0) or 0) or None
    usage.upstream_latency_ms = int((usage_meta or {}).get("upstream_latency_ms", 0) or 0) or None
    usage.error_code = str((usage_meta or {}).get("error_code") or "").strip() or None
    usage.error_message = str((usage_meta or {}).get("error_message") or "").strip()[:1000] or None
    usage.response_text = response_text
    usage.usage = usage_meta
    usage.status = "completed"
    usage.completed_at = utc_now()
    await db.commit()
    await settle_quota_ledger(
        db,
        request_id=usage.request_id,
        status="settled",
        final_cost_credits=float(final),
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        metadata_patch={"usage": usage_meta or {}},
    )

    # ── Synavis Core 镜像（Phase 1：火后不管，不阻塞主流程） ──────────────────────
    # 将实际 token 消耗折算为 unit_price=1 的 microcredit 形式，方便引擎记账
    # total_tokens 为 0 时退化为按 final_cost 换算
    _units = usage.total_tokens or 0
    _tenant_id = str(getattr(usage, "tenant_id", "") or "default")
    if _units > 0:
        # 每 token 单价（微credit），向上取整防止 0
        _unit_price = max(1, int(float(final) * 1_000_000 / _units))
    else:
        # 无 token 信息时，把总费用作为 1 个单元上报
        _units = 1
        _unit_price = max(1, int(float(final) * 1_000_000))
    try:
        await _synavis.notify_usage_completed(
            user_id=usage.user_id,
            tenant_id=_tenant_id,
            resource_type=f"llm_tokens:{usage.model_id or 'unknown'}",
            usage_units=_units,
            unit_price_microcredits=_unit_price,
            request_id=usage.request_id,
        )
    except Exception:  # noqa: BLE001
        pass  # 引擎事件镜像永远不影响主业务
    # ─────────────────────────────────────────────────────────────────────────────
