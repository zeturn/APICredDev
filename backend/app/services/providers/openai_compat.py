from typing import Any, Dict, Tuple

import httpx

from app.services.providers.base import ProviderAdapter


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

