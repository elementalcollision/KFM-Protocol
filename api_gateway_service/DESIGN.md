# API Gateway Architecture & Message Structure

This document captures the architectural design, routing strategy, standardized message schemas, and error handling approach for the KFM-AE API Gateway, as outlined in Task 8.1.

## 1. Technology Selection

- **Framework**: FastAPI with Pydantic for schema validation
- **HTTP Client**: HTTPX for async HTTP requests to backend services
- **Infrastructure**: Self-hosted service (can be migrated to AWS API Gateway later if needed)

## 2. Standardized Message Structure

All API communications use a standardized message structure to ensure consistency and facilitate debugging, logging, and tracing.

### 2.1 Base Message Structure

The `BaseMessage` schema defines the core fields required in all API messages:

```python
class BaseMessage(BaseModel):
    request_id: UUID                # Unique identifier for request tracking
    timestamp: datetime             # UTC timestamp for the request
    source_service: str             # Identifier of the calling service/client
    target_service: str             # Identifier of the destination service
    api_version: str = "v1"         # API version (default: v1)
```

### 2.2 Request/Response Models

Generic request and response models extend `BaseMessage` with a payload field:

```python
class RequestData(BaseMessage):
    payload: Dict[str, Any]         # Request payload data

class ResponseData(BaseMessage):
    payload: Dict[str, Any]         # Response payload data
```

### 2.3 Error Handling

Standardized error responses ensure consistent error reporting:

```python
class ErrorDetail(BaseModel):
    field: Optional[str]            # Field that caused the error (if applicable)
    code: str                       # Error code for programmatic handling
    message: str                    # Human-readable error message

class ErrorResponse(BaseMessage):
    error: ErrorDetail              # Error details
    status_code: int                # HTTP status code
```

### 2.4 Schema Extension

Domain-specific schemas extend the base models. For example:

```python
class AgentListRequest(RequestData):
    payload: Dict = Field(default={}, description="Optional filtering parameters")

class AgentListResponse(ResponseData):
    payload: Dict[str, List[AgentDetail]] = Field(
        ..., 
        description="Dictionary containing 'agents' list and metadata"
    )
```

## 3. Routing Strategy

The API Gateway will use path-based routing:

- Base path: `/api/v1/{service_name}/{endpoint}`
- Example: `/api/v1/agent-registry/agents` routes to the Agent Registry service's `/agents` endpoint

A service registry will map service names to backend URLs, configured via environment variables or a configuration file.

## 4. Integration Pattern

- **Service Communication**: Async HTTP calls using HTTPX client
- **Error Handling**: Standardized error responses with appropriate HTTP status codes
- **Request Flow**:
  1. Client request → API Gateway
  2. Gateway validates and transforms request
  3. Gateway routes request to backend service
  4. Gateway transforms response and returns to client

## 5. Communication Patterns

### 5.1 Synchronous Communication

The API Gateway implements a robust synchronous communication pattern for immediate request-response scenarios:

#### 5.1.1 Timeout Configuration

Different endpoints have different performance characteristics, so the API Gateway uses a tiered timeout system:

```python
class TimeoutCategory(Enum):
    FAST = 1        # Quick operations (<1s)
    STANDARD = 5    # Normal operations (1-5s)
    EXTENDED = 30   # Complex operations (5-30s)
    LONG_RUNNING = 120  # Long-running operations (30s+)
```

Each service and endpoint has a configured timeout category, which is automatically applied when routing requests. This is implemented in `app/core/timeout.py` with the `SERVICE_TIMEOUT_MAPPINGS` configuration that maps services and endpoints to appropriate timeout categories.

#### 5.1.2 Response Transformation

The `ResponseTransformerMiddleware` (in `app/middleware/response_transformer.py`) ensures all responses follow a consistent format:

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

This middleware handles:
- Transformation of raw responses to standardized format
- Inclusion of request metadata (request ID, timing information)
- Proper error handling and standardization
- Consistent status codes and response structure

#### 5.1.3 Resilience Patterns

Several resilience patterns are implemented to handle failures gracefully:

- **Circuit Breaker** (`app/core/circuit_breaker.py`): Prevents cascading failures by stopping requests to failing services
  - Maintains states (CLOSED, OPEN, HALF-OPEN) to manage service recovery
  - Provides automatic service health monitoring
  - Configurable failure thresholds and recovery timeouts
  - Exposes circuit status through the `/health/circuit-breakers` endpoint

- **Retry Mechanism** (in HTTP client): Automatically retries requests that fail due to transient issues
  - Uses exponential backoff for retries
  - Configurable retry count and status codes
  - Smart retry logic that respects circuit breaker state

- **Response Caching** (`app/core/cache.py`): Caches responses from frequently accessed endpoints
  - Time-based expiration with configurable TTL
  - Support for stale cache serving when backend services are unavailable
  - LRU (Least Recently Used) eviction policy to manage memory usage
  - Cache status headers for client awareness

- **Graceful Degradation**: Falls back to alternative responses when services are unavailable
  - Returns cached data when possible with stale indicators
  - Provides empty/default responses when necessary
  - Includes detailed error information to help diagnose issues

The HTTP client service (`app/services/http_client.py`) integrates these patterns to provide resilient communication with backend services:
- Dynamic timeout selection based on service and endpoint
- Automatic circuit breaker integration
- Connection pooling for performance optimization
- Complete error handling and standardization

For more details on the synchronous communication implementation, see:
- [Synchronous Communication Documentation](./docs/sync_communication.md)
- [Synchronous Communication FAQ](./docs/sync_communication_faq.md)
- [API Usage Guide](./docs/api_usage.md)

### 5.2 Asynchronous Communication

The asynchronous communication pattern will be implemented in the next subtask (8.4). This will include:
- Task tracking endpoints
- Task queue system
- Notification mechanisms (webhooks/event streams)
- Task state persistence

## 6. Future Considerations

- Rate limiting and throttling
- Authentication and authorization
- Request/response logging
- Asynchronous communication pattern for long-running operations (coming in subtask 8.4)
- Webhook support for event notifications

