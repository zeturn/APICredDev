from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

is_sqlite = settings.database_url.startswith("sqlite")

engine_kwargs: dict[str, Any] = {
    "future": True,
    "echo": False,
}

if not is_sqlite:
    engine_kwargs.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_recycle": settings.db_pool_recycle,
            "pool_timeout": settings.db_pool_timeout,
            "pool_pre_ping": settings.db_pool_pre_ping,
        }
    )

engine = create_async_engine(settings.database_url, **engine_kwargs)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
