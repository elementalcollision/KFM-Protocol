from typing import List, Optional, Type
import uuid
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload # If needed for relationships

from agent_registry_service.models.agent_registry_entry import AgentRegistryEntryModel
from agent_registry_service.schemas.agent_registry_entry import AgentCreateSchema, AgentUpdateSchema


async def get_agent_entry(
    db: AsyncSession, agent_id: uuid.UUID
) -> Optional[AgentRegistryEntryModel]:
    """Get a single agent entry by ID."""
    result = await db.execute(select(AgentRegistryEntryModel).filter(AgentRegistryEntryModel.id == agent_id))
    return result.scalars().first()


async def get_all_agent_entries(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[AgentRegistryEntryModel]:
    """Get all agent entries with pagination."""
    result = await db.execute(
        select(AgentRegistryEntryModel)
        .offset(skip)
        .limit(limit)
        .order_by(AgentRegistryEntryModel.created_at) # Optional: order by creation time
    )
    return result.scalars().all()


async def create_agent_entry(
    db: AsyncSession, *, obj_in: AgentCreateSchema
) -> AgentRegistryEntryModel:
    """Create a new agent entry."""
    # Pydantic V2: use model_dump, exclude_unset=True might be useful
    obj_in_data = obj_in.model_dump()
    db_obj = AgentRegistryEntryModel(**obj_in_data)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update_agent_entry(
    db: AsyncSession, *, db_obj: AgentRegistryEntryModel, obj_in: AgentUpdateSchema | dict
) -> AgentRegistryEntryModel:
    """Update an existing agent entry."""
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        # Pydantic V2: use model_dump with exclude_unset=True
        update_data = obj_in.model_dump(exclude_unset=True)
        
    # Ensure updated_at is always set
    update_data["updated_at"] = datetime.utcnow()

    for field, value in update_data.items():
        setattr(db_obj, field, value)
        
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete_agent_entry(db: AsyncSession, *, agent_id: uuid.UUID) -> Optional[AgentRegistryEntryModel]:
    """Delete an agent entry by ID."""
    db_obj = await get_agent_entry(db, agent_id)
    if db_obj:
        await db.delete(db_obj)
        await db.commit()
    return db_obj 