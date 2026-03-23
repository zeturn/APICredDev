import uuid

import pytest

from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.services.billing_service import record_stripe_event, get_wallet


@pytest.mark.asyncio
async def test_stripe_idempotent(db_session):
    user_id = str(uuid.uuid4())
    user = User(id=user_id, email="e@f.com", password_hash="x")
    wallet = Wallet(user_id=user_id, balance_credits=0)
    db_session.add(user)
    db_session.add(wallet)
    await db_session.commit()

    await record_stripe_event(db_session, "evt_1", "checkout.session.completed", user_id, 100, {})
    await record_stripe_event(db_session, "evt_1", "checkout.session.completed", user_id, 100, {})
    wallet_obj = await get_wallet(db_session, user.id)
    assert float(wallet_obj.balance_credits) == 100

