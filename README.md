# KFM-AE: Kubernetes Fleet Manager for Autonomous Entities

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

KFM-AE is a comprehensive system designed to manage the lifecycle, evolution, and operationalization of autonomous entities (like AI agents, models, or complex software components) within a Kubernetes environment.

## Overview

This project provides a robust backend infrastructure consisting of multiple microservices that work together to:

*   **Register & Discover:** Maintain a central registry of all managed entities, their metadata, state, and capabilities. Allow entities to discover each other.
*   **Manage Lifecycle:** Enforce a defined lifecycle (NEW -> EXPERIMENTAL -> CANDIDATE -> STABLE -> DEPRECATED -> ARCHIVED -> KILLED) through dedicated operators.
*   **Control Evolution (F-Operator):** Handle adaptation, experimentation, versioning, and composition of entities.
*   **Govern Promotion (M-Operator):** Manage the promotion process to STABLE state through configurable checklists and approvals.
*   **Handle End-of-Life (K-Operator):** Manage deprecation, archival, and deletion of entities.
*   **Automate Actions (Policy Engine):** Trigger KFM operations based on defined policies and system metrics.
*   **Manage Resources (Resource Manager):** Allocate and reclaim Kubernetes resources based on entity lifecycle state and quotas.
*   **Observe:** Provide comprehensive logging, metrics, and tracing across the entire system.

See the [System Architecture Documentation](docs/architecture.md) for a detailed overview of the components and their interactions.

## Getting Started

### Prerequisites

*   Python 3.11+
*   Docker & Docker Compose
*   Kubernetes Cluster (e.g., Minikube, Kind, k3s, or a cloud provider cluster)
*   `kubectl` configured to interact with your cluster
*   (Optional) `locust` for load testing (`pip install locust`)
*   (Optional) Taskmaster CLI (`npm install -g task-master-ai`)

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/elementalcollision/KFM-Protocol.git
    cd KFMEvolution
    ```

2.  **Set up Python Environment (Recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate # Or .\venv\Scripts\activate on Windows
    pip install -r requirements.txt
    ```
    *(Note: Individual services have their own `requirements.txt` files used for container builds and isolated testing.)*

3.  **Configure Environment Variables:**
    *   Copy `.env.example` to `.env`.
    *   Review and update variables in `.env`, especially database credentials, service URLs (if not using default Docker Compose networking), and API keys.
    *   Individual services might have their own `.env.example` files within their directories that need similar setup for local development outside containers.

4.  **Set up Databases (if running locally):**
    *   Ensure PostgreSQL is running and accessible.
    *   Ensure Neo4j (or other graph DB) is running and accessible.
    *   Ensure RabbitMQ is running and accessible.
    *   Ensure Redis is running and accessible.
    *   Update connection details in the root `.env` file.

5.  **Database Migrations (Agent Registry Service Example):**
    *   The Agent Registry service uses Alembic for migrations.
    *   Ensure the database specified in `.env` exists.
    *   Navigate to the service directory: `cd agent_registry_service`
    *   Run migrations: `alembic upgrade head`
    *   *(Repeat for other services with database migrations, e.g., M-Operator)*

### Running Locally (Docker Compose - Recommended)

*A `docker-compose.yml` file needs to be created to define and orchestrate all services.* 

1.  **Build Images (Optional - Compose can build):**
    ```bash
    docker compose build 
    ```
2.  **Start Services:**
    ```bash
    docker compose up -d
    ```
3.  **Access Services:**
    *   API Gateway: `http://localhost:8000` (or configured port)
    *   Admin UI: `http://localhost:3000` (or configured port, if included in Compose)

### Running Locally (Individual Services)

*   Ensure all dependencies (databases, message bus) are running.
*   Set required environment variables for each service.
*   Navigate to each service directory (e.g., `cd api_gateway_service`).
*   Run the service using uvicorn:
    ```bash
    uvicorn <service_module>.app.main:app --reload --port <service_port>
    # e.g., uvicorn api_gateway_service.app.main:app --reload --port 8000
    ```

### Running on Kubernetes

1.  **Build and Push Docker Images:**
    *   Configure your container registry details (e.g., Docker Hub username) in `.github/workflows/docker-publish.yaml`.
    *   Ensure Docker Hub credentials (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`) are set as GitHub Actions secrets.
    *   Pushing to `main` branch will trigger the workflow to build and push images.
    *   Alternatively, build manually: `docker build -t <your-registry>/<image-name>:<tag> .` and `docker push ...` for each service.

2.  **Update Kubernetes Manifests:**
    *   Modify the `image:` fields in all `kubernetes/base/*/deployment.yaml` files to point to your pushed images (including the correct tag, e.g., the Git SHA).
    *   Review and adjust namespaces, resource requests/limits, service types (LoadBalancer vs Ingress), and configurations (ConfigMaps/Secrets) in `kubernetes/base/`.

3.  **Apply Manifests:**
    *   Ensure `kubectl` is configured for your target cluster.
    *   Create namespaces if they don't exist (e.g., `kubectl create namespace kfm-gateway`).
    *   Apply the base manifests:
        ```bash
        kubectl apply -f kubernetes/base/config/ # ConfigMaps/Secrets first
        kubectl apply -f kubernetes/base/agent_registry_service/
        kubectl apply -f kubernetes/base/api_gateway_service/
        kubectl apply -f kubernetes/base/f_operator_service/
        kubectl apply -f kubernetes/base/k_operator_service/
        kubectl apply -f kubernetes/base/m_operator_service/
        kubectl apply -f kubernetes/base/policy_engine/
        kubectl apply -f kubernetes/base/resource_manager_service/
        # Apply Discovery Service manifests if implemented
        ```
    *   Apply observability manifests:
        ```bash
        kubectl apply -f kubernetes/observability/ # Apply Jaeger, Prometheus, ELK etc.
        ```

## Project Structure

*(Provide a brief overview of the main directories, e.g., service directories, kubernetes, docs, tests)*

```
KFMEvolution/
├── .github/             # GitHub Actions workflows
├── .venv/               # Python virtual environment (if used)
├── api_gateway_service/ # API Gateway microservice
├── agent_registry_service/ # Agent Registry microservice
├── f_operator_service/  # F Operator microservice
├── k_operator_service/  # K Operator microservice
├── m_operator_service/  # M Operator microservice
├── policy_engine/       # Policy Engine microservice
├── resource_manager_service/ # Resource Manager microservice
├── kfm-admin-ui/        # React Admin UI frontend
├── kubernetes/          # Kubernetes manifests (base, observability)
│   ├── base/            # Base manifests for each service
│   └── observability/   # Manifests for monitoring stack
├── database/            # Database schemas, migrations (potentially moved into services)
├── docs/                # Project documentation (architecture, runbooks)
├── policies/            # Default KFM policies (loaded by Policy Engine)
├── scripts/             # Utility scripts
├── tasks/               # Task definitions (if using Taskmaster)
├── tests/               # Integration, load tests
│   └── load/
├── .env                 # Local environment variables (ignored by git)
├── .env.example         # Example environment variables
├── .gitignore           
├── Dockerfile           # (If a root Dockerfile exists)
├── README.md            # This file
├── requirements.txt     # Root Python dependencies (mainly for testing/dev tools)
└── ...                  # Other config files (pytest.ini, etc.)
```

## Contributing

*(Add contribution guidelines if applicable)*

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.