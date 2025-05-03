import logging
import time
import uuid
from contextvars import ContextVar
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Define context variables for request_id and Kubernetes metadata
REQUEST_ID_CTX_KEY = "request_id"
POD_NAME_CTX_KEY = "pod_name"
NAMESPACE_CTX_KEY = "namespace"

_request_id_ctx_var: ContextVar[str] = ContextVar(REQUEST_ID_CTX_KEY, default=None)
_pod_name_ctx_var: ContextVar[str] = ContextVar(POD_NAME_CTX_KEY, default=None)
_namespace_ctx_var: ContextVar[str] = ContextVar(NAMESPACE_CTX_KEY, default=None)

# Initialize K8s context variables (done once at import time)
_pod_name_ctx_var.set(os.environ.get("POD_NAME", "unknown"))
_namespace_ctx_var.set(os.environ.get("POD_NAMESPACE", "unknown"))

def get_request_id() -> str:
    """Retrieve the current request ID from context."""
    return _request_id_ctx_var.get()

def get_pod_name() -> str:
    """Retrieve the current pod name from context."""
    return _pod_name_ctx_var.get()

def get_namespace() -> str:
    """Retrieve the current namespace from context."""
    return _namespace_ctx_var.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Generate or retrieve request ID and set it in context."""
        # Try to get request ID from header (e.g., X-Request-ID)
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4()) # Generate a new one if not found
        
        # Set the request ID in the context variable
        token = _request_id_ctx_var.set(request_id)
        
        # Include K8s metadata in logs via extra dict
        extra = {
            "request_id": request_id,
            "pod_name": get_pod_name(),
            "namespace": get_namespace()
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
            # Reset the request_id context variable after the request is done
            _request_id_ctx_var.reset(token)
            
        return response 