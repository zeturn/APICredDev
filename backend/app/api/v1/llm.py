import logging
import os

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from fastapi import Request

from app.core.deps import get_db, get_bearer_token, require_scopes
from app.core.errors import AppError
from app.core.time import utc_now
from app.db.models.model import Model
from app.db.models.provider_key import ProviderKey
from app.schemas.llm import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChoice, ChatCompletionUsage, ChatMessage
from app.services.billing_service import authorize_usage, settle_usage
from app.services.providers.openai_compat import OpenAICompatAdapter
from app.services.routing_service import get_candidates
from app.services.usage_service import estimate_tokens, calculate_cost
from app.services.quota_service import try_reserve
from app.redis.client import get_redis
from app.core.config import settings


router = APIRouter(prefix="", tags=["llm"])
logger = logging.getLogger("apicred.llm")


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: Request,
    payload: ChatCompletionRequest,
    db: AsyncSession = Depends(get_db),
    api_token=Depends(get_bearer_token),
) -> ChatCompletionResponse:
    request_id = request.state.request_id
    await require_scopes(["llm"], api_token, request)
    result = await db.execute(select(Model).where(Model.name == payload.model))
    model = result.scalar_one_or_none()
    if not model or not model.enabled:
        raise AppError("model_not_found", "model not available", request_id, 404)

    est_tokens = estimate_tokens([m.model_dump() for m in payload.messages], payload.max_tokens)
    estimated_cost = calculate_cost(model, est_tokens)
    try:
        usage_session = await authorize_usage(
            db,
            user_id=api_token.user_id,
            token_id=api_token.id,
            request_id=str(request_id),
            model_id=model.id,
            estimated_cost=estimated_cost,
            meta={"model": model.name, "request_id": str(request_id)},
        )
    except ValueError:
        raise AppError("insufficient_balance", "insufficient balance", request_id, 402)

    candidates = await get_candidates(db, model.id)
    if not candidates:
        await settle_usage(db, usage_session, 0, {"error": "no_candidates"})
        raise AppError("no_upstream_capacity", "no available upstream keys", request_id, 503)

    adapter = OpenAICompatAdapter()
    redis = get_redis()
    try:
        attempts = 0
        for candidate in candidates:
            attempts += 1
            if attempts > settings.max_key_attempts:
                break
            delta = 1 if candidate.mpk.quota_unit == "requests" else est_tokens
            ok = await try_reserve(redis, candidate.provider_key.id, model.id, delta, candidate.mpk.quota_rules or {})
            if not ok:
                continue
            api_key = os.getenv(candidate.provider_key.secret_ref, "")
            base_url = candidate.provider_key.key_name
            try:
                logger.info(
                    "llm_request request_id=%s user_id=%s model=%s provider_key_id=%s",
                    request_id,
                    api_token.user_id,
                    model.name,
                    candidate.provider_key.id,
                )
                raw, usage = await adapter.chat_completions(payload.model_dump(), api_key, base_url)
                usage_session.upstream_provider = candidate.provider_key.provider
                usage_session.upstream_key_id = candidate.provider_key.id
                total_tokens = int(usage.get("total_tokens", 0))
                final_cost = calculate_cost(model, total_tokens, request_count=1)
                await settle_usage(db, usage_session, final_cost, usage)
                choices = [
                    ChatCompletionChoice(
                        index=i,
                        message=ChatMessage(role=c["message"]["role"], content=c["message"]["content"]),
                        finish_reason=c.get("finish_reason"),
                    )
                    for i, c in enumerate(raw.get("choices", []))
                ]
                return ChatCompletionResponse(
                    id=raw.get("id", str(request_id)),
                    choices=choices,
                    usage=ChatCompletionUsage(**usage),
                )
            except httpx.HTTPStatusError as exc:
                info = adapter.normalize_error(exc)
                await _apply_cooldown(db, candidate.provider_key, info)
                if not info.get("retryable"):
                    break
            except Exception as exc:
                info = adapter.normalize_error(exc)
                await _apply_cooldown(db, candidate.provider_key, info)
        await settle_usage(db, usage_session, 0, {"error": "upstream_failed"})
        raise AppError("upstream_failed", "upstream error", request_id, 502)
    finally:
        await redis.aclose()


async def _apply_cooldown(db: AsyncSession, provider_key: ProviderKey, info: dict) -> None:
    cooldown = int(info.get("cooldown_seconds", 60))
    if info.get("code") == "auth_failed":
        provider_key.health_state = "disabled"
    provider_key.cooldown_until = utc_now() if cooldown <= 0 else utc_now() + __import__("datetime").timedelta(seconds=cooldown)
    await db.commit()

