import logging
import asyncio
import httpx
from typing import Dict, Any, Optional, Union, List
from functools import lru_cache
import re

from app.core.config import APIGatewaySettings, get_settings
from app.core.errors import ServiceConnectionError
from app.core.circuit_breaker import get_circuit_breaker_registry, CircuitBreakerOpenException
from app.core.timeout import get_timeout_for_request


logger = logging.getLogger(__name__)


class HTTPClientService:
    """
    HTTP client service for backend communication.
    
    Handles retries, timeouts, and error handling for HTTP requests to backend services.
    """
    def __init__(self, settings: APIGatewaySettings = get_settings()):
        """
        Initialize HTTP client service with settings.
        
        Args:
            settings: API Gateway settings.
        """
        self.settings = settings
        self.max_retries = settings.HTTP_MAX_RETRIES
        self.retry_backoff = settings.HTTP_RETRY_BACKOFF
        self.retry_status_codes = settings.HTTP_RETRY_STATUS_CODES
        
        # Create client with default timeout - will be overridden per request
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS))
        self.circuit_breaker_registry = get_circuit_breaker_registry()
        
    async def get(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Execute GET request with retry and error handling.
        
        Args:
            url: URL to request.
            params: Query parameters.
            headers: HTTP headers.
            service: Service name for timeout and circuit breaker.
            endpoint: Endpoint name for timeout and circuit breaker.
            timeout: Custom timeout in seconds (overrides service/endpoint mapping).
            
        Returns:
            Any: Response data (JSON or text).
            
        Raises:
            ServiceConnectionError: If connection to service fails after retries.
            CircuitBreakerOpenException: If circuit breaker is open.
        """
        return await self._execute_with_retry(
            method="GET", 
            url=url, 
            params=params, 
            headers=headers,
            service=service,
            endpoint=endpoint,
            timeout=timeout
        )
        
    async def post(
        self, 
        url: str, 
        json: Any, 
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Execute POST request with retry and error handling.
        
        Args:
            url: URL to request.
            json: JSON data to send.
            params: Query parameters.
            headers: HTTP headers.
            service: Service name for timeout and circuit breaker.
            endpoint: Endpoint name for timeout and circuit breaker.
            timeout: Custom timeout in seconds (overrides service/endpoint mapping).
            
        Returns:
            Any: Response data (JSON or text).
            
        Raises:
            ServiceConnectionError: If connection to service fails after retries.
            CircuitBreakerOpenException: If circuit breaker is open.
        """
        return await self._execute_with_retry(
            method="POST", 
            url=url, 
            json=json, 
            params=params, 
            headers=headers,
            service=service,
            endpoint=endpoint,
            timeout=timeout
        )
        
    async def put(
        self, 
        url: str, 
        json: Any, 
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Execute PUT request with retry and error handling.
        
        Args:
            url: URL to request.
            json: JSON data to send.
            params: Query parameters.
            headers: HTTP headers.
            service: Service name for timeout and circuit breaker.
            endpoint: Endpoint name for timeout and circuit breaker.
            timeout: Custom timeout in seconds (overrides service/endpoint mapping).
            
        Returns:
            Any: Response data (JSON or text).
            
        Raises:
            ServiceConnectionError: If connection to service fails after retries.
            CircuitBreakerOpenException: If circuit breaker is open.
        """
        return await self._execute_with_retry(
            method="PUT", 
            url=url, 
            json=json, 
            params=params, 
            headers=headers,
            service=service,
            endpoint=endpoint,
            timeout=timeout
        )
        
    async def delete(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Execute DELETE request with retry and error handling.
        
        Args:
            url: URL to request.
            params: Query parameters.
            headers: HTTP headers.
            service: Service name for timeout and circuit breaker.
            endpoint: Endpoint name for timeout and circuit breaker.
            timeout: Custom timeout in seconds (overrides service/endpoint mapping).
            
        Returns:
            Any: Response data (JSON or text).
            
        Raises:
            ServiceConnectionError: If connection to service fails after retries.
            CircuitBreakerOpenException: If circuit breaker is open.
        """
        return await self._execute_with_retry(
            method="DELETE", 
            url=url, 
            params=params, 
            headers=headers,
            service=service,
            endpoint=endpoint,
            timeout=timeout
        )
        
    async def forward_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        path_params: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Forward a request to a backend service.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            url: URL to forward to.
            headers: HTTP headers.
            params: Query parameters.
            path_params: Path parameters to substitute in URL.
            body: Request body.
            service: Service name for timeout and circuit breaker.
            endpoint: Endpoint name for timeout and circuit breaker.
            timeout: Custom timeout in seconds (overrides service/endpoint mapping).
            
        Returns:
            Any: Response data.
            
        Raises:
            ServiceConnectionError: If connection to service fails after retries.
            CircuitBreakerOpenException: If circuit breaker is open.
        """
        # Replace path parameters in URL
        if path_params:
            for param, value in path_params.items():
                url = url.replace(f"{{{param}}}", str(value))
                
        # Setup request arguments
        request_args = {
            "headers": headers,
            "params": params,
            "service": service,
            "endpoint": endpoint,
            "timeout": timeout
        }
        
        # Add body for POST/PUT
        if method in ["POST", "PUT", "PATCH"] and body:
            request_args["content"] = body
            
        return await self._execute_with_retry(method=method, url=url, **request_args)
        
    async def _execute_with_retry(
        self, 
        method: str, 
        url: str,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Execute request with retry logic and circuit breaker.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            url: URL to request.
            service: Service name for timeout and circuit breaker.
            endpoint: Endpoint name for timeout and circuit breaker.
            timeout: Custom timeout in seconds (overrides service/endpoint mapping).
            **kwargs: Additional arguments for request.
            
        Returns:
            Any: Response data.
            
        Raises:
            ServiceConnectionError: If connection to service fails after retries.
            CircuitBreakerOpenException: If circuit breaker is open.
        """
        # Extract service and endpoint from URL if not provided
        if not service:
            service = self._extract_service_from_url(url)
        if not endpoint:
            endpoint = self._extract_endpoint_from_url(url)
            
        # Determine appropriate timeout
        if timeout is None and service and endpoint:
            timeout = get_timeout_for_request(service, endpoint)
        elif timeout is None:
            timeout = self.settings.HTTP_TIMEOUT_SECONDS
        
        # Create a circuit breaker key for this request
        circuit_name = f"{service or 'unknown'}.{endpoint or 'unknown'}"
        circuit_breaker = await self.circuit_breaker_registry.get_or_create(circuit_name)
        
        try:
            # Execute with circuit breaker
            return await circuit_breaker.execute(
                self._do_request_with_retry,
                method=method,
                url=url,
                timeout=timeout,
                **kwargs
            )
        except CircuitBreakerOpenException as e:
            logger.warning(f"Circuit breaker open for {circuit_name}: {str(e)}")
            raise
            
    async def _do_request_with_retry(
        self, 
        method: str, 
        url: str, 
        timeout: int,
        **kwargs
    ) -> Any:
        """
        Execute request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            url: URL to request.
            timeout: Timeout in seconds.
            **kwargs: Additional arguments for request.
            
        Returns:
            Any: Response data.
            
        Raises:
            ServiceConnectionError: If connection to service fails after retries.
        """
        retries = 0
        last_exception = None
        
        # Set timeout for this request
        request_timeout = httpx.Timeout(timeout)
        
        while retries <= self.max_retries:
            try:
                # Log the request attempt
                if retries > 0:
                    logger.info(f"Retry {retries}/{self.max_retries} for {method} {url}")
                
                # Execute request with specific timeout
                response = await self.client.request(
                    method, 
                    url, 
                    timeout=request_timeout,
                    **kwargs
                )
                
                # Check if status code indicates we should retry
                if response.status_code in self.retry_status_codes and retries < self.max_retries:
                    retries += 1
                    await asyncio.sleep(self.retry_backoff * (2 ** retries))
                    continue
                    
                # Check if it's an error response
                if response.status_code >= 400:
                    return self._handle_error_response(response)
                
                # Parse response based on content type
                if "application/json" in response.headers.get("content-type", ""):
                    return response.json()
                return response.text
                
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                retries += 1
                
                if retries <= self.max_retries:
                    await asyncio.sleep(self.retry_backoff * (2 ** retries))
                else:
                    break
                    
        # If we've exhausted retries, raise the last exception
        raise ServiceConnectionError(
            f"Failed to connect to service after {self.max_retries} retries: {str(last_exception)}"
        )
    
    def _handle_error_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Handle error response from backend service.
        
        Args:
            response: HTTPX response.
            
        Returns:
            Dict[str, Any]: Standardized error response.
        """
        try:
            # Try to parse as JSON
            error_data = response.json()
            return error_data
        except Exception:
            # If not JSON, create a standard error response
            return {
                "error": {
                    "status_code": response.status_code,
                    "message": response.text or "Unknown error"
                }
            }
            
    def _extract_service_from_url(self, url: str) -> Optional[str]:
        """
        Extract service name from URL.
        
        Args:
            url: URL to parse.
            
        Returns:
            Optional[str]: Service name if found, None otherwise.
        """
        # Try to extract service name from URL pattern like http://service-name:port/...
        match = re.search(r'//([^:/]+)', url)
        if match:
            service = match.group(1)
            # Convert service-name to service_name
            service = service.replace('-', '_')
            return service
        return None
        
    def _extract_endpoint_from_url(self, url: str) -> Optional[str]:
        """
        Extract endpoint name from URL.
        
        Args:
            url: URL to parse.
            
        Returns:
            Optional[str]: Endpoint name if found, None otherwise.
        """
        # Try to extract the last path component as the endpoint
        match = re.search(r'/([^/]+)/?$', url)
        if match:
            return match.group(1)
        return None
        
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


@lru_cache()
def get_http_client(settings: APIGatewaySettings = get_settings()) -> HTTPClientService:
    """
    Get HTTP client service instance.
    
    Returns:
        HTTPClientService: HTTP client service.
    """
    return HTTPClientService(settings) 