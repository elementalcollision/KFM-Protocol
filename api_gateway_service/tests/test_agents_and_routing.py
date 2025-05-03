import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import patch, MagicMock

# Import routers to be tested (assume these are available)
from app.api.endpoints.agents import router as agents_router
from app.api.router import router as main_router

API_KEY = "supersecretkey"

@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(main_router, prefix="/api/v1")
    return app

# --- /agents endpoint tests ---
def test_list_agents_success(test_app):
    with patch("app.services.http_client.HTTPClientService.get") as mock_get:
        mock_get.return_value = [{"id": "agent-123", "name": "Test Agent", "status": "active"}]
        client = TestClient(test_app)
        response = client.get("/api/v1/agents", headers={"x-api-key": API_KEY})
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

def test_get_agent_success(test_app):
    with patch("app.services.http_client.HTTPClientService.get") as mock_get:
        mock_get.return_value = {"id": "agent-123", "name": "Test Agent", "status": "active"}
        client = TestClient(test_app)
        response = client.get("/api/v1/agents/agent-123", headers={"x-api-key": API_KEY})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "agent-123"

def test_get_agent_not_found(test_app):
    with patch("app.services.http_client.HTTPClientService.get", side_effect=Exception("Not found")):
        client = TestClient(test_app)
        response = client.get("/api/v1/agents/nonexistent", headers={"x-api-key": API_KEY})
        assert response.status_code in (404, 503)

def test_get_agent_state_success(test_app):
    with patch("app.services.http_client.HTTPClientService.get") as mock_get:
        mock_get.return_value = {"state": "idle", "last_updated": "2024-06-01T12:00:00Z"}
        client = TestClient(test_app)
        response = client.get("/api/v1/agents/agent-123/state", headers={"x-api-key": API_KEY})
        assert response.status_code == 200
        data = response.json()
        assert "state" in data

def test_update_agent_state_success(test_app):
    with patch("app.services.http_client.HTTPClientService.put") as mock_put:
        mock_put.return_value = {"state": "active", "last_updated": "2024-06-01T12:00:00Z"}
        client = TestClient(test_app)
        response = client.put(
            "/api/v1/agents/agent-123/state",
            json={"state": "active"},
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "active"

def test_auth_required_on_agents_endpoints(test_app):
    client = TestClient(test_app)
    response = client.get("/api/v1/agents")
    assert response.status_code == 401

# --- Dynamic routing endpoint tests ---
def test_dynamic_route_success(test_app):
    with patch("app.services.http_client.HTTPClientService.forward_request") as mock_forward, \
         patch("app.core.service_registry.ServiceRegistry.get_service_url") as mock_url:
        mock_url.return_value = "http://mock-service"
        mock_forward.return_value = {"result": "ok"}
        client = TestClient(test_app)
        response = client.get("/api/v1/agent-registry/agents", headers={"x-api-key": API_KEY})
        assert response.status_code == 200
        data = response.json()
        assert "result" in data

def test_dynamic_route_service_not_found(test_app):
    with patch("app.core.service_registry.ServiceRegistry.get_service_url", side_effect=Exception("Service not found")):
        client = TestClient(test_app)
        response = client.get("/api/v1/nonexistent-service/foo", headers={"x-api-key": API_KEY})
        assert response.status_code == 404

def test_dynamic_route_auth_required(test_app):
    client = TestClient(test_app)
    response = client.get("/api/v1/agent-registry/agents")
    assert response.status_code == 401

def test_dynamic_route_validation_error(test_app):
    with patch("app.services.http_client.HTTPClientService.forward_request", side_effect=Exception("Validation error")), \
         patch("app.core.service_registry.ServiceRegistry.get_service_url") as mock_url:
        mock_url.return_value = "http://mock-service"
        client = TestClient(test_app)
        response = client.post(
            "/api/v1/agent-registry/agents",
            json={"invalid": "data"},
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code in (422, 503) 