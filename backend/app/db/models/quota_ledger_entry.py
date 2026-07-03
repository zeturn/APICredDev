import uuid

from sqlalchemy import DateTime, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class QuotaLedgerEntry(Base):
    __tablename__ = "quota_ledger_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    usage_session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    request_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    token_id: Mapped[str] = mapped_column(String, index=True)
    public_model_id: Mapped[str] = mapped_column(String, index=True)
    public_model_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    upstream_model: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    provider_credential_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    quota_unit: Mapped[str] = mapped_column(String, default="tokens")
    reserved_delta: Mapped[int] = mapped_column(Integer, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_credits: Mapped[float] = mapped_column(Numeric(20, 6), default=0)
    final_cost_credits: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    status: Mapped[str] = mapped_column(String, index=True, default="reserved")
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    settled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
