import json
import sys
from typing import Any, Dict, Tuple

import httpx

from app.services.providers.base import ProviderAdapter, ProviderStreamResult


class OpenAICompatAdapter(ProviderAdapter):
    name = "openai_compat"

    async def chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        url = base_url.rstrip("/") + "/v1/chat/completions"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage") or {}
            usage_dict = {
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
                "total_tokens": int(usage.get("total_tokens", 0)),
            }
            return data, usage_dict

    async def stream_chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> ProviderStreamResult:
        url = base_url.rstrip("/") + "/v1/chat/completions"
        stream_payload = dict(payload)
        stream_payload["stream"] = True
        stream_options = dict(stream_payload.get("stream_options") or {})
        stream_options["include_usage"] = True
        stream_payload["stream_options"] = stream_options

        client = httpx.AsyncClient(timeout=None)
        stream_ctx = client.stream(
            "POST",
            url,
            json=stream_payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response = await stream_ctx.__aenter__()
        try:
            response.raise_for_status()
        except Exception:
            await stream_ctx.__aexit__(*sys.exc_info())
            await client.aclose()
            raise

        state: Dict[str, Any] = {
            "id": None,
            "role": "assistant",
            "content_parts": [],
            "finish_reason": None,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

        async def _iterator():
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                yield f"data: {data}\n\n"
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                if chunk.get("id"):
                    state["id"] = chunk["id"]
                choices = chunk.get("choices") or []
                if choices:
                    choice = choices[0]
                    delta = choice.get("delta") or {}
                    if delta.get("role"):
                        state["role"] = delta["role"]
                    if delta.get("content"):
                        state["content_parts"].append(delta["content"])
                    if choice.get("finish_reason") is not None:
                        state["finish_reason"] = choice.get("finish_reason")
                usage = chunk.get("usage") or {}
                if usage:
                    state["usage"] = {
                        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                        "completion_tokens": int(usage.get("completion_tokens", 0)),
                        "total_tokens": int(usage.get("total_tokens", 0)),
                    }

        async def _finalize() -> Tuple[Dict[str, Any], Dict[str, int]]:
            try:
                await stream_ctx.__aexit__(None, None, None)
            finally:
                await client.aclose()
            raw = {
                "id": state["id"] or "chatcmpl-stream",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": state["role"], "content": "".join(state["content_parts"])},
                        "finish_reason": state["finish_reason"],
                    }
                ],
                "usage": state["usage"],
            }
            return raw, state["usage"]

        return ProviderStreamResult(iterator=_iterator(), finalize=_finalize)

    def normalize_error(self, exception_or_response: Any) -> Dict[str, Any]:
        if isinstance(exception_or_response, httpx.HTTPStatusError):
            status = exception_or_response.response.status_code
            if status in (401, 403):
                return {"code": "auth_failed", "retryable": False, "cooldown_seconds": 3600}
            if status == 429:
                return {"code": "rate_limited", "retryable": True, "cooldown_seconds": 60}
            if status >= 500:
                return {"code": "upstream_error", "retryable": True, "cooldown_seconds": 15}
        return {"code": "network_error", "retryable": True, "cooldown_seconds": 15}

