import logging
import logging.config

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from api_gateway_service.core.config import settings
from api_gateway_service.core.logging_config import LOGGING_CONFIG
from api_gateway_service.core.tracing_config import configure_tracing
from api_gateway_service.app.middleware.request_id import RequestIdMiddleware
from api_gateway_service.app.api.router import api_router

# Apply logging configuration BEFORE app instantiation
logging.config.dictConfig(LOGGING_CONFIG)
logging.getLogger().setLevel(settings.LOG_LEVEL)

# Configure Tracing early
tracer_provider = None
if settings.OTEL_TRACE_ENABLED:
    tracer_provider = configure_tracing()
    HTTPXClientInstrumentor().instrument()

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (e.g., init connections)
    logger.info("API Gateway starting up...")
    yield
    # Shutdown logic
    if tracer_provider:
        logger.info("Shutting down OpenTelemetry tracer provider...")
        tracer_provider.shutdown()
    logger.info("API Gateway shutting down...")

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

# Include the main API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    # Basic health check
    return {"status": "healthy"}

logger.info(f"API Gateway configured for environment: {settings.APP_ENV}") 