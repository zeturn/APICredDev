import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ProviderEndpoint(Base):
    __tablename__ = "provider_endpoints"
    __table_args__ = (UniqueConstraint("provider_id", "name", name="uq_provider_endpoint_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(String, ForeignKey("providers.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    base_url: Mapped[str] = mapped_column(String)
    endpoint_type: Mapped[str] = mapped_column(String, default="openai_compatible")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    health_state: Mapped[str] = mapped_column(String, default="healthy")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
