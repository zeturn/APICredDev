from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, permission
from app.db.models.brand import Brand
from app.db.models.model import Model
from app.schemas.models import ModelItem


router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelItem])
async def list_models(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(permission("user_console")),
) -> list[ModelItem]:
    result = await db.execute(select(Model, Brand).outerjoin(Brand, Brand.id == Model.brand_id).where(Model.enabled.is_(True)))
    rows = result.all()
    return [
        ModelItem(
            id=m.id,
            name=m.name,
            brand_id=m.brand_id,
            brand_name=brand.name if brand else None,
            brand_icon_url=brand.icon_url if brand else None,
            icon_url=m.icon_url,
            effective_icon_url=m.icon_url or (brand.icon_url if brand else None),
            category=m.category,
            enabled=m.enabled,
            multiplier=float(m.multiplier),
            pricing=m.pricing or {},
        )
        for m, brand in rows
    ]

