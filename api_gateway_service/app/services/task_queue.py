from app.core.redis import get_redis

QUEUE_KEY = "async_task_queue"

async def enqueue_task(task_id: str) -> None:
    redis = await get_redis()
    await redis.rpush(QUEUE_KEY, task_id)

async def dequeue_task() -> str:
    redis = await get_redis()
    result = await redis.lpop(QUEUE_KEY)
    return result 