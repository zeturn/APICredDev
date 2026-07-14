import math
from decimal import Decimal
from typing import Any

from app.core.credit_units import usd_to_credit_points


def estimate_prompt_tokens(messages: list[dict]) -> int:
    approx = 0
    for msg in messages:
        content = msg.get("content", "")
        approx += max(1, len(content) // 4)
    return max(1, approx)


def estimate_tokens(messages: list[dict], max_tokens: int | None) -> int:
    approx = estimate_prompt_tokens(messages)
    if max_tokens:
        approx += max_tokens
    return max(1, approx)


def calculate_cost(
    model: Any,
    total_tokens: int = 0,
    request_count: int = 1,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    cached_input_tokens: int = 0,
) -> float:
    pricing = model.pricing or {}
    multiplier = Decimal(str(getattr(model, "multiplier", 1) or 1))
    mode = pricing.get("mode")

    if mode == "free":
        return 0.0

    if mode == "token_segments":
        prompt = int(prompt_tokens if prompt_tokens is not None else total_tokens)
        completion = int(completion_tokens or 0)
        cached = max(0, int(cached_input_tokens or 0))
        non_cached_prompt = max(0, prompt - cached)
        tier = None
        for item in pricing.get("tiers", []) or []:
            min_input_tokens = int(item.get("min_input_tokens", 0) or 0)
            max_input_tokens = item.get("max_input_tokens")
            if prompt < min_input_tokens:
                continue
            if max_input_tokens is not None and prompt > int(max_input_tokens):
                continue
            tier = item
            break
        input_price = Decimal(str((tier or pricing).get("input_per_million", 0) or 0))
        cached_input_price = Decimal(str((tier or pricing).get("cached_input_per_million", pricing.get("cached_input_per_million", input_price)) or 0))
        output_price = Decimal(str((tier or pricing).get("output_per_million", 0) or 0))
        cost_usd = (
            (Decimal(non_cached_prompt) / Decimal(1_000_000)) * input_price
            + (Decimal(cached) / Decimal(1_000_000)) * cached_input_price
            + (Decimal(completion) / Decimal(1_000_000)) * output_price
        )
        return float(usd_to_credit_points(cost_usd * multiplier))

    unit = pricing.get("unit", "1k_tokens")
    price = Decimal(str(pricing.get("price", 0) or 0))
    if unit == "1k_tokens":
        units = math.ceil(total_tokens / 1000)
    else:
        units = request_count
    return float(usd_to_credit_points(Decimal(units) * price * multiplier))

