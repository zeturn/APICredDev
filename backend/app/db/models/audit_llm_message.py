import uuid6
from sqlalchemy import String, DateTime, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class AuditLLMMessage(Base):
    __tablename__ = "audit_llm_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid6.uuid7()))
    usage_session_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    request_id: Mapped[str] = mapped_column(String, index=True)
    model_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    upstream_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    upstream_credential_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    content_preview: Mapped[str | None] = mapped_column(String, nullable=True)
    redaction_applied: Mapped[bool] = mapped_column(default=False)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    message_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    retention_expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    user_deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
