from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_bucket(dt: datetime, unit: str) -> str:
    if unit == "minute":
        return dt.strftime("%Y%m%d%H%M")
    if unit == "hour":
        return dt.strftime("%Y%m%d%H")
    if unit == "day":
        return dt.strftime("%Y%m%d")
    if unit == "month":
        return dt.strftime("%Y%m")
    raise ValueError(f"unsupported bucket unit: {unit}")

