import logging
import logging.config
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
# from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from resource_manager_service.core.config import settings
# from resource_manager_service.core.logging_config import LOGGING_CONFIG # Placeholder
# from resource_manager_service.core.tracing_config import configure_tracing # Placeholder
from resource_manager_service.services.quota_service import QuotaService # Import QuotaService
from resource_manager_service.services.k8s_client import KubernetesClient, K8sClientError # Import K8s client
from resource_manager_service.services.event_listener import EventListener # Import EventListener
from resource_manager_service.core.metrics import REGISTRY # Import custom registry

# TODO: Apply logging configuration once created
# logging.config.dictConfig(LOGGING_CONFIG)
# logging.getLogger().setLevel(settings.LOG_LEVEL)

# TODO: Configure Tracing early once created
# tracer_provider = None
# if settings.OTEL_TRACE_ENABLED:
#     tracer_provider = configure_tracing()
#     HTTPXClientInstrumentor().instrument() # Instrument httpx client

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    
    # Initialize Quota Service
    quota_service = QuotaService() # Instantiates and calls load_quotas()
    if quota_service.quota_config:
        app.state.quota_service = quota_service # Store instance in app state
        logger.info("Resource quotas loaded successfully.")
    else:
        app.state.quota_service = None
        logger.error("Failed to load resource quotas. Service might not enforce quotas correctly.")
        # Depending on requirements, you might want to prevent startup if quotas fail:
        # raise RuntimeError("Critical error: Failed to load resource quota configuration.")

    # Initialize K8s Client
    try:
        k8s_client = KubernetesClient()
        app.state.k8s_client = k8s_client # Store instance in app state
        logger.info("Kubernetes client initialized successfully.")
        k8s_initialized = True # Flag to indicate success
    except K8sClientError as e:
        app.state.k8s_client = None
        k8s_initialized = False
        logger.error(f"Failed to initialize Kubernetes client: {e}")
        # Decide if this is critical - maybe allow startup but log error?

    # Initialize and start Event Listener
    # Only start if K8s client initialized successfully
    if k8s_initialized:
        event_listener = EventListener(k8s_client=app.state.k8s_client) # Pass client
        app.state.event_listener = event_listener
        try:
            await event_listener.connect()
            # Run the consumer in the background
            app.state.event_listener_task = asyncio.create_task(event_listener.start_consuming())
            logger.info("Event listener connected and started.")
        except Exception as e:
            logger.error(f"Failed to start event listener: {e}")
            # Handle failure appropriately - maybe prevent startup?
            app.state.event_listener = None
            app.state.event_listener_task = None
    else:
        logger.warning("Skipping Event Listener initialization because Kubernetes client failed to load.")
        app.state.event_listener = None
        app.state.event_listener_task = None

    yield # Application runs
    
    # Shutdown logic
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    # Stop event listener
    if hasattr(app.state, 'event_listener_task') and app.state.event_listener_task:
        logger.info("Stopping event listener task...")
        app.state.event_listener_task.cancel()
        try:
            await app.state.event_listener_task
        except asyncio.CancelledError:
            logger.info("Event listener task cancelled successfully.")
    if hasattr(app.state, 'event_listener') and app.state.event_listener:
        await app.state.event_listener.disconnect()
    
    # TODO: Shutdown tracer provider
    # if tracer_provider:
    #     tracer_provider.shutdown()
    # TODO: Close K8s client connections if necessary (client lib might handle this)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Instrument app with Prometheus metrics using custom registry
Instrumentator(registry=REGISTRY).instrument(app).expose(app)
logger.info("Prometheus metrics endpoint /metrics exposed.")

# TODO: Instrument app with OpenTelemetry Tracing once logging/tracing is set up
# if settings.OTEL_TRACE_ENABLED:
#     FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
#     logger.info("FastAPI app instrumented with OpenTelemetry.")

# TODO: Add Middleware (Request ID, Auth, CORS) once core/middleware exist
# from resource_manager_service.app.middleware.request_id import RequestIdMiddleware
# app.add_middleware(RequestIdMiddleware)

# TODO: Include API routers once endpoints are created
# from resource_manager_service.app.api.api_v1.api import api_router
# app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    # Basic health check, can be expanded later
    logger.info("Health check requested")
    # Potentially check app.state.quota_service health?
    return {"status": "healthy", "service": settings.PROJECT_NAME}

logger.info(f"{settings.PROJECT_NAME} configured for environment: {settings.APP_ENV}")

# Example runner (for local dev)
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("resource_manager_service.app.main:app", host="0.0.0.0", port=8006, reload=True) # Choose an appropriate port 