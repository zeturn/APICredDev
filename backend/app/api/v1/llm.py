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
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.public_model import PublicModel
from app.schemas.llm import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChoice, ChatCompletionUsage, ChatMessage
from app.services.billing_service import authorize_usage, settle_usage
from app.services.providers.base import ProviderStreamResult, stream_chunks_from_raw
from app.services.providers.factory import get_provider_adapter
from app.services.providers.presets import get_provider_default_base_url
from app.services.routing_service import ModelRouteCandidate, get_route_candidates
from app.services.usage_service import estimate_prompt_tokens, estimate_tokens, calculate_cost
from app.services.quota_service import try_reserve
from app.redis.client import get_redis
from app.core.config import settings
from app.core.url_safety import normalize_upstream_base_url


router = APIRouter(prefix="", tags=["llm"])
logger = logging.getLogger("apicred.llm")


PROVIDER_MODEL_ALIASES: dict[str, dict[str, str]] = {
    # DeepSeek's OpenAI-compatible API currently accepts the provider model
    # identifiers below. APICred may expose product-tier names such as
    # deepseek-v4-pro, so translate those before calling the upstream.
    "deepseek": {
        "deepseek-v4-pro": "deepseek-chat",
        "deepseek-v4": "deepseek-chat",
        "deepseek-v3": "deepseek-chat",
        "deepseek-r1": "deepseek-reasoner",
    },
}


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
    if isinstance(candidate, ModelRouteCandidate):
        route_base_url = (candidate.route.base_url_override or "").strip()
        if route_base_url:
            return normalize_upstream_base_url(route_base_url)
        endpoint_base_url = (candidate.endpoint.base_url or "").strip() if candidate.endpoint else ""
        if endpoint_base_url:
            return normalize_upstream_base_url(endpoint_base_url)
        provider_default_base_url = (candidate.provider.default_base_url or "").strip()
        if provider_default_base_url:
            return normalize_upstream_base_url(provider_default_base_url)
        return normalize_upstream_base_url(get_provider_default_base_url(candidate.provider.slug))

    return None


