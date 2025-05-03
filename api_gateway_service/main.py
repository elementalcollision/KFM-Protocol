import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.middleware.request_processor import RequestProcessorMiddleware
from app.middleware.response_transformer import ResponseTransformerMiddleware
from app.api.router import router
from app.services.task_worker import start_worker


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api_gateway")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application.
    """
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # Register error handlers
    register_exception_handlers(app)
    
    # Add middleware - order matters!
    # 1. Request processor middleware (runs first)
    app.add_middleware(RequestProcessorMiddleware, settings=settings)
    
    # 2. Response transformer middleware (runs after request processor)
    app.add_middleware(ResponseTransformerMiddleware)
    
    # 3. CORS middleware (runs last)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this to specific domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(router, prefix=settings.API_PREFIX)
    
    # Add circuit breaker status endpoint
    @app.get("/health/circuit-breakers")
    async def circuit_breaker_status():
        from app.core.circuit_breaker import get_circuit_breaker_registry
        registry = get_circuit_breaker_registry()
        return {
            "status": "ok",
            "circuit_breakers": registry.get_all_states()
        }
    
    # Add root health check endpoint
    @app.get("/health")
    async def root_health_check():
        return {"status": "ok"}
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
        start_worker(app)
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        # Close any open resources
        from app.services.http_client import get_http_client
        await get_http_client().close()
        
        logger.info(f"Shutting down {settings.API_TITLE}")
    
    # Add custom OpenAPI schema with API key security
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            }
        }
        openapi_schema["security"] = [{"ApiKeyAuth": []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    app.openapi = custom_openapi
    
    return app


# Create application instance
app = create_application()

