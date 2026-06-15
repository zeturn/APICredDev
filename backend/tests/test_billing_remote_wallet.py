from __future__ import annotations

import hashlib
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.models.ledger import LedgerEntry
from app.db.models.recharge_code import RechargeCode
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.services.billing_service import authorize_usage, get_wallet, redeem_code, settle_usage


class _RemoteWalletClient:
    balance = 0
    wallet_calls: list[dict] = []
    adjust_calls: list[dict] = []

    @classmethod
    def reset(cls, *, balance: int) -> None:
        cls.balance = balance
        cls.wallet_calls = []
        cls.adjust_calls = []

    async def s2s_get_user_wallet(self, user_id: str, currency: str, limit: int = 1, tenant_id: str | None = None):
        type(self).wallet_calls.append(
            {
                "user_id": user_id,
                "currency": currency,
                "limit": limit,
                "tenant_id": tenant_id,
            }
        )
        return {"balance": type(self).balance}

    async def s2s_adjust_user_wallet(
        self,
        user_id: str,
        currency: str,
        operation: str,
        amount: int,
        reference: str,
        tenant_id: str | None = None,
    ):
        type(self).adjust_calls.append(
            {
                "user_id": user_id,
                "currency": currency,
                "operation": operation,
                "amount": amount,
                "reference": reference,
                "tenant_id": tenant_id,
            }
        )
        if operation == "decrease" and type(self).balance < amount:
            return {"error": {"message": "insufficient balance"}}
        if operation == "decrease":
            type(self).balance -= amount
        else:
            type(self).balance += amount
        return {"ok": True}


def _enable_remote_wallet(monkeypatch, *, balance: int) -> None:
    _RemoteWalletClient.reset(balance=balance)
    monkeypatch.setattr(settings, "basalt_s2s_client_id", "s2s-id")
    monkeypatch.setattr(settings, "basalt_s2s_client_secret", "s2s-secret")
    monkeypatch.setattr(settings, "basalt_credit_currency", "CREDIT")
    monkeypatch.setattr(settings, "basalt_credit_scale", 1_000_000)
    monkeypatch.setattr("app.services.billing_service.BasaltPassClient", _RemoteWalletClient)


async def _remote_user(db_session, *, email: str = "remote-wallet@example.com") -> User:
    user = User(
        email=email,
        password_hash="x",
        basalt_user_id="basalt-u-1",
        basalt_tenant_id="tenant-1",
    )
    db_session.add(user)
    await db_session.commit()
    db_session.add(Wallet(user_id=user.id, balance_credits=0))
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_get_wallet_syncs_remote_balance_once(db_session, monkeypatch):
    _enable_remote_wallet(monkeypatch, balance=12_500_000)
    user = await _remote_user(db_session)

    wallet = await get_wallet(db_session, user.id)

    assert wallet.balance_credits == Decimal("12.5")
    assert _RemoteWalletClient.wallet_calls == [
        {
            "user_id": "basalt-u-1",
            "currency": "CREDIT",
            "limit": 1,
            "tenant_id": "tenant-1",
        }
    ]


@pytest.mark.asyncio
async def test_authorize_and_settle_usage_adjust_remote_wallet(db_session, monkeypatch):
    _enable_remote_wallet(monkeypatch, balance=20_000_000)
    user = await _remote_user(db_session, email="remote-usage@example.com")

    usage = await authorize_usage(
        db_session,
        user_id=user.id,
        token_id="token-1",
        request_id="request-1",
        model_id="model-1",
        estimated_cost=Decimal("3.5"),
        meta={"model": "m"},
    )
    wallet_after_auth = await db_session.get(Wallet, user.id)

    assert wallet_after_auth.balance_credits == Decimal("16.5")
    assert _RemoteWalletClient.adjust_calls[0]["operation"] == "decrease"
    assert _RemoteWalletClient.adjust_calls[0]["amount"] == 3_500_000
    assert _RemoteWalletClient.adjust_calls[0]["reference"] == "apicred:usage_pending:request-1"

    await settle_usage(db_session, usage, Decimal("2.25"), {"total_tokens": 10})
    wallet_after_settle = await db_session.get(Wallet, user.id)

    assert wallet_after_settle.balance_credits == Decimal("17.75")
    assert _RemoteWalletClient.adjust_calls[1]["operation"] == "increase"
    assert _RemoteWalletClient.adjust_calls[1]["amount"] == 1_250_000
    assert _RemoteWalletClient.adjust_calls[1]["reference"] == f"apicred:usage_settle:{usage.id}"

    ledger_rows = list((await db_session.execute(select(LedgerEntry).where(LedgerEntry.user_id == user.id))).scalars())
    assert [row.entry_type for row in ledger_rows] == ["pending_debit", "adjustment"]


@pytest.mark.asyncio
async def test_authorize_usage_rejects_insufficient_remote_balance(db_session, monkeypatch):
    _enable_remote_wallet(monkeypatch, balance=2_000_000)
    user = await _remote_user(db_session, email="remote-insufficient@example.com")

    with pytest.raises(ValueError, match="insufficient_balance"):
        await authorize_usage(
            db_session,
            user_id=user.id,
            token_id="token-1",
            request_id="request-2",
            model_id="model-1",
            estimated_cost=Decimal("2.01"),
            meta={},
        )

    assert _RemoteWalletClient.adjust_calls == []


@pytest.mark.asyncio
async def test_redeem_code_increases_remote_wallet_and_marks_code_used(db_session, monkeypatch):
    _enable_remote_wallet(monkeypatch, balance=1_000_000)
    user = await _remote_user(db_session, email="remote-redeem@example.com")
    code_hash = hashlib.sha256(b"REMOTE-CODE").hexdigest()
    code = RechargeCode(code_hash=code_hash, amount_credits=Decimal("4.25"))
    db_session.add(code)
    await db_session.commit()

    wallet = await redeem_code(db_session, user.id, code_hash)

    assert wallet.balance_credits == Decimal("5.25")
    assert _RemoteWalletClient.adjust_calls == [
        {
            "user_id": "basalt-u-1",
            "currency": "CREDIT",
            "operation": "increase",
            "amount": 4_250_000,
            "reference": f"apicred:recharge_code:{code.id}",
            "tenant_id": "tenant-1",
        }
    ]

    used_code = await db_session.get(RechargeCode, code.id)
    assert used_code.status == "used"
    assert used_code.used_by_user_id == user.id
