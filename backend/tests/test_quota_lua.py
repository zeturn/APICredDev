import asyncio

import pytest
from redis.asyncio import Redis

from app.core.config import settings
from app.redis.quota_lua import LUA_SCRIPT


async def _close_redis(redis: Redis) -> None:
    if hasattr(redis, "aclose"):
        await redis.aclose()
    else:
        await redis.close()


@pytest.mark.asyncio
async def test_quota_lua_concurrent():
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.ping()
    except Exception:
        await _close_redis(redis)
        pytest.skip("redis not available")

    key = "quota:test:minute:bucket"
    await redis.delete(key)

    async def worker():
        return await redis.eval(LUA_SCRIPT, 1, key, 1, 5, -1, -1, -1, 120, 0, 0, 0)

    results = await asyncio.gather(*[worker() for _ in range(10)])
    assert sum(int(r) for r in results) == 5
    await redis.delete(key)
    await _close_redis(redis)

