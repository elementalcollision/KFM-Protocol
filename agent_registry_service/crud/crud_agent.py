import logging # Import logging
from typing import Any, Dict, Optional, Union, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc # Import func for count, desc/asc for sorting
from sqlalchemy.orm import Session

from agent_registry_service.models.agent import Agent
from agent_registry_service.schemas.agent import AgentCreate, AgentUpdate, LifecycleStateEnum, AgentStateUpdate

logger = logging.getLogger(__name__) # Get logger for this module

# Helper function to get agent by ID (used internally)
async def get_agent_by_id(db: AsyncSession, agent_id: UUID) -> Optional[Agent]:
    result = await db.execute(select(Agent).filter(Agent.unique_id == agent_id))
    return result.scalars().first()

async def get(db: AsyncSession, agent_id: UUID) -> Optional[Agent]:
    """Get a single agent by unique_id."""
    logger.info(f"Fetching agent with id: {agent_id}")
    return await get_agent_by_id(db, agent_id)

async def get_multi(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    agent_type: Optional[str] = None,
    lifecycle_state: Optional[LifecycleStateEnum] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = True,
) -> tuple[List[Agent], int]: # Return items and total count
    """Get multiple agents with pagination."""
    logger.info(f"Fetching multiple agents: skip={skip}, limit={limit}, type={agent_type}, state={lifecycle_state}, sort={sort_by} ({'DESC' if sort_desc else 'ASC'})")
    # Base query
    stmt = select(Agent)

    # Filtering
    if agent_type:
        stmt = stmt.filter(Agent.type.ilike(f"%{agent_type}%")) # Case-insensitive partial match
    if lifecycle_state:
        stmt = stmt.filter(Agent.lifecycle_state == lifecycle_state)

    # --- Get Total Count --- 
    # Create a separate query for counting to avoid issues with limits/offsets/ordering on count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    # -----------------------

    # Sorting
    if sort_by:
        column_to_sort = getattr(Agent, sort_by, None)
        if column_to_sort:
            order_func = desc if sort_desc else asc
            stmt = stmt.order_by(order_func(column_to_sort))
    else:
        # Default sort
        stmt = stmt.order_by(desc(Agent.creation_timestamp))

    # Pagination
    stmt = stmt.offset(skip).limit(limit)

    # Execute final query for items
    result = await db.execute(stmt)
    items = result.scalars().all()
    logger.info(f"Found {total} agents, returning {len(items)} items.")
    return items, total

async def create(db: AsyncSession, *, obj_in: AgentCreate) -> Agent:
    """Create a new agent."""
    # Convert Pydantic model to dict, excluding unset fields if necessary
    # Use obj_in.model_dump() in Pydantic v2
    obj_in_data = obj_in.model_dump()
    logger.info(f"Creating agent with data: {obj_in_data}")

    db_obj = Agent(**obj_in_data)
    db.add(db_obj)
    try:
        await db.commit()
        await db.refresh(db_obj)
        logger.info(f"Agent created successfully with id: {db_obj.unique_id}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating agent: {e}", exc_info=True)
        raise # Re-raise the exception after logging
    return db_obj

async def update(
    db: AsyncSession, *, db_obj: Agent, obj_in: Union[AgentUpdate, Dict[str, Any]]
) -> Agent:
    """Update an existing agent."""
    # Use obj_in.model_dump() in Pydantic v2
    logger.info(f"Updating agent id: {db_obj.unique_id}")
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        # Exclude unset ensures we only update provided fields (for PATCH)
        update_data = obj_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    try:
        await db.commit()
        await db.refresh(db_obj)
        logger.info(f"Agent id: {db_obj.unique_id} updated successfully.")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating agent id: {db_obj.unique_id}: {e}", exc_info=True)
        raise
    return db_obj

async def remove(db: AsyncSession, *, agent_id: UUID) -> Optional[Agent]:
    """Delete an agent."""
    db_obj = await get_agent_by_id(db, agent_id)
    if db_obj:
        await db.delete(db_obj)
        try:
            await db.commit()
            logger.info(f"Agent id: {agent_id} removed successfully.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error removing agent id: {agent_id}: {e}", exc_info=True)
            raise
    return db_obj # Return the deleted object or None if not found 

async def update_state(db: AsyncSession, *, agent_id: UUID, state_in: AgentStateUpdate) -> Optional[Agent]:
    """Update only the lifecycle_state of an agent."""
    db_obj = await get_agent_by_id(db, agent_id)
    if not db_obj:
        return None

    logger.info(f"Updating state for agent id: {agent_id} to {state_in.lifecycle_state}")
    # Update only the lifecycle_state field
    db_obj.lifecycle_state = state_in.lifecycle_state
    db.add(db_obj)
    try:
        await db.commit()
        await db.refresh(db_obj)
        logger.info(f"Agent id: {agent_id} state updated successfully.")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating state for agent id: {agent_id}: {e}", exc_info=True)
        raise
    return db_obj 