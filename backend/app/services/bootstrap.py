import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User
from app.db.models.wallet import Wallet


logger = logging.getLogger(__name__)


async def ensure_admin_user(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.email == settings.admin_email))
    user = result.scalar_one_or_none()
    if user:
        return

    admin_id = str(uuid.uuid4())
    admin = User(id=admin_id, email=settings.admin_email, password_hash=hash_password(settings.admin_password))
    wallet = Wallet(user_id=admin_id, balance_credits=0)
    db.add(admin)
    db.add(wallet)
    await db.commit()
    logger.info("Default admin user created: %s", settings.admin_email)
