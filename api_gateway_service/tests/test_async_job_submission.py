import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.api.endpoints.async_tasks import router as async_router

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
    from app.services import task_store, task_queue
    monkeypatch.setattr(task_store, "get_redis", get_dummy_redis)
    monkeypatch.setattr(task_queue, "get_redis", get_dummy_redis)
    return dummy

@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(async_router)
    return app

@pytest.mark.asyncio
async def test_submit_async_job(test_app):
    with patch("app.services.task_store.create_task", new_callable=AsyncMock) as mock_create_task:
        response = TestClient(test_app).post(
            "/async/testservice/testop",
            json={"payload": {"foo": "bar"}}
        )
        assert response.status_code == 200
        data = response.json()
        assert "taskId" in data
        assert data["status"] == "pending"
        assert mock_create_task.await_count == 1

@pytest.mark.asyncio
async def test_get_task_status_existing(test_app):
    # Create and store a task
    from app.models.task import AsyncTask
    from app.services import task_store
    task = AsyncTask()
    await task_store.create_task(task)
    response = TestClient(test_app).get(f"/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["taskId"] == str(task.id)
    assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_get_task_status_not_found(test_app):
    response = TestClient(test_app).get("/tasks/nonexistent-task-id")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Task not found"

@pytest.mark.asyncio
async def test_register_webhook_success(test_app):
    from app.models.task import AsyncTask
    from app.services import task_store
    task = AsyncTask()
    await task_store.create_task(task)
    response = TestClient(test_app).post(
        f"/tasks/{task.id}/webhook",
        json={"webhook_url": "https://example.com/webhook"}
    )
    assert response.status_code == 204
    updated = await task_store.get_task(task.id)
    assert updated.webhook_url == "https://example.com/webhook"

@pytest.mark.asyncio
async def test_register_webhook_non_https(test_app):
    from app.models.task import AsyncTask
    from app.services import task_store
    task = AsyncTask()
    await task_store.create_task(task)
    response = TestClient(test_app).post(
        f"/tasks/{task.id}/webhook",
        json={"webhook_url": "http://example.com/webhook"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Webhook URL must use HTTPS."

@pytest.mark.asyncio
async def test_register_webhook_task_not_found(test_app):
    response = TestClient(test_app).post(
        "/tasks/nonexistent-task-id/webhook",
        json={"webhook_url": "https://example.com/webhook"}
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Task not found"

API_KEY = "supersecretkey"

@pytest.mark.asyncio
def test_auth_required_on_async_job(test_app):
    # No API key
    response = TestClient(test_app).post(
        "/async/testservice/testop",
        json={"payload": {"foo": "bar"}}
    )
    assert response.status_code == 401
    # With API key
    response = TestClient(test_app).post(
        "/async/testservice/testop",
        json={"payload": {"foo": "bar"}},
        headers={"x-api-key": API_KEY}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_auth_required_on_get_task_status(test_app):
    from app.models.task import AsyncTask
    from app.services import task_store
    task = AsyncTask()
    await task_store.create_task(task)
    # No API key
    response = TestClient(test_app).get(f"/tasks/{task.id}")
    assert response.status_code == 401
    # With API key
    response = TestClient(test_app).get(f"/tasks/{task.id}", headers={"x-api-key": API_KEY})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_auth_required_on_webhook(test_app):
    from app.models.task import AsyncTask
    from app.services import task_store
    task = AsyncTask()
    await task_store.create_task(task)
    # No API key
    response = TestClient(test_app).post(
        f"/tasks/{task.id}/webhook",
        json={"webhook_url": "https://example.com/webhook"}
    )
    assert response.status_code == 401
    # With API key
    response = TestClient(test_app).post(
        f"/tasks/{task.id}/webhook",
        json={"webhook_url": "https://example.com/webhook"},
        headers={"x-api-key": API_KEY}
    )
    assert response.status_code == 204

@pytest.mark.asyncio
def test_auth_required_on_sse(test_app):
    # No API key
    response = TestClient(test_app).get("/tasks/events")
    assert response.status_code == 401
    # With API key
    response = TestClient(test_app).get("/tasks/events", headers={"x-api-key": API_KEY})
    assert response.status_code == 200 