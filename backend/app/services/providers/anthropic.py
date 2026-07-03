import json
import sys
from typing import Any, Dict, Tuple

import httpx

from app.services.providers.base import ProviderAdapter, ProviderStreamResult


class AnthropicAdapter(ProviderAdapter):
    name = "anthropic"

    async def chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        url = base_url.rstrip("/") + "/v1/messages"
        system_messages = []
        messages = []
        for message in payload.get("messages", []):
            role = message.get("role")
            content = message.get("content", "")
            if role == "system":
                system_messages.append(str(content))
                continue
            mapped_role = "assistant" if role == "assistant" else "user"
            messages.append({"role": mapped_role, "content": str(content)})

        request_payload: Dict[str, Any] = {
            "model": payload["model"],
            "messages": messages,
            "max_tokens": int(payload.get("max_tokens") or 1024),
        }
        if system_messages:
            request_payload["system"] = "\n\n".join(system_messages)
        if payload.get("temperature") is not None:
            request_payload["temperature"] = payload["temperature"]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json=request_payload,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        text_parts = [
            block.get("text", "")
            for block in data.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        usage = data.get("usage") or {}
        usage_dict = {
            "prompt_tokens": int(usage.get("input_tokens", 0)),
            "completion_tokens": int(usage.get("output_tokens", 0)),
            "total_tokens": int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0)),
        }
        normalized = {
            "id": data.get("id"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "".join(text_parts)},
                    "finish_reason": data.get("stop_reason"),
                }
            ],
            "usage": usage_dict,
        }
        return normalized, usage_dict

    async def stream_chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> ProviderStreamResult:
        url = base_url.rstrip("/") + "/v1/messages"
        system_messages = []
        messages = []
        for message in payload.get("messages", []):
            role = message.get("role")
            content = message.get("content", "")
            if role == "system":
                system_messages.append(str(content))
                continue
            mapped_role = "assistant" if role == "assistant" else "user"
            messages.append({"role": mapped_role, "content": str(content)})

        request_payload: Dict[str, Any] = {
            "model": payload["model"],
            "messages": messages,
            "max_tokens": int(payload.get("max_tokens") or 1024),
            "stream": True,
        }
        if system_messages:
            request_payload["system"] = "\n\n".join(system_messages)
        if payload.get("temperature") is not None:
            request_payload["temperature"] = payload["temperature"]

        client = httpx.AsyncClient(timeout=None)
        stream_ctx = client.stream(
            "POST",
            url,
            json=request_payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
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
            "saw_role": False,
        }

        async def _iterator():
            current_event = None
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    continue
                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()
                if current_event == "ping":
                    continue
                try:
                    payload_data = json.loads(data)
                except json.JSONDecodeError:
                    continue

                if current_event == "message_start":
                    message = payload_data.get("message") or {}
                    state["id"] = message.get("id")
                    usage = message.get("usage") or {}
                    prompt_tokens = int(usage.get("input_tokens", 0))
                    completion_tokens = int(usage.get("output_tokens", 0))
                    state["usage"] = {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    }
                    continue

                if current_event == "content_block_delta":
                    delta = payload_data.get("delta") or {}
                    if delta.get("type") != "text_delta":
                        continue
                    text = delta.get("text", "")
                    if not text:
                        continue
                    state["content_parts"].append(text)
                    chunk_payload = {
                        "id": state["id"] or "chatcmpl-anthropic-stream",
                        "object": "chat.completion.chunk",
                        "choices": [
                            {
                                "index": 0,
                                "delta": (
                                    {"role": "assistant", "content": text}
                                    if not state["saw_role"]
                                    else {"content": text}
                                ),
                                "finish_reason": None,
                            }
                        ],
                    }
                    state["saw_role"] = True
                    yield f"data: {json.dumps(chunk_payload, ensure_ascii=False)}\n\n"
                    continue

                if current_event == "message_delta":
                    delta = payload_data.get("delta") or {}
                    if delta.get("stop_reason") is not None:
                        state["finish_reason"] = delta.get("stop_reason")
                    usage = payload_data.get("usage") or {}
                    prompt_tokens = state["usage"]["prompt_tokens"]
                    completion_tokens = int(usage.get("output_tokens", state["usage"]["completion_tokens"]))
                    state["usage"] = {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    }
                    continue

                if current_event == "message_stop":
                    final_chunk = {
                        "id": state["id"] or "chatcmpl-anthropic-stream",
                        "object": "chat.completion.chunk",
                        "choices": [
                            {
                                "index": 0,
                                "delta": {},
                                "finish_reason": state["finish_reason"] or "stop",
                            }
                        ],
                    }
                    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    break

        async def _finalize() -> Tuple[Dict[str, Any], Dict[str, int]]:
            try:
                await stream_ctx.__aexit__(None, None, None)
            finally:
                await client.aclose()
            usage = state["usage"]
            raw = {
                "id": state["id"] or "chatcmpl-anthropic-stream",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": state["role"], "content": "".join(state["content_parts"])},
                        "finish_reason": state["finish_reason"] or "stop",
                    }
                ],
                "usage": usage,
            }
            return raw, usage

        return ProviderStreamResult(iterator=_iterator(), finalize=_finalize)

    def normalize_error(self, exception_or_response: Any) -> Dict[str, Any]:
        if isinstance(exception_or_response, httpx.TimeoutException):
            return {"code": "timeout", "retryable": True, "cooldown_seconds": 15}
        if isinstance(exception_or_response, httpx.HTTPStatusError):
            status = exception_or_response.response.status_code
            if status in (401, 403):
                return {"code": "auth_failed", "retryable": False, "cooldown_seconds": 3600}
            if status == 429:
                return {"code": "rate_limited", "retryable": True, "cooldown_seconds": 60}
            if status >= 500:
                return {"code": "upstream_error", "retryable": True, "cooldown_seconds": 15}
            return {"code": "request_error", "retryable": False, "cooldown_seconds": 0}
        return {"code": "network_error", "retryable": True, "cooldown_seconds": 15}
