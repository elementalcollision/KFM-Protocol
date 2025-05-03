from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid
from datetime import datetime, timedelta

# --- Enums ---

class AgentState(str, Enum):
    """Mirrors the AgentState Enum from the state machine for consistency."""
    NEW = "new"
    EXPERIMENTAL = "experimental"
    CANDIDATE = "candidate"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    KILLED = "killed"

class OperatorType(str, Enum):
    """Comparison operators for conditions."""
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER_THAN = ">"
    GREATER_THAN_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_EQUAL = "<="
    CONTAINS = "contains"          # For lists or strings
    NOT_CONTAINS = "not_contains"  # For lists or strings
    REGEX_MATCH = "regex_match"    # For strings

class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

class ConditionType(str, Enum):
    """Types of conditions that can be evaluated."""
    TIME_IN_STATE = "time_in_state"
    METRIC_THRESHOLD = "metric_threshold"
    DEPENDENCY_CHECK = "dependency_check"
    METADATA_MATCH = "metadata_match"
    # Note: COMPOSITE is implicitly handled by structure (AND/OR/NOT keys)

class DependencyConditionType(str, Enum):
    """Specific checks for dependency conditions."""
    NONE_IN_STATE = "none_in_state"
    ALL_IN_STATE = "all_in_state"
    ANY_IN_STATE = "any_in_state"
    COUNT_EQUALS = "count_equals"
    COUNT_GREATER_THAN = "count_greater_than"
    COUNT_LESS_THAN = "count_less_than"

class ActionType(str, Enum):
    """Types of actions that can be triggered by policies."""
    TRIGGER_KFM_OPERATION = "trigger_kfm_operation"
    NOTIFY = "notify"
    LOG = "log"                     # Log a specific message
    WEBHOOK = "webhook"             # Call an external webhook

class KFMOperationType(str, Enum):
    """Maps to K, F, M operations (or specific state transitions)."""
    DEPRECATE = "DEPRECATE"         # K
    ARCHIVE = "ARCHIVE"             # K
    KILL = "KILL"                   # K
    ADAPT = "ADAPT"                 # F (generic, params define specifics)
    PROMOTE = "PROMOTE"             # M

# --- Condition Models ---

class BaseCondition(BaseModel):
    # Base model for conditions, allowing Union typing
    pass

class TimeInStateCondition(BaseCondition):
    type: Literal[ConditionType.TIME_IN_STATE] = ConditionType.TIME_IN_STATE
    operator: OperatorType
    value: str = Field(..., description="Duration string, e.g., '30 days', '12 hours'")

class MetricThresholdCondition(BaseCondition):
    type: Literal[ConditionType.METRIC_THRESHOLD] = ConditionType.METRIC_THRESHOLD
    metric_name: str = Field(..., description="Name of the metric to evaluate")
    operator: OperatorType
    value: Union[int, float, str] = Field(..., description="Threshold value")

class DependencyCheckCondition(BaseCondition):
    type: Literal[ConditionType.DEPENDENCY_CHECK] = ConditionType.DEPENDENCY_CHECK
    relationship_type: str = Field(..., description="Type of dependency relationship, e.g., 'DEPENDS_ON'")
    condition: DependencyConditionType
    state: Optional[AgentState] = Field(None, description="State to check dependencies against (required for state-based conditions)")
    count: Optional[int] = Field(None, description="Count value for count-based conditions")

class MetadataMatchCondition(BaseCondition):
    type: Literal[ConditionType.METADATA_MATCH] = ConditionType.METADATA_MATCH
    key: str = Field(..., description="Metadata key to check")
    operator: OperatorType = Field(OperatorType.EQUAL, description="Operator to compare metadata value")
    value: Any = Field(..., description="Value to match against the metadata key")

# Recursive type hint for nested conditions
AnyCondition = Union[
    TimeInStateCondition,
    MetricThresholdCondition,
    DependencyCheckCondition,
    MetadataMatchCondition,
    Dict[LogicalOperator, List['AnyCondition']] # For AND/OR/NOT
]

# Update forward references for the recursive type hint
# Note: Pydantic v2 handles forward references more automatically,
# but explicit update_forward_refs might be needed in some complex cases or v1.
# If using Pydantic v2, this might not be strictly necessary.
# CompositeCondition.update_forward_refs() # Example if needed

# --- Action Models ---

class BaseAction(BaseModel):
    type: ActionType

class TriggerKFMAction(BaseAction):
    type: Literal[ActionType.TRIGGER_KFM_OPERATION] = ActionType.TRIGGER_KFM_OPERATION
    operation: KFMOperationType
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the KFM operator call")

