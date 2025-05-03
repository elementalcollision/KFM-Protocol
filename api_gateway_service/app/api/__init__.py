from fastapi import APIRouter

from app.api.endpoints import agents


# Create main API router
api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(agents.router)
