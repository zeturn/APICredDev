import hashlib

from sqlalchemy import func, select
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user, permission
from app.core.errors import AppError
from app.db.models.model import Model
from app.db.models.usage_session import UsageSession
from app.schemas.billing import WalletResponse, LedgerItem, RedeemRequest, RedeemResponse
from app.services.billing_service import get_wallet, list_ledger, redeem_code
from app.services.dashboard_service import get_user_usage_summary


router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/wallet", response_model=WalletResponse)
async def wallet(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("read")),
) -> WalletResponse:
    wallet_obj = await get_wallet(db, user.id)
    return WalletResponse(balance_credits=float(wallet_obj.balance_credits), updated_at=wallet_obj.updated_at.isoformat())


@router.get("/summary")
async def billing_summary(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("read")),
) -> dict:
    wallet_obj = await get_wallet(db, user.id)
    used_credits = float(
        (await db.execute(select(func.coalesce(func.sum(UsageSession.final_cost_credits), 0)).where(UsageSession.user_id == user.id))).scalar() or 0
    )
    usage_sessions = int((await db.execute(select(func.count()).select_from(UsageSession).where(UsageSession.user_id == user.id))).scalar() or 0)
    available_models = int((await db.execute(select(func.count()).select_from(Model).where(Model.enabled.is_(True)))).scalar() or 0)
    return {
        "balance_credits": float(wallet_obj.balance_credits),
        "used_credits": used_credits,
        "usage_sessions": usage_sessions,
        "available_models": available_models,
        "updated_at": wallet_obj.updated_at.isoformat(),
    }


@router.get("/ledger", response_model=list[LedgerItem])
async def ledger(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("read")),
) -> list[LedgerItem]:
    entries = await list_ledger(db, user.id, limit=50)
    return [
        LedgerItem(
            id=e.id,
            entry_type=e.entry_type,
            amount_credits=float(e.amount_credits),
            status=e.status,
            ref_type=e.ref_type,
            ref_id=e.ref_id,
            meta=e.meta or {},
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.get("/usage")
async def usage(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("read")),
) -> dict:
    return await get_user_usage_summary(db, user.id)


@router.post("/redeem", response_model=RedeemResponse)
async def redeem(
    payload: RedeemRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _: None = Depends(permission("write")),
) -> RedeemResponse:
    request_id = request.state.request_id
    code_hash = hashlib.sha256(payload.code.encode("utf-8")).hexdigest()
    try:
        wallet_obj = await redeem_code(db, user.id, code_hash)
    except ValueError:
        raise AppError("invalid_code", "invalid or used code", request_id, 400)
    return RedeemResponse(balance_credits=float(wallet_obj.balance_credits))

