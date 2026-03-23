from sqlalchemy import String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class Wallet(Base):
    __tablename__ = "wallets"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), primary_key=True)
    balance_credits: Mapped[float] = mapped_column(Numeric(20, 6), default=0)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

