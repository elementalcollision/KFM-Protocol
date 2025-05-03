# KFM Policy Engine Internals

This document describes the internal implementation of the KFM Policy Engine, located in the `policy_engine/` directory.

## Overview

The Policy Engine is responsible for loading, evaluating, and executing actions based on defined policies against agent contexts. It provides mechanisms for:

-   Parsing and validating policy definitions (see [Policy Format](policy_format.md)).
-   Evaluating policy conditions against agent data.
-   Executing configured actions (e.g., logging, calling KFM operators, webhooks).
-   Maintaining an audit trail of evaluations and actions.
-   Dynamically reloading policy configurations.

## Core Components

-   **`models.py`**: Contains Pydantic models defining the structure of policies, conditions, actions, and audit logs (`Policy`, `TimeInStateCondition`, `TriggerKFMAction`, `PolicyAuditLogEntry`, etc.).
-   **`parser.py`**: Handles loading and validating policy YAML files against the Pydantic models (`load_policy_file`).
-   **`engine.py`**: Implements the `PolicyEngine` class, containing the core evaluation and action execution logic.
-   **`logging_config.py`**: Configures the dedicated audit logger (`policy_audit`) to output structured JSON logs.

## Policy Engine (`engine.py`)

The `PolicyEngine` class is the main entry point for using the engine.

### Initialization

```python
from policy_engine.engine import PolicyEngine

# Initialize empty
engine = PolicyEngine()

# Initialize with policies loaded from a file
engine = PolicyEngine(policy_file_path="policies/active_policies.yaml")

# Initialize with a pre-loaded list of Policy objects
# policies = [...]
# engine = PolicyEngine(policies=policies)
```

### Policy Loading and Reloading

-   **`load_policies(policy_file_path)`**: Loads policies from the specified file, replacing any existing policies in the engine instance. Raises errors on failure.
-   **`reload_policies(policy_file_path)`**: Attempts to load policies from the specified file. On success, it atomically replaces the current policies. On failure (parsing, validation error), it logs the error and keeps the existing policies, returning `False`.

*Note: Triggering reloads dynamically (e.g., via file watching or API calls) is handled by the service layer integrating the engine.* 

### Evaluation

-   **`run_evaluation(agents_context)`**: Takes a list of agent context dictionaries. It iterates through all *enabled* policies and agents:
    1.  Checks if the agent matches the policy's `target` criteria (`_matches_target`).
    2.  If the target matches, evaluates the policy's `conditions` (`_evaluate_policy_conditions`).
    3.  Handles complex conditions including nested `AND`/`OR`/`NOT` logic.
    4.  Calls specific helper methods for condition types (`_evaluate_time_in_state`, `_evaluate_metric_threshold`, etc.).
    5.  Creates an initial `PolicyAuditLogEntry` for each evaluation.
    6.  Returns a list of tuples `(Policy, AgentContext, PolicyAuditLogEntry)` for all successful matches.

### Action Execution

-   **`execute_actions(matched_policies)`**: Takes the list of matched tuples from `run_evaluation`.
    1.  Iterates through each match.
    2.  For each action defined in the matched policy, it calls the corresponding handler method (e.g., `_handle_trigger_kfm_operation`, `_handle_log_action`).
    3.  Action handlers perform the specific task (e.g., make an HTTP call to a KFM operator, log a message).
    4.  Updates the corresponding `PolicyAuditLogEntry` with action details and outcomes.
    5.  Logs the completed `PolicyAuditLogEntry` using the `policy_audit` logger.

### Action Handlers

Specific private methods handle each `ActionType`:

-   `_handle_log_action`: Logs a message using standard Python logging.
-   `_handle_trigger_kfm_operation`: Constructs a payload and makes an async HTTP call (using `httpx`) to the configured KFM operator URL.
-   `_handle_notify`, `_handle_webhook`: Currently placeholders, intended for integration with notification systems or calling external webhooks.

## Audit Trail (`logging_config.py`)

-   A dedicated logger named `policy_audit` is used.
-   `configure_policy_audit_logging` sets up this logger.
-   `JsonFormatter` ensures log records, including the `PolicyAuditLogEntry` data passed via `extra={"audit_data": ...}`, are output as structured JSON lines to a configured file (default: `logs/policy_audit.log`).
-   This allows external log aggregation tools (like Elasticsearch, Splunk, Datadog) to easily ingest and query policy evaluation history (integration covered in Task 10). 