import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4, UUID

# Assuming the FastAPI app instance is importable for the client fixture
# from agent_registry_service.main import app 

# We need a way to create agents in the test DB first
# Assuming schemas are available
from agent_registry_service.schemas.agent import AgentCreate, AgentStateUpdate, LifecycleStateEnum

# Use client fixture provided by conftest.py (assumed setup)

@pytest.mark.asyncio
async def test_create_agent_for_state_tests(client: AsyncClient) -> UUID:
    """Helper to create an agent and return its ID."""
    agent_data = {
        "name": f"State Test Agent {uuid4()}",
        "type": "TestType",
        "version": "1.0"
        # Assuming other required fields like owner are handled or not required by AgentCreate
    }
    response = await client.post("/api/v1/agents/", json=agent_data)
    assert response.status_code == status.HTTP_201_CREATED
    agent_id = response.json().get("unique_id")
    assert agent_id is not None
    return UUID(agent_id)

@pytest.mark.asyncio
async def test_update_agent_state_success(client: AsyncClient):
    """Test successfully updating an agent's state via the API."""
    agent_id = await test_create_agent_for_state_tests(client)
    
    # Initial state should be NEW (based on model default)
    response = await client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("lifecycle_state") == LifecycleStateEnum.NEW.value

    # Transition NEW -> EXPERIMENTAL
    state_update_data = {"lifecycle_state": LifecycleStateEnum.EXPERIMENTAL.value}
    response = await client.put(f"/api/v1/agents/{agent_id}/state", json=state_update_data)
    assert response.status_code == status.HTTP_200_OK
    updated_agent = response.json()
    assert updated_agent.get("lifecycle_state") == LifecycleStateEnum.EXPERIMENTAL.value
    assert updated_agent.get("unique_id") == str(agent_id)

    # Verify the state is persisted
    response = await client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("lifecycle_state") == LifecycleStateEnum.EXPERIMENTAL.value

@pytest.mark.asyncio
async def test_update_agent_state_not_found(client: AsyncClient):
    """Test updating state for a non-existent agent."""
    non_existent_id = uuid4()
    state_update_data = {"lifecycle_state": LifecycleStateEnum.EXPERIMENTAL.value}
    response = await client.put(f"/api/v1/agents/{non_existent_id}/state", json=state_update_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_update_agent_state_invalid_transition(client: AsyncClient):
    """Test attempting an invalid state transition via the API."""
    agent_id = await test_create_agent_for_state_tests(client)
    
    # Initial state is NEW. Try transitioning NEW -> STABLE (invalid)
    state_update_data = {"lifecycle_state": LifecycleStateEnum.STABLE.value}
    response = await client.put(f"/api/v1/agents/{agent_id}/state", json=state_update_data)
    
    # We expect the CRUD layer (or state machine logic called by it) 
    # to reject this and result in an error. The exact status code might vary 
    # depending on implementation (e.g., 400 Bad Request if validation happens).
    # If crud_agent.update_state doesn't perform validation itself but relies on 
    # the StateMachine class raising InvalidTransitionError, we need an exception handler.
    # Assuming a 400 Bad Request for now.
    assert response.status_code == status.HTTP_400_BAD_REQUEST 
    # assert "Invalid transition" in response.json().get("detail", "") # Check detail message if available

    # Verify state hasn't changed
    response = await client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("lifecycle_state") == LifecycleStateEnum.NEW.value

@pytest.mark.asyncio
async def test_update_agent_state_invalid_payload(client: AsyncClient):
    """Test sending invalid data to the state update endpoint."""
    agent_id = await test_create_agent_for_state_tests(client)
    
    # Invalid state value
    invalid_state_data = {"lifecycle_state": "INVALID_STATE_VALUE"}
    response = await client.put(f"/api/v1/agents/{agent_id}/state", json=invalid_state_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY # FastAPI validation error

    # Missing state field
    missing_state_data = {"other_field": "value"}
    response = await client.put(f"/api/v1/agents/{agent_id}/state", json=missing_state_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY 