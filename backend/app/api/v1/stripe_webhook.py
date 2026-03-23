import json

import stripe
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.deps import get_db
from app.services.billing_service import record_stripe_event


router = APIRouter(prefix="/billing/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    request_id = request.state.request_id
    payload = await request.body()
    if not stripe_signature:
        raise AppError("stripe_signature_missing", "missing signature", request_id, 400)
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except Exception:
        raise AppError("stripe_signature_invalid", "invalid signature", request_id, 400)

    event_id = event.get("id")
    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})
    metadata = data_object.get("metadata", {}) if isinstance(data_object, dict) else {}
    user_id = metadata.get("user_id")
    amount_credits = float(metadata.get("amount_credits", settings.stripe_price_credits))
    if not user_id:
        raise AppError("stripe_missing_user", "missing user_id", request_id, 400)
    await record_stripe_event(db, event_id, event_type, user_id, amount_credits, {"raw": json.loads(payload or b"{}")})
    return {"ok": True}

