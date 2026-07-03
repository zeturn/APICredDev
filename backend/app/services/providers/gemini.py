import json
import sys
from typing import Any, Dict, Tuple

import httpx

from app.services.providers.base import ProviderAdapter, ProviderStreamResult


class GeminiAdapter(ProviderAdapter):
    name = "gemini"

    async def chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        model_name = payload["model"]
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        url = base_url.rstrip("/") + f"/v1beta/{model_name}:generateContent"

        system_messages = []
        contents = []
        for message in payload.get("messages", []):
            role = message.get("role")
            content = str(message.get("content", ""))
            if role == "system":
                system_messages.append(content)
                continue
            mapped_role = "model" if role == "assistant" else "user"
            contents.append({"role": mapped_role, "parts": [{"text": content}]})

        request_payload: Dict[str, Any] = {"contents": contents}
        if system_messages:
            request_payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_messages)}]}

        generation_config: Dict[str, Any] = {}
        if payload.get("max_tokens") is not None:
            generation_config["maxOutputTokens"] = payload["max_tokens"]
        if payload.get("temperature") is not None:
            generation_config["temperature"] = payload["temperature"]
        if generation_config:
            request_payload["generationConfig"] = generation_config

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                params={"key": api_key},
                json=request_payload,
                headers={"content-type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates") or []
        first = candidates[0] if candidates else {}
        parts = ((first.get("content") or {}).get("parts") or []) if isinstance(first, dict) else []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        usage = data.get("usageMetadata") or {}
        usage_dict = {
            "prompt_tokens": int(usage.get("promptTokenCount", 0)),
            "completion_tokens": int(usage.get("candidatesTokenCount", 0)),
            "total_tokens": int(usage.get("totalTokenCount", 0)),
        }
        normalized = {
            "id": data.get("responseId", "gemini-response"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": first.get("finishReason"),
                }
            ],
            "usage": usage_dict,
        }
        return normalized, usage_dict

    async def stream_chat_completions(self, payload: Dict[str, Any], api_key: str, base_url: str) -> ProviderStreamResult:
        model_name = payload["model"]
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        url = base_url.rstrip("/") + f"/v1beta/{model_name}:streamGenerateContent"

        system_messages = []
        contents = []
        for message in payload.get("messages", []):
            role = message.get("role")
            content = str(message.get("content", ""))
            if role == "system":
                system_messages.append(content)
                continue
            mapped_role = "model" if role == "assistant" else "user"
            contents.append({"role": mapped_role, "parts": [{"text": content}]})

        request_payload: Dict[str, Any] = {"contents": contents}
        if system_messages:
            request_payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_messages)}]}

        generation_config: Dict[str, Any] = {}
        if payload.get("max_tokens") is not None:
            generation_config["maxOutputTokens"] = payload["max_tokens"]
        if payload.get("temperature") is not None:
            generation_config["temperature"] = payload["temperature"]
        if generation_config:
            request_payload["generationConfig"] = generation_config

        client = httpx.AsyncClient(timeout=None)
        stream_ctx = client.stream(
            "POST",
            url,
            params={"key": api_key, "alt": "sse"},
            json=request_payload,
            headers={"content-type": "application/json"},
        )
        response = await stream_ctx.__aenter__()
        try:
            response.raise_for_status()
        except Exception:
            await stream_ctx.__aexit__(*sys.exc_info())
            await client.aclose()
            raise

        state: Dict[str, Any] = {
            "id": "gemini-response",
            "role": "assistant",
            "content_parts": [],
            "finish_reason": None,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "saw_role": False,
        }

        async def _iterator():
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                try:
                    payload_data = json.loads(data)
                except json.JSONDecodeError:
                    continue

                if payload_data.get("responseId"):
                    state["id"] = payload_data["responseId"]

                candidates = payload_data.get("candidates") or []
                if candidates:
                    first = candidates[0]
                    parts = ((first.get("content") or {}).get("parts") or []) if isinstance(first, dict) else []
                    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict) and part.get("text"))
                    if text:
                        state["content_parts"].append(text)
                        chunk_payload = {
                            "id": state["id"],
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
                    if first.get("finishReason") is not None:
                        state["finish_reason"] = first.get("finishReason")

                usage = payload_data.get("usageMetadata") or {}
                if usage:
                    state["usage"] = {
                        "prompt_tokens": int(usage.get("promptTokenCount", 0)),
                        "completion_tokens": int(usage.get("candidatesTokenCount", 0)),
                        "total_tokens": int(usage.get("totalTokenCount", 0)),
                    }

            final_chunk = {
                "id": state["id"],
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

        async def _finalize() -> Tuple[Dict[str, Any], Dict[str, int]]:
            try:
                await stream_ctx.__aexit__(None, None, None)
            finally:
                await client.aclose()
            usage = state["usage"]
            raw = {
                "id": state["id"],
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
