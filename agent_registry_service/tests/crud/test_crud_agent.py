import pytest
from uuid import uuid4
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from agent_registry_service import crud
from agent_registry_service import schemas
from agent_registry_service.models import Agent, LifecycleStateEnum

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

async def test_create_agent(db_session: AsyncSession):
    agent_in = schemas.AgentCreate(
        type="AI Model",
        version="1.0.0",
        owner="Test Team",
        lifecycle_state=LifecycleStateEnum.EXPERIMENTAL
    )
    agent = await crud.agent.create(db=db_session, obj_in=agent_in)
    assert agent.type == agent_in.type
    assert agent.version == agent_in.version
    assert agent.owner == agent_in.owner
    assert agent.lifecycle_state == agent_in.lifecycle_state
    assert agent.unique_id is not None
    assert agent.creation_timestamp is not None

async def test_get_agent(db_session: AsyncSession):
    agent_in = schemas.AgentCreate(type="Service", version="0.1-alpha")
    created_agent = await crud.agent.create(db=db_session, obj_in=agent_in)

    fetched_agent = await crud.agent.get(db=db_session, agent_id=created_agent.unique_id)
    assert fetched_agent
    assert fetched_agent.unique_id == created_agent.unique_id
    assert fetched_agent.type == created_agent.type

async def test_get_nonexistent_agent(db_session: AsyncSession):
    non_existent_id = uuid4()
    fetched_agent = await crud.agent.get(db=db_session, agent_id=non_existent_id)
    assert fetched_agent is None

async def test_get_multi_agent(db_session: AsyncSession):
    agent1_in = schemas.AgentCreate(type="AI Model", version="1.0")
    agent2_in = schemas.AgentCreate(type="Software", version="2.1")
    await crud.agent.create(db=db_session, obj_in=agent1_in)
    await crud.agent.create(db=db_session, obj_in=agent2_in)

    agents, total = await crud.agent.get_multi(db=db_session, skip=0, limit=10)
    assert total == 2
    assert len(agents) == 2

async def test_get_multi_agent_pagination(db_session: AsyncSession):
    for i in range(5):
        await crud.agent.create(db=db_session, obj_in=schemas.AgentCreate(type=f"Type {i}", version=str(i)))

    agents_page1, total1 = await crud.agent.get_multi(db=db_session, skip=0, limit=2)
    assert total1 == 5
    assert len(agents_page1) == 2

    agents_page2, total2 = await crud.agent.get_multi(db=db_session, skip=2, limit=2)
    assert total2 == 5
    assert len(agents_page2) == 2

    agents_page3, total3 = await crud.agent.get_multi(db=db_session, skip=4, limit=2)
    assert total3 == 5
    assert len(agents_page3) == 1

async def test_get_multi_agent_filtering(db_session: AsyncSession):
    await crud.agent.create(db=db_session, obj_in=schemas.AgentCreate(type="Model", version="1", lifecycle_state=LifecycleStateEnum.STABLE))
    await crud.agent.create(db=db_session, obj_in=schemas.AgentCreate(type="Service", version="2", lifecycle_state=LifecycleStateEnum.EXPERIMENTAL))
    await crud.agent.create(db=db_session, obj_in=schemas.AgentCreate(type="Model", version="3", lifecycle_state=LifecycleStateEnum.STABLE))

    # Filter by type
    agents_model, total_model = await crud.agent.get_multi(db=db_session, agent_type="Model")
    assert total_model == 2
    assert len(agents_model) == 2

    # Filter by state
    agents_stable, total_stable = await crud.agent.get_multi(db=db_session, lifecycle_state=LifecycleStateEnum.STABLE)
    assert total_stable == 2
    assert len(agents_stable) == 2

    # Filter by type and state
    agents_combo, total_combo = await crud.agent.get_multi(db=db_session, agent_type="Service", lifecycle_state=LifecycleStateEnum.EXPERIMENTAL)
    assert total_combo == 1
    assert len(agents_combo) == 1
    assert agents_combo[0].version == "2"


async def test_update_agent(db_session: AsyncSession):
    agent_in = schemas.AgentCreate(type="InitialType", version="1.0")
    created_agent = await crud.agent.create(db=db_session, obj_in=agent_in)

    update_data = schemas.AgentUpdate(owner="NewOwner", version="1.1")
    updated_agent = await crud.agent.update(db=db_session, db_obj=created_agent, obj_in=update_data)

    assert updated_agent.unique_id == created_agent.unique_id
    assert updated_agent.type == "InitialType" # Type not updated
    assert updated_agent.version == "1.1"
    assert updated_agent.owner == "NewOwner"

async def test_update_agent_state(db_session: AsyncSession):
    agent_in = schemas.AgentCreate(type="TestState", version="1.0", lifecycle_state=LifecycleStateEnum.NEW)
    created_agent = await crud.agent.create(db=db_session, obj_in=agent_in)

    state_update_data = schemas.AgentStateUpdate(lifecycle_state=LifecycleStateEnum.STABLE)
    updated_agent = await crud.agent.update_state(db=db_session, agent_id=created_agent.unique_id, state_in=state_update_data)

    assert updated_agent
    assert updated_agent.unique_id == created_agent.unique_id
    assert updated_agent.lifecycle_state == LifecycleStateEnum.STABLE

async def test_remove_agent(db_session: AsyncSession):
    agent_in = schemas.AgentCreate(type="ToBeDeleted", version="1.0")
    created_agent = await crud.agent.create(db=db_session, obj_in=agent_in)

    removed_agent = await crud.agent.remove(db=db_session, agent_id=created_agent.unique_id)
    assert removed_agent
    assert removed_agent.unique_id == created_agent.unique_id

    # Verify it's actually gone
    fetched_agent = await crud.agent.get(db=db_session, agent_id=created_agent.unique_id)
    assert fetched_agent is None 