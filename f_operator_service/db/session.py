from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import logging

from f_operator_service.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

if not settings.SQLALCHEMY_DATABASE_URI_F:
    logger.error("Database URI (SQLALCHEMY_DATABASE_URI_F) is not configured.")
    # Consider raising an exception here if DB is critical
    engine = None
    SessionLocal = None
else:
    try:
        engine = create_async_engine(
            settings.SQLALCHEMY_DATABASE_URI_F,
            pool_pre_ping=True,
            # Consider adding pool size settings for production
            # pool_size=10,
            # max_overflow=20,
        )
        SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        logger.info("Database engine and session created successfully.")
    except Exception as e:
        logger.error(f"Failed to create database engine or session: {e}", exc_info=True)
        engine = None
        SessionLocal = None

async def get_db() -> AsyncSession:
    """Dependency to get a DB session."""
    if SessionLocal is None:
        logger.error("SessionLocal is not initialized. Cannot get DB session.")
        raise RuntimeError("Database session factory not initialized.")
        
    async with SessionLocal() as session:
        try:
            yield session
            # Optionally commit here if needed globally, but usually done in CRUD
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close() 