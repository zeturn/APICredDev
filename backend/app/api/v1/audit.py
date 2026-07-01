from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, permission
from app.core.errors import AppError
from app.services.audit_service import list_user_audit_conversations, soft_delete_user_conversation


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/conversations")
async def user_audit_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("user_console")),
) -> dict:
    return await list_user_audit_conversations(db, user.id, page=page, page_size=page_size)


@router.delete("/conversations/{usage_session_id}")
async def user_audit_conversation_delete(
    usage_session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("user_console")),
) -> dict:
    deleted = await soft_delete_user_conversation(db, user.id, usage_session_id)
    if deleted == 0:
        raise AppError("audit_conversation_not_found", "conversation not found", request.state.request_id, 404)
    return {"ok": True, "deleted_messages": deleted}
