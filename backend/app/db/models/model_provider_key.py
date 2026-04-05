import uuid
from sqlalchemy import String, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ModelProviderKey(Base):
    __tablename__ = "model_provider_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id: Mapped[str] = mapped_column(String, ForeignKey("models.id"), index=True)
    provider_key_id: Mapped[str] = mapped_column(String, ForeignKey("provider_keys.id"), index=True)
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    quota_unit: Mapped[str] = mapped_column(String, default="requests")
    quota_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

