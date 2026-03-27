import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class ProviderStreamResult:
    iterator: AsyncIterator[str]
    finalize: Callable[[], Awaitable[Tuple[Dict[str, Any], Dict[str, int]]]]


async def stream_chunks_from_raw(raw: Dict[str, Any]) -> AsyncIterator[str]:
    completion_id = raw.get("id", "chatcmpl-stream")
    choices = raw.get("choices", [])
    first_choice = choices[0] if choices else {}
    message = first_choice.get("message") or {}
    content = message.get("content", "")
    finish_reason = first_choice.get("finish_reason", "stop")

    first_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": content},
                "finish_reason": None,
            }
        ],
    }
    yield f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n"

    final_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": finish_reason,
            }
        ],
    }
    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


class ProviderAdapter(ABC):
    name: str

    @abstractmethod
    async def chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        raise NotImplementedError

    @abstractmethod
    def normalize_error(self, exception_or_response: Any) -> Dict[str, Any]:
        raise NotImplementedError

    async def stream_chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> ProviderStreamResult:
        raw, usage = await self.chat_completions(payload, api_key, base_url)

        async def _finalize() -> Tuple[Dict[str, Any], Dict[str, int]]:
            return raw, usage

        return ProviderStreamResult(iterator=stream_chunks_from_raw(raw), finalize=_finalize)

