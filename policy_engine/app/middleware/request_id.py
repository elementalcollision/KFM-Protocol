import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Define context variables for request_id and policy context
REQUEST_ID_CTX_KEY = "request_id"
POLICY_ID_CTX_KEY = "policy_id"

_request_id_ctx_var: ContextVar[str] = ContextVar(REQUEST_ID_CTX_KEY, default=None)
_policy_id_ctx_var: ContextVar[str] = ContextVar(POLICY_ID_CTX_KEY, default=None)

def get_request_id() -> str:
    """Retrieve the current request ID from context."""
    return _request_id_ctx_var.get()

def get_policy_id() -> str:
    """Retrieve the current policy ID from context, if set."""
    return _policy_id_ctx_var.get()

def set_policy_id(policy_id: str) -> None:
    """Set the policy ID in the context."""
    if policy_id:
        _policy_id_ctx_var.set(policy_id)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Generate or retrieve request ID and set it in context."""
        # Try to get request ID from header (e.g., X-Request-ID)
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4()) # Generate a new one if not found
        
        # Set the request ID in the context variable
        token = _request_id_ctx_var.set(request_id)
        
        # Try to extract policy_id from path parameters if present
        path_params = request.path_params
        policy_id = path_params.get("policy_id", None)
        policy_token = None
        if policy_id:
            policy_token = _policy_id_ctx_var.set(policy_id)
            
        # Extra fields for logging
        extra = {
            "request_id": request_id,
            "policy_id": policy_id
        }
        
        logger.debug(f"Request {request_id} received: {request.method} {request.url.path}", extra=extra)
        start_time = time.monotonic()
        
        try:
            response = await call_next(request)
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            process_time = (time.monotonic() - start_time) * 1000
            logger.info(
                f"Request {request_id} completed: {response.status_code} ({process_time:.2f}ms)",
                extra=extra
            )
        except Exception as e:
             # Log uncaught exceptions with request ID
             process_time = (time.monotonic() - start_time) * 1000
             logger.error(
                 f"Request {request_id} failed: {e} ({process_time:.2f}ms)",
                 exc_info=True,
                 extra=extra
             )
             # Reraise the exception to be handled by FastAPI's exception handlers
             raise e
        finally:
            # Reset the context variables after the request is done
            _request_id_ctx_var.reset(token)
            if policy_token:
                _policy_id_ctx_var.reset(policy_token)
            
        return response 