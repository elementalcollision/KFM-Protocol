import json
from typing import Optional
from uuid import UUID
from app.models.task import AsyncTask
from app.core.redis import get_redis

TASK_HASH_KEY = "async_tasks"

async def create_task(task: AsyncTask) -> None:
    redis = await get_redis()
    await redis.hset(TASK_HASH_KEY, str(task.id), task.json())

async def get_task(task_id: UUID) -> Optional[AsyncTask]:
    redis = await get_redis()
    data = await redis.hget(TASK_HASH_KEY, str(task_id))
    if data:
        return AsyncTask.parse_raw(data)
    return None

async def update_task(task: AsyncTask) -> None:
    redis = await get_redis()
    await redis.hset(TASK_HASH_KEY, str(task.id), task.json())

async def delete_task(task_id: UUID) -> None:
    redis = await get_redis()
    await redis.hdel(TASK_HASH_KEY, str(task_id)) 