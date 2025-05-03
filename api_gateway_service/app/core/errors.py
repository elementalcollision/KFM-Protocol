from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, Dict, Any, List


class ServiceNotFoundError(Exception):
    """Raised when a requested service is not found in the registry."""
    pass


class ServiceUnavailableError(Exception):
    """Raised when a service is temporarily unavailable."""
    pass


class ServiceConnectionError(Exception):
    """Raised when connection to a service fails."""
    pass


async def service_not_found_handler(request: Request, exc: ServiceNotFoundError) -> JSONResponse:
    """Handle ServiceNotFoundError exceptions."""
    return JSONResponse(
        status_code=404,
        content={
            "request_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "api_gateway",
            "target_service": "client",
            "api_version": "v1",
            "error": {
                "code": "SERVICE_NOT_FOUND",
                "message": str(exc)
            },
            "status_code": 404
        }
    )


async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    """Handle ServiceUnavailableError exceptions."""
    return JSONResponse(
        status_code=503,
        content={
            "request_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "api_gateway",
            "target_service": "client",
            "api_version": "v1",
            "error": {
                "code": "SERVICE_UNAVAILABLE",
                "message": str(exc)
            },
            "status_code": 503
        }
    )


async def service_connection_handler(request: Request, exc: ServiceConnectionError) -> JSONResponse:
    """Handle ServiceConnectionError exceptions."""
    return JSONResponse(
        status_code=502,
        content={
            "request_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "api_gateway",
            "target_service": "client",
            "api_version": "v1",
            "error": {
                "code": "SERVICE_CONNECTION_ERROR",
                "message": str(exc)
            },
            "status_code": 502
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle RequestValidationError exceptions."""
    errors: List[Dict[str, Any]] = exc.errors()
    return JSONResponse(
        status_code=422,
        content={
            "request_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "api_gateway",
            "target_service": "client",
            "api_version": "v1",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "field": errors[0]["loc"][-1] if errors else None,
                "details": errors
            },
            "status_code": 422
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTPException exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "request_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "api_gateway",
            "target_service": "client",
            "api_version": "v1",
            "error": {
                "code": f"HTTP_ERROR_{exc.status_code}",
                "message": exc.detail
            },
            "status_code": exc.status_code
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "request_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "api_gateway",
            "target_service": "client",
            "api_version": "v1",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc)
            },
            "status_code": 500
        }
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(ServiceNotFoundError, service_not_found_handler)
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_handler)
    app.add_exception_handler(ServiceConnectionError, service_connection_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler) 