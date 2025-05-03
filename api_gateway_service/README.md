# API Gateway Service

A unified entry point for clients to interact with the KFM-AE ecosystem's microservices.

## Overview

The API Gateway service provides a single access point for external clients to interact with various KFM-AE microservices. It handles routing, load balancing, request/response transformation, and implements resilience patterns for improved reliability.

## Features

- **Unified API surface** for all backend microservices
- **Dynamic routing** to appropriate backend services
- **Standardized message format** for all API communication
- **Resilience patterns**: Circuit breaker, retry mechanism, response caching
- **Adaptive timeouts** based on service and endpoint characteristics
- **Graceful degradation** when services are unavailable
- **Request/response correlation** with unique request IDs
- **Performance monitoring** with request timing information

## Documentation

- [API Gateway Design](DESIGN.md): Architectural design and standardized message structure
- [Synchronous Communication Pattern](docs/sync_communication.md): Detailed implementation of the synchronous communication pattern
- [Synchronous Communication FAQ](docs/sync_communication_faq.md): Frequently asked questions about synchronous communication
- [API Usage Guide](docs/api_usage.md): Comprehensive API reference with examples

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL (for backend services)

### Setup

1. Clone the repository

```bash
git clone https://github.com/your-org/KFMEvolution.git
cd KFMEvolution/api_gateway_service
```

2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example` and configure your environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Start the service

```bash
uvicorn main:app --reload
```

The API Gateway will be available at `http://localhost:8000`.

## Configuration

The API Gateway is configured through environment variables or a `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| API_TITLE | Title of the API | "KFM-AE API Gateway" |
| API_VERSION | API version | "1.0" |
| API_PREFIX | API route prefix | "/api/v1" |
| AGENT_REGISTRY_URL | URL to Agent Registry service | "http://localhost:8001" |
| F_OPERATOR_URL | URL to F-Operator service | "http://localhost:8002" |
| M_OPERATOR_URL | URL to M-Operator service | "http://localhost:8003" |
| K_OPERATOR_URL | URL to K-Operator service | "http://localhost:8004" |
| HTTP_TIMEOUT_SECONDS | Default HTTP timeout | 30 |
| HTTP_MAX_RETRIES | Maximum number of retries | 3 |
| HTTP_RETRY_BACKOFF | Base backoff time in seconds | 0.5 |
| LOG_LEVEL | Logging level | "INFO" |

## Usage

### API Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Health Checks

- `GET /health` - Basic health check
- `GET /health/circuit-breakers` - Status of all circuit breakers

### Examples

#### Agent Registry

```bash
# List all agents
curl -X GET "http://localhost:8000/api/v1/agents"

# Get a specific agent
curl -X GET "http://localhost:8000/api/v1/agents/123"
```

#### F-Operator

```bash
# Execute a function
curl -X POST "http://localhost:8000/api/v1/functions/execute" \
  -H "Content-Type: application/json" \
  -d '{"function_id": "123", "parameters": {"param1": "value1"}}'
```

## Project Structure

```
api_gateway_service/
├── app/
│   ├── api/
│   │   ├── endpoints/           # API endpoint implementations
│   │   │   ├── agents.py
│   │   │   └── ...
│   │   └── router.py            # API route definitions
│   ├── core/
│   │   ├── cache.py             # Cache implementation
│   │   ├── circuit_breaker.py   # Circuit breaker pattern
│   │   ├── config.py            # Application configuration
│   │   ├── errors.py            # Error handling
│   │   ├── timeout.py           # Timeout configuration
│   │   └── ...
│   ├── middleware/
│   │   ├── request_processor.py # Request processing middleware
│   │   ├── response_transformer.py # Response transformation middleware
│   │   └── ...
│   ├── models/                  # Data models and schemas
│   ├── schemas/                 # Pydantic schemas
│   └── services/
│       ├── http_client.py       # HTTP client for backend communication
│       └── ...
├── docs/                        # Documentation
│   └── sync_communication.md    # Sync communication documentation
├── tests/                       # Unit and integration tests
├── .env.example                 # Example environment configuration
├── DESIGN.md                    # Design documentation
├── main.py                      # Application entry point
├── README.md                    # This file
└── requirements.txt             # Python dependencies
```

## Architecture

The API Gateway uses a middleware-based architecture:

1. **Request Processor Middleware** - Handles request ID generation, timing, and logging
2. **Response Transformer Middleware** - Ensures consistent response format
3. **Core Router** - Routes requests to appropriate backend services
4. **HTTP Client** - Communicates with backend services with resilience patterns

## Testing

To run tests:

```bash
pytest
```

## License

[MIT](LICENSE) 