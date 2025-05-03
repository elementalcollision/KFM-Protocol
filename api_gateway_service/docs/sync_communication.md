# Synchronous Communication Pattern

This document describes the synchronous communication pattern implemented in the API Gateway service.

> **Note:** For frequently asked questions, see the [Synchronous Communication FAQ](sync_communication_faq.md).

## Overview

The synchronous communication pattern provides immediate request-response interactions between clients and backend services. This pattern is used for operations that require an immediate response, such as retrieving data or performing simple operations.

## Core Components

### 1. Timeout Configuration

The API Gateway implements a flexible timeout system that adapts to different types of operations:

```python
# From app/core/timeout.py
class TimeoutCategory(Enum):
    FAST = 1        # Quick operations (<1s)
    STANDARD = 5    # Normal operations (1-5s)
    EXTENDED = 30   # Complex operations (5-30s)
    LONG_RUNNING = 120  # Long-running operations (30s+)
```

Timeouts are configured per service and endpoint, allowing for fine-grained control over how long each operation can take:

```python
SERVICE_TIMEOUT_MAPPINGS = {
    "agent-registry": {
        "get_agent": TimeoutCategory.FAST,
        "list_agents": TimeoutCategory.FAST,
        # ...
    },
    "f-operator": {
        "execute_function": TimeoutCategory.EXTENDED,
        # ...
    }
}
```

### 2. Response Transformation

All responses are transformed into a standardized format using the `ResponseTransformerMiddleware`, ensuring consistency across the API:

```json
{
  "status": "success",  // or "error"
  "data": { ... },      // only present for successful responses
  "error": { ... },     // only present for error responses
  "metadata": {
    "request_id": "uuid-string",
    "timestamp": "iso-timestamp",
    "service": "api_gateway",
    "status_code": 200
  }
}
```

### 3. Circuit Breaker

The circuit breaker pattern prevents cascading failures by temporarily stopping requests to failing services:

- **Closed State**: Normal operation, requests proceed to backend services
- **Open State**: Service is failing, requests are rejected immediately
- **Half-Open State**: Testing if service has recovered, limited requests allowed

### 4. Caching Strategy

Response caching improves performance for frequently-accessed endpoints:

- Time-based expiration
- LRU (Least Recently Used) eviction when capacity is reached
- Stale cache serving when backend services are unavailable

## Key Behaviors

### Dynamic Timeout Selection

```python
# Example HTTP client call with dynamic timeout
response = await http_client.get(
    f"{settings.AGENT_REGISTRY_URL}/agents",
    service="agent-registry",
    endpoint="list_agents"
)
```

The HTTP client automatically selects the appropriate timeout based on the service and endpoint.

### Graceful Degradation

When a service is unavailable due to the circuit breaker being open:

1. Try to serve stale cached data if available
2. Return a fallback empty response if no cache is available
3. Include circuit status in the response for observability

```python
except CircuitBreakerOpenException:
    # Circuit breaker is open, try to serve stale data
    stale_data = await cache.get(cache_key)
    if stale_data:
        return {"agents": stale_data, "cache": "stale", "circuit": "open"}
    
    # No stale data, return fallback empty response
    return {"agents": [], "cache": "none", "circuit": "open"}
```

### Retry Logic

Requests to backend services include automatic retry logic with exponential backoff:

1. Configurable maximum retries (default: 3)
2. Exponential backoff between retries
3. Retry only on specific status codes (408, 429, 500, 502, 503, 504)

## API Endpoints

### Health Check Endpoints

- `GET /health` - Basic health check
- `GET /health/circuit-breakers` - Status of all circuit breakers

### Example Agent Endpoints

- `GET /api/v1/agents` - List all agents (with caching)
- `GET /api/v1/agents/{agent_id}` - Get a specific agent

## Configuration

Configuration is provided through environment variables or `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| HTTP_TIMEOUT_SECONDS | Default timeout for HTTP requests | 30 |
| HTTP_MAX_RETRIES | Maximum number of retries | 3 |
| HTTP_RETRY_BACKOFF | Base backoff time in seconds | 0.5 |
| HTTP_RETRY_STATUS_CODES | Status codes to retry | [408, 429, 500, 502, 503, 504] |

## Performance Considerations

1. **Connection Pooling**: The HTTP client uses connection pooling to reduce connection establishment overhead.

2. **Cache Optimization**: Frequently accessed data is cached to reduce backend service load.

3. **Circuit Breaker Tuning**: Circuit breakers can be tuned with the following parameters:
   - Failure threshold
   - Recovery timeout
   - Half-open max calls

## Monitoring and Observability

- All requests include `X-Request-ID` for correlation
- Response headers include `X-Process-Time` for performance tracking
- Circuit breaker states are exposed through the `/health/circuit-breakers` endpoint
- Structured logging is used throughout for easier analysis

## Example Usage

```python
# Client code example
async def get_agent(agent_id: str):
    try:
        response = await http_client.get(
            f"{settings.AGENT_REGISTRY_URL}/agents/{agent_id}",
            service="agent-registry",
            endpoint="get_agent"
        )
        return response
    except CircuitBreakerOpenException:
        # Handle circuit breaker open
        return fallback_response()
    except ServiceConnectionError:
        # Handle connection error
        return error_response()
``` 