import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"
    __table_args__ = (UniqueConstraint("provider_id", "name", name="uq_provider_credential_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(String, ForeignKey("providers.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    secret_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    secret_last4: Mapped[str | None] = mapped_column(String, nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    health_state: Mapped[str] = mapped_column(String, default="healthy")
    cooldown_until: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
