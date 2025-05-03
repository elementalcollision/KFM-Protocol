import time
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, Callable, TypeVar, Awaitable

logger = logging.getLogger(__name__)

# Type variables for generic function handling
T = TypeVar('T')


class CircuitState(Enum):
    """
    Circuit breaker states.
    
    - CLOSED: Normal operation, requests proceed
    - OPEN: Circuit is broken, requests are rejected
    - HALF_OPEN: Testing if service has recovered
    """
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpenException(Exception):
    """
    Exception raised when a request is rejected due to an open circuit.
    """
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    
    Monitors service health and prevents cascading failures.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 1
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the protected service/endpoint.
            failure_threshold: Number of failures before opening the circuit.
            recovery_timeout: Seconds to wait before attempting recovery.
            half_open_max_calls: Maximum concurrent calls in half-open state.
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0
        self._lock = asyncio.Lock()
        
    async def execute(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Async function to execute.
            *args: Function arguments.
            **kwargs: Function keyword arguments.
            
        Returns:
            T: Function result.
            
        Raises:
            CircuitBreakerOpenException: If circuit is open.
            Exception: Any exception raised by the function.
        """
        await self._check_state()
        
        try:
            # Track half-open calls
            if self.state == CircuitState.HALF_OPEN:
                async with self._lock:
                    self.half_open_calls += 1
                    if self.half_open_calls > self.half_open_max_calls:
                        raise CircuitBreakerOpenException(
                            f"Circuit {self.name} is half-open and at capacity"
                        )
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Success - reset if in half-open state
            if self.state == CircuitState.HALF_OPEN:
                await self._reset()
            
            return result
            
        except CircuitBreakerOpenException:
            # Re-raise circuit breaker exceptions
            raise
        except Exception as e:
            # Handle failure
            await self._handle_failure(e)
            raise
            
    async def _check_state(self):
        """
        Check and potentially update circuit state.
        
        Raises:
            CircuitBreakerOpenException: If circuit is open.
        """
        async with self._lock:
            # If circuit is open, check if recovery timeout has elapsed
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    logger.info(f"Circuit {self.name} transitioning from OPEN to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit {self.name} is open - service unavailable"
                    )
    
    async def _handle_failure(self, exception: Exception):
        """
        Handle a function execution failure.
        
        Args:
            exception: Exception that occurred.
        """
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.warning(
                f"Circuit {self.name} recorded failure {self.failure_count}/{self.failure_threshold}: {str(exception)}"
            )
            
            # If in half-open state or failure threshold reached, open circuit
            if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
                old_state = self.state
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name} transitioning from {old_state.value} to OPEN")
    
    async def _reset(self):
        """Reset the circuit breaker to closed state."""
        async with self._lock:
            old_state = self.state
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.half_open_calls = 0
            logger.info(f"Circuit {self.name} transitioning from {old_state.value} to CLOSED")


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    """
    def __init__(self):
        """Initialize an empty registry of circuit breakers."""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
        
    async def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 1
    ) -> CircuitBreaker:
        """
        Get an existing circuit breaker or create a new one.
        
        Args:
            name: Name of the protected service/endpoint.
            failure_threshold: Number of failures before opening the circuit.
            recovery_timeout: Seconds to wait before attempting recovery.
            half_open_max_calls: Maximum concurrent calls in half-open state.
            
        Returns:
            CircuitBreaker: The circuit breaker.
        """
        async with self._lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    half_open_max_calls=half_open_max_calls
                )
            return self.circuit_breakers[name]
            
    def get_all_states(self) -> Dict[str, str]:
        """
        Get the state of all circuit breakers.
        
        Returns:
            Dict[str, str]: Mapping of circuit breaker names to states.
        """
        return {name: cb.state.value for name, cb in self.circuit_breakers.items()}


# Singleton instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """
    Get the circuit breaker registry singleton.
    
    Returns:
        CircuitBreakerRegistry: The circuit breaker registry.
    """
    return _registry 