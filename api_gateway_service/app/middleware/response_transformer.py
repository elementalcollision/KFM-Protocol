import json
import logging
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi.responses import JSONResponse, Response
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class ResponseTransformerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for transforming responses to a standardized format.
    
    Ensures consistent response structure across all API endpoints.
    """
    def __init__(self, app: ASGIApp):
        """
        Initialize response transformer middleware.
        
        Args:
            app: ASGI application.
        """
        super().__init__(app)
        
    async def dispatch(self, request: Request, call_next):
        """
        Process request and transform response.
        
        Args:
            request: FastAPI request.
            call_next: Next middleware or endpoint handler.
            
        Returns:
            Response: Transformed FastAPI response.
        """
        # Process the request with the rest of the application
        response = await call_next(request)
        
        # Get request ID from state or headers
        request_id = getattr(request.state, "request_id", None)
        if not request_id and hasattr(response, "headers"):
            request_id = response.headers.get("X-Request-ID", None)
        
        # Skip transformation if not a JSON response
        if not isinstance(response, JSONResponse):
            return response
            
        # Get response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
            
        # Parse the response body
        try:
            # Decode and parse JSON
            response_data = json.loads(response_body.decode())
            
            # Skip transformation if already in standard format
            if isinstance(response_data, dict) and all(k in response_data for k in ["status", "data", "metadata"]):
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
            # Transform to standard format
            transformed_data = {
                "status": "success" if response.status_code < 400 else "error",
                "data": response_data if response.status_code < 400 else None,
                "error": response_data if response.status_code >= 400 else None,
                "metadata": {
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": "api_gateway",
                    "status_code": response.status_code
                }
            }
            
            # Create a new response with transformed data
            return JSONResponse(
                content=transformed_data,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse response body as JSON: {e}")
            return response
        except Exception as e:
            logger.exception(f"Error transforming response: {e}")
            return response 