import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from k_operator_service.core.config import settings
from k_operator_service.core.logging_config import LOGGING_CONFIG
from k_operator_service.core.tracing_config import configure_tracing
from k_operator_service.app.middleware.request_id import RequestIdMiddleware, get_pod_name, get_namespace
from k_operator_service.app.api.endpoints import operations
from k_operator_service.events.publisher import lifespan as publisher_lifespan

# Apply logging configuration BEFORE app instantiation
logging.config.dictConfig(LOGGING_CONFIG)
logging.getLogger().setLevel(settings.LOG_LEVEL)

# Configure Tracing early
tracer_provider = None
if settings.OTEL_TRACE_ENABLED:
    tracer_provider = configure_tracing()
    HTTPXClientInstrumentor().instrument()

logger = logging.getLogger(__name__)

# Kubernetes client setup could happen here or in lifespan
# from kubernetes import client, config

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    async with publisher_lifespan(app):
        logger.info(f"Starting {settings.PROJECT_NAME}...")
        yield
        logger.info(f"Shutting down {settings.PROJECT_NAME}...")
        if tracer_provider:
            logger.info("Shutting down OpenTelemetry tracer provider...")
            tracer_provider.shutdown()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.PROJECT_VERSION, # Add version if defined in settings
    lifespan=app_lifespan # Register the combined lifespan
)

# Instrument the app with Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Instrument the app with OpenTelemetry Tracing
if settings.OTEL_TRACE_ENABLED:
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    logger.info("FastAPI app instrumented with OpenTelemetry.")

# Add Middleware (order matters)
app.add_middleware(RequestIdMiddleware)
# Add other middleware like CORS, Auth, etc. here

# Include the API router
app.include_router(
    operations.router,
    prefix=settings.API_V1_STR,
    tags=["K-Operations"]
)

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    logger.info("Health check requested", extra={
        "pod_name": get_pod_name(),
        "namespace": get_namespace()
    })
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "pod": get_pod_name(),
        "namespace": get_namespace()
    }

logger.info(f"K Operator Service configured for environment: {settings.APP_ENV}")

# Optional: Add startup/shutdown events if needed later
# @app.on_event("startup")
# async def startup_event():
#     logger.info("K Operator Service starting up...")
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("K Operator Service shutting down...")


# To run the app (example using uvicorn):
# Ensure uvicorn is installed: pip install uvicorn
# Run from the workspace root directory:
# uvicorn k_operator_service.app.main:app --reload --port 8001 