import uuid

from sqlalchemy import Boolean, DateTime, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class AccessPolicy(Base):
    __tablename__ = "access_policies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scope_type: Mapped[str] = mapped_column(String, index=True)
    scope_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    allowed_public_models_json: Mapped[list] = mapped_column(JSON, default=list)
    blocked_public_models_json: Mapped[list] = mapped_column(JSON, default=list)
    allowed_providers_json: Mapped[list] = mapped_column(JSON, default=list)
    blocked_providers_json: Mapped[list] = mapped_column(JSON, default=list)
    max_requests_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_requests_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_tokens_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_cost_credits_per_day: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    max_cost_credits_per_month: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
