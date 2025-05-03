# API Gateway Usage Guide

This document provides detailed usage instructions and examples for the KFM-AE API Gateway service.

## Table of Contents
- [Base URL and Versioning](#base-url-and-versioning)
- [Authentication](#authentication)
- [Request Format](#request-format)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Synchronous Endpoints](#synchronous-endpoints)
- [Service-Specific Endpoints](#service-specific-endpoints)
  - [Agent Registry Service](#agent-registry-service)
  - [F-Operator Service](#f-operator-service)
  - [M-Operator Service](#m-operator-service)
  - [K-Operator Service](#k-operator-service)
- [Health and Monitoring](#health-and-monitoring)

## Base URL and Versioning

All API requests should use the following base URL format:

```
http://{host}:{port}/api/{version}/{service}/{endpoint}
```

- **host**: The hostname or IP address of the API Gateway (default: `localhost`)
- **port**: The port the API Gateway is running on (default: `8000`)
- **version**: The API version (default: `v1`)
- **service**: The target service name
- **endpoint**: The specific endpoint path

Example:
```
http://localhost:8000/api/v1/agent-registry/agents
```

## Authentication

Authentication will be implemented in future versions. Currently, all endpoints are accessible without authentication in the development environment.

## Request Format

### Headers

- `Content-Type`: `application/json` (for POST/PUT/PATCH requests)
- `X-Request-ID` (optional): Client-provided unique identifier for request tracking

### Body (for POST/PUT/PATCH requests)

All request bodies must be valid JSON objects with the following structure:

```json
{
  "data": {
    // Request-specific payload
  },
  "metadata": {
    // Optional metadata
  }
}
```

## Response Format

All responses follow a consistent structure:

```json
{
  "status": "success", // or "error"
  "data": {
    // Response payload (for successful requests)
  },
  "error": {
    // Error details (for failed requests)
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { /* Additional error information */ }
  },
  "metadata": {
    "request_id": "uuid-string",
    "timestamp": "2023-05-12T10:15:30Z",
    "service": "api_gateway",
    "status_code": 200
  }
}
```

## Error Handling

The API Gateway uses standard HTTP status codes with a consistent error response format.

### Common Status Codes

- `200 OK`: Request succeeded
- `400 Bad Request`: Invalid request format or parameters
- `404 Not Found`: Resource not found
- `408 Request Timeout`: Request timed out
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error
- `502 Bad Gateway`: Upstream service error
- `503 Service Unavailable`: Service temporarily unavailable
- `504 Gateway Timeout`: Upstream service timeout

### Error Response Example

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "agent_id",
      "reason": "Must be a valid UUID format"
    }
  },
  "metadata": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2023-05-12T10:15:30Z",
    "service": "api_gateway",
    "status_code": 400
  }
}
```

## Synchronous Endpoints

Synchronous endpoints provide immediate responses and use timeout categories based on the operation complexity:

- **FAST** (1 second): Simple read operations
- **STANDARD** (5 seconds): Normal operations
- **EXTENDED** (30 seconds): Complex operations
- **LONG_RUNNING** (120 seconds): Intensive operations

### Circuit Breaker Behavior

If a service is experiencing issues, the circuit breaker may enter an OPEN state, and you'll receive a response with:

```json
{
  "status": "error",
  "error": {
    "code": "CIRCUIT_OPEN",
    "message": "Service temporarily unavailable due to repeated failures",
    "details": {
      "service": "agent-registry",
      "time_to_recovery": "25s"
    }
  },
  "metadata": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2023-05-12T10:15:30Z",
    "service": "api_gateway",
    "status_code": 503
  }
}
```

## Service-Specific Endpoints

### Agent Registry Service

#### List Agents
- **Endpoint**: `GET /api/v1/agents`
- **Timeout**: FAST (1 second)
- **Query Parameters**:
  - `limit` (optional): Maximum number of agents to return
  - `offset` (optional): Pagination offset
  - `status` (optional): Filter by agent status

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/agents?limit=10&status=active"
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "agents": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Agent1",
        "type": "personal_assistant",
        "status": "active",
        "created_at": "2023-05-12T10:15:30Z"
      },
      {
        "id": "662f9511-f2ab-51e5-b817-557766551111",
        "name": "Agent2",
        "type": "data_analyst",
        "status": "active",
        "created_at": "2023-05-12T11:20:35Z"
      }
    ],
    "total": 2,
    "limit": 10,
    "offset": 0
  },
  "metadata": {
    "request_id": "123e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2023-05-12T15:30:45Z",
    "service": "api_gateway",
    "status_code": 200
  }
}
```

#### Get Agent
- **Endpoint**: `GET /api/v1/agents/{agent_id}`
- **Timeout**: FAST (1 second)
- **Path Parameters**:
  - `agent_id`: The unique identifier of the agent

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/agents/550e8400-e29b-41d4-a716-446655440000"
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "agent": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Agent1",
      "type": "personal_assistant",
      "status": "active",
      "created_at": "2023-05-12T10:15:30Z",
      "updated_at": "2023-05-12T10:15:30Z",
      "configuration": {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 4000
      }
    }
  },
  "metadata": {
    "request_id": "123e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2023-05-12T15:31:20Z",
    "service": "api_gateway",
    "status_code": 200
  }
}
```

#### Create Agent
- **Endpoint**: `POST /api/v1/agents`
- **Timeout**: STANDARD (5 seconds)
- **Request Body**:

```json
{
  "data": {
    "name": "New Agent",
    "type": "personal_assistant",
    "configuration": {
      "model": "gpt-4",
      "temperature": 0.7,
      "max_tokens": 4000
    }
  }
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "New Agent",
      "type": "personal_assistant",
      "configuration": {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 4000
      }
    }
  }'
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "agent": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "New Agent",
      "type": "personal_assistant",
      "status": "active",
      "created_at": "2023-05-12T15:32:10Z",
      "updated_at": "2023-05-12T15:32:10Z",
      "configuration": {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 4000
      }
    }
  },
  "metadata": {
    "request_id": "123e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2023-05-12T15:32:10Z",
    "service": "api_gateway",
    "status_code": 201
  }
}
```

### F-Operator Service

#### Execute Function
- **Endpoint**: `POST /api/v1/functions/execute`
- **Timeout**: EXTENDED (30 seconds)
- **Request Body**:

```json
{
  "data": {
    "function_id": "f123",
    "parameters": {
      "param1": "value1",
      "param2": 42
    }
  }
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/functions/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "function_id": "f123",
      "parameters": {
        "param1": "value1",
        "param2": 42
      }
    }
  }'
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "execution_id": "exec-123",
    "result": {
      "output": "Function executed successfully",
      "data": {
        "calculated_value": 84
      }
    }
  },
  "metadata": {
    "request_id": "123e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2023-05-12T15:33:45Z",
    "service": "api_gateway",
    "status_code": 200,
    "execution_time_ms": 2546
  }
}
```

## Health and Monitoring

### Health Check
- **Endpoint**: `GET /health`

**Example Request:**
```bash
curl -X GET "http://localhost:8000/health"
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "status": "healthy",
    "version": "1.0",
    "uptime": "2h 15m 30s"
  },
  "metadata": {
    "timestamp": "2023-05-12T15:35:10Z",
    "service": "api_gateway"
  }
}
```

### Circuit Breaker Status
- **Endpoint**: `GET /health/circuit-breakers`

**Example Request:**
```bash
curl -X GET "http://localhost:8000/health/circuit-breakers"
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "circuit_breakers": {
      "agent-registry": {
        "state": "closed",
        "failure_count": 0,
        "last_failure": null
      },
      "f-operator": {
        "state": "open",
        "failure_count": 5,
        "last_failure": "2023-05-12T15:30:10Z",
        "estimated_recovery": "2023-05-12T15:35:10Z"
      },
      "m-operator": {
        "state": "closed",
        "failure_count": 0,
        "last_failure": null
      },
      "k-operator": {
        "state": "half_open",
        "failure_count": 3,
        "last_failure": "2023-05-12T15:20:10Z"
      }
    }
  },
  "metadata": {
    "timestamp": "2023-05-12T15:35:10Z",
    "service": "api_gateway"
  }
}
```

## Error Examples

### Invalid Request
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request format",
    "details": {
      "field": "data",
      "reason": "Missing required field"
    }
  },
  "metadata": {
    "request_id": "123e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2023-05-12T15:36:20Z",
    "service": "api_gateway",
    "status_code": 400
  }
}
```

### Service Timeout
```json
{
  "status": "error",
  "error": {
    "code": "SERVICE_TIMEOUT",
    "message": "Request to backend service timed out",
    "details": {
      "service": "f-operator",
      "endpoint": "execute_function",
      "timeout": 30
    }
  },
  "metadata": {
    "request_id": "123e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2023-05-12T15:37:30Z",
    "service": "api_gateway",
    "status_code": 504
  }
}
``` 