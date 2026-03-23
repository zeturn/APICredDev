import hashlib

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.errors import AppError
from app.schemas.billing import WalletResponse, LedgerItem, RedeemRequest, RedeemResponse
from app.services.billing_service import get_wallet, list_ledger, redeem_code


router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/wallet", response_model=WalletResponse)
async def wallet(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> WalletResponse:
    wallet_obj = await get_wallet(db, user.id)
    return WalletResponse(balance_credits=float(wallet_obj.balance_credits), updated_at=wallet_obj.updated_at.isoformat())


@router.get("/ledger", response_model=list[LedgerItem])
async def ledger(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> list[LedgerItem]:
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


@router.post("/redeem", response_model=RedeemResponse)
async def redeem(payload: RedeemRequest, request: Request, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> RedeemResponse:
    request_id = request.state.request_id
    code_hash = hashlib.sha256(payload.code.encode("utf-8")).hexdigest()
    try:
        wallet_obj = await redeem_code(db, user.id, code_hash)
    except ValueError:
        raise AppError("invalid_code", "invalid or used code", request_id, 400)
    return RedeemResponse(balance_credits=float(wallet_obj.balance_credits))

