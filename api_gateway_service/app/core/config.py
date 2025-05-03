from pydantic_settings import BaseSettings
from typing import Dict, Any, Optional
from pydantic import ConfigDict


class APIGatewaySettings(BaseSettings):
    """
    API Gateway configuration settings.
    
    Load settings from environment variables or .env file.
    
    API_KEYS: Comma-separated list of valid API keys for authentication.
    """
    # API settings
    API_TITLE: str = "KFM-AE API Gateway"
    API_VERSION: str = "1.0"
    API_PREFIX: str = "/api/v1"
    
    # Service URLs - These will be loaded from environment variables
    AGENT_REGISTRY_URL: str = "http://localhost:8001"
    F_OPERATOR_URL: str = "http://localhost:8002"
    M_OPERATOR_URL: str = "http://localhost:8003"
    K_OPERATOR_URL: str = "http://localhost:8004"
    
    # Service name mappings
    SERVICE_NAME_MAPPINGS: Dict[str, str] = {
        "agent-registry": "AGENT_REGISTRY_URL",
        "f-operator": "F_OPERATOR_URL",
        "m-operator": "M_OPERATOR_URL",
        "k-operator": "K_OPERATOR_URL",
    }
    
    # HTTP Client settings
    HTTP_TIMEOUT_SECONDS: int = 30
    HTTP_MAX_RETRIES: int = 3
    HTTP_RETRY_BACKOFF: float = 0.5
    HTTP_RETRY_STATUS_CODES: list = [408, 429, 500, 502, 503, 504]
    
    # Service registry settings
    SERVICE_CACHE_TTL_SECONDS: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # API key management
    API_KEYS: str = "supersecretkey"  # Comma-separated list of valid API keys

    def get_api_key_set(self) -> set:
        return set(k.strip() for k in self.API_KEYS.split(",") if k.strip())
    
    model_config = ConfigDict(extra='ignore')


def get_settings() -> APIGatewaySettings:
    """
    Get API Gateway settings from environment variables or .env file.
    
    Returns:
        APIGatewaySettings: API Gateway settings.
    """
    return APIGatewaySettings() 