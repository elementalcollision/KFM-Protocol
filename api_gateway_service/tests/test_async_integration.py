import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.endpoints.async_tasks import router as async_router
from app.services import task_worker, task_store, task_queue
from app.models.task import TaskStatus
import asyncio

API_KEY = "supersecretkey"

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

@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(async_router)
    return app

@pytest.mark.asyncio
async def test_async_task_end_to_end(monkeypatch, test_app):
    client = TestClient(test_app)
    # 1. Submit async job
    resp = client.post(
        "/async/testservice/testop",
        json={"payload": {"foo": "bar"}},
        headers={"x-api-key": API_KEY}
    )
    assert resp.status_code == 200
    task_id = resp.json()["taskId"]

    # 2. Register webhook
    webhook_called = {}
    class DummyResponse:
        status_code = 200
    class DummyClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return None
        async def post(self, url, json):
            webhook_called["url"] = url
            webhook_called["json"] = json
            return DummyResponse()
    monkeypatch.setattr("httpx.AsyncClient", lambda timeout: DummyClient())
    resp = client.post(
        f"/tasks/{task_id}/webhook",
        json={"webhook_url": "https://example.com/webhook"},
        headers={"x-api-key": API_KEY}
    )
    assert resp.status_code == 204

    # 3. Simulate worker processing (should succeed on 3rd try)
    for _ in range(5):
        await task_worker.process_task(task_id)
        t = await task_store.get_task(task_id)
        if t.status == TaskStatus.SUCCESS:
            break
    t = await task_store.get_task(task_id)
    assert t.status == TaskStatus.SUCCESS
    assert t.result["message"] == "Task completed successfully"

    # 4. Poll for status
    resp = client.get(f"/tasks/{task_id}", headers={"x-api-key": API_KEY})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["result"]["message"] == "Task completed successfully"

    # 5. Verify webhook was called
    assert webhook_called["url"] == "https://example.com/webhook"
    assert webhook_called["json"]["status"] == TaskStatus.SUCCESS 