class NotifyAction(BaseAction):
    type: Literal[ActionType.NOTIFY] = ActionType.NOTIFY
    channel: str = Field(..., description="Notification channel (e.g., 'slack', 'email')")
    recipient: str = Field(..., description="Target recipient (e.g., '#channel', 'user@example.com')")
    message_template: str = Field(..., description="Message template (can use placeholders like {{agent.id}})")

class LogAction(BaseAction):
    type: Literal[ActionType.LOG] = ActionType.LOG
    message: str = Field(..., description="Message to log")
    level: str = Field("INFO", description="Log level (e.g., 'INFO', 'WARN', 'ERROR')")

class WebhookAction(BaseAction):
    type: Literal[ActionType.WEBHOOK] = ActionType.WEBHOOK
    url: str = Field(..., description="URL of the webhook to call")
    method: str = Field("POST", description="HTTP method (e.g., 'POST', 'PUT')")
    headers: Optional[Dict[str, str]] = Field(None, description="Optional HTTP headers")
    payload_template: Optional[Dict[str, Any]] = Field(None, description="Template for the JSON payload")

AnyAction = Union[TriggerKFMAction, NotifyAction, LogAction, WebhookAction]

# --- Target and Policy Models ---

class MetadataTarget(BaseModel):
    key: str
    value: Any
    operator: OperatorType = OperatorType.EQUAL

class PolicyTarget(BaseModel):
    type: Optional[str] = Field(None, description="Filter agents by type")
    state: Optional[AgentState] = Field(None, description="Filter agents by lifecycle state")
    metadata_match: Optional[Union[MetadataTarget, List[MetadataTarget]]] = Field(None, description="Filter agents by metadata key/value")
    # Add other target criteria as needed (e.g., name_regex)

class Policy(BaseModel):
    id: str = Field(..., description="Unique identifier for the policy")
    name: str = Field(..., description="Human-readable name for the policy")
    description: Optional[str] = Field(None, description="Detailed description of the policy's purpose")
    enabled: bool = Field(True, description="Whether the policy is active")
    target: PolicyTarget = Field(default_factory=PolicyTarget, description="Criteria to select agents this policy applies to")
    conditions: List[AnyCondition] = Field(..., description="List of conditions (implicitly ANDed) or a single dict with AND/OR/NOT key")
    actions: List[AnyAction] = Field(..., description="List of actions to take if conditions are met")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for versioning, tags, etc.")

    @validator('conditions', pre=True)
    def ensure_conditions_list(cls, v):
        """Allow single dict for top-level AND/OR/NOT."""
        if isinstance(v, dict):
            # Ensure it's a valid logical operator dict
            if len(v) == 1 and list(v.keys())[0] in [op.value for op in LogicalOperator]:
                 return [v] # Wrap the single dict in a list
            else:
                 raise ValueError("Single condition dict must have AND, OR, or NOT as the key")
        elif isinstance(v, list):
            return v
        raise TypeError("Conditions must be a list or a single logical operator dict")

class PolicyFile(BaseModel):
    policies: List[Policy]

# --- Audit Log Model ---

class PolicyAuditLogEntry(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the audit log entry")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the evaluation/action occurred (UTC)")
    policy_id: str = Field(..., description="ID of the policy being evaluated")
    policy_name: str = Field(..., description="Name of the policy being evaluated")
    agent_id: str = Field(..., description="ID of the agent being evaluated")
    # Store the input context? Might be large. Maybe store hash or key identifiers.
    # evaluation_context: Optional[Dict[str, Any]] = Field(None, description="The agent context used for evaluation")
    evaluation_result: bool = Field(..., description="Outcome of the condition evaluation (True if conditions met)")
    conditions_details: Optional[Any] = Field(None, description="Details about individual condition results (structure TBD)")
    actions_triggered: Optional[List[Dict[str, Any]]] = Field(None, description="List of actions attempted if evaluation was True")
    action_outcomes: Optional[List[Dict[str, Any]]] = Field(None, description="List of outcomes for each attempted action (e.g., {'action_type': 'notify', 'status': 'success'}) ")
    error_message: Optional[str] = Field(None, description="Error message if evaluation or action execution failed")

    class Config:
        # Pydantic V2 config
        # frozen = True # Consider making audit logs immutable
        # Pydantic V1 config
        allow_mutation = False # Consider making audit logs immutable

# --- Update Forward References ---
# Pydantic v2 should handle this automatically in most cases.
# If using Pydantic v1 or encountering issues, uncomment lines like these:
# CompositeCondition.update_forward_refs()
# AnyCondition.update_forward_refs() # May not work directly on Union, update containing models
Policy.update_forward_refs() 