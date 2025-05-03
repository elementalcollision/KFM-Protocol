from pydantic_settings import BaseSettings
from typing import Optional
from datetime import timedelta
from isodate import parse_duration # For parsing ISO 8601 durations
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "KFM K Operator Service"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Grace Periods (using ISO 8601 duration format for robustness)
    DEFAULT_DEPRECATION_GRACE_PERIOD_ISO: str = "P30D" # Default 30 days
    DEFAULT_ARCHIVAL_RETENTION_PERIOD_ISO: str = "P90D" # Default 90 days

    # Service Dependencies
    AGENT_REGISTRY_URL: str = "http://localhost:8000/api/v1" # Example

    # Optional DB connection (if K operator needs direct access)
    # POSTGRES_SERVER: Optional[str] = None
    # POSTGRES_USER: Optional[str] = None
    # POSTGRES_PASSWORD: Optional[str] = None
    # POSTGRES_DB: Optional[str] = None
    # SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # Security Settings
    SECRET_KEY: str = "a_very_secret_key_that_should_be_in_env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Example: 30 minutes

    @property
    def deprecation_grace_period(self) -> timedelta:
        try:
            return parse_duration(self.DEFAULT_DEPRECATION_GRACE_PERIOD_ISO)
        except Exception:
            logger.error(f"Invalid ISO 8601 duration format for DEFAULT_DEPRECATION_GRACE_PERIOD_ISO: '{self.DEFAULT_DEPRECATION_GRACE_PERIOD_ISO}'. Falling back to 30 days.")
            return timedelta(days=30)

    @property
    def archival_retention_period(self) -> timedelta:
        try:
            return parse_duration(self.DEFAULT_ARCHIVAL_RETENTION_PERIOD_ISO)
        except Exception:
            logger.error(f"Invalid ISO 8601 duration format for DEFAULT_ARCHIVAL_RETENTION_PERIOD_ISO: '{self.DEFAULT_ARCHIVAL_RETENTION_PERIOD_ISO}'. Falling back to 90 days.")
            return timedelta(days=90)

    # Example database URI construction if needed
    # @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    # def assemble_db_connection(cls, v: Optional[str], values: dict[str, Any]) -> Any:
    #     if isinstance(v, str):
    #         return v
    #     if values.get("POSTGRES_SERVER") and values.get("POSTGRES_USER") and values.get("POSTGRES_PASSWORD") and values.get("POSTGRES_DB"):
    #         return (
    #             f"postgresql+asyncpg://"
    #             f"{values['POSTGRES_USER']}:{values['POSTGRES_PASSWORD']}@"
    #             f"{values['POSTGRES_SERVER']}/{values['POSTGRES_DB']}"
    #         )
    #     return v

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

# Instantiate settings
settings = Settings()

# Add isodate to requirements if not already present
# pip install isodate 