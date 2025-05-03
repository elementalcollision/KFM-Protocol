from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from m_operator_service.app.core.config import settings

# Create the async engine
engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True, echo=settings.DB_ECHO)

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