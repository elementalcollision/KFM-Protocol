import pytest
import asyncio
from app.models.task import AsyncTask, TaskStatus
from app.services import task_store, task_queue, task_worker
from unittest.mock import AsyncMock, patch

class DummyRedis:
    def __init__(self):
        self.data = {}
        self.queue = []
    async def hset(self, key, field, value):
        self.data.setdefault(key, {})[field] = value
    async def hget(self, key, field):
        return self.data.get(key, {}).get(field)
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
    monkeypatch.setattr(task_store, "get_redis", get_dummy_redis)
    monkeypatch.setattr(task_queue, "get_redis", get_dummy_redis)
    return dummy

@pytest.mark.asyncio
async def test_worker_retries_and_succeeds():
    # Create a task with max_retries=3
    task = AsyncTask(max_retries=3)
    await task_store.create_task(task)
    # Simulate up to 5 processing attempts (should succeed on 3rd)
    for _ in range(5):
        await task_worker.process_task(str(task.id))
        t = await task_store.get_task(task.id)
        if t.status == TaskStatus.SUCCESS:
            break
    t = await task_store.get_task(task.id)
    assert t.status == TaskStatus.SUCCESS
    assert t.retries == 2

@pytest.mark.asyncio
async def test_send_webhook_notification_success(monkeypatch):
    task = AsyncTask(webhook_url="https://example.com/webhook", status=TaskStatus.SUCCESS)
    called = {}
    class DummyResponse:
        status_code = 200
    class DummyClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return None
        async def post(self, url, json):
            called["url"] = url
            called["json"] = json
            return DummyResponse()
    monkeypatch.setattr("httpx.AsyncClient", lambda timeout: DummyClient())
    await task_worker.send_webhook_notification(task)
    assert called["url"] == "https://example.com/webhook"
    assert called["json"]["status"] == TaskStatus.SUCCESS

@pytest.mark.asyncio
async def test_send_webhook_notification_retries(monkeypatch):
    task = AsyncTask(webhook_url="https://example.com/webhook", status=TaskStatus.SUCCESS)
    attempts = []
    class DummyResponse:
        status_code = 500
    class DummyClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return None
        async def post(self, url, json):
            attempts.append(1)
            return DummyResponse()
    monkeypatch.setattr("httpx.AsyncClient", lambda timeout: DummyClient())
    await task_worker.send_webhook_notification(task, max_retries=3)
    assert len(attempts) == 3

@pytest.mark.asyncio
async def test_task_timeout(monkeypatch):
    # Patch do_work to sleep longer than timeout
    from app.models.task import AsyncTask, TaskStatus
    task = AsyncTask(timeout_seconds=0, max_retries=2)
    await task_store.create_task(task)
    # Patch do_work to always sleep (simulate long task)
    orig_process_task = task_worker.process_task
    async def slow_process_task(task_id):
        t = await task_store.get_task(task_id)
        t.retries = 0
        t.timeout_seconds = 0
        await task_store.update_task(t)
        await orig_process_task(task_id)
    await slow_process_task(str(task.id))
    t = await task_store.get_task(task.id)
    assert t.status == TaskStatus.FAILED
    assert "timed out" in t.error 