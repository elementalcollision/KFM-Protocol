import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from m_operator_service.core.config import settings
from m_operator_service.core.logging_config import LOGGING_CONFIG
from m_operator_service.core.tracing_config import configure_tracing
from m_operator_service.app.middleware.request_id import RequestIdMiddleware
from m_operator_service.app.api.api_v1.api import api_router

# Apply logging configuration BEFORE app instantiation
logging.config.dictConfig(LOGGING_CONFIG)
logging.getLogger().setLevel(settings.LOG_LEVEL)

# Configure Tracing early
tracer_provider = None
if settings.OTEL_TRACE_ENABLED:
    tracer_provider = configure_tracing()
    HTTPXClientInstrumentor().instrument()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services, job scheduler, etc.
    logger.info(f"Starting M Operator Service...")
    
    # Initialize model registry, tracking systems, etc.
    # app.state.model_registry = ...
    
    yield  # Application runs here
    
    # Cleanup/shutdown: Close connections, stop scheduler, etc.
    if tracer_provider:
        logger.info("Shutting down OpenTelemetry tracer provider...")
        tracer_provider.shutdown()
    logger.info("Shutting down M Operator Service")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
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
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME
    }

logger.info(f"M Operator Service configured for environment: {settings.APP_ENV}") 