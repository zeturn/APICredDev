from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Any

from app.core.config import settings


MICROCREDIT_QUANT = Decimal("0.000001")


def credit_scale() -> int:
    return max(int(settings.basalt_credit_scale or 1), 1)


def as_decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def credits_to_microcredits(value: Any, *, rounding=ROUND_HALF_UP) -> int:
    credits = as_decimal(value)
    micros = (credits * Decimal(credit_scale())).quantize(Decimal("1"), rounding=rounding)
    return int(micros)


def microcredits_to_credits(value: Any) -> Decimal:
    credits = as_decimal(value) / Decimal(credit_scale())
    return credits.quantize(MICROCREDIT_QUANT)


def billable_credits(value: Any) -> Decimal:
    micros = credits_to_microcredits(value, rounding=ROUND_CEILING)
    if micros <= 0:
        return Decimal("0")
    return microcredits_to_credits(micros)
