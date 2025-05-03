import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Path, Security
from fastapi.responses import Response, JSONResponse
from pydantic import ValidationError

from app.core.config import APIGatewaySettings, get_settings
from app.core.service_registry import ServiceRegistry, get_service_registry
from app.core.errors import ServiceNotFoundError, ServiceUnavailableError, ServiceConnectionError
from app.services.http_client import HTTPClientService, get_http_client
from app.api import api_router
from app.api.endpoints import async_tasks
from app.api.endpoints.async_tasks import get_api_key
from app.schemas.base import ErrorResponse


logger = logging.getLogger(__name__)

# Create router for dynamic routing
router = APIRouter()

# Include API routers
# router.include_router(api_router) # This seems incorrect, api_router uses this router
router.include_router(async_tasks.router, prefix="/async", tags=["AsyncTasks"])


@router.api_route("/{service}/{path:path}", 
                  methods=["GET", "POST", "PUT", "DELETE", "PATCH"], 
                  summary="Dynamic Proxy Route",
                  # Use a separate variable for the long description
                  description=(
                      "Forwards requests to the appropriate backend KFM microservice based on the `{service}` path parameter. "
                      "Handles authentication via `X-API-Key` header and proxies the request including path, query parameters, and body.\n\n"
                      "**Available Services (based on current gateway configuration):**\n"
                      "*   `agent-registry`\n"
                      "*   `f-operator`\n"
                      "*   `m-operator`\n"
                      "*   `k-operator`\n"
                      # Add others as they get registered in config
                      # "*   `agent-discovery`\n"
                      # "*   `policy-engine`\n"
                      # "*   `resource-manager`\n\n"
                      "**Note:** Specific path parameters (`{path:path}`) and request/response bodies depend on the target backend service's API contract. "
                      "Refer to individual service documentation for details."
                  ),
                  # Define responses correctly
                  responses={
                      200: {"description": "Success (Response structure depends on backend service)"},
                      202: {"description": "Accepted (For asynchronous tasks, includes task ID)", "model": async_tasks.TaskResponse},
                      400: {"description": "Bad Request (e.g., invalid input for backend service)", "model": ErrorResponse},
                      401: {"description": "Invalid or missing API key", "model": ErrorResponse},
                      403: {"description": "Forbidden (Insufficient permissions)", "model": ErrorResponse},
                      404: {"description": "Service or backend resource not found", "model": ErrorResponse},
                      422: {"description": "Validation Error (Request body validation failed)", "model": ErrorResponse},
                      502: {"description": "Bad Gateway (Error connecting to backend service)", "model": ErrorResponse},
                      503: {"description": "Service Unavailable (Backend service unavailable or circuit breaker open)", "model": ErrorResponse},
                      500: {"description": "Internal Server Error (Unexpected gateway or backend error)", "model": ErrorResponse}
                  }
                 )
async def dynamic_route(
    request: Request,
    # Add example values for OpenAPI
    service: str = Path(..., description="The name of the target backend service (e.g., 'agent-registry', 'f-operator').", example="agent-registry"),
    path: str = Path(..., description="The specific API path within the target service.", example="agents/some-uuid/state"),
    service_registry: ServiceRegistry = Depends(get_service_registry),
    http_client: HTTPClientService = Depends(get_http_client),
    # Use alias for OpenAPI documentation, actual dependency check happens via get_api_key
    api_key: str = Security(get_api_key, name="X-API-Key") 
):
    """
    **Dynamic Proxy Route**

    Proxies incoming requests to the correct backend KFM microservice.

    - **service**: Name of the target service (e.g., `agent-registry`).
    - **path**: The endpoint path on the target service (e.g., `agents` or `agents/some-uuid/state`).
    - Requires valid `X-API-Key` header for authentication.
    - Forwards methods, headers, query parameters, and body.
    """
    try:
        # Get target service URL
        service_url = service_registry.get_service_url(service)
        
        # Extract path parameters (excluding service and path)
        path_params = request.path_params.copy()
        path_params.pop("service")
        path_params.pop("path")
        
        # Get request body if present
        body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
        
        # Forward request to backend service
        response = await http_client.forward_request(
            method=request.method,
            url=f"{service_url}/{path}",
            headers=dict(request.headers),
            params=dict(request.query_params),
            path_params=path_params,
            body=body
        )
        
        return response
        
    except ServiceNotFoundError as e:
        logger.warning(f"Service not found: {service}")
        raise HTTPException(status_code=404, detail=str(e))
        
    except ServiceUnavailableError as e:
        logger.warning(f"Service unavailable: {service}")
        raise HTTPException(status_code=503, detail=str(e))
        
    except ServiceConnectionError as e:
        logger.error(f"Service connection error: {service} - {str(e)}")
        # Mark service as unavailable
        service_registry.mark_service_unavailable(service)
        raise HTTPException(status_code=502, detail=str(e))
        
    except ValidationError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
        
    except Exception as e:
        logger.exception(f"Unexpected error in dynamic routing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# Add health check endpoint
@router.get("/health", responses={
    401: {"description": "Invalid or missing API key", "model": ErrorResponse}
})
async def health_check(
    service_registry: ServiceRegistry = Depends(get_service_registry),
    dep=Depends(get_api_key)
):
    """
    Health check endpoint for API Gateway and registered services.

    Authentication: Requires a valid X-API-Key header.
    
    Returns the status of the API Gateway and all registered backend services.
    
    Error Responses:
      - 401: Invalid or missing API key
    
    Example:
      curl -H "X-API-Key: <your-key>" http://localhost:8000/api/v1/health
    """
    services_status = {}
    for service_name, service_info in service_registry.services.items():
        services_status[service_name] = {
            "url": service_info.url,
            "available": service_info.available,
            "last_check": service_info.last_check
        }
        
    return {
        "status": "ok",
        "services": services_status
    } 