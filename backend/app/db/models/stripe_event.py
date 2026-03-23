from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String)
    processed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

