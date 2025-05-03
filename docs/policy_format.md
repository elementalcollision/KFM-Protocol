# KFM Policy Engine Rule Format

This document describes the YAML format used to define policies for the KFM Policy Engine. Policies automate actions (like triggering K, F, or M operations) based on conditions evaluated against agents in the registry.

The structure is defined and validated by Pydantic models in `policy_engine.models`.

## Top-Level Structure

Policy files contain a single top-level key `policies`, which is a list of individual policy definitions.

```yaml
policies:
  - id: policy-001
    # ... policy definition 1 ...
  - id: policy-002
    # ... policy definition 2 ...
```

## Policy Definition

Each policy object has the following fields:

-   `id` (string, required): A unique identifier for the policy (e.g., `deprecate-stale-v1`).
-   `name` (string, required): A human-readable name for the policy (e.g., "Deprecate Stale Agents").
-   `description` (string, optional): A more detailed explanation of what the policy does.
-   `enabled` (boolean, optional, default: `true`): Set to `false` to disable the policy without deleting it.
-   `target` (object, optional, default: applies to all agents): Defines the subset of agents this policy applies to. See [Target Definition](#target-definition) below.
-   `conditions` (list or object, required): The conditions that must be met for the actions to trigger. See [Conditions Definition](#conditions-definition) below.
-   `actions` (list, required): The actions to perform when the conditions are met. See [Actions Definition](#actions-definition) below.
-   `metadata` (object, optional): An optional dictionary for storing extra information like version, tags, author, etc.

### Target Definition

The `target` object filters which agents the policy's conditions will be evaluated against. If omitted, the policy applies to all agents.

-   `type` (string, optional): Filter by agent type (e.g., `"Software Artifact"`).
-   `state` (string, optional): Filter by agent lifecycle state (must match `AgentState` enum values like `"STABLE"`, `"EXPERIMENTAL"`).
-   `metadata_match` (object or list, optional): Filter based on agent metadata.
    -   If an object: `{ key: string, value: any, operator: string (optional, default '==') }`. Uses `OperatorType` values.
    -   If a list of objects: All metadata conditions in the list must be met (implicit AND).

Example:
```yaml
target:
  state: "STABLE"
  metadata_match:
    - key: "priority"
      value: "high"
    - key: "criticality"
      operator: ">="
      value: 3
```

### Conditions Definition

Conditions define the logic evaluated against targeted agents.

-   Can be a **list** of condition objects. If multiple conditions are in the list, they are implicitly **AND**ed together.
-   Can be a **single object** with one key: `AND`, `OR`, or `NOT`. The value is a list of condition objects to be combined with that logical operator. This allows for complex nested logic.

```yaml
# Example 1: Implicit AND
conditions:
  - type: time_in_state
    operator: ">="
    value: "90 days"
  - type: metric_threshold
    metric_name: "error_rate"
    operator: ">"
    value: 0.05

# Example 2: Explicit OR with nested AND
conditions:
  OR:
    - type: metric_threshold
      metric_name: "cpu_usage_avg_1h"
      operator: ">"
      value: 90
    - AND:
      - type: time_in_state
        operator: ">="
        value: "7 days"
      - type: metadata_match
        key: "auto_restart_failed"
        value: true
```

#### Condition Types

-   **`time_in_state`**: Checks how long the agent has been in its current state.
    -   `operator`: Comparison operator (`OperatorType`).
    -   `value`: Duration string (e.g., `"30 days"`, `"12 hours"`, `"1 week"`). Parsing logic TBD.
-   **`metric_threshold`**: Checks an agent-specific metric against a threshold. (Requires integration with a metrics source).
    -   `metric_name`: Name of the metric.
    -   `operator`: Comparison operator (`OperatorType`).
    -   `value`: Numeric or string threshold value.
-   **`dependency_check`**: Checks the state or count of agent dependencies. (Requires integration with the dependency graph).
    -   `relationship_type`: Type of relationship (e.g., `"DEPENDS_ON"`).
    -   `condition`: The check to perform (`DependencyConditionType` enum):
        -   `none_in_state`: True if *no* dependencies are in the specified `state`.
        -   `all_in_state`: True if *all* dependencies are in the specified `state`.
        -   `any_in_state`: True if *at least one* dependency is in the specified `state`.
        -   `count_equals`: True if the number of dependencies matches `count`.
        -   `count_greater_than`: True if the number of dependencies is greater than `count`.
        -   `count_less_than`: True if the number of dependencies is less than `count`.
    -   `state`: Required for state-based conditions (`AgentState` enum value).
    -   `count`: Required for count-based conditions (integer).
-   **`metadata_match`**: Checks if a metadata key/value matches specified criteria.
    -   `key`: The metadata key name.
    -   `operator`: Comparison operator (`OperatorType`, defaults to `==`).
    -   `value`: The value to compare against.

### Actions Definition

Actions define what happens when a policy's conditions evaluate to true for a targeted agent. Actions are executed in the order they appear in the list.

#### Action Types

-   **`trigger_kfm_operation`**: Calls one of the KFM Operator services.
    -   `operation`: The KFM operation (`KFMOperationType` enum: `"DEPRECATE"`, `"ARCHIVE"`, `"KILL"`, `"ADAPT"`, `"PROMOTE"`).
    -   `parameters`: A dictionary of parameters required by the specific KFM operator API endpoint (e.g., `justification`).
-   **`notify`**: Sends a notification.
    -   `channel`: Notification channel (e.g., `"slack"`, `"email"`).
    -   `recipient`: Target recipient (e.g., `"#channel"`, `"user@example.com"`).
    -   `message_template`: Message content. Can use Jinja2-like placeholders for context (e.g., `{{ agent.id }}`, `{{ policy.name }}`).
-   **`log`**: Writes a specific message to the policy engine's logs.
    -   `message`: The log message string.
    -   `level`: Log level (e.g., `"INFO"`, `"WARN"`, `"ERROR"`, default: `"INFO"`).
-   **`webhook`**: Makes an HTTP call to an external system.
    -   `url`: The target URL.
    -   `method`: HTTP method (e.g., `"POST"`, `"PUT"`, default: `"POST"`).
    -   `headers`: (Optional) Dictionary of HTTP headers.
    -   `payload_template`: (Optional) Dictionary defining the JSON payload. Can use placeholders like `message_template`.

## Example Policy

```yaml
policies:
  - id: promote-candidate-agents
    name: "Promote Ready Candidate Agents"
    description: "Automatically promotes CANDIDATE agents to STABLE if they meet metrics and have no critical dependencies."
    enabled: true
    target:
      state: "CANDIDATE"
      metadata_match:
        key: "ready_for_promotion"
        value: true
    conditions:
      - type: metric_threshold
        metric_name: "test_coverage_pct"
        operator: ">="
        value: 95
      - type: metric_threshold
        metric_name: "stability_score"
        operator: ">="
        value: 0.99
      - type: dependency_check
        relationship_type: "DEPENDS_ON"
        condition: "none_in_state"
        state: "EXPERIMENTAL" # Cannot promote if depending on experimental agents
      - type: time_in_state
        operator: ">="
        value: "7 days" # Must be candidate for at least 7 days
    actions:
      - type: trigger_kfm_operation
        operation: "PROMOTE"
        parameters:
          justification: "Policy [promote-candidate-agents]: Agent met all promotion criteria."
      - type: notify
        channel: "slack"
        recipient: "#agent-promotions"
        message_template: "Agent {{ agent.id }} ({{ agent.name }}) automatically promoted to STABLE by policy '{{ policy.name }}'."
``` 