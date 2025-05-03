# Synchronous Communication Pattern FAQ

This document answers frequently asked questions about the synchronous communication pattern implemented in the API Gateway service.

## Table of Contents
1. [General Questions](#general-questions)
2. [Timeout Configuration](#timeout-configuration)
3. [Circuit Breaker](#circuit-breaker)
4. [Response Caching](#response-caching)
5. [Error Handling](#error-handling)
6. [Performance Optimization](#performance-optimization)

## General Questions

### Q: What is the synchronous communication pattern?
**A:** The synchronous communication pattern is a request-response interaction model where the client sends a request and waits for an immediate response. The API Gateway implements this pattern for operations that require immediate feedback, like retrieving data or performing simple operations.

### Q: When should I use synchronous vs. asynchronous endpoints?
**A:** Use synchronous endpoints for:
- Quick operations that complete in seconds
- Simple read operations
- Operations where the client needs immediate feedback

Use asynchronous endpoints (see upcoming implementation) for:
- Long-running operations that may take minutes or longer
- Resource-intensive processing
- Operations that may need to survive API Gateway restarts

### Q: How do I know if an endpoint is synchronous?
**A:** All API Gateway endpoints are synchronous by default unless explicitly marked as asynchronous. Asynchronous endpoints typically follow a pattern where they return a task ID that can be used to check status later.

## Timeout Configuration

### Q: What are the different timeout categories?
**A:** The API Gateway defines four timeout categories:
- **FAST** (1 second): For simple read operations like retrieving a single record
- **STANDARD** (5 seconds): For normal operations like creating a record
- **EXTENDED** (30 seconds): For complex operations involving multiple steps
- **LONG_RUNNING** (120 seconds): For intensive operations that approach the limit of what's reasonable for synchronous processing

### Q: Can I customize timeouts for specific endpoints?
**A:** Yes, the API Gateway's timeout system maps specific timeouts to service/endpoint combinations. If you need a custom timeout for your use case, please contact the API Gateway team to update the `SERVICE_TIMEOUT_MAPPINGS` configuration.

### Q: What happens when a request times out?
**A:** When a request times out, the API Gateway will:
1. Cancel the request to the backend service
2. Return a 504 Gateway Timeout response with details about which service timed out
3. Log the timeout for monitoring purposes

## Circuit Breaker

### Q: What is the circuit breaker pattern?
**A:** The circuit breaker pattern is a resilience mechanism that prevents cascading failures by temporarily stopping requests to failing services. It works like an electrical circuit breaker:
- **Closed State**: Normal operation, requests flow through
- **Open State**: Service is failing, requests are rejected immediately
- **Half-Open State**: Testing if service has recovered, limited requests allowed

### Q: How does the circuit breaker detect failures?
**A:** The circuit breaker tracks failures based on:
1. HTTP errors (status codes 500+)
2. Connection errors
3. Timeout errors

After a configurable number of consecutive failures (default: 5), the circuit breaker opens.

### Q: How long does a circuit breaker stay open?
**A:** The circuit breaker remains open for a configurable recovery timeout (default: 30 seconds). After this period, it transitions to a half-open state where it allows a limited number of test requests to check if the service has recovered.

### Q: Can I check the status of circuit breakers?
**A:** Yes, you can check the status of all circuit breakers by calling the `/health/circuit-breakers` endpoint, which returns the state of each service's circuit breaker.

## Response Caching

### Q: What responses are cached?
**A:** By default, only read operations (GET requests) with successful responses (status code 200) are cached. The caching behavior is configured per endpoint.

### Q: How long are responses cached?
**A:** Cache TTL (Time To Live) varies by endpoint:
- Frequently changing data: 30-60 seconds
- Relatively stable data: 5-15 minutes
- Reference data: Up to 1 hour

### Q: Does the API Gateway serve stale cache data?
**A:** Yes, when a backend service is unavailable (circuit breaker open), the API Gateway will attempt to serve stale cached data with a special header `X-Cache-Status: stale` to indicate the data may be outdated.

### Q: How can I force a cache refresh?
**A:** Add the `Cache-Control: no-cache` header to your request to bypass the cache and force a fresh request to the backend service.

## Error Handling

### Q: What error status codes can I expect?
**A:** The API Gateway uses standard HTTP status codes:
- 400 series: Client errors (invalid requests, authentication issues)
- 500 series: Server errors (backend service issues, internal errors)

Specific error codes include:
- 408: Request Timeout
- 429: Too Many Requests (rate limiting)
- 502: Bad Gateway (backend service error)
- 503: Service Unavailable (circuit breaker open)
- 504: Gateway Timeout (backend service timeout)

### Q: How are errors standardized?
**A:** All error responses follow a consistent format:
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { /* Additional context */ }
  },
  "metadata": {
    "request_id": "uuid",
    "timestamp": "iso-timestamp",
    "service": "api_gateway",
    "status_code": 400
  }
}
```

## Performance Optimization

### Q: How does the API Gateway handle connection pooling?
**A:** The API Gateway maintains connection pools to each backend service, with a default maximum of 100 concurrent connections per service. This reduces the overhead of establishing new connections for each request.

### Q: Is there any request rate limiting?
**A:** Rate limiting will be implemented in a future update. Currently, the API Gateway does not impose rate limits, but backend services may have their own rate limiting.

### Q: How can I optimize my API usage for performance?
**A:** For optimal performance:
1. Use batch operations when retrieving multiple resources
2. Include only necessary fields in responses when possible
3. Leverage caching by using consistent request parameters
4. Consider using asynchronous endpoints for intensive operations 