def is_url_like_base_url(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _resolve_api_key(candidate) -> str:
    encrypted_secret = getattr(candidate.credential, "secret_encrypted", None) if candidate.credential else None
    if encrypted_secret:
        return decrypt_secret(encrypted_secret)
    return ""


def _candidate_provider(candidate) -> str:
    return candidate.provider.slug


def _candidate_credential_id(candidate) -> str:
    if candidate.credential:
        return candidate.credential.id
    return candidate.route.id


def _candidate_quota_unit(candidate) -> str:
    return candidate.route.quota_unit


def _candidate_quota_rules(candidate) -> dict:
    return candidate.route.quota_rules or {}


def _resolve_upstream_model_name(candidate, model, provider: str) -> str:
    return candidate.upstream_model.upstream_name


def _payload_for_candidate(payload_dict: dict, candidate, model) -> dict:
    request_payload = dict(payload_dict)
    upstream_model = _resolve_upstream_model_name(candidate, model, _candidate_provider(candidate))
    request_payload["model"] = upstream_model
    return request_payload


def _upstream_error_message(info: dict | None) -> str:
    if not info:
        return "upstream error"
    status = info.get("status")
    code = info.get("code") or "upstream_error"
    detail = str(info.get("detail") or "").strip()
    if detail:
        return f"{code}: {detail[:500]}"
    if status:
        return f"{code}: upstream HTTP {status}"
    return str(code)


def _client_status_for_upstream_error(info: dict | None) -> int:
    code = (info or {}).get("code")
    status = int((info or {}).get("status") or 0)
    if code == "auth_failed":
        return 502
    if code == "request_error" or 400 <= status < 500:
        return 502
    if code == "rate_limited" or status == 429:
        return 503
    return 503


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
    result = await db.execute(select(PublicModel).where(PublicModel.slug == payload.model))
    model = result.scalar_one_or_none()
    if not model or not model.enabled:
        raise AppError("model_not_found", "model not available", request_id, 404)
    public_model_name = model.slug

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
            model_name=public_model_name,
            estimated_cost=estimated_cost,
            meta={"model": public_model_name, "request_id": str(request_id)},
            request_messages=_messages_to_records(payload.messages),
            request_text=_messages_to_text(payload.messages),
        )
    except ValueError:
        raise AppError("insufficient_balance", "insufficient balance", request_id, 402)

    candidates = await get_route_candidates(db, model.id)
    if not candidates:
        await settle_usage(db, usage_session, 0, {"error": "no_candidates"})
        raise AppError("no_upstream_capacity", "no available upstream keys", request_id, 503)

    redis = get_redis()
    stream_response_started = False
    try:
        attempts = 0
        last_error_info: dict | None = None
        for candidate in candidates:
            attempts += 1
            if attempts > settings.max_key_attempts:
                break
            delta = 1 if _candidate_quota_unit(candidate) == "requests" else est_tokens
            ok = await try_reserve(redis, _candidate_credential_id(candidate), model.id, delta, _candidate_quota_rules(candidate))
            if not ok:
                continue
            api_key = _resolve_api_key(candidate)
            base_url = await _resolve_base_url(db, candidate)
            provider_name = _candidate_provider(candidate)
            candidate_credential_id = _candidate_credential_id(candidate)
            adapter = get_provider_adapter(provider_name)
            upstream_payload = _payload_for_candidate(payload_dict, candidate, model)
            upstream_model = upstream_payload.get("model")
            try:
                logger.info(
                    "llm_request request_id=%s user_id=%s model=%s upstream_model=%s provider=%s credential_id=%s",
                    request_id,
                    api_token.user_id,
                    public_model_name,
                    upstream_model,
                    provider_name,
                    candidate_credential_id,
                )
                usage_session.upstream_provider = provider_name
                usage_session.upstream_credential_id = candidate_credential_id
                if payload.stream:
                    stream_result = await adapter.stream_chat_completions(upstream_payload, api_key, base_url)
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
                raw, usage = await adapter.chat_completions(upstream_payload, api_key, base_url)
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
                info["status"] = exc.response.status_code
                info["detail"] = exc.response.text[:2000]
                last_error_info = info
                logger.warning(
                    "llm_upstream_http_error request_id=%s provider=%s credential_id=%s model=%s upstream_model=%s code=%s status=%s retryable=%s detail=%s",
                    request_id,
                    provider_name,
                    candidate_credential_id,
                    public_model_name,
                    upstream_model,
                    info.get("code"),
                    exc.response.status_code,
                    info.get("retryable"),
                    exc.response.text[:500],
                )
                await _apply_cooldown(db, candidate, info)
                if not info.get("retryable"):
                    break
            except Exception as exc:
                info = adapter.normalize_error(exc)
                info["detail"] = str(exc)[:2000]
                last_error_info = info
                logger.exception(
                    "llm_upstream_error request_id=%s provider=%s credential_id=%s model=%s upstream_model=%s code=%s retryable=%s detail=%s",
                    request_id,
                    provider_name,
                    candidate_credential_id,
                    public_model_name,
                    upstream_model,
                    info.get("code"),
                    info.get("retryable"),
                    str(exc)[:500],
                )
                await _apply_cooldown(db, candidate, info)
        await settle_usage(db, usage_session, 0, {"error": "upstream_failed", "upstream": last_error_info or {}})
        raise AppError("upstream_failed", _upstream_error_message(last_error_info), request_id, _client_status_for_upstream_error(last_error_info))
    finally:
        if not stream_response_started:
            await redis.aclose()


async def _apply_cooldown(db: AsyncSession, candidate, info: dict) -> None:
    cooldown = int(info.get("cooldown_seconds", 60))
    credential_or_key: ProviderCredential | None = candidate.credential
    if credential_or_key is None:
        return
    if info.get("code") == "auth_failed":
        credential_or_key.health_state = "disabled"
    credential_or_key.cooldown_until = utc_now() if cooldown <= 0 else utc_now() + __import__("datetime").timedelta(seconds=cooldown)
    await db.commit()


async def _stream_chat_completion_chunks(raw: dict) -> AsyncIterator[str]:
    async for chunk in stream_chunks_from_raw(raw):
        yield chunk


async def _proxy_stream_and_settle(
    *,
    db: AsyncSession,
    redis,
    usage_session,
    model: PublicModel,
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
