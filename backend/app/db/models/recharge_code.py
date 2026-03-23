import uuid
from sqlalchemy import String, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class RechargeCode(Base):
    __tablename__ = "recharge_codes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    amount_credits: Mapped[float] = mapped_column(Numeric(20, 6))
    status: Mapped[str] = mapped_column(String, default="unused")
    used_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    used_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

