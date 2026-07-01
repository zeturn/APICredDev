from __future__ import annotations

from typing import Any

import httpx
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.secrets import decrypt_secret
from app.core.time import utc_now
from app.core.url_safety import normalize_upstream_base_url
from app.db.models.provider_credential import ProviderCredential
from app.db.models.public_model import PublicModel
from app.services.quota_service import try_reserve
from app.services.routing_service import ModelRouteCandidate, get_route_candidates


SEARCH_TOOL_NAMES = {"brave_web_search", "brave_search", "web_search", "search_web"}


def request_uses_search_tool(payload_tools: list[dict[str, Any]] | None, tool_choice: Any = None) -> bool:
    if isinstance(tool_choice, dict):
        function = tool_choice.get("function") if isinstance(tool_choice.get("function"), dict) else {}
        name = str(function.get("name") or tool_choice.get("name") or "").strip()
        if name in SEARCH_TOOL_NAMES:
            return True

    for tool in payload_tools or []:
        if not isinstance(tool, dict):
            continue
        function = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        name = str(function.get("name") or tool.get("name") or "").strip()
        if name in SEARCH_TOOL_NAMES:
            return True
    return False


def search_model_from_tools(payload_tools: list[dict[str, Any]] | None, tool_choice: Any = None) -> str:
    candidates: list[dict[str, Any]] = []
    if isinstance(tool_choice, dict):
        candidates.append(tool_choice)
    candidates.extend([tool for tool in payload_tools or [] if isinstance(tool, dict)])
    for tool in candidates:
        function = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        name = str(function.get("name") or tool.get("name") or "").strip()
        if name in SEARCH_TOOL_NAMES:
            model = str(
                tool.get("model")
                or tool.get("search_model")
                or function.get("model")
                or function.get("search_model")
                or ""
            ).strip()
            if model:
                return model
    return settings.search_default_model_slug


def latest_user_query(messages: list[Any]) -> str:
    for message in reversed(messages):
        role = getattr(message, "role", None)
        content = getattr(message, "content", None)
        if role == "user" and isinstance(content, str) and content.strip():
            return content.strip()[:400]
    return ""


def strip_managed_search_tools(payload: dict[str, Any]) -> dict[str, Any]:
    next_payload = dict(payload)
    tools = []
    for tool in next_payload.get("tools") or []:
        if not isinstance(tool, dict):
            tools.append(tool)
            continue
        function = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        name = str(function.get("name") or tool.get("name") or "").strip()
        if name not in SEARCH_TOOL_NAMES:
            tools.append(tool)
    if tools:
        next_payload["tools"] = tools
    else:
        next_payload.pop("tools", None)
        next_payload.pop("tool_choice", None)
    return next_payload


class BraveSearchClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.brave_search_api_key
        self.base_url = (base_url or settings.brave_search_base_url).rstrip("/")

    async def web_search(
        self,
        query: str,
        *,
        count: int | None = None,
        country: str | None = None,
        search_lang: str | None = None,
        freshness: str | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("Brave Search API key is not configured")
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("search query is required")
        params: dict[str, Any] = {
            "q": clean_query[:400],
            "count": max(1, min(int(count or settings.brave_search_default_count or 5), 20)),
            "country": country or settings.brave_search_default_country,
            "search_lang": search_lang or settings.brave_search_default_lang,
            "result_filter": "web,news",
            "text_decorations": "false",
        }
        if freshness:
            params["freshness"] = freshness
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/web/search",
                params=params,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self.api_key,
                },
            )
        response.raise_for_status()
        return normalize_brave_response(response.json())


def _candidate_base_url(candidate: ModelRouteCandidate) -> str:
    route_url = (candidate.route.base_url_override or "").strip()
    if route_url:
        return normalize_upstream_base_url(route_url)
    endpoint_url = (candidate.endpoint.base_url or "").strip() if candidate.endpoint else ""
    if endpoint_url:
        return normalize_upstream_base_url(endpoint_url)
    return settings.brave_search_base_url


