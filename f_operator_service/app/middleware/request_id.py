import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Define context variables for request_id
REQUEST_ID_CTX_KEY = "request_id"
_request_id_ctx_var: ContextVar[str] = ContextVar(REQUEST_ID_CTX_KEY, default=None)

def get_request_id() -> str:
    """Retrieve the current request ID from context."""
    return _request_id_ctx_var.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Generate or retrieve request ID and set it in context."""
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        token = _request_id_ctx_var.set(request_id)
        
        logger.debug(f"Request {request_id} received: {request.method} {request.url.path}")
        start_time = time.monotonic()
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            process_time = (time.monotonic() - start_time) * 1000
            logger.info(
                f"Request {request_id} completed: {response.status_code} ({process_time:.2f}ms)"
            )
        except Exception as e:
             process_time = (time.monotonic() - start_time) * 1000
             logger.error(
                 f"Request {request_id} failed: {e} ({process_time:.2f}ms)",
                 exc_info=True
             )
             raise e
        finally:
            _request_id_ctx_var.reset(token)
            
        return response 