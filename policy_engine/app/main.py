import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from policy_engine.core.config import settings
from policy_engine.core.logging_config import LOGGING_CONFIG  # Import logging config
from policy_engine.core.tracing_config import configure_tracing
from policy_engine.app.middleware.request_id import RequestIdMiddleware  # Import middleware

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
    # Startup: Initialize policy engine components
    logger.info(f"Starting Policy Engine...")
    
    # Initialize policy files, client connections, etc.
    # app.state.policy_engine = ...
    
    yield  # Application runs here
    
    # Cleanup/shutdown
    if tracer_provider:
        logger.info("Shutting down OpenTelemetry tracer provider...")
        tracer_provider.shutdown()
    logger.info("Shutting down Policy Engine")

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

# Include API routers
# app.include_router(policies_router, prefix=settings.API_V1_STR)
# app.include_router(evaluate_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME
    }

logger.info(f"Policy Engine configured for environment: {settings.APP_ENV}") 