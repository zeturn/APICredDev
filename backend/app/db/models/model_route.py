import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ModelRoute(Base):
    __tablename__ = "model_routes"
    __table_args__ = (
        UniqueConstraint(
            "public_model_id",
            "upstream_model_id",
            "provider_credential_id",
            name="uq_model_route_target",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    public_model_id: Mapped[str] = mapped_column(String, ForeignKey("public_models.id"), index=True)
    upstream_model_id: Mapped[str] = mapped_column(String, ForeignKey("upstream_models.id"), index=True)
    provider_credential_id: Mapped[str | None] = mapped_column(String, ForeignKey("provider_credentials.id"), index=True, nullable=True)
    base_url_override: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    quota_unit: Mapped[str] = mapped_column(String, default="tokens")
    quota_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
