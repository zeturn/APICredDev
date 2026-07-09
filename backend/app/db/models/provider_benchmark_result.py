import uuid6

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ProviderBenchmarkResult(Base):
    __tablename__ = "provider_benchmark_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid6.uuid7()))
    run_id: Mapped[str] = mapped_column(String, index=True)
    provider: Mapped[str] = mapped_column(String, index=True)
    credential_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    upstream_model: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    success_rate: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    avg_latency_ms: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    p95_latency_ms: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    error_rate: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Numeric(20, 6), default=0)
    health_state_before: Mapped[str | None] = mapped_column(String, nullable=True)
    health_state_after: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
