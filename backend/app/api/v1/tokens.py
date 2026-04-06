from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user, permission
from app.core.errors import AppError
from app.schemas.tokens import TokenCreateRequest, TokenCreateResponse, TokenListItem
from app.services.token_service import create_token, list_tokens, revoke_token


router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.post("", response_model=TokenCreateResponse)
async def create(
    payload: TokenCreateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("user_console")),
) -> TokenCreateResponse:
    token, raw = await create_token(db, user.id, payload.name, payload.scopes)
    return TokenCreateResponse(id=token.id, name=token.name, token=raw, scopes=token.scopes)


@router.get("", response_model=list[TokenListItem])
async def list_all(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("user_console")),
) -> list[TokenListItem]:
    tokens = await list_tokens(db, user.id)
    return [
        TokenListItem(
            id=t.id,
            name=t.name,
            scopes=t.scopes or [],
            status=t.status,
            created_at=t.created_at.isoformat(),
            last_used_at=t.last_used_at.isoformat() if t.last_used_at else None,
        )
        for t in tokens
    ]


@router.delete("/{token_id}")
async def delete(
    token_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("user_console")),
) -> dict:
    request_id = request.state.request_id
    try:
        await revoke_token(db, user.id, token_id)
    except ValueError:
        raise AppError("not_found", "token not found", request_id, 404)
    return {"ok": True}

