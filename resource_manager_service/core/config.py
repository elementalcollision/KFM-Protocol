import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "KFM Resource Manager Service"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Kubernetes Config Path (if running outside cluster)
    KUBE_CONFIG_PATH: Optional[str] = os.getenv("KUBE_CONFIG_PATH", None)

    # --- Observability --- 
    # Tracing Configuration
    SERVICE_NAME: str = "resource-manager-service" # Default service name for OTEL
    OTEL_TRACE_ENABLED: bool = os.getenv("OTEL_TRACE_ENABLED", "true").lower() == "true"
    OTLP_ENDPOINT: Optional[str] = os.getenv("OTLP_ENDPOINT", None) # e.g., http://jaeger-collector...:4318/v1/traces

    # Configuration Management Endpoint (Task 12 - Where to get quota config)
    # Example: Assumes a central config service or file path
    CONFIG_SOURCE_URL: Optional[str] = os.getenv("CONFIG_SOURCE_URL", None)
    CONFIG_QUOTA_FILE: str = os.getenv("CONFIG_QUOTA_FILE", "/config/resource_quotas.yaml") # Path within container or URL

    # --- Messaging --- 
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/") # Default local RabbitMQ
    KFM_EVENT_EXCHANGE: str = os.getenv("KFM_EVENT_EXCHANGE", "kfm_events")
    RESOURCE_EVENT_QUEUE: str = os.getenv("RESOURCE_EVENT_QUEUE", "resource_manager_queue")
    RESOURCE_EVENT_ROUTING_KEY: str = os.getenv("RESOURCE_EVENT_ROUTING_KEY", "agent.state.#") # Listen for all state changes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings() 