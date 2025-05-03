from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, Field
from typing import Dict, Any, List

class Settings(BaseSettings):
    # Database connection URL
    DATABASE_URL: PostgresDsn
    # Echo SQL statements (for debugging)
    DB_ECHO: bool = False
    # Alembic migrations directory
    ALEMBIC_MIGRATIONS_DIR: str = "alembic"

    # Service URLs
    AGENT_REGISTRY_SERVICE_URL: str = "http://localhost:8000" # Example default

    # Maintenance Settings
    MAINTENANCE_REVIEW_INTERVAL_DAYS: int = 90
    MAINTENANCE_SCHEDULER_HOUR: int = 2 # Hour to run daily check
    MAINTENANCE_SCHEDULER_MINUTE: int = 0
    MAINTENANCE_SCHEDULER_DAY_OF_WEEK: str = 'sun' # Day to run weekly agent scheduling

    # Approval Workflow Configuration (loaded from config/default-config.yaml)
    APPROVAL_WORKFLOWS: Dict[str, Any] = {
        "default": {
            "roles": [
                {"role": "DEFAULT_APPROVER", "required": True}
            ]
        }
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Add mechanism to load from YAML later if needed

# Instantiate settings
settings = Settings() 