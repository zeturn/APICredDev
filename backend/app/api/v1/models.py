from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.db.models.model import Model
from app.schemas.models import ModelItem


router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelItem])
async def list_models(db: AsyncSession = Depends(get_db)) -> list[ModelItem]:
    result = await db.execute(select(Model).where(Model.enabled.is_(True)))
    models = result.scalars().all()
    return [
        ModelItem(
            id=m.id,
            name=m.name,
            category=m.category,
            enabled=m.enabled,
            multiplier=float(m.multiplier),
            pricing=m.pricing or {},
        )
        for m in models
    ]

