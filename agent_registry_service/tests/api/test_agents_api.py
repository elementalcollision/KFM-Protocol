import pytest
from typing import Dict, Any, Optional
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from agent_registry_service import crud, schemas
from agent_registry_service.core.config import settings
from agent_registry_service.models import User, Agent, LifecycleStateEnum
from agent_registry_service.core.security import create_access_token

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

API_V1_STR = settings.API_V1_STR

# --- Test User Setup --- 

async def create_test_user(db: AsyncSession) -> User:
    from agent_registry_service.core.security import get_password_hash
    # Simplified user creation for tests
    user = User(
        username=f"testuser_{uuid4()}@example.com", 
        hashed_password=get_password_hash("testpassword"), 
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# Fixture to create a user and generate a token for tests
@pytest.fixture(scope="function")
async def test_user_token(db_session: AsyncSession) -> Dict[str, str]:
    user = await create_test_user(db_session)
    token = create_access_token(subject=user.username) # Use username as subject
    return {"Authorization": f"Bearer {token}"}

# --- Agent Test Data --- 

def get_valid_agent_create_data() -> Dict[str, Any]:
    return {
        "type": "API Service",
        "version": "v1.0",
        "owner": "Testing Dept",
        "lifecycle_state": "NEW"
    }

# --- API Tests --- 

async def test_create_agent_success(client: AsyncClient, test_user_token: Dict[str, str]):
    data = get_valid_agent_create_data()
    response = await client.post(f"{API_V1_STR}/agents/", headers=test_user_token, json=data)
    assert response.status_code == 201
    content = response.json()
    assert content["type"] == data["type"]
    assert content["version"] == data["version"]
    assert content["owner"] == data["owner"]
    assert content["lifecycle_state"] == data["lifecycle_state"]
    assert "unique_id" in content
    assert "creation_timestamp" in content

async def test_create_agent_unauthenticated(client: AsyncClient):
    data = get_valid_agent_create_data()
    response = await client.post(f"{API_V1_STR}/agents/", json=data)
    assert response.status_code == 403 # Assuming default FastAPI behavior for missing auth

async def test_read_agent_success(client: AsyncClient, db_session: AsyncSession, test_user_token: Dict[str, str]):
    # Create an agent first
    agent_in = schemas.AgentCreate(**get_valid_agent_create_data())
    agent = await crud.agent.create(db=db_session, obj_in=agent_in)

    response = await client.get(f"{API_V1_STR}/agents/{agent.unique_id}", headers=test_user_token)
    assert response.status_code == 200
    content = response.json()
    assert content["unique_id"] == str(agent.unique_id)
    assert content["type"] == agent.type

async def test_read_agent_not_found(client: AsyncClient, test_user_token: Dict[str, str]):
    non_existent_id = uuid4()
    response = await client.get(f"{API_V1_STR}/agents/{non_existent_id}", headers=test_user_token)
    assert response.status_code == 404

async def test_read_agents_list(client: AsyncClient, db_session: AsyncSession, test_user_token: Dict[str, str]):
    # Create a couple of agents
    await crud.agent.create(db=db_session, obj_in=schemas.AgentCreate(**get_valid_agent_create_data()))
    await crud.agent.create(db=db_session, obj_in=schemas.AgentCreate(type="Model", version="2.0"))

    response = await client.get(f"{API_V1_STR}/agents/", headers=test_user_token, params={"limit": 5})
    assert response.status_code == 200
    content = response.json()
    assert content["total"] == 2
    assert len(content["items"]) == 2

async def test_read_agents_list_pagination_filter_sort(client: AsyncClient, db_session: AsyncSession, test_user_token: Dict[str, str]):
    # Create agents with different properties
    data1 = get_valid_agent_create_data()
    data1["type"] = "ServiceA"
    data1["lifecycle_state"] = "STABLE"
    await crud.agent.create(db=db_session, obj_in=schemas.AgentCreate(**data1))
    await asyncio.sleep(0.01) # Ensure distinct timestamps
    data2 = get_valid_agent_create_data()
    data2["type"] = "ModelB"
    data2["lifecycle_state"] = "EXPERIMENTAL"
    await crud.agent.create(db=db_session, obj_in=schemas.AgentCreate(**data2))
    await asyncio.sleep(0.01)
    data3 = get_valid_agent_create_data()
    data3["type"] = "ServiceA"
    data3["lifecycle_state"] = "STABLE"
    await crud.agent.create(db=db_session, obj_in=schemas.AgentCreate(**data3))

    # Test filtering by type
    response = await client.get(f"{API_V1_STR}/agents/", headers=test_user_token, params={"agent_type": "ServiceA"})
    assert response.status_code == 200
    assert response.json()["total"] == 2

    # Test filtering by state
    response = await client.get(f"{API_V1_STR}/agents/", headers=test_user_token, params={"lifecycle_state": "STABLE"})
    assert response.status_code == 200
    assert response.json()["total"] == 2

    # Test pagination
    response = await client.get(f"{API_V1_STR}/agents/", headers=test_user_token, params={"limit": 1, "skip": 1})
    assert response.status_code == 200
    content = response.json()
    assert content["total"] == 3
    assert len(content["items"]) == 1
    # Check if the second item created is returned (default sort desc timestamp)
    assert content["items"][0]["type"] == "ModelB"

    # Test sorting (e.g., by type ascending)
    response = await client.get(f"{API_V1_STR}/agents/", headers=test_user_token, params={"sort_by": "type", "sort_desc": "false"})
    assert response.status_code == 200
    content = response.json()
    assert content["total"] == 3
    assert content["items"][0]["type"] == "ModelB"
    assert content["items"][1]["type"] == "ServiceA"
    assert content["items"][2]["type"] == "ServiceA"


async def test_update_agent_success(client: AsyncClient, db_session: AsyncSession, test_user_token: Dict[str, str]):
    # Create an agent first
    agent_in = schemas.AgentCreate(**get_valid_agent_create_data())
    agent = await crud.agent.create(db=db_session, obj_in=agent_in)

    update_data = {"owner": "Updated Owner", "version": "v1.1-beta"}
    response = await client.put(f"{API_V1_STR}/agents/{agent.unique_id}", headers=test_user_token, json=update_data)
    assert response.status_code == 200
    content = response.json()
    assert content["unique_id"] == str(agent.unique_id)
    assert content["owner"] == update_data["owner"]
    assert content["version"] == update_data["version"]
    assert content["type"] == agent.type # Should not change

async def test_update_agent_not_found(client: AsyncClient, test_user_token: Dict[str, str]):
    non_existent_id = uuid4()
    update_data = {"owner": "Updated Owner"}
    response = await client.put(f"{API_V1_STR}/agents/{non_existent_id}", headers=test_user_token, json=update_data)
    assert response.status_code == 404

async def test_update_agent_state_success(client: AsyncClient, db_session: AsyncSession, test_user_token: Dict[str, str]):
    agent_in = schemas.AgentCreate(**get_valid_agent_create_data(), lifecycle_state=LifecycleStateEnum.NEW)
    agent = await crud.agent.create(db=db_session, obj_in=agent_in)

    state_update_data = {"lifecycle_state": "STABLE"}
    response = await client.put(f"{API_V1_STR}/agents/{agent.unique_id}/state", headers=test_user_token, json=state_update_data)
    assert response.status_code == 200
    content = response.json()
    assert content["unique_id"] == str(agent.unique_id)
    assert content["lifecycle_state"] == "STABLE"

async def test_update_agent_state_not_found(client: AsyncClient, test_user_token: Dict[str, str]):
    non_existent_id = uuid4()
    state_update_data = {"lifecycle_state": "STABLE"}
    response = await client.put(f"{API_V1_STR}/agents/{non_existent_id}/state", headers=test_user_token, json=state_update_data)
    assert response.status_code == 404

async def test_delete_agent_success(client: AsyncClient, db_session: AsyncSession, test_user_token: Dict[str, str]):
    agent_in = schemas.AgentCreate(**get_valid_agent_create_data())
    agent = await crud.agent.create(db=db_session, obj_in=agent_in)

    response = await client.delete(f"{API_V1_STR}/agents/{agent.unique_id}", headers=test_user_token)
    assert response.status_code == 200
    content = response.json()
    assert content["unique_id"] == str(agent.unique_id)

    # Verify deletion
    response_get = await client.get(f"{API_V1_STR}/agents/{agent.unique_id}", headers=test_user_token)
    assert response_get.status_code == 404

async def test_delete_agent_not_found(client: AsyncClient, test_user_token: Dict[str, str]):
    non_existent_id = uuid4()
    response = await client.delete(f"{API_V1_STR}/agents/{non_existent_id}", headers=test_user_token)
    assert response.status_code == 404 