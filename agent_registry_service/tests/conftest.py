import asyncio
import pytest
from typing import AsyncGenerator, Generator

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Import settings first and apply test overrides
from agent_registry_service.core.config import settings
# Use an in-memory SQLite database for tests
# Note: SQLite does not fully support all PostgreSQL features (like ENUM directly)
# You might need workarounds or use a test PostgreSQL DB for full compatibility.
TEST_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db" # Use file for persistence during test run if needed, or ":memory:"
settings.SQLALCHEMY_DATABASE_URI = TEST_SQLALCHEMY_DATABASE_URL

# Now import other components that might depend on settings
from agent_registry_service.models.base_class import Base
from agent_registry_service.app.main import app # Import your FastAPI app
from agent_registry_service.db.session import get_db # Import the dependency

# Create async engine for tests using the overridden URL
# Make sure settings.SQLALCHEMY_DATABASE_URI is a string
engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI), # Use the overridden test URL
    poolclass=NullPool,
    echo=False
)

# Create a session factory for tests
TestingSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

@pytest.fixture(scope="session")
def event_loop(request) -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function") # Use 'function' scope for db isolation per test
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for testing, handling setup/teardown."""
    # Connect to the database and create tables
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all) # Ensure clean state
        await connection.run_sync(Base.metadata.create_all)

    # Create a new session for the test
    async with TestingSessionLocal() as session:
        yield session # Provide the session to the test
        # Rollback any changes made during the test
        await session.rollback() # Important for isolation

    # Optional: Drop tables after test (can be slow if done per function)
    # async with engine.begin() as connection:
    #     await connection.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Yield an AsyncClient for making requests to the FastAPI app."""

    # Override the production `get_db` dependency with our test session
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # Create the test client
    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client

    # Clean up the dependency override after the test
    app.dependency_overrides.pop(get_db, None) 