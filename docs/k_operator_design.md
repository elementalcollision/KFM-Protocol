# KFM K (Kill) Operator Design

This document outlines the design for the K Operator service, responsible for handling the end-of-life processes for agents within the KFM-AE system.

## Purpose

The K Operator automates and manages the controlled removal of agents from the system. This includes marking agents for removal (deprecation), handling interim states (archival), and orchestrating final deletion, ensuring that dependencies are notified and resources are reclaimed appropriately.

## Core Functionality

-   Provides API endpoints to manually trigger deprecation, archival, or deletion (subject to permissions).
-   Automatically transitions agents through end-of-life states based on configurable grace periods.
-   Integrates with other KFM services (Registry, Notification, Resource Management, Discovery) to perform necessary side effects during transitions.
-   Maintains audit logs for all operations.

## State Model and Transitions

The K Operator manages transitions between the following states, defined in the main `AgentState` enum (`agent_registry_service.core.state_machine.AgentState`):

1.  **(Input State)** -> `DEPRECATED`:
    *   **Trigger:** Explicit API call (`POST /agents/{id}/deprecate`) or triggered by the Policy Engine.
    *   **Action:** Agent state is updated to `DEPRECATED`. Notifications are sent. Agent might still be functional but marked for removal.
    *   **Starts:** Deprecation Grace Period.

2.  `DEPRECATED` -> `ARCHIVED`:
    *   **Trigger:** Automatically triggered by the K Operator's scheduled task when `current_time > (deprecated_timestamp + deprecation_grace_period)`.
    *   **Action:** Agent state is updated to `ARCHIVED`. Agent becomes non-functional. Resources may be deallocated. Agent removed from active discovery.
    *   **Starts:** Archival Retention Period.

3.  `ARCHIVED` -> **Deletion / `KILLED`**:
    *   **Trigger:** Automatically triggered by the K Operator's scheduled task when `current_time > (archived_timestamp + archival_retention_period)`.
    *   **Action:** Agent data is permanently deleted or marked as `KILLED` (if explicit state needed before deletion). Final resource cleanup occurs. Audit logs finalized.

*Note: Transitions might also be possible back to earlier states (e.g., `DEPRECATED` -> `ACTIVE`) via specific operator actions (potentially M operator) or manual intervention, subject to rules.* 

## Grace Period Logic

-   **Configuration:** Grace periods are defined globally within the K Operator's configuration. Specific overrides per agent type might be added later.
    -   `DEFAULT_DEPRECATION_GRACE_PERIOD`: Time an agent remains `DEPRECATED` before auto-archival (e.g., "30 days").
    -   `DEFAULT_ARCHIVAL_RETENTION_PERIOD`: Time an agent remains `ARCHIVED` before auto-deletion (e.g., "90 days").
    -   *Configuration Source:* Pydantic Settings model (`k_operator_service/core/config.py`) loaded from environment variables or `.env` file.
-   **Tracking:** The timestamp for entering the `DEPRECATED` and `ARCHIVED` states is determined by querying the `StateTransitionLog` table for the most recent entry for the agent transitioning *to* that specific state.
-   **Scheduled Trigger:** A background scheduler (e.g., APScheduler, Kubernetes CronJob) within the K Operator service is required to periodically query agents in `DEPRECATED` and `ARCHIVED` states and compare their state entry timestamps against the configured grace/retention periods to trigger the automatic transitions.

## API Endpoints (Initial Design)

-   `POST /agents/{agent_id}/deprecate`: Manually trigger transition to `DEPRECATED`.
-   `POST /agents/{agent_id}/archive`: Manually trigger transition to `ARCHIVED` (may bypass grace period).
-   `DELETE /agents/{agent_id}`: Manually trigger immediate deletion (requires high permissions, may bypass grace/retention).

*(Detailed API specs to be defined in relevant subtasks)*

## Dependencies & Interactions

-   **Agent Registry Service:** To query agent state and update agent state.
-   **StateTransitionLog Table:** To query state entry timestamps.
-   **Notification Service:** To inform dependents/owners of state changes.
-   **Resource Management Service:** To trigger resource deallocation.
-   **Discovery Service:** To remove agents from being discoverable.
-   **Policy Engine:** Can trigger K Operator endpoints based on policy rules. 