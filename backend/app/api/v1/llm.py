import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from fastapi import Request
from fastapi.responses import StreamingResponse

from app.core.deps import get_db, get_bearer_token, require_scopes, token_permission
from app.core.errors import AppError
from app.core.secrets import decrypt_secret
from app.core.time import utc_now
from app.db.models.model import Model
from app.db.models.provider import Provider
from app.db.models.provider_key import ProviderKey
from app.schemas.llm import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChoice, ChatCompletionUsage, ChatMessage
from app.services.billing_service import authorize_usage, settle_usage
from app.services.providers.base import ProviderStreamResult, stream_chunks_from_raw
from app.services.providers.factory import get_provider_adapter
from app.services.providers.presets import get_provider_default_base_url
from app.services.routing_service import get_candidates
from app.services.usage_service import estimate_prompt_tokens, estimate_tokens, calculate_cost
from app.services.quota_service import try_reserve
from app.redis.client import get_redis
from app.core.config import settings


router = APIRouter(prefix="", tags=["llm"])
logger = logging.getLogger("apicred.llm")


def _messages_to_records(messages: list[ChatMessage]) -> list[dict]:
    return [message.model_dump() for message in messages]


def _messages_to_text(messages: list[ChatMessage]) -> str:
    parts: list[str] = []
    for message in messages:
        content = (message.content or "").strip()
        if not content:
            continue
        parts.append(f"{message.role}: {content}")
    return "\n\n".join(parts)


def _extract_response_text(raw: dict | None) -> str | None:
    if not raw:
        return None
    texts: list[str] = []
    for choice in raw.get("choices", []):
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            texts.append(content.strip())
    if texts:
        return "\n\n".join(texts)
    return None


async def _resolve_base_url(db: AsyncSession, candidate) -> str | None:
    model_provider_base_url = getattr(candidate.mpk, "base_url", None)
    if model_provider_base_url:
        return model_provider_base_url
    provider_key_base_url = (candidate.provider_key.key_name or "").strip()
    if provider_key_base_url:
        return provider_key_base_url
    provider = None
    provider_id = getattr(candidate.provider_key, "provider_id", None)
    if provider_id:
        provider = await db.get(Provider, provider_id)
    provider_default_base_url = (getattr(provider, "default_base_url", None) or "").strip() if provider else ""
    if provider_default_base_url:
        return provider_default_base_url
    return get_provider_default_base_url(candidate.provider_key.provider)


