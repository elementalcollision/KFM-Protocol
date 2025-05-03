import uuid
from contextvars import ContextVar, Token
from typing import Optional, Union

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Define the context variable with a default value of None
REQUEST_ID_CTX_KEY = "request_id"
_request_id_ctx_var: ContextVar[Optional[str]] = ContextVar(REQUEST_ID_CTX_KEY, default=None)

def get_request_id() -> Optional[str]:
    """Retrieve the current request ID from contextvar."""
    return _request_id_ctx_var.get()

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Injects a request ID into contextvars and response headers.
        Retrieves ID from X-Request-ID header or generates a new UUID.
        """
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set the context variable
        request_id_token: Token = _request_id_ctx_var.set(request_id)

        response = await call_next(request)

        # Add the request ID to the response headers
        response.headers["X-Request-ID"] = get_request_id()

        # Reset the context variable (important for cleanup)
        _request_id_ctx_var.reset(request_id_token)

        return response 