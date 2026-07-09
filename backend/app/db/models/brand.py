import uuid6

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid6.uuid7()))
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    icon_slug: Mapped[str | None] = mapped_column(String, nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
