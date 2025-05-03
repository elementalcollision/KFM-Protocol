import aioredis
from typing import Optional

_redis_pool: Optional[aioredis.Redis] = None

async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(
            "redis://localhost:6379", decode_responses=True
        )
    return _redis_pool 