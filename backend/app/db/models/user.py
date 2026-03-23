import uuid
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    basalt_user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    basalt_tenant_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

