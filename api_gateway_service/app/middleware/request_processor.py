import time
import logging
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi.responses import JSONResponse

from app.core.config import APIGatewaySettings, get_settings


logger = logging.getLogger(__name__)


class RequestProcessorMiddleware(BaseHTTPMiddleware):
    """
    Middleware for processing requests and responses.
    
    Handles request ID generation, logging, and timing.
    """
    def __init__(self, app: ASGIApp, settings: APIGatewaySettings = get_settings()):
        """
        Initialize request processor middleware.
        
        Args:
            app: ASGI application.
            settings: API Gateway settings.
        """
        super().__init__(app)
        self.settings = settings
        
    async def dispatch(self, request: Request, call_next):
        """
        Process request and response.
        
        Args:
            request: FastAPI request.
            call_next: Next middleware or endpoint handler.
            
        Returns:
            Response: FastAPI response.
        """
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Set X-Request-ID for future use in other middleware or handlers
        request.state.request_id = request_id
        
        # Start timing request processing
        start_time = time.time()
        
        # Add logging context
        log_context = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown",
        }
        
        logger.info(f"Request started: {request.method} {request.url.path}", extra=log_context)
        
        try:
            # Process request with next middleware or endpoint handler
            response = await call_next(request)
            
            # Add request ID to response headers
            if hasattr(response, "headers"):
                response.headers["X-Request-ID"] = request_id
                
                # Add timing information to response headers
                process_time = time.time() - start_time
                response.headers["X-Process-Time"] = f"{process_time:.6f}"
                
                log_context["status_code"] = response.status_code
                log_context["process_time"] = f"{process_time:.6f}"
                
                logger.info(
                    f"Request completed: {response.status_code} in {process_time:.6f}s",
                    extra=log_context
                )
                
            return response
            
        except Exception as e:
            # Log exception
            process_time = time.time() - start_time
            log_context["error"] = str(e)
            log_context["process_time"] = f"{process_time:.6f}"
            
            logger.exception(f"Request failed: {str(e)}", extra=log_context)
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "source_service": "api_gateway",
                    "target_service": "client",
                    "api_version": "v1",
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "Internal server error"
                    },
                    "status_code": 500
                }
            ) 