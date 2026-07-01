import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class UpstreamModel(Base):
    __tablename__ = "upstream_models"
    __table_args__ = (UniqueConstraint("provider_id", "upstream_name", name="uq_upstream_model_provider_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(String, ForeignKey("providers.id"), index=True)
    upstream_name: Mapped[str] = mapped_column(String, index=True)
    display_name: Mapped[str] = mapped_column(String)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    default_pricing: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
