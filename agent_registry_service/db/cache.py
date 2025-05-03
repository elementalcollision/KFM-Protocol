import logging
from typing import AsyncGenerator, Optional
import redis.asyncio as redis

from agent_registry_service.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_pool: Optional[redis.ConnectionPool] = None

async def init_redis_pool() -> redis.ConnectionPool:
    """Initializes the Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        logger.info(f"Initializing Redis connection pool for {settings.REDIS_HOST}:{settings.REDIS_PORT} (DB {settings.REDIS_DB})")
        try:
            _redis_pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                ssl=settings.REDIS_SSL,
                # decode_responses=True, # Let caller handle encoding/decoding (e.g., JSON)
                max_connections=50, # TODO: Make configurable?
                socket_connect_timeout=5, # Add timeout
                socket_keepalive=True,
            )
            # Test connection
            async with redis.Redis(connection_pool=_redis_pool) as r:
                 await r.ping()
            logger.info("Redis connection pool initialized and connection tested.")
        except redis.exceptions.ConnectionError as e:
             logger.error(f"Failed to connect to Redis: {e}")
             _redis_pool = None # Ensure pool remains None if connection fails
             # Depending on requirements, might raise exception or allow app to start without cache
             raise RuntimeError(f"Could not connect to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}") from e
        except Exception as e:
             logger.error(f"An unexpected error occurred during Redis pool initialization: {e}", exc_info=True)
             _redis_pool = None
             raise
    return _redis_pool

async def get_redis_client() -> redis.Redis:
    """FastAPI dependency to get an async Redis client from the pool."""
    pool = await init_redis_pool() # Ensure pool is initialized
    if not pool:
         # Handle case where pool failed to initialize (e.g., return None or raise specific error)
         logger.error("Redis pool is not initialized. Cannot get Redis client.")
         # Decide behavior: raise error or return a dummy client/None?
         raise HTTPException(status_code=503, detail="Cache service unavailable")
         
    return redis.Redis(connection_pool=pool)

async def close_redis_pool():
    """Closes the Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        logger.info("Closing Redis connection pool.")
        await _redis_pool.disconnect()
        _redis_pool = None 