# KFM-AE Configuration Management

This document outlines the strategy for managing configuration across the KFM-Agentic Evolution (KFM-AE) microservices.

## Strategy: Kubernetes Native

We utilize Kubernetes native resources for configuration management:

-   **`ConfigMap`**: For non-sensitive configuration parameters (e.g., service URLs, logging levels, feature flags, thresholds).
-   **`Secret`**: For sensitive data (e.g., database credentials, API keys, TLS certificates).

## Mounting Strategy

Configuration and secrets are primarily mounted into service containers as **files** within specific directories:

-   Non-sensitive config (from ConfigMaps): `/etc/config/`
-   Sensitive config (from Secrets): `/etc/secrets/`

This approach allows for dynamic updates and keeps the environment cleaner.

## Dynamic Updates

Configuration changes made to Kubernetes ConfigMaps or Secrets are automatically reflected in the mounted files within running pods (eventual consistency).

Services must implement a dynamic reload mechanism (e.g., file watching + `reload_settings()`) to utilize these updates without restarts. The implementation of the file watching trigger is deferred until containerization (Task 13).

## Configuration Versioning and History

Since configuration is managed via Kubernetes manifests (`ConfigMap` and `Secret` YAML files), versioning and history tracking are handled through **Git**. Changes to configuration manifests should be committed to the Git repository, providing a full audit trail of modifications.

## Configuration Validation

Validation occurs at two levels:

1.  **Manifest Validation (CI/CD):** Before applying changes to Kubernetes, manifests in `kubernetes/base/config/` should be validated for correct syntax and structure using tools like `kubeval` or `kubectl --dry-run=client` within a CI/CD pipeline.
2.  **Service-Level Validation:** Services validate the loaded configuration values at runtime. We use `Pydantic Settings`, which automatically performs type validation. Additional specific validation rules (e.g., ensuring `LOG_LEVEL` is one of the expected values) are implemented using Pydantic's features (like `Literal` types or custom validators) within the `Settings` model (e.g., in `agent_registry_service/core/config.py`).

## Local Development Simulation

Locally, secrets are managed via `.env` (gitignored), and non-sensitive defaults are in `config/default-config.yaml`. Services load config with priority: Env Vars > `.env` > Class Defaults.

## Configuration API (Deferred)

A dedicated API for programmatically *updating* configuration at runtime is **deferred**. Changes are managed via GitOps/manifest updates.

## Example Manifests

Examples are in `kubernetes/base/config/` (`kfm-configmap.yaml`, `kfm-secrets.yaml`). Secrets require base64 encoding before deployment.

## Service Implementation

Services use libraries like `Pydantic Settings` (via `get_settings()`) configured for local loading (Env Vars > `.env` > Defaults). Deployment requires adjusting config loading to read from mounted files (`/etc/config/`, `/etc/secrets/`).

## Feature Flag System

Feature flags are defined in `config/default-config.yaml` under the `feature_flags` section. Each flag supports global activation and targeted rollout rules:

```yaml
feature_flags:
  - name: "example_experiment_flag"
    description: "Controls the example experiment"
    is_active: false
    rules: []
  - name: "new_adaptation_algorithm"
    description: "Enable a new adaptation algorithm for testing"
    is_active: true
    rules:
      - type: "percentage"
        value: 10 # Enable for 10% of agents (requires agent_id context)
      - type: "agent_ids"
        value: ["agent-123", "agent-456"]
      - type: "environment"
        value: ["staging", "test"]
```

- **Rule Types**:
  - `percentage`: Enables the flag for a percentage of agents, determined by a hash of `agent_id`.
  - `agent_ids`: Enables the flag for specific agent IDs.
  - `environment`: Enables the flag for specific environments (e.g., `staging`, `production`).

- **Evaluation**: The API endpoint `/api/v1/feature-flags/{flag_name}/active` accepts `agent_id` and `environment` as query parameters to evaluate context-aware activation.

## Experimentation Framework

Experiments are managed via the F Operator service and are linked to feature flags. Experiments are stored in the database and can be created, updated, and deleted via API endpoints. See the F Operator README and API docs for details.

## Integration Service URLs

The F Operator service integrates with the Agent Registry and Policy Engine via configurable URLs and tokens:

- `AGENT_REGISTRY_URL`: Base URL for the Agent Registry Service (default: `http://localhost:8000`)
- `AGENT_REGISTRY_TOKEN`: Optional bearer token for authenticating with the Agent Registry
- `POLICY_ENGINE_URL`: Base URL for the Policy Engine (default: `http://localhost:9000`)
- `POLICY_ENGINE_TOKEN`: Optional bearer token for authenticating with the Policy Engine

Set these in your `.env` or environment variables to enable inter-service communication. 