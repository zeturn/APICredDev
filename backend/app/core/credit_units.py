from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Any

from app.core.config import settings


CREDIT_POINT_QUANT = Decimal("1")


def credit_points_per_usd() -> int:
    return max(int(settings.basalt_credit_scale or 1), 1)


def as_decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def credits_to_microcredits(value: Any, *, rounding=ROUND_HALF_UP) -> int:
    points = as_decimal(value)
    return int(points.quantize(CREDIT_POINT_QUANT, rounding=rounding))


def microcredits_to_credits(value: Any) -> Decimal:
    return as_decimal(value).quantize(CREDIT_POINT_QUANT)


def billable_credits(value: Any) -> Decimal:
    points = credits_to_microcredits(value, rounding=ROUND_CEILING)
    if points <= 0:
        return Decimal("0")
    return microcredits_to_credits(points)


def usd_to_credit_points(value: Any, *, rounding=ROUND_CEILING) -> Decimal:
    usd = as_decimal(value)
    points = (usd * Decimal(credit_points_per_usd())).quantize(CREDIT_POINT_QUANT, rounding=rounding)
    if points <= 0:
        return Decimal("0")
    return points
