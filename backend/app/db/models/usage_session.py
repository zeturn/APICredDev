import uuid
from sqlalchemy import String, DateTime, JSON, Numeric, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class UsageSession(Base):
    __tablename__ = "usage_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    token_id: Mapped[str] = mapped_column(String, index=True)
    request_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    model_id: Mapped[str] = mapped_column(String, index=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="started")
    estimated_cost_credits: Mapped[float] = mapped_column(Numeric(20, 6), default=0)
    final_cost_credits: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    upstream_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    upstream_key_id: Mapped[str | None] = mapped_column(String, nullable=True)
    request_messages: Mapped[list[dict]] = mapped_column(JSON, default=list)
    request_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

