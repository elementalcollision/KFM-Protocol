import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.core.service_registry import ServiceRegistry, get_service_registry
from app.core.errors import ServiceNotFoundError, ServiceUnavailableError, ServiceConnectionError
from app.services.http_client import HTTPClientService, get_http_client
from app.core.cache import get_response_cache
from app.core.config import get_settings
from app.core.circuit_breaker import CircuitBreakerOpenException
from app.api.endpoints.async_tasks import get_api_key
from app.schemas.base import ErrorResponse


logger = logging.getLogger(__name__)

# Create router for agent operations
router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/", responses={
    401: {"description": "Invalid or missing API key", "model": ErrorResponse},
    503: {"description": "Agent Registry service unavailable", "model": ErrorResponse}
})
async def list_agents(
    request: Request,
    http_client: HTTPClientService = Depends(get_http_client),
    dep=Depends(get_api_key)
):
    """
    List all agents with optional filtering and caching.

    Authentication: Requires a valid X-API-Key header.
    
    Returns a list of all registered agents. Uses response caching for performance.
    
    Error Responses:
      - 401: Invalid or missing API key
      - 503: Agent Registry service unavailable
    
    Example:
      curl -H "X-API-Key: <your-key>" http://localhost:8000/api/v1/agents
    """
    cache = get_response_cache()
    cache_key = "agents_list"
    
    # Try to get from cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        # Add cache header to response
        return {"agents": cached_data, "cache": "hit"}
    
    try:
        # Get from backend service
        settings = get_settings()
        response = await http_client.get(
            f"{settings.AGENT_REGISTRY_URL}/agents",
            service="agent-registry",
            endpoint="list_agents"
        )
        
        # Cache the response for 30 seconds
        await cache.set(cache_key, response, ttl_seconds=30)
        
        return {"agents": response, "cache": "miss"}
        
    except CircuitBreakerOpenException:
        # Circuit breaker is open, try to serve stale data if available
        stale_data = await cache.get(cache_key)
        if stale_data:
            return {"agents": stale_data, "cache": "stale", "circuit": "open"}
        
        # No stale data, return fallback empty response
        return {"agents": [], "cache": "none", "circuit": "open", "message": "Service temporarily unavailable"}
        
    except ServiceConnectionError as e:
        logger.error(f"Failed to connect to agent-registry service: {str(e)}")
        raise HTTPException(status_code=503, detail="Agent Registry service unavailable")


@router.get("/{agent_id}", responses={
    401: {"description": "Invalid or missing API key", "model": ErrorResponse},
    503: {"description": "Agent Registry service unavailable or circuit breaker open", "model": ErrorResponse}
})
async def get_agent(
    agent_id: str,
    request: Request,
    http_client: HTTPClientService = Depends(get_http_client),
    dep=Depends(get_api_key)
):
    """
    Get details for a specific agent by ID.

    Authentication: Requires a valid X-API-Key header.
    
    Returns agent details for the given agent ID.
    
    Error Responses:
      - 401: Invalid or missing API key
      - 503: Agent Registry service unavailable or circuit breaker open
    
    Example:
      curl -H "X-API-Key: <your-key>" http://localhost:8000/api/v1/agents/<agent_id>
    """
    try:
        settings = get_settings()
        response = await http_client.get(
            f"{settings.AGENT_REGISTRY_URL}/agents/{agent_id}",
            service="agent-registry",
            endpoint="get_agent"
        )
        return response
        
    except CircuitBreakerOpenException:
        logger.warning(f"Circuit breaker open for agent-registry.get_agent")
        raise HTTPException(
            status_code=503, 
            detail="Agent Registry service temporarily unavailable due to circuit breaker"
        )
        
    except ServiceConnectionError as e:
        logger.error(f"Failed to connect to agent-registry service: {str(e)}")
        raise HTTPException(status_code=503, detail="Agent Registry service unavailable")


@router.get("/{agent_id}/state", responses={
    401: {"description": "Invalid or missing API key", "model": ErrorResponse},
    503: {"description": "Agent Registry service unavailable", "model": ErrorResponse},
    500: {"description": "Unexpected error", "model": ErrorResponse}
})
async def get_agent_state(
    agent_id: str,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    http_client: HTTPClientService = Depends(get_http_client),
    dep=Depends(get_api_key)
):
    """
    Get the current state for a specific agent by ID.

    Authentication: Requires a valid X-API-Key header.
    
    Returns the state information for the specified agent.
    
    Error Responses:
      - 401: Invalid or missing API key
      - 503: Agent Registry service unavailable
      - 500: Unexpected error
    
    Example:
      curl -H "X-API-Key: <your-key>" http://localhost:8000/api/v1/agents/<agent_id>/state
    """
    try:
        # Get agent registry service URL
        agent_registry_url = service_registry.get_service_url("agent-registry")
            
        # Call agent registry service
        response = await http_client.get(
            f"{agent_registry_url}/agents/{agent_id}/state"
        )
        
        return response
        
    except (ServiceNotFoundError, ServiceUnavailableError, ServiceConnectionError) as e:
        logger.error(f"Error accessing agent registry service: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Agent registry service unavailable: {str(e)}")
        
    except Exception as e:
        logger.exception(f"Unexpected error getting agent state for {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.put("/{agent_id}/state", responses={
    401: {"description": "Invalid or missing API key", "model": ErrorResponse},
    503: {"description": "Agent Registry service unavailable", "model": ErrorResponse},
    500: {"description": "Unexpected error", "model": ErrorResponse}
})
async def update_agent_state(
    agent_id: str,
    state: Dict[str, Any],
    service_registry: ServiceRegistry = Depends(get_service_registry),
    http_client: HTTPClientService = Depends(get_http_client),
    dep=Depends(get_api_key)
):
    """
    Update the state for a specific agent by ID.

    Authentication: Requires a valid X-API-Key header.
    
    Updates the state of the specified agent with the provided data.
    
    Error Responses:
      - 401: Invalid or missing API key
      - 503: Agent Registry service unavailable
      - 500: Unexpected error
    
    Example:
      curl -X PUT -H "X-API-Key: <your-key>" -H "Content-Type: application/json" \
        -d '{"state": {"status": "active"}}' \
        http://localhost:8000/api/v1/agents/<agent_id>/state
    """
    try:
        # Get agent registry service URL
        agent_registry_url = service_registry.get_service_url("agent-registry")
            
        # Call agent registry service
        response = await http_client.put(
            f"{agent_registry_url}/agents/{agent_id}/state",
            json=state
        )
        
        return response
        
    except (ServiceNotFoundError, ServiceUnavailableError, ServiceConnectionError) as e:
        logger.error(f"Error accessing agent registry service: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Agent registry service unavailable: {str(e)}")
        
    except Exception as e:
        logger.exception(f"Unexpected error updating agent state for {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") 