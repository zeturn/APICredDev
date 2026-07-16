from redis.asyncio import Redis

from app.core.time import utc_now, format_bucket
from app.redis.quota_lua import LUA_SCRIPT


TTL_SECONDS = {
    "minute": 120,
    "hour": 7200,
    "day": 172800,
    "month": 3456000,
}


async def try_reserve(
    redis: Redis,
    credential_id: str,
    model_id: str,
    delta: int,
    quota_rules: dict,
) -> bool:
    if not quota_rules or all(quota_rules.get(unit) in (None, -1) for unit in ("minute", "hour", "day", "month")):
        return True

    quota_scope = str(quota_rules.get("group") or model_id or "").strip()
    if not quota_scope:
        quota_scope = "default"

    now = utc_now()
    keys = []
    limits = []
    ttls = []
    for unit in ("minute", "hour", "day", "month"):
        limit = quota_rules.get(unit, -1)
        if limit is None:
            limit = -1
        bucket = format_bucket(now, unit)
        keys.append(f"quota:{credential_id}:{quota_scope}:{unit}:{bucket}")
        limits.append(int(limit))
        ttls.append(TTL_SECONDS[unit])
    args = [delta] + limits + ttls
    result = await redis.eval(LUA_SCRIPT, 4, *keys, *args)
    return int(result) == 1
