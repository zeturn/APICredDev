import uuid6

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"
    __table_args__ = (UniqueConstraint("provider_endpoint_id", "display_name", name="uq_provider_credential_display_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid6.uuid7()))
    provider_endpoint_id: Mapped[str] = mapped_column(String, ForeignKey("provider_endpoints.id"), index=True)
    display_name: Mapped[str] = mapped_column(String)
    secret_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    secret_last4: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    health_state: Mapped[str] = mapped_column(String, default="healthy")
    cooldown_until: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
