import logging
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel
from functools import lru_cache

from .config import APIGatewaySettings, get_settings
from .errors import ServiceNotFoundError, ServiceUnavailableError


logger = logging.getLogger(__name__)


class ServiceInfo(BaseModel):
    """Information about a backend service."""
    url: str
    available: bool = True
    last_check: float = 0
    health_info: Optional[Dict[str, Any]] = None


class ServiceRegistry:
    """
    Registry for backend services.
    
    Manages mapping of service names to URLs and service health information.
    """
    def __init__(self, settings: APIGatewaySettings = get_settings()):
        """
        Initialize ServiceRegistry with settings.
        
        Args:
            settings: API Gateway settings.
        """
        self.settings = settings
        self.services: Dict[str, ServiceInfo] = {}
        self._load_services()
        
    def _load_services(self) -> None:
        """Load service mappings from settings."""
        for service_name, url_setting_name in self.settings.SERVICE_NAME_MAPPINGS.items():
            if hasattr(self.settings, url_setting_name):
                service_url = getattr(self.settings, url_setting_name)
                self.services[service_name] = ServiceInfo(url=service_url)
                logger.info(f"Registered service: {service_name} -> {service_url}")
            else:
                logger.warning(f"Missing URL setting for service: {service_name}")
        
    def get_service_url(self, service_name: str) -> str:
        """
        Get the URL for a registered service.
        
        Args:
            service_name: Name of the service.
            
        Returns:
            str: URL of the service.
            
        Raises:
            ServiceNotFoundError: If service is not registered.
            ServiceUnavailableError: If service is unavailable.
        """
        if service_name not in self.services:
            logger.error(f"Service {service_name} not found in registry")
            raise ServiceNotFoundError(f"Service '{service_name}' not registered")
        
        service_info = self.services[service_name]
        
        # Check if service is marked as unavailable
        if not service_info.available:
            # Check if we should retry after cache TTL
            if time.time() - service_info.last_check > self.settings.SERVICE_CACHE_TTL_SECONDS:
                # Reset availability for next attempt
                service_info.available = True
            else:
                logger.warning(f"Service {service_name} is currently unavailable")
                raise ServiceUnavailableError(f"Service '{service_name}' is currently unavailable")
                
        return service_info.url
    
    def mark_service_unavailable(self, service_name: str) -> None:
        """
        Mark a service as unavailable.
        
        Args:
            service_name: Name of the service to mark as unavailable.
            
        Raises:
            ServiceNotFoundError: If service is not registered.
        """
        if service_name not in self.services:
            raise ServiceNotFoundError(f"Service '{service_name}' not registered")
            
        self.services[service_name].available = False
        self.services[service_name].last_check = time.time()
        logger.warning(f"Marked service {service_name} as unavailable")
    
    def mark_service_available(self, service_name: str) -> None:
        """
        Mark a service as available.
        
        Args:
            service_name: Name of the service to mark as available.
            
        Raises:
            ServiceNotFoundError: If service is not registered.
        """
        if service_name not in self.services:
            raise ServiceNotFoundError(f"Service '{service_name}' not registered")
            
        self.services[service_name].available = True
        self.services[service_name].last_check = time.time()
        logger.info(f"Marked service {service_name} as available")
    
    def update_service_health(self, service_name: str, health_info: Dict[str, Any]) -> None:
        """
        Update health information for a service.
        
        Args:
            service_name: Name of the service.
            health_info: Health information for the service.
            
        Raises:
            ServiceNotFoundError: If service is not registered.
        """
        if service_name not in self.services:
            raise ServiceNotFoundError(f"Service '{service_name}' not registered")
            
        self.services[service_name].health_info = health_info
        self.services[service_name].last_check = time.time()
        logger.debug(f"Updated health info for service {service_name}")
        
        
@lru_cache()
def get_service_registry(settings: APIGatewaySettings = get_settings()) -> ServiceRegistry:
    """
    Get the ServiceRegistry instance (cached).
    
    Args:
        settings: API Gateway settings.
        
    Returns:
        ServiceRegistry: ServiceRegistry instance.
    """
    return ServiceRegistry(settings) 