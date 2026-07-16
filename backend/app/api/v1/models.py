from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_bearer_token, get_current_user, get_db, permission, require_scopes
from app.core.errors import AppError
from app.db.models.public_model import PublicModel
from app.schemas.models import ModelItem
from app.services.basaltpass_client import BasaltPassClient


router = APIRouter(prefix="/models", tags=["models"])
_require_user_console = permission("user_console")


async def require_models_access(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    client: BasaltPassClient = Depends(BasaltPassClient),
) -> None:
    if authorization and authorization.startswith("Bearer "):
        try:
            token = await get_bearer_token(request=request, authorization=authorization, db=db)
            await require_scopes(["llm"], token, request)
            return
        except AppError as exc:
            if exc.code not in {"token_invalid", "token_missing"}:
                raise
    current_user = await get_current_user(request=request, authorization=authorization, db=db)
    await _require_user_console(request=request, current_user=current_user, client=client)


@router.get("", response_model=list[ModelItem])
async def list_models(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_models_access),
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

