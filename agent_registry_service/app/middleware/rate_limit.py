import time
import logging
from typing import Tuple

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis.asyncio as redis

# Assuming redis client dependency is available (e.g., from db.cache)
# from agent_registry_service.db.cache import get_redis_client
# Assuming settings are available 
# from agent_registry_service.core.config import get_settings

logger = logging.getLogger(__name__)

# Placeholder: Fetch settings from config or pass them in
# settings = get_settings() 
# RATE_LIMIT_PER_MINUTE = settings.RATE_LIMIT_PER_MINUTE
# REDIS_CLIENT = get_redis_client() # This needs proper injection
RATE_LIMIT_PER_MINUTE = 60 # Example default
REDIS_CLIENT = None # Placeholder - MUST BE INJECTED

async def get_redis_client_dependency() -> redis.Redis:
    # Placeholder: Replace with actual dependency fetching redis client
    if REDIS_CLIENT is None:
         # This should not happen in a real setup where Redis is initialized at startup
         logger.error("Redis client dependency not configured for Rate Limiter.")
         raise HTTPException(status_code=500, detail="Rate limiting configuration error")
    return REDIS_CLIENT

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based sliding window rate limiting middleware."""

    def __init__(self, app, redis_client: redis.Redis, rate_limit: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.redis = redis_client
        self.rate = rate_limit
        self.window = window_seconds
        logger.info(f"Initialized RateLimitMiddleware: {self.rate} requests / {self.window} seconds")

    async def dispatch(self, request: Request, call_next: callable) -> Response:
        if not self.redis:
            logger.warning("Redis client not available for rate limiting. Skipping check.")
            return await call_next(request)
            
        # Use IP address as the primary identifier
        # TODO: Enhance to use user ID or API key if authenticated
        client_id = request.client.host if request.client else "unknown_ip"
        
        try:
            # Calculate keys for current and previous window for sliding effect
            current_time = int(time.time())
            current_window_start = (current_time // self.window) * self.window
            key = f"rate_limit:{client_id}:{current_window_start}"

            # Use a pipeline for atomic operations
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, self.window * 2) # Keep key for 2 windows to cover sliding window
                results = await pipe.execute()
                
            current_count = results[0]

            if current_count > self.rate:
                logger.warning(f"Rate limit exceeded for client {client_id} ({current_count}/{self.rate})")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Allowed: {self.rate} requests per {self.window} seconds.",
                    headers={"Retry-After": str(self.window)} # Inform client when to retry
                )
            
            logger.debug(f"Rate limit check passed for client {client_id} ({current_count}/{self.rate})")

        except redis.RedisError as e:
            logger.error(f"Redis error during rate limiting for {client_id}: {e}", exc_info=True)
            # Fail open or closed? Fail open for now (allow request if cache fails)
        except HTTPException as http_exc:
             raise http_exc # Re-raise the 429 Too Many Requests
        except Exception as e:
            logger.error(f"Unexpected error during rate limiting for {client_id}: {e}", exc_info=True)
            # Fail open

        # Proceed with the request
        response = await call_next(request)
        return response 