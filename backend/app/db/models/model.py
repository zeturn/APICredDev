import uuid
from sqlalchemy import String, DateTime, Numeric, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class Model(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    category: Mapped[str] = mapped_column(String, default="llm")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    multiplier: Mapped[float] = mapped_column(Numeric(20, 6), default=1)
    pricing: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

