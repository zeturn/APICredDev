from fastapi import APIRouter, Request

from app.core.errors import AppError


router = APIRouter(prefix="/billing/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
) -> dict:
    raise AppError("stripe_disabled", "stripe webhook is disabled; use BasaltPass financial flows", request.state.request_id, 410)

