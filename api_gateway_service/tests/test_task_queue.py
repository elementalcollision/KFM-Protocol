import pytest
import asyncio
from app.services import task_queue

class DummyRedis:
    def __init__(self):
        self.queue = []
    async def rpush(self, key, value):
        self.queue.append(value)
    async def lpop(self, key):
        if self.queue:
            return self.queue.pop(0)
        return None

@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    dummy = DummyRedis()
    async def get_dummy_redis():
        return dummy
    monkeypatch.setattr(task_queue, "get_redis", get_dummy_redis)
    return dummy

@pytest.mark.asyncio
async def test_enqueue_and_dequeue_task():
    await task_queue.enqueue_task("task1")
    await task_queue.enqueue_task("task2")
    t1 = await task_queue.dequeue_task()
    t2 = await task_queue.dequeue_task()
    t3 = await task_queue.dequeue_task()
    assert t1 == "task1"
    assert t2 == "task2"
    assert t3 is None 