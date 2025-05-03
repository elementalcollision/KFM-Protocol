from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from agent_registry_service.core.config import settings # Adjusted import path

# Create the async engine
engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True, echo=False) # echo=False for less noise

# Create the async session factory
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False, # Important for FastAPI background tasks
)

async def get_db() -> AsyncSession:
    """Dependency function that yields an async session."""
    async with AsyncSessionLocal() as session:
        yield session
        # Optional: await session.commit() if you want auto-commit (usually not recommended)
        # Optional: await session.rollback() if needed based on exceptions 