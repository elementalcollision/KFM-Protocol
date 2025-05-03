import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Adjust imports based on the actual location relative to service root
# Assuming this file is at agent_registry_service/api/endpoints/agents.py
from agent_registry_service import crud, schemas 
from agent_registry_service.db.session import get_db
from agent_registry_service.core.registry_manager import RegistryManager, get_registry_manager
# from agent_registry_service.api import deps # Check correct path for deps if needed
# from agent_registry_service import models # If needed for auth, etc.

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/", 
    response_model=schemas.AgentRegistryEntry, 
    status_code=status.HTTP_201_CREATED,
    summary="Register Agent",
    description="Registers a new agent instance in the central registry."
)
async def register_agent(
    *, 
    db: AsyncSession = Depends(get_db),
    manager: RegistryManager = Depends(get_registry_manager),
    agent_in: schemas.AgentCreateSchema,
    # current_user: models.User = Depends(deps.get_current_active_user) # Example: Add auth if needed
):
    """Registers a new agent instance."""
    logger.info(f"Registering new agent of type: {agent_in.type}")
    try:
        # Use the manager to handle registration (which includes DB and memory update)
        registered_agent = await manager.register_agent(obj_in=agent_in, db=db)
        return registered_agent
    except Exception as e: # Catch potential DB errors or other issues
        # TODO: Implement more specific exception handling (e.g., duplicate entry?)
        logger.error(f"Error registering agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to register agent."
        )


@router.get(
    "/", 
    response_model=List[schemas.AgentRegistryEntry],
    summary="List Agents",
    description="Retrieves a list of registered agents from the in-memory store."
)
async def list_agents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    manager: RegistryManager = Depends(get_registry_manager),
    # current_user: models.User = Depends(deps.get_current_active_user) 
):
    """Retrieve a list of registered agents from the in-memory store."""
    logger.info(f"Listing agents (limit={limit}, skip={skip})")
    # Get agents directly from the manager's in-memory store
    all_agents = await manager.get_all_agents()
    # Apply pagination manually 
    return all_agents[skip : skip + limit]


@router.get(
    "/{agent_id}", 
    response_model=schemas.AgentRegistryEntry,
    summary="Get Agent Details",
    description="Gets details for a specific agent by ID from the in-memory store."
)
async def get_agent_details(
    agent_id: uuid.UUID,
    manager: RegistryManager = Depends(get_registry_manager),
    # current_user: models.User = Depends(deps.get_current_active_user)
):
    """Get details for a specific agent by ID from the in-memory store."""
    logger.info(f"Getting details for agent {agent_id}")
    agent = await manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.put(
    "/{agent_id}", 
    response_model=schemas.AgentRegistryEntry,
    summary="Update Agent Details",
    description="Updates an existing agent's details in the registry."
)
async def update_agent_details(
    agent_id: uuid.UUID,
    *, 
    db: AsyncSession = Depends(get_db),
    manager: RegistryManager = Depends(get_registry_manager),
    agent_in: schemas.AgentUpdateSchema,
    # current_user: models.User = Depends(deps.get_current_active_user) 
):
    """Update an existing agent's details."""
    logger.info(f"Updating agent {agent_id}")
    updated_agent = await manager.update_agent(agent_id=agent_id, obj_in=agent_in, db=db)
    if not updated_agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return updated_agent


@router.delete(
    "/{agent_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deregister Agent",
    description="Deregisters an agent (removes from registry)."
)
async def deregister_agent(
    agent_id: uuid.UUID,
    *, 
    db: AsyncSession = Depends(get_db),
    manager: RegistryManager = Depends(get_registry_manager),
    # current_user: models.User = Depends(deps.get_current_active_user)
):
    """Deregister an agent (remove from registry)."""
    logger.info(f"Deregistering agent {agent_id}")
    success = await manager.deregister_agent(agent_id=agent_id, db=db)
    if not success:
        # Technically, deleting a non-existent resource is often idempotent (DELETE RFC)
        # So, returning 204 is acceptable even if it wasn't found.
        # If strict feedback is needed, raise 404 here.
        logger.warning(f"Attempted to deregister non-existent agent {agent_id}, returning 204 anyway.")
        pass # Or raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return None # Return No Content for 204 status


# Discovery Endpoint
@router.post(
    "/discover", 
    response_model=schemas.PaginatedAgentResponse, # Use the pagination schema
    summary="Discover Agents",
    description="Discovers agents based on specified criteria."
)
async def discover_agents_endpoint(
    criteria: schemas.DiscoveryCriteria,
    manager: RegistryManager = Depends(get_registry_manager),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth
):
    """Discover agents based on criteria using the RegistryManager."""
    logger.info(f"Discovering agents with criteria: {criteria.model_dump(exclude_defaults=True)}")
    try:
        # Use the discover_agents method from the manager
        agents, total = await manager.discover_agents(criteria=criteria)
        
        # Return paginated response
        return schemas.PaginatedAgentResponse(
            items=agents,
            total=total,
            limit=criteria.pagination.limit,
            skip=criteria.pagination.skip
        )
    except ValueError as ve:
        logger.warning(f"Invalid discovery criteria: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error discovering agents: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to discover agents")

# Removed old placeholder discover endpoint 