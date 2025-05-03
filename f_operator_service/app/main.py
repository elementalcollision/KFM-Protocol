from fastapi import FastAPI
import logging
import logging.config
import uvicorn
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from f_operator_service.core.config import get_settings
from f_operator_service.core.logging_config import LOGGING_CONFIG
from f_operator_service.core.tracing_config import configure_tracing
from f_operator_service.app.middleware.request_id import RequestIdMiddleware
from f_operator_service.app.api.endpoints import adaptation
from f_operator_service.app.api.endpoints import feature_flag, experiment
from f_operator_service.app.api.endpoints import provenance
from f_operator_service.app.api.endpoints import promotion
from f_operator_service.app.api.endpoints import checklist
from f_operator_service.app.api.api import api_router

# Apply logging config early
logging.config.dictConfig(LOGGING_CONFIG)
logging.getLogger().setLevel(get_settings().LOG_LEVEL)

logger = logging.getLogger(__name__)

settings = get_settings()

# Configure Tracing early
tracer_provider = None
if settings.OTEL_TRACE_ENABLED:
    tracer_provider = configure_tracing()
    HTTPXClientInstrumentor().instrument()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    # Add any other startup logic here
    yield
    # Shutdown logic
    if tracer_provider:
        logger.info("Shutting down OpenTelemetry tracer provider...")
        tracer_provider.shutdown()
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Instrument the app with Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Instrument the app with OpenTelemetry Tracing
if settings.OTEL_TRACE_ENABLED:
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    logger.info("FastAPI app instrumented with OpenTelemetry.")

# Add Middleware
app.add_middleware(RequestIdMiddleware)

# Include routers
app.include_router(
    adaptation.router, 
    prefix=f"{settings.API_V1_STR}/agents", 
    tags=["Adaptation"]
)
app.include_router(
    feature_flag.router,
    prefix=f"{settings.API_V1_STR}",
    tags=["Feature Flags"]
)
app.include_router(
    experiment.router,
    prefix=f"{settings.API_V1_STR}",
    tags=["Experiments"]
)
app.include_router(
    provenance.router,
    prefix=f"{settings.API_V1_STR}/provenance",
    tags=["Provenance"]
)
app.include_router(
    promotion.router,
    prefix=f"{settings.API_V1_STR}",
    tags=["Promotion"]
)
app.include_router(
    checklist.router,
    prefix=f"{settings.API_V1_STR}/checklists",
    tags=["Checklists"]
)

@app.get("/health", tags=["Health"])
def health_check():
    logger.info("Health check requested")
    return {"status": "healthy", "service": settings.PROJECT_NAME}

if __name__ == "__main__":
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    uvicorn.run("f_operator_service.app.main:app", host="0.0.0.0", port=8002, reload=True) # Example port, adjust as needed 