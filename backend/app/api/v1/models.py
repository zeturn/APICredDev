from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, permission
from app.db.models.public_model import PublicModel
from app.schemas.models import ModelItem


router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelItem])
async def list_models(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(permission("user_console")),
) -> list[ModelItem]:
    result = await db.execute(select(PublicModel).where(PublicModel.enabled.is_(True)).order_by(PublicModel.slug.asc()))
    rows = result.scalars().all()
    return [
        ModelItem(
            id=model.id,
            name=model.slug,
            display_name=model.display_name,
            category=model.category,
            enabled=model.enabled,
            multiplier=float(model.multiplier or 1),
            pricing=model.pricing or {},
        )
        for model in rows
    ]

