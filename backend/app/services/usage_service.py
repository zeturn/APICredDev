import math
from typing import Tuple

from app.db.models.model import Model


def estimate_tokens(messages: list[dict], max_tokens: int | None) -> int:
    approx = 0
    for msg in messages:
        content = msg.get("content", "")
        approx += max(1, len(content) // 4)
    if max_tokens:
        approx += max_tokens
    return max(1, approx)


def calculate_cost(model: Model, total_tokens: int, request_count: int = 1) -> float:
    pricing = model.pricing or {}
    unit = pricing.get("unit", "1k_tokens")
    price = float(pricing.get("price", 0))
    multiplier = float(model.multiplier or 1)
    if unit == "1k_tokens":
        units = math.ceil(total_tokens / 1000)
    else:
        units = request_count
    return float(units * price * multiplier)

