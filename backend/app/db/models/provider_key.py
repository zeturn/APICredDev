import uuid
from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ProviderKey(Base):
    __tablename__ = "provider_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str | None] = mapped_column(String, ForeignKey("providers.id"), index=True, nullable=True)
    endpoint_id: Mapped[str | None] = mapped_column(String, ForeignKey("provider_endpoints.id"), index=True, nullable=True)
    provider: Mapped[str] = mapped_column(String)
    # Backward-compatible legacy field. Prefer display_name for the human label and
    # provider_endpoints.base_url for endpoint routing.
    key_name: Mapped[str] = mapped_column(String)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    secret_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    secret_last4: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    health_state: Mapped[str] = mapped_column(String, default="healthy")
    cooldown_until: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
