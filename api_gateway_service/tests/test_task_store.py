import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from app.models.task import AsyncTask, TaskStatus
from app.services import task_store

class DummyRedis:
    def __init__(self):
        self.data = {}
    async def hset(self, key, field, value):
        self.data.setdefault(key, {})[field] = value
    async def hget(self, key, field):
        return self.data.get(key, {}).get(field)
    async def hdel(self, key, field):
        if key in self.data and field in self.data[key]:
            del self.data[key][field]

@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    dummy = DummyRedis()
    async def get_dummy_redis():
        return dummy
    monkeypatch.setattr(task_store, "get_redis", get_dummy_redis)
    return dummy

@pytest.mark.asyncio
async def test_create_and_get_task():
    task = AsyncTask(status=TaskStatus.PENDING)
    await task_store.create_task(task)
    fetched = await task_store.get_task(task.id)
    assert fetched is not None
    assert fetched.id == task.id
    assert fetched.status == TaskStatus.PENDING

@pytest.mark.asyncio
async def test_update_task():
    task = AsyncTask(status=TaskStatus.PENDING)
    await task_store.create_task(task)
    task.status = TaskStatus.SUCCESS
    await task_store.update_task(task)
    fetched = await task_store.get_task(task.id)
    assert fetched.status == TaskStatus.SUCCESS

@pytest.mark.asyncio
async def test_delete_task():
    task = AsyncTask(status=TaskStatus.PENDING)
    await task_store.create_task(task)
    await task_store.delete_task(task.id)
    fetched = await task_store.get_task(task.id)
    assert fetched is None 