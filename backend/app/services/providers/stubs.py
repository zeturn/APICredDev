from typing import Any, Dict, Tuple

from app.services.providers.base import ProviderAdapter


class StubAdapter(ProviderAdapter):
    name = "stub"

    async def chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        data = {
            "id": "stub",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "stub"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        return data, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

    def normalize_error(self, exception_or_response: Any) -> Dict[str, Any]:
        return {"code": "stub_error", "retryable": False, "cooldown_seconds": 60}