def _resolve_api_key(candidate) -> str:
    encrypted_secret = getattr(candidate.provider_key, "secret_encrypted", None)
    if encrypted_secret:
        return decrypt_secret(encrypted_secret)
    return ""


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: Request,
    payload: ChatCompletionRequest,
    db: AsyncSession = Depends(get_db),
    api_token=Depends(get_bearer_token),
    _: None = Depends(token_permission("user_console")),
) -> ChatCompletionResponse:
    request_id = request.state.request_id
    await require_scopes(["llm"], api_token, request)
    payload_dict = payload.model_dump(exclude_none=True)
    result = await db.execute(select(Model).where(Model.name == payload.model))
    model = result.scalar_one_or_none()
    if not model or not model.enabled:
        raise AppError("model_not_found", "model not available", request_id, 404)

    prompt_estimate = estimate_prompt_tokens([m.model_dump() for m in payload.messages])
    est_tokens = estimate_tokens([m.model_dump() for m in payload.messages], payload.max_tokens)
    estimated_cost = calculate_cost(
        model,
        est_tokens,
        prompt_tokens=prompt_estimate,
        completion_tokens=payload.max_tokens or 0,
    )
    try:
        usage_session = await authorize_usage(
            db,
            user_id=api_token.user_id,
            token_id=api_token.id,
            request_id=str(request_id),
            model_id=model.id,
            model_name=model.name,
            estimated_cost=estimated_cost,
            meta={"model": model.name, "request_id": str(request_id)},
            request_messages=_messages_to_records(payload.messages),
            request_text=_messages_to_text(payload.messages),
        )
    except ValueError:
        raise AppError("insufficient_balance", "insufficient balance", request_id, 402)

    candidates = await get_candidates(db, model.id)
    if not candidates:
        await settle_usage(db, usage_session, 0, {"error": "no_candidates"})
        raise AppError("no_upstream_capacity", "no available upstream keys", request_id, 503)

    redis = get_redis()
    stream_response_started = False
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
            api_key = _resolve_api_key(candidate)
            base_url = await _resolve_base_url(db, candidate)
            adapter = get_provider_adapter(candidate.provider_key.provider)
            try:
                logger.info(
                    "llm_request request_id=%s user_id=%s model=%s provider=%s provider_key_id=%s",
                    request_id,
                    api_token.user_id,
                    model.name,
                    candidate.provider_key.provider,
                    candidate.provider_key.id,
                )
                usage_session.upstream_provider = candidate.provider_key.provider
                usage_session.upstream_key_id = candidate.provider_key.id
                if payload.stream:
                    stream_result = await adapter.stream_chat_completions(payload_dict, api_key, base_url)
                    stream_response_started = True
                    return StreamingResponse(
                        _proxy_stream_and_settle(
                            db=db,
                            redis=redis,
                            usage_session=usage_session,
                            model=model,
                            stream_result=stream_result,
                        ),
                        media_type="text/event-stream",
                    )
                raw, usage = await adapter.chat_completions(payload_dict, api_key, base_url)
                prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
                completion_tokens = int(usage.get("completion_tokens", 0) or 0)
                total_tokens = int(usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens))
                final_cost = calculate_cost(
                    model,
                    total_tokens,
                    request_count=1,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
                await settle_usage(db, usage_session, final_cost, usage, response_text=_extract_response_text(raw))
                choices = [
                    ChatCompletionChoice(
                        index=i,
                        message=ChatMessage(role=c["message"]["role"], content=c["message"]["content"]),
                        finish_reason=c.get("finish_reason"),
                    )
                    for i, c in enumerate(raw.get("choices", []))
                ]
                response = ChatCompletionResponse(
                    id=raw.get("id", str(request_id)),
                    choices=choices,
                    usage=ChatCompletionUsage(**usage),
                )
                return response
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
        if not stream_response_started:
            await redis.aclose()


async def _apply_cooldown(db: AsyncSession, provider_key: ProviderKey, info: dict) -> None:
    cooldown = int(info.get("cooldown_seconds", 60))
    if info.get("code") == "auth_failed":
        provider_key.health_state = "disabled"
    provider_key.cooldown_until = utc_now() if cooldown <= 0 else utc_now() + __import__("datetime").timedelta(seconds=cooldown)
    await db.commit()


async def _stream_chat_completion_chunks(raw: dict) -> AsyncIterator[str]:
    async for chunk in stream_chunks_from_raw(raw):
        yield chunk


async def _proxy_stream_and_settle(
    *,
    db: AsyncSession,
    redis,
    usage_session,
    model: Model,
    stream_result: ProviderStreamResult,
) -> AsyncIterator[str]:
    finalized = False
    settled = False
    raw = None
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    try:
        async for chunk in stream_result.iterator:
            yield chunk
        raw, usage = await stream_result.finalize()
        finalized = True
        prompt_tokens = int((usage or {}).get("prompt_tokens", 0) or 0)
        completion_tokens = int((usage or {}).get("completion_tokens", 0) or 0)
        total_tokens = int((usage or {}).get("total_tokens", 0) or (prompt_tokens + completion_tokens))
        final_cost = calculate_cost(
            model,
            total_tokens,
            request_count=1,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        await settle_usage(db, usage_session, final_cost, usage, response_text=_extract_response_text(raw))
        settled = True
    finally:
        if not finalized:
            try:
                raw, usage = await stream_result.finalize()
            except Exception:
                raw, usage = None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        if not settled:
            prompt_tokens = int((usage or {}).get("prompt_tokens", 0) or 0)
            completion_tokens = int((usage or {}).get("completion_tokens", 0) or 0)
            total_tokens = int((usage or {}).get("total_tokens", 0) or (prompt_tokens + completion_tokens))
            final_cost = calculate_cost(
                model,
                total_tokens,
                request_count=1,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            await settle_usage(
                db,
                usage_session,
                final_cost,
                usage or {"error": "stream_interrupted"},
                response_text=_extract_response_text(raw),
            )
        await redis.aclose()

