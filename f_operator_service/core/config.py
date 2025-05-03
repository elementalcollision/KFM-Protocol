import os
from typing import Optional, Literal, List, Dict, Any
from functools import lru_cache
import logging
from pathlib import Path
import yaml
from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict

from f_operator_service.schemas.feature_flag import FeatureFlag

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

APP_ENV = os.environ.get("APP_ENV", "development")

class Settings(BaseSettings):
    PROJECT_NAME: str = "KFM F Operator Service"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = APP_ENV
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- Security Settings ---
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "your-secret-key-for-jwt")  # Change in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AUTH_SERVICE_URL: str = "http://localhost:8001"  # URL of the central auth service
    AUTH_SERVICE_TOKEN: Optional[str] = None  # Token for communicating with auth service

    # --- Git Settings ---
    GIT_REPO_BASE_PATH: str = "/tmp/f_operator_repos"
    GIT_DEFAULT_REMOTE: str = "origin"
    GIT_SSH_KEY_PATH: Optional[str] = None # Optional path to SSH private key
    GIT_ACCESS_TOKEN: Optional[str] = None # For HTTPS auth, loaded from env

    # --- AI Platform Settings (Optional) ---
    # Example: Securely load API keys/tokens/roles from environment
    HUGGINGFACE_API_TOKEN: Optional[str] = None
    SAGEMAKER_ROLE_ARN: Optional[str] = None
    # Add other platform-specific credentials or endpoints as needed

    # --- Feature Flags (Loaded from default config, can be overridden) ---
    feature_flags: List[FeatureFlag] = []

    # --- Integration Service URLs ---
    AGENT_REGISTRY_URL: str = "http://localhost:8000" # Default for local dev
    AGENT_REGISTRY_TOKEN: Optional[str] = None
    POLICY_ENGINE_URL: str = "http://localhost:9000"
    POLICY_ENGINE_TOKEN: Optional[str] = None

    # Add other service-specific settings here, e.g.:
    # AGENT_REGISTRY_URL: Optional[str] = "http://agent-registry-service:8000"

    # --- Database Settings (for Experiments) ---
    POSTGRES_SERVER_F: Optional[str] = "localhost"
    POSTGRES_USER_F: Optional[str] = "postgres"
    POSTGRES_PASSWORD_F: Optional[str] = "password"
    POSTGRES_DB_F: Optional[str] = "kfm_f_operator_db" # Separate DB name
    POSTGRES_PORT_F: Optional[str] = "5432"
    SQLALCHEMY_DATABASE_URI_F: Optional[str] = None

    # Use SettingsConfigDict in Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # Load from YAML - requires PyYAML installed
        # Need a custom loader or parse manually in get_settings if not natively supported
        # For simplicity, assume feature flags are loaded manually in get_settings for now.
        # yaml_file='../../config/default-config.yaml' # Path relative to .env?
    )

    @property
    def access_token_expires(self) -> timedelta:
        """Get access token expiration time as timedelta."""
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

    @property
    def refresh_token_expires(self) -> timedelta:
        """Get refresh token expiration time as timedelta."""
        return timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)

@lru_cache(maxsize=None)
def get_settings() -> Settings:
    logger.info("Loading F Operator settings...")
    # Find the root config path (assuming service runs from project root or service dir)
    root_config_path = Path("config/default-config.yaml")
    if not root_config_path.exists():
         # Try path relative to this file's directory if running service standalone
         root_config_path = Path(__file__).parent.parent.parent / "config/default-config.yaml"

    default_config_data = {}
    if root_config_path.exists():
        try:
            with open(root_config_path, 'r') as f:
                default_config_data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load default config from {root_config_path}: {e}")
    else:
        logger.warning(f"Default config file not found at {root_config_path}")

    # Load settings from .env and environment variables first
    try:
        settings_instance = Settings()
        
        # Manually merge feature flags from default config if not overridden by env/.env
        # Pydantic settings doesn't directly load lists of models from yaml easily
        if not settings_instance.feature_flags: # Check if flags were set via env/.env somehow
             loaded_flags = default_config_data.get("feature_flags", [])
             settings_instance.feature_flags = [
                 FeatureFlag(**flag_data) for flag_data in loaded_flags
             ]

        # Assemble DB URI if not set explicitly
        if not settings_instance.SQLALCHEMY_DATABASE_URI_F:
            user = settings_instance.POSTGRES_USER_F
            pwd = settings_instance.POSTGRES_PASSWORD_F
            server = settings_instance.POSTGRES_SERVER_F
            port = settings_instance.POSTGRES_PORT_F
            db = settings_instance.POSTGRES_DB_F
            if all([user, pwd, server, port, db]):
                settings_instance.SQLALCHEMY_DATABASE_URI_F = \
                    f"postgresql+asyncpg://{user}:{pwd}@{server}:{port}/{db}"
            else:
                 logger.warning("F Operator DB URI cannot be constructed. Missing POSTGRES_*_F variables.")

        # Validate security settings
        if settings_instance.APP_ENV == "production":
            if settings_instance.SECRET_KEY == "your-secret-key-for-jwt":
                logger.error("Production environment detected but using default SECRET_KEY!")
                raise ValueError("Must set a secure SECRET_KEY in production")

        logging.getLogger().setLevel(settings_instance.LOG_LEVEL)
        logger.info(f"F Operator settings loaded successfully for APP_ENV: {settings_instance.APP_ENV}")
        # logger.debug(f"Loaded feature flags: {settings_instance.feature_flags}")
        return settings_instance
    except Exception as e:
        logger.error(f"Failed to load F Operator settings: {e}", exc_info=True)
        raise

def reload_settings():
    logger.warning("Reloading F Operator settings...")
    get_settings.cache_clear() 