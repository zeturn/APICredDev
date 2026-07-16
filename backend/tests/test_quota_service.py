from app.services.quota_service import try_reserve


class FakeRedis:
    def __init__(self):
        self.calls = []

    async def eval(self, script, key_count, *args):
        self.calls.append((script, key_count, args))
        return 1


async def test_try_reserve_defaults_to_model_scoped_keys():
    redis = FakeRedis()

    assert await try_reserve(redis, "credential-a", "model-a", 10, {"day": 100})

    _, key_count, args = redis.calls[0]
    assert key_count == 4
    keys = args[:4]
    assert all(key.startswith("quota:credential-a:model-a:") for key in keys)


async def test_try_reserve_group_shares_keys_across_models():
    redis = FakeRedis()

    assert await try_reserve(redis, "credential-a", "model-a", 10, {"group": "openai-free-mini", "day": 100})
    assert await try_reserve(redis, "credential-a", "model-b", 10, {"group": "openai-free-mini", "day": 100})

    first_keys = redis.calls[0][2][:4]
    second_keys = redis.calls[1][2][:4]
    assert first_keys == second_keys
    assert all(key.startswith("quota:credential-a:openai-free-mini:") for key in first_keys)
