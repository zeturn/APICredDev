import uuid6

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class PublicModel(Base):
    __tablename__ = "public_models"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid6.uuid7()))
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    brand_id: Mapped[str | None] = mapped_column(String, ForeignKey("brands.id"), index=True, nullable=True)
    category: Mapped[str] = mapped_column(String, default="llm")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    pricing: Mapped[dict] = mapped_column(JSON, default=dict)
    multiplier: Mapped[float] = mapped_column(Numeric(20, 6), default=1)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
