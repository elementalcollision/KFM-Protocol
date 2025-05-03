import logging
import logging.config
from fastapi import FastAPI, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from typing import Optional
import asyncio
from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor # Add OTEL import
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor # Add OTEL HTTPX import

from agent_registry_service.core.config import settings, get_settings
from agent_registry_service.core.logging_config import LOGGING_CONFIG
from agent_registry_service.core.tracing_config import configure_tracing # Add OTEL config import
from agent_registry_service.app.middleware.request_id import RequestIdMiddleware # Import middleware
# Import routers later when they are created
from agent_registry_service.api.endpoints import agents # Import the agents router
from agent_registry_service.api.endpoints import auth   # Import the auth router
from agent_registry_service.api.endpoints import subscriptions # Import subscriptions router
from agent_registry_service.api.api import api_router  # This might not be used if endpoints are included directly
from agent_registry_service.db.session import get_db, engine # Assuming engine is defined here for startup
from agent_registry_service.db.cache import init_redis_pool, close_redis_pool, get_redis_client, _redis_pool # Redis deps
from agent_registry_service.core.registry_manager import RegistryManager, get_registry_manager_dep # Import updated manager dep
from agent_registry_service.services.subscription_service import SubscriptionService # Import service
from agent_registry_service.services.notification_service import NotificationService # Import service
from agent_registry_service.app.middleware.rate_limit import RateLimitMiddleware # Import Rate Limiter
import redis.asyncio as redis # Import for type hint

# Apply logging configuration before creating app instance that might log
logging.config.dictConfig(LOGGING_CONFIG)

# Configure Tracing early
tracer_provider = None
if settings.OTEL_TRACE_ENABLED:
    tracer_provider = configure_tracing()
    HTTPXClientInstrumentor().instrument() # Instrument httpx client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup...")
    redis_client_instance: Optional[redis.Redis] = None
    registry_manager_instance: Optional[RegistryManager] = None
    subscription_service_instance: Optional[SubscriptionService] = None

    # Initialize Redis Pool
    try:
        await init_redis_pool()
        redis_client_instance = await get_redis_client()
        app.state.redis_pool = _redis_pool # Store pool for health check access
        app.state.redis_client = redis_client_instance # Store client for middleware/deps
        logger.info("Redis connection pool initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize Redis pool: {e}", exc_info=True)
        app.state.redis_pool = None
        app.state.redis_client = None
        # Allow app to start, but log critical failure

    # Instantiate shared services
    # TODO: Pass configuration properly if needed
    notification_service_instance = NotificationService()
    app.state.notification_service = notification_service_instance

    # Instantiate RegistryManager singleton
    if redis_client_instance:
        settings_obj = get_settings()
        registry_manager_instance = RegistryManager(redis_client=redis_client_instance, cache_ttl=settings_obj.DISCOVERY_CACHE_TTL_SECONDS)
        app.state.registry_manager = registry_manager_instance
        logger.info("RegistryManager singleton initialized with Redis cache.")
    else:
        logger.warning("Redis client unavailable, RegistryManager will operate without caching.")
        # Initialize without cache client or with a dummy one if designed to handle None
        # registry_manager_instance = RegistryManager(redis_client=None, cache_ttl=0)
        # app.state.registry_manager = registry_manager_instance
        app.state.registry_manager = None # Indicate manager might be unavailable/limited

    # Initialize Registry Manager data from DB if manager exists
    if registry_manager_instance: 
        try:
            async with AsyncSession(bind=engine) as session:
                try:
                    logger.info("Initializing Registry Manager data from database...")
                    await registry_manager_instance.initialize_from_db(session)
                    logger.info("Registry Manager data initialized.")
                except Exception as e:
                    logger.error(f"Failed to initialize Registry Manager data: {e}", exc_info=True)
                    # Manager exists but failed to load data, state might be inconsistent
        except Exception as e:
            logger.error(f"Database connection failed during manager initialization: {e}", exc_info=True)
            # Mark manager as potentially unavailable if DB load fails?
            # app.state.registry_manager = None 
            
    # Instantiate and start SubscriptionService if dependencies met
    if redis_client_instance and registry_manager_instance:
        subscription_service_instance = SubscriptionService(
            redis_client=redis_client_instance, 
            notification_service=notification_service_instance,
            db_session_factory=AsyncSessionLocal # Pass the factory
        )
        # Start listener in background
        asyncio.create_task(subscription_service_instance.start_listener()) 
        app.state.subscription_service = subscription_service_instance
        logger.info("SubscriptionService initialized and listener started.")
    else:
        logger.warning("SubscriptionService not started due to missing Redis or RegistryManager.")
        app.state.subscription_service = None

    logger.info("Application startup sequence complete.")
    
    yield # Application runs here
    
    # Shutdown
    logger.info("Application shutdown...")
    if app.state.subscription_service:
        await app.state.subscription_service.stop_listener()
    await close_redis_pool()
    logger.info("Redis pool closed.")
    # Add DB engine disposal if needed: await engine.dispose()
    if tracer_provider:
        logger.info("Shutting down OpenTelemetry tracer provider...")
        tracer_provider.shutdown()
    logger.info("Application shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    # Add other app configurations like middleware here if preferred
)

# Instrument the app with Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Instrument the app with OpenTelemetry Tracing
if settings.OTEL_TRACE_ENABLED:
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    logger.info("FastAPI app instrumented with OpenTelemetry.")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Middleware
app.add_middleware(RequestIdMiddleware) # Add request ID middleware
# TODO: Add Rate Limit Middleware later

# Include routers
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}/agents", tags=["Agents"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(subscriptions.router, prefix=f"{settings.API_V1_STR}/subscriptions", tags=["Subscriptions"]) # Add subscription router

# --- Startup Event Handler (Keep old style for now) --- 
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup...")
    # TODO: Initialize Redis Pool here if not using lifespan
    # TODO: Initialize Registry Manager here if not using lifespan
    # TODO: Start Subscription Service listener here if not using lifespan
    # Example DB init for registry manager:
    async for session in get_db(): # Assuming get_db works with old startup style
         try:
             logger.info("Initializing Registry Manager from database...")
             # Need registry manager instance
             # await registry_manager.initialize_from_db(session)
             logger.info("Registry Manager initialized.")
         except Exception as e:
             logger.error(f"Failed to initialize Registry Manager: {e}", exc_info=True)
         break
    logger.info("Application startup complete.")

# --- Root and Health Endpoints (Keep simple version for now) --- 
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

@app.get("/health", tags=["Health"])
async def health_check(): # Keep original simple health check
    # Basic health check, enhanced version deferred
    return {"status": "OK"}

# Get the logger for the main module
logger = logging.getLogger(__name__)
logger.info("Agent Registry Service starting...")

logger.info(f"{settings.PROJECT_NAME} setup complete.") 