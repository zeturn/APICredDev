import hashlib
import uuid

import pytest

from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.db.models.recharge_code import RechargeCode
from app.services.billing_service import redeem_code, get_wallet


@pytest.mark.asyncio
async def test_redeem_idempotent(db_session):
    user_id = str(uuid.uuid4())
    user = User(id=user_id, email="c@d.com", password_hash="x")
    wallet = Wallet(user_id=user_id, balance_credits=0)
    code_hash = hashlib.sha256(b"CODE123").hexdigest()
    code = RechargeCode(code_hash=code_hash, amount_credits=50)
    db_session.add(user)
    db_session.add(wallet)
    db_session.add(code)
    await db_session.commit()

    wallet_obj = await redeem_code(db_session, user_id, code_hash)
    assert float(wallet_obj.balance_credits) == 50
    with pytest.raises(ValueError):
        await redeem_code(db_session, user_id, code_hash)

