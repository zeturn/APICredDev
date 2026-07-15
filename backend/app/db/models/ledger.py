import uuid6
from sqlalchemy import String, DateTime, Numeric, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (UniqueConstraint("ref_type", "ref_id", "entry_type", name="uq_ledger_ref"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid6.uuid7()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    principal_type: Mapped[str] = mapped_column(String, default="user", index=True)
    principal_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    entry_type: Mapped[str] = mapped_column(String)
    amount_credits: Mapped[float] = mapped_column(Numeric(20, 6))
    status: Mapped[str] = mapped_column(String, default="pending")
    ref_type: Mapped[str] = mapped_column(String)
    ref_id: Mapped[str] = mapped_column(String)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

