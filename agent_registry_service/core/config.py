import os
from typing import Optional, Any, Union, Dict, Literal
from datetime import timedelta
from functools import lru_cache
import logging

from pydantic import PostgresDsn, field_validator, ValidationInfo
from pydantic_settings import BaseSettings

# Configure logging early to catch potential issues during settings load
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Read APP_ENV early, defaulting to 'development' for local setup
# This helps the validator know the context even before Settings is fully loaded
APP_ENV = os.environ.get("APP_ENV", "development")

class Settings(BaseSettings):
    # --- Core Settings ---
    APP_ENV: str = APP_ENV # Load from environment or use default
    PROJECT_NAME: str = "KFM Agent Registry Service"
    API_V1_STR: str = "/api/v1"
    # Use Literal for type hinting and validation
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- Database Settings ---
    # Define defaults directly in the class. .env or Env Vars will override.
    POSTGRES_SERVER: Optional[str] = "localhost"
    POSTGRES_USER: Optional[str] = "postgres"
    POSTGRES_PASSWORD: Optional[str] = "password"
    POSTGRES_DB: Optional[str] = "kfm_registry" # Example DB name
    POSTGRES_PORT: str = "5432" # Pydantic expects str for port in DSN builder if not int

    # Asynchronous Database URL constructed from parts
    # Optional allows it to be None initially, validator constructs it
    SQLALCHEMY_DATABASE_URI: Optional[Union[PostgresDsn, str]] = None

    # --- JWT Settings ---
    # Define defaults directly in the class. .env or Env Vars will override.
    SECRET_KEY: str = "default_dev_secret_key_CHANGE_ME" # Default insecure key
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    # --- Redis Cache Settings ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    DISCOVERY_CACHE_TTL_SECONDS: int = 300 # 5 minutes default TTL

    @field_validator("SQLALCHEMY_DATABASE_URI", mode='before')
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> Any:
        # Use APP_ENV determined *before* BaseSettings initialization
        # Or access from info.data if defined in Settings model itself
        current_app_env = info.data.get("APP_ENV", APP_ENV) # Get APP_ENV from validated data or pre-read env
        is_test_env = current_app_env == "test"

        # If running in test environment, expect URI to be set elsewhere
        if is_test_env:
            if isinstance(v, str): return v # Use provided URI if explicitly set for tests
            # Return None; conftest should provide the actual test DB URL.
            # This prevents trying to build a Postgres DSN during testing if vars aren't set.
            return None

        # --- Production/Development Environment Logic ---

        # If SQLALCHEMY_DATABASE_URI is explicitly set (and not test mode), use it directly
        if isinstance(v, str) and v:
            return v

        # Construct DSN from parts if not explicitly provided and not in test mode
        values_data = info.data # Contains values already loaded (defaults, .env, env vars)

        # Ensure required Postgres vars are present
        required_vars = ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_SERVER", "POSTGRES_DB"]
        missing_vars = [var for var in required_vars if not values_data.get(var)]
        if missing_vars:
            # Raise error only if essential vars are missing *after* loading from all sources
            raise ValueError(f"Missing required Postgres settings in {current_app_env} environment: {', '.join(missing_vars)}")

        try:
            # Ensure port is treated as string for DSN builder if needed
            port_val = values_data.get("POSTGRES_PORT", "5432")
            # Basic validation if needed, pydantic DSN builder handles numeric conversion
            # int(port_val)
        except (ValueError, TypeError):
            raise ValueError("Invalid POSTGRES_PORT, must be a valid number string.")

        # Build the DSN string
        # Note: PostgresDsn.build is useful but can be sensitive to types.
        # Constructing the string manually offers more control.
        db_uri = (
            f"postgresql+asyncpg://{values_data['POSTGRES_USER']}:{values_data['POSTGRES_PASSWORD']}"
            f"@{values_data['POSTGRES_SERVER']}:{port_val}/{values_data['POSTGRES_DB']}"
        )
        return db_uri


    class Config:
        # Load .env file. Variables in .env override class defaults.
        # Environment variables override .env variables.
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Future K8s Deployment: Uncomment and configure secrets directory
        # secrets_dir = '/etc/secrets'
        # Optional: Add config sources for YAML if needed

# Use lru_cache to cache the settings instance
# maxsize=None ensures it caches indefinitely until cleared
@lru_cache(maxsize=None)
def get_settings() -> Settings:
    logger.info("Loading settings...")
    try:
        settings_instance = Settings()
        # Reconfigure root logger level based on loaded settings
        logging.getLogger().setLevel(settings_instance.LOG_LEVEL)
        logger.info(f"Settings loaded successfully for APP_ENV: {settings_instance.APP_ENV}")
        return settings_instance
    except Exception as e:
        logger.error(f"Failed to load settings: {e}", exc_info=True)
        raise

def reload_settings():
    """Clears the settings cache, forcing a reload on the next call to get_settings()."""
    logger.warning("Reloading application settings...")
    get_settings.cache_clear()
    # Optionally, trigger dependent service re-initializations here

# Global settings instance - accessed via get_settings()
# Avoid importing 'settings' directly elsewhere; use get_settings() instead.
# settings = get_settings() # Remove direct instantiation at module level

# --- File Watcher Integration Point (Conceptual) --- 
# In main.py or a background task runner:
# 
# import asyncio
# from watchfiles import awatch
# from core.config import reload_settings
# 
# async def watch_config_files():
#     config_paths = ['/etc/config', '/etc/secrets'] # Add default-config.yaml for local?
#     logger.info(f"Starting file watcher for config changes in: {config_paths}")
#     async for changes in awatch(*config_paths):
#         logger.warning(f"Detected config change: {changes}. Triggering settings reload.")
#         reload_settings()
#         # Add delay/debounce if needed
#         await asyncio.sleep(2) # Simple debounce
# 
# # In FastAPI startup event:
# asyncio.create_task(watch_config_files())
# 

# Optional: Add a log statement to show loaded settings during startup (for debugging)
# import logging
# logging.basicConfig(level=settings.LOG_LEVEL)
# logging.info(f"Settings loaded for APP_ENV: {settings.APP_ENV}")
# logging.debug(f"Loaded settings: {settings.model_dump()}") # Use model_dump in Pydantic v2 