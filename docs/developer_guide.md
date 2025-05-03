# KFM-AE Developer Guide

This guide provides information for developers who want to interact with the KFM-AE system to register, manage, and utilize autonomous entities (agents).

## Table of Contents

*   [Overview](#overview)
*   [Prerequisites](#prerequisites)
*   [Authentication](#authentication)
*   [API Gateway Interaction](#api-gateway-interaction)
*   [Core Concepts](#core-concepts)
    *   [Agents](#agents)
    *   [Lifecycle States](#lifecycle-states)
    *   [Metadata](#metadata)
    *   [Dependencies](#dependencies)
*   [Common Workflows](#common-workflows)
    *   [Registering a New Agent](#registering-a-new-agent)
    *   [Querying/Discovering Agents](#queryingdiscovering-agents)
    *   [Updating Agent Metadata](#updating-agent-metadata)
    *   [Triggering Adaptation (F-Op)](#triggering-adaptation-f-op)
    *   [Requesting Promotion (M-Op)](#requesting-promotion-m-op)
    *   [Deprecating/Archiving/Deleting (K-Op)](#deprecatingarchivingdeleting-k-op)
    *   [Tracking Asynchronous Tasks](#tracking-asynchronous-tasks)
*   [API Reference](#api-reference)
*   [Troubleshooting](#troubleshooting)

## Overview

Developers interact with KFM-AE primarily through its RESTful API, exposed via the **API Gateway**. This allows you to programmatically manage your agents throughout their lifecycle.

Refer to the [System Architecture Documentation](./architecture.md) for a detailed component breakdown.

## Prerequisites

*   Understanding of REST APIs.
*   An HTTP client tool (e.g., `curl`, Postman) or library (e.g., `requests` in Python, `axios` in Node.js).
*   A valid API Key obtained from the KFM administrators.
*   The base URL of the KFM API Gateway.

## Authentication

All requests to the KFM API Gateway require authentication using an API key.

*   Include your API key in the `X-API-Key` header of every request.
    ```
    X-API-Key: YOUR_API_KEY_HERE
    ```
*   Failure to provide a valid key will result in a `401 Unauthorized` or `403 Forbidden` error.

## API Gateway Interaction

*   **Base URL:** All API calls should be directed to the API Gateway URL (e.g., `http://<gateway-host>:<port>/api/v1`).
*   **Routing:** The gateway uses path-based routing. The first segment after the prefix identifies the target service (e.g., `agent-registry`, `f-operator`).
    *   Example: `POST /api/v1/agent-registry/agents` routes to the agent registration endpoint on the Agent Registry service.
*   **Standard Message Structure:** Expect requests and responses to follow a standard JSON structure, often including fields like `requestId`, `timestamp`, `payload`, `error`, etc. (Refer to specific endpoint documentation).
*   **OpenAPI Spec:** The API Gateway exposes an OpenAPI specification (usually at `/openapi.json` or via `/docs`, `/redoc`) detailing available routes (dynamically discovered), request/response schemas, and authentication requirements.

## Core Concepts

*   **Agents:** The core entities managed by KFM-AE. Can represent AI models, software artifacts, data structures, etc. Each has a unique ID, type, version, state, owner, metadata, and potentially dependencies.
*   **Lifecycle States:** Agents progress through defined states: `NEW`, `EXPERIMENTAL`, `CANDIDATE`, `STABLE`, `DEPRECATED`, `ARCHIVED`, `KILLED`. Transitions are governed by KFM Operators and policies.
*   **Metadata:** Flexible key-value pairs associated with an agent for storing custom information.
*   **Dependencies:** Relationships between agents (e.g., agent A `DEPENDS_ON` agent B) managed potentially in a graph database.

## Common Workflows

*(Note: Replace placeholders like `{agent-id}`, `{service-name}`, `<gateway-url>` with actual values)*

### Registering a New Agent

*   **Endpoint:** `POST /api/v1/agent-registry/agents`
*   **Body:** JSON payload with `name`, `type`, `version`, `owner`, `metadata`, etc.
*   **Result:** Creates the agent in the `NEW` state. Returns the new agent details, including its generated `id`.

### Querying/Discovering Agents

*   **Endpoint:** `GET /api/v1/agent-discovery/agents` (or potentially direct to registry `GET /api/v1/agent-registry/agents`)
*   **Query Params:** Filter by `state`, `type`, `capabilities`, `name`, etc. Supports pagination (`limit`, `offset` or cursor).
*   **Result:** List of agents matching the criteria.

### Updating Agent Metadata

*   **Endpoint:** `PATCH /api/v1/agent-registry/agents/{agent-id}`
*   **Body:** JSON payload with the fields to update (e.g., `{"metadata": {"new_key": "new_value"}}`).
*   **Result:** Updated agent details.

### Triggering Adaptation (F-Op)

*   **Endpoint:** `POST /api/v1/f-operator/agents/{agent-id}/adapt` (or potentially `/api/v1/async/f-operator/adapt`)
*   **Body:** JSON payload specifying adaptation type and parameters (e.g., `{"adapt_type": "code_update", "source_ref": "commit-hash"}`).
*   **Result:** Synchronous: Result of adaptation. Asynchronous: Task ID (HTTP 202).

### Requesting Promotion (M-Op)

*   **Endpoint:** `POST /api/v1/m-operator/agents/{agent-id}/promote`
*   **Body:** JSON payload specifying target state (`CANDIDATE` or `STABLE`) and required evidence/justification.
*   **Result:** Confirmation that the promotion review process has started.

### Deprecating/Archiving/Deleting (K-Op)

*   **Deprecate:** `POST /api/v1/k-operator/agents/{agent-id}/deprecate`
*   **Archive:** `POST /api/v1/k-operator/agents/{agent-id}/archive`
*   **Delete:** `DELETE /api/v1/k-operator/agents/{agent-id}`
*   **Body (for POST):** Optional JSON payload with reason, force flags, etc.
*   **Result:** Confirmation of action or HTTP 204 for deletion.

### Tracking Asynchronous Tasks

*   **Endpoint:** `GET /api/v1/tasks/{task-id}`
*   **Result:** JSON payload containing task `status` (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`), `result` (if completed), `error` (if failed).

## API Reference

For a detailed API specification, including all endpoints, request/response schemas, and examples, please refer to the interactive documentation provided by the API Gateway:

*   **Swagger UI:** `http://<gateway-url>/docs`
*   **ReDoc:** `http://<gateway-url>/redoc`

## Troubleshooting

*   **401/403 Errors:** Verify your `X-API-Key` is correct and has the necessary permissions for the operation.
*   **404 Errors:** Double-check the service name and path in your URL. Ensure the target entity (e.g., agent ID) exists.
*   **5xx Errors:** Indicate a server-side problem. Check the API Gateway health (`/health`) and consult the [Troubleshooting Runbooks](./runbooks/) or contact an administrator. 