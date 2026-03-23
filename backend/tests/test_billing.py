import uuid

import pytest

from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.services.billing_service import authorize_usage, settle_usage, get_wallet


@pytest.mark.asyncio
async def test_billing_idempotent_settle(db_session):
    user_id = str(uuid.uuid4())
    user = User(id=user_id, email="a@b.com", password_hash="x")
    wallet = Wallet(user_id=user_id, balance_credits=100)
    db_session.add(user)
    db_session.add(wallet)
    await db_session.commit()

    usage = await authorize_usage(
        db_session,
        user_id=user.id,
        token_id="t1",
        request_id="r1",
        model_id="m1",
        estimated_cost=10,
        meta={},
    )
    await settle_usage(db_session, usage, 8, {"total_tokens": 10})
    await settle_usage(db_session, usage, 8, {"total_tokens": 10})
    wallet_obj = await get_wallet(db_session, user.id)
    assert float(wallet_obj.balance_credits) == 92

