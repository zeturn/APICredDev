import uuid

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ProviderBenchmarkRun(Base):
    __tablename__ = "provider_benchmark_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    dry_run: Mapped[bool] = mapped_column(default=True)
    public_model: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    runs: Mapped[int] = mapped_column(Integer, default=1)
    prompt: Mapped[str | None] = mapped_column(String, nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