def _candidate_api_key(candidate: ModelRouteCandidate) -> str:
    encrypted = getattr(candidate.credential, "secret_encrypted", None) if candidate.credential else None
    return decrypt_secret(encrypted) if encrypted else ""


def _candidate_credential_id(candidate: ModelRouteCandidate) -> str:
    return candidate.credential.id if candidate.credential else candidate.route.id


async def _apply_search_cooldown(db: AsyncSession, candidate: ModelRouteCandidate, status_code: int) -> None:
    credential: ProviderCredential | None = candidate.credential
    if not credential:
        return
    if status_code in {401, 403}:
        credential.health_state = "disabled"
    if status_code == 429 or status_code >= 500:
        credential.cooldown_until = utc_now()
    await db.commit()


async def managed_web_search(
    db: AsyncSession,
    redis: Redis,
    query: str,
    *,
    search_model_slug: str | None = None,
    count: int | None = None,
) -> tuple[dict[str, Any], PublicModel | None]:
    slug = (search_model_slug or settings.search_default_model_slug).strip()
    model = (await db.execute(select(PublicModel).where(PublicModel.slug == slug))).scalar_one_or_none()
    if not model or not model.enabled or model.category != "search":
        # Compatibility fallback for existing deployments before admins register
        # a search public model.
        return await BraveSearchClient().web_search(query, count=count), None

    candidates = await get_route_candidates(db, model.id)
    if not candidates:
        return await BraveSearchClient().web_search(query, count=count), model

    last_status = 0
    for candidate in candidates:
        delta = 1
        ok = await try_reserve(
            redis,
            _candidate_credential_id(candidate),
            model.id,
            delta,
            candidate.route.quota_rules or {},
        )
        if not ok:
            continue
        provider_slug = candidate.provider.slug
        upstream_name = candidate.upstream_model.upstream_name
        if provider_slug != "brave-search" or upstream_name not in {"web-search", "brave-web-search"}:
            continue
        api_key = _candidate_api_key(candidate)
        if not api_key:
            continue
        try:
            result = await BraveSearchClient(api_key=api_key, base_url=_candidate_base_url(candidate)).web_search(query, count=count)
            return result, model
        except httpx.HTTPStatusError as exc:
            last_status = exc.response.status_code
            await _apply_search_cooldown(db, candidate, last_status)
            if last_status in {401, 403}:
                continue
            if last_status == 429 or last_status >= 500:
                continue
            raise

    if last_status:
        raise httpx.HTTPStatusError(
            f"all search routes failed, last status {last_status}",
            request=httpx.Request("GET", settings.brave_search_base_url),
            response=httpx.Response(last_status),
        )
    raise ValueError("no available search routes")


def _normalize_result(item: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "source": source,
        "title": item.get("title"),
        "url": item.get("url"),
        "description": item.get("description"),
        "age": item.get("age"),
        "page_age": item.get("page_age"),
    }


def normalize_brave_response(raw: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for item in ((raw.get("web") or {}).get("results") or []):
        if isinstance(item, dict):
            results.append(_normalize_result(item, "web"))
    for item in ((raw.get("news") or {}).get("results") or []):
        if isinstance(item, dict):
            results.append(_normalize_result(item, "news"))
    return {
        "query": ((raw.get("query") or {}).get("original") or (raw.get("query") or {}).get("altered")),
        "results": results[:20],
    }


def search_context_message(search_payload: dict[str, Any]) -> dict[str, str]:
    lines = [
        "Use the following Brave Search results as current web context.",
        "Cite URLs in your answer when you rely on them.",
    ]
    for index, item in enumerate(search_payload.get("results") or [], start=1):
        title = item.get("title") or "Untitled"
        url = item.get("url") or ""
        description = item.get("description") or ""
        date = item.get("age") or item.get("page_age") or ""
        lines.append(f"[{index}] {title}\nURL: {url}\nDate: {date}\nSnippet: {description}")
    if len(lines) == 2:
        lines.append("No web results were returned.")
    return {"role": "system", "content": "\n\n".join(lines)}
