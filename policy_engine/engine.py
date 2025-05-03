import logging
from typing import List, Dict, Any, Tuple, Union, Optional
from datetime import datetime, timedelta, timezone
import re # For regex matching
import httpx # Added for API calls
import copy # For deep copying policies during reload

# Assuming models and parser are accessible
from .models import (
    Policy, PolicyTarget, MetadataTarget, BaseCondition, LogicalOperator, ConditionType,
    OperatorType, TimeInStateCondition, MetricThresholdCondition, DependencyCheckCondition,
    MetadataMatchCondition, AnyCondition, AgentState, ActionType, TriggerKFMAction,
    NotifyAction, LogAction, WebhookAction, KFMOperationType, PolicyAuditLogEntry
)
from .parser import load_policy_file
# TODO: Replace with actual config import
# from core.config import settings

# --- Placeholder for KFM Operator URLs --- #
# These should come from configuration (e.g., settings object or env vars)
KFM_OPERATOR_URLS = {
    KFMOperationType.DEPRECATE: "http://localhost:8001/api/v1/k-operator/deprecate", # Example URL
    KFMOperationType.ARCHIVE: "http://localhost:8001/api/v1/k-operator/archive",   # Example URL
    KFMOperationType.KILL: "http://localhost:8001/api/v1/k-operator/kill",       # Example URL
    KFMOperationType.ADAPT: "http://localhost:8002/api/v1/f-operator/adapt",       # Example URL
    KFMOperationType.PROMOTE: "http://localhost:8003/api/v1/m-operator/promote",   # Example URL
}

# Placeholder for Agent type - replace with actual import when available
# from agent_registry_service.models import Agent # Example
AgentContext = Dict[str, Any] # Using Dict as a placeholder for now

logger = logging.getLogger(__name__)

# --- Duration Parser Helper --- #
def _parse_duration(duration_str: str) -> timedelta:
    """Parses a duration string (e.g., '30 days', '12 hours') into a timedelta object."""
    duration_str = duration_str.strip()
    match = re.match(r"^(\d+)\s*(second|minute|hour|day|week)s?$", duration_str, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid duration format: '{duration_str}'. Expected format like '30 days', '12 hours'.")

    value = int(match.group(1))
    unit = match.group(2).lower()

    if unit == "second":
        return timedelta(seconds=value)
    elif unit == "minute":
        return timedelta(minutes=value)
    elif unit == "hour":
        return timedelta(hours=value)
    elif unit == "day":
        return timedelta(days=value)
    elif unit == "week":
        return timedelta(weeks=value)
    else:
        # This case should not be reached due to regex matching
         raise ValueError(f"Unknown duration unit: '{unit}'") # Should not happen

# --- Comparison Helper (Updated for Timedelta) --- #
def _compare(agent_value: Any, operator: OperatorType, policy_value: Any) -> bool:
    """Performs comparison based on the operator type, including timedelta comparisons."""
    try:
        # Check for timedelta comparison first
        if isinstance(agent_value, timedelta) and isinstance(policy_value, timedelta):
            if operator == OperatorType.EQUAL: return agent_value == policy_value
            if operator == OperatorType.NOT_EQUAL: return agent_value != policy_value
            if operator == OperatorType.GREATER_THAN: return agent_value > policy_value
            if operator == OperatorType.GREATER_THAN_EQUAL: return agent_value >= policy_value
            if operator == OperatorType.LESS_THAN: return agent_value < policy_value
            if operator == OperatorType.LESS_THAN_EQUAL: return agent_value <= policy_value
            else:
                 logger.warning(f"Unsupported operator '{operator.value}' for timedelta comparison. Returning False.")
                 return False

        # Type coercion attempts for numerical comparisons
        num_agent_val = None
        num_policy_val = None
        if isinstance(agent_value, (int, float)) and isinstance(policy_value, (int, float)):
            num_agent_val = agent_value
            num_policy_val = policy_value
        elif isinstance(agent_value, str) and isinstance(policy_value, (int, float)):
             try: 
                 num_agent_val = float(agent_value) 
             except ValueError:
                 pass # Keep num_agent_val as None if conversion fails
             num_policy_val = policy_value
        elif isinstance(agent_value, (int, float)) and isinstance(policy_value, str):
             num_agent_val = agent_value # Corrected: was assigning agent_value to itself
             try: 
                 num_policy_val = float(policy_value)
             except ValueError:
                 pass # Keep num_policy_val as None if conversion fails

        if operator == OperatorType.EQUAL:
            # Use numerical comparison if possible, otherwise string/generic comparison
            return num_agent_val == num_policy_val if num_agent_val is not None and num_policy_val is not None else agent_value == policy_value
        elif operator == OperatorType.NOT_EQUAL:
             return num_agent_val != num_policy_val if num_agent_val is not None and num_policy_val is not None else agent_value != policy_value
        elif operator in [OperatorType.GREATER_THAN, OperatorType.GREATER_THAN_EQUAL, OperatorType.LESS_THAN, OperatorType.LESS_THAN_EQUAL]:
            if num_agent_val is None or num_policy_val is None:
                 logger.warning(f"Cannot perform numerical comparison: {agent_value} {operator.value} {policy_value}. Returning False.")
                 return False # Cannot compare non-numerics with these operators
            if operator == OperatorType.GREATER_THAN: return num_agent_val > num_policy_val
            if operator == OperatorType.GREATER_THAN_EQUAL: return num_agent_val >= num_policy_val
            if operator == OperatorType.LESS_THAN: return num_agent_val < num_policy_val
            if operator == OperatorType.LESS_THAN_EQUAL: return num_agent_val <= num_policy_val
        elif operator == OperatorType.CONTAINS:
            return isinstance(agent_value, (str, list, tuple, dict)) and policy_value in agent_value
        elif operator == OperatorType.NOT_CONTAINS:
             return not (isinstance(agent_value, (str, list, tuple, dict)) and policy_value in agent_value)
        elif operator == OperatorType.REGEX_MATCH:
            return isinstance(agent_value, str) and isinstance(policy_value, str) and bool(re.match(policy_value, agent_value))
        else:
            logger.error(f"Unsupported operator: {operator}")
            return False
    except Exception as e:
         logger.error(f"Error during comparison ({agent_value} {operator.value} {policy_value}): {e}", exc_info=True)
         return False

class PolicyEngine:
    """
    Evaluates policies against agent context.
    """
    def __init__(self, policy_file_path: str = None, policies: List[Policy] = None):
        """
        Initializes the PolicyEngine. Policies can be provided directly or loaded later.

        Args:
            policy_file_path: Optional path to the YAML file containing policies to load initially.
            policies: Optional pre-loaded list of Policy objects. Takes precedence over `policy_file_path`.
        """
        self._audit_logger = logging.getLogger("policy_audit")
        self.policies: List[Policy] = []
        # TODO: Add a lock for thread-safe policy updates if engine is used concurrently
        # from threading import RLock
        # self._policy_lock = RLock()

        if policies:
            self.policies = policies
            logger.info(f"Initialized PolicyEngine with {len(self.policies)} provided policies.")
        elif policy_file_path:
            try:
                self.load_policies(policy_file_path)
            except Exception as e:
                logger.error(f"Failed to load initial policies from {policy_file_path} during init: {e}", exc_info=True)
                # raise # Option 1: Fail initialization
                # Option 2: Continue with no policies, log error handled in load_policies
        else:
             logger.warning("PolicyEngine initialized without any policies loaded.")

    def load_policies(self, policy_file_path: str):
        """
        Loads policies from the specified YAML file path and updates the engine's policies.

        Args:
            policy_file_path: The path to the policy YAML file.

        Raises:
            FileNotFoundError, YAMLError, ValidationError: If loading or validation fails.
        """
        logger.info(f"Attempting to load policies from: {policy_file_path}")
        try:
            loaded_policies = load_policy_file(policy_file_path)
            # with self._policy_lock: # Uncomment if using lock
            self.policies = loaded_policies
            logger.info(f"Successfully loaded {len(self.policies)} policies from {policy_file_path}.")
        except FileNotFoundError as e:
            logger.error(f"Policy file not found: {policy_file_path}")
            raise e
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML policy file {policy_file_path}: {e}")
            raise e
        except ValidationError as e:
            logger.error(f"Policy validation failed for {policy_file_path}: {e}")
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred loading policies from {policy_file_path}: {e}", exc_info=True)
            raise e

    def reload_policies(self, policy_file_path: str) -> bool:
        """
        Attempts to reload policies from the specified file path.
        If loading and validation succeed, atomically updates the engine's policies.
        If loading fails, the existing policies remain unchanged.

        Args:
            policy_file_path: The path to the policy YAML file.

        Returns:
            True if policies were successfully reloaded, False otherwise.
        """
        logger.info(f"Attempting to reload policies from: {policy_file_path}")
        try:
            # Attempt to load the new policies (includes validation)
            new_policies = load_policy_file(policy_file_path)

            # Store old policies for potential logging/comparison if needed
            # old_policy_count = len(self.policies)

            # Atomically update policies (use lock if engine is concurrent)
            # with self._policy_lock:
            self.policies = new_policies

            logger.info(f"Successfully reloaded {len(self.policies)} policies from {policy_file_path}.")
            # Potentially trigger notification hooks about policy reload
            return True
        except (FileNotFoundError, yaml.YAMLError, ValidationError) as e:
            # Log specific loading/validation errors but don't raise
            logger.error(f"Failed to reload policies from {policy_file_path}. Keeping existing policies. Error: {e}")
            return False
        except Exception as e:
            # Log unexpected errors
            logger.error(f"An unexpected error occurred during policy reload from {policy_file_path}. Keeping existing policies. Error: {e}", exc_info=True)
            return False

    def run_evaluation(self, agents_context: List[Dict]) -> List[Tuple[Policy, Dict]]:
        """
        Runs all enabled policies against a list of agent contexts.

        Args:
            agents_context: A list of dictionaries, each representing an agent's current state and metadata.

        Returns:
            A list of tuples, where each tuple contains the matched Policy object
            and the corresponding agent_context dict for which the policy conditions were met.
        """
        matched_policy_agents: List[Tuple[Policy, Dict]] = []
        active_policies = [p for p in self.policies if p.enabled]

        if not active_policies:
            logger.info("No active policies found to evaluate.")
            return []

        logger.info(f"Evaluating {len(agents_context)} agents against {len(active_policies)} active policies.")

        for policy in active_policies:
            logger.debug(f"Evaluating Policy ID: {policy.id} ({policy.name})")
            for agent_ctx in agents_context:
                agent_id = agent_ctx.get('id', 'unknown_id') # Assuming agent context has an 'id'
                logger.debug(f"  Checking target for Agent ID: {agent_id}")
                if self._matches_target(policy, agent_ctx):
                    logger.debug(f"    Agent ID {agent_id} matches target. Evaluating conditions...")
                    if self._evaluate_policy_conditions(policy, agent_ctx):
                        logger.info(f"    Conditions MET for Policy ID {policy.id} on Agent ID {agent_id}.")
                        matched_policy_agents.append((policy, agent_ctx))
                    else:
                        logger.debug(f"    Conditions NOT MET for Policy ID {policy.id} on Agent ID {agent_id}.")
                else:
                     logger.debug(f"    Agent ID {agent_id} does not match target.")

        logger.info(f"Policy evaluation complete. Found {len(matched_policy_agents)} policy-agent matches triggering actions.")
        return matched_policy_agents

    async def execute_actions(self, matched_policies: List[Tuple[Policy, Dict, PolicyAuditLogEntry]]):
        """
        Executes the actions for policies that matched their conditions for specific agents.

        Args:
            matched_policies: List of (Policy, AgentContext, PolicyAuditLogEntry) tuples from run_evaluation.
        """
        logger.info(f"Executing actions for {len(matched_policies)} matched policy-agent pairs.")
        # Initialize action handlers mapping
        self._action_handlers = {
            ActionType.TRIGGER_KFM_OPERATION: self._handle_trigger_kfm_operation,
            ActionType.NOTIFY: self._handle_notify,
            ActionType.LOG: self._handle_log_action,
            ActionType.WEBHOOK: self._handle_webhook,
        }

        async with httpx.AsyncClient() as client: # Create client once for reuse
            for policy, agent_context, audit_entry in matched_policies:
                agent_id = agent_context.get('id', 'unknown_id')
                logger.info(f"Executing actions for Policy ID {policy.id} on Agent ID {agent_id}")
                action_outcomes = [] # Store outcomes for this policy
                for action in policy.actions:
                    handler = self._action_handlers.get(action.type)
                    if handler:
                        try:
                            logger.debug(f"  Executing action type: {action.type}")
                            outcome = await handler(action, policy, agent_context, client)
                            action_outcomes.append(outcome)
                        except Exception as e:
                            logger.error(
                                f"  Error executing action type {action.type} for policy {policy.id} "
                                f"on agent {agent_id}: {e}", exc_info=True
                            )
                    else:
                        logger.warning(f"  No handler found for action type: {action.type}")

                # --- Update Audit Log ---
                audit_entry.actions_triggered = [a.model_dump(mode='json') for a in policy.actions] # Log attempted actions
                audit_entry.action_outcomes = action_outcomes
                audit_entry.timestamp = datetime.now(timezone.utc) # Update timestamp to reflect action completion
                self._log_audit_entry(audit_entry)

    # --- Action Handlers --- #

    async def _handle_trigger_kfm_operation(
        self,
        action: TriggerKFMAction,
        policy: Policy,
        agent_context: AgentContext,
        client: httpx.AsyncClient
    ):
        """Handles the triggering of a KFM operator API call."""
        agent_id = agent_context.get('id')
        if not agent_id:
            logger.error(f"Cannot trigger KFM operation for policy {policy.id}: Agent context missing 'id'.")
            return

        target_url = KFM_OPERATOR_URLS.get(action.operation)
        if not target_url:
            logger.error(f"Cannot trigger KFM operation '{action.operation.value}' for policy {policy.id}: No target URL configured.")
            return

        # TODO: Implement payload construction (using action.parameters and agent_context)
        # TODO: Implement Jinja2 templating for parameters if needed
        payload = {
            "agent_id": agent_id,
            "triggered_by_policy_id": policy.id,
            "parameters": action.parameters # Pass through parameters for now
        }
        # Add justification if present in parameters
        if 'justification' in action.parameters:
            payload['justification'] = action.parameters['justification']

        logger.info(f"  Triggering KFM Operation: {action.operation.value} for Agent {agent_id} at {target_url}")
        logger.debug(f"    Payload: {payload}")

        try:
            # Assuming operators expect POST for these actions
            # TODO: Determine correct HTTP method based on operator/operation
            response = await client.post(target_url, json=payload, timeout=30.0) # Added timeout
            response.raise_for_status() # Raise exception for 4xx/5xx errors
            logger.info(f"    KFM Operation {action.operation.value} for Agent {agent_id} triggered successfully. Status: {response.status_code}")
            # Potentially process response data if needed
        except httpx.RequestError as e:
            logger.error(f"    Error calling KFM operator for {action.operation.value} on Agent {agent_id}: Request failed {e}")
        except httpx.HTTPStatusError as e:
            logger.error(
                f"    Error calling KFM operator for {action.operation.value} on Agent {agent_id}: "
                f"Status code {e.response.status_code}, Response: {e.response.text}"
            )
        except Exception as e:
             logger.error(f"    Unexpected error during KFM operator call for {action.operation.value} on Agent {agent_id}: {e}", exc_info=True)

    async def _handle_notify(
        self,
        action: NotifyAction,
        policy: Policy,
        agent_context: AgentContext,
        client: httpx.AsyncClient # Keep client arg for consistency, though not used here yet
    ):
        """(Placeholder) Handles sending notifications."""
        # TODO: Implement actual notification logic (e.g., Slack, Email)
        # TODO: Implement Jinja2 templating for action.message_template
        rendered_message = action.message_template # Placeholder rendering
        logger.info(f"  [Placeholder] Notify Action: Channel='{action.channel}', Recipient='{action.recipient}', Message='{rendered_message}'")

    async def _handle_log_action(
        self,
        action: LogAction,
        policy: Policy,
        agent_context: AgentContext,
        client: httpx.AsyncClient
    ):
        """Handles logging a specific message."""
        # TODO: Implement Jinja2 templating for action.message
        rendered_message = action.message # Placeholder rendering
        log_level = getattr(logging, action.level.upper(), logging.INFO)
        # Add extra context for structured logging
        log_extras = {
            'policy_id': policy.id,
            'agent_id': agent_context.get('id')
        }
        logger.log(log_level, f"Policy Action Log: {rendered_message}", extra=log_extras)

    async def _handle_webhook(
        self,
        action: WebhookAction,
        policy: Policy,
        agent_context: AgentContext,
        client: httpx.AsyncClient
    ):
        """(Placeholder/Basic) Handles calling an external webhook."""
        # TODO: Implement Jinja2 templating for action.payload_template
        payload = action.payload_template # Placeholder rendering
        logger.info(f"  [Placeholder] Webhook Action: Method='{action.method}', URL='{action.url}', Payload='{payload}'")
        # Example basic implementation (can be enhanced)
        # try:
        #     response = await client.request(
        #         method=action.method,
        #         url=action.url,
        #         headers=action.headers,
        #         json=payload, # Assumes JSON payload
        #         timeout=15.0
        #     )
        #     response.raise_for_status()
        #     logger.info(f"    Webhook call to {action.url} successful. Status: {response.status_code}")
        # except Exception as e:
        #     logger.error(f"    Error calling webhook {action.url}: {e}")

    def _matches_target(self, policy: Policy, agent_context: AgentContext) -> bool:
        """
        Checks if an agent context matches the policy's target criteria.
        """
        target = policy.target
        if not target: # Empty target matches all
            return True

        # Check Type
        if target.type and agent_context.get('type') != target.type:
            logger.debug(f"    Target mismatch (type): Agent type '{agent_context.get('type')}' != Target type '{target.type}'")
            return False

        # Check State
        if target.state:
            try:
                # Ensure comparison is against the enum value if possible
                target_state_val = AgentState(target.state).value
                agent_state_val = agent_context.get('state')
                if agent_state_val != target_state_val:
                    logger.debug(f"    Target mismatch (state): Agent state '{agent_state_val}' != Target state '{target_state_val}'")
                    return False
            except ValueError:
                logger.warning(f"Invalid target state '{target.state}' in policy {policy.id}. Skipping state check.")
            except KeyError:
                 logger.warning(f"Agent context missing 'state' for policy {policy.id} target check. Skipping state check.")

        # Check Metadata
        if target.metadata_match:
            agent_metadata = agent_context.get('metadata', {})
            if not isinstance(agent_metadata, dict):
                 logger.warning(f"Agent context 'metadata' is not a dict for policy {policy.id} target check. Skipping metadata check.")
                 return False # Cannot match if metadata is not a dict

            matches_to_check = target.metadata_match
            if not isinstance(matches_to_check, list):
                 matches_to_check = [matches_to_check] # Ensure it's a list

            for meta_target in matches_to_check:
                if not isinstance(meta_target, MetadataTarget):
                    logger.error(f"Invalid metadata_match item in policy {policy.id}: {meta_target}")
                    return False # Invalid policy structure

                agent_value = agent_metadata.get(meta_target.key)
                if agent_value is None and meta_target.operator != OperatorType.NOT_EQUAL: # Key doesn't exist
                    # Only NOT_EQUAL can be true if key is missing (e.g., key != some_value is true if key doesn't exist)
                    # However, for simplicity, we require the key to exist for most checks.
                    # A specific 'key_exists' operator could be added if needed.
                    logger.debug(f"    Target mismatch (metadata): Key '{meta_target.key}' not found in agent metadata.")
                    return False

                if not _compare(agent_value, meta_target.operator, meta_target.value):
                    logger.debug(f"    Target mismatch (metadata): Comparison failed for key '{meta_target.key}': '{agent_value}' {meta_target.operator.value} '{meta_target.value}'")
                    return False

        # If all checks passed
        return True

    def _evaluate_policy_conditions(self, policy: Policy, agent_context: AgentContext) -> bool:
        """
        Evaluates the combined conditions of a policy for a given agent context.
        Handles the top-level list (implicit AND) or single AND/OR/NOT dict.
        """
        if not policy.conditions:
             return True # No conditions means policy applies if target matches

        # The validator in Policy model ensures conditions is a list
        # where each item is either a condition object or a single logical operator dict.
        if len(policy.conditions) == 1 and isinstance(policy.conditions[0], dict):
            # Handle single top-level AND/OR/NOT
            operator_str = list(policy.conditions[0].keys())[0]
            operator = LogicalOperator(operator_str) # Validate enum
            nested_conditions = policy.conditions[0][operator_str]
            return self._evaluate_logical_group(operator, nested_conditions, agent_context)
        else:
            # Handle list of conditions (implicit AND)
            return self._evaluate_logical_group(LogicalOperator.AND, policy.conditions, agent_context)

    def _evaluate_logical_group(self, operator: LogicalOperator, conditions: List[AnyCondition], agent_context: Dict) -> bool:
        """
        Recursively evaluates a list of conditions based on the logical operator (AND, OR, NOT).
        """
        if operator == LogicalOperator.NOT:
            if len(conditions) != 1:
                logger.error(f"NOT operator requires exactly one condition, got {len(conditions)}.")
                return False # Or raise error
            # Recursively evaluate the single condition inside NOT
            return not self._evaluate_condition(conditions[0], agent_context)

        if not conditions:
             return True # Empty AND/OR group is considered true

        results = [self._evaluate_condition(cond, agent_context) for cond in conditions]

        if operator == LogicalOperator.AND:
            return all(results)
        elif operator == LogicalOperator.OR:
            return any(results)
        else:
             logger.error(f"Unsupported logical operator: {operator}")
             return False # Or raise error

    def _evaluate_condition(self, condition: AnyCondition, agent_context: Dict) -> bool:
        """
        Dispatches evaluation to the appropriate helper method based on condition type.
        Handles nested logical operators.
        """
        if isinstance(condition, dict):
            # Nested AND/OR/NOT
            if len(condition) != 1:
                 logger.error(f"Invalid nested logical condition structure: {condition}")
                 return False
            operator_str = list(condition.keys())[0]
            operator = LogicalOperator(operator_str)
            nested_conditions = condition[operator_str]
            return self._evaluate_logical_group(operator, nested_conditions, agent_context)

        # Dispatch to specific condition type evaluators
        # TODO: Implement these specific evaluator methods
        if condition.type == ConditionType.TIME_IN_STATE:
            return self._evaluate_time_in_state(condition, agent_context)
        elif condition.type == ConditionType.METRIC_THRESHOLD:
            return self._evaluate_metric_threshold(condition, agent_context)
        elif condition.type == ConditionType.DEPENDENCY_CHECK:
            return self._evaluate_dependency_check(condition, agent_context)
        elif condition.type == ConditionType.METADATA_MATCH:
            return self._evaluate_metadata_match(condition, agent_context)
        else:
            logger.warning(f"Unsupported condition type: {condition.type}")
            return False # Default to false for unknown types

    # --- Placeholder Evaluator Methods --- #
    # These need to be implemented with actual logic based on agent_context
    # and potential external service integrations (metrics, dependencies).

    def _evaluate_time_in_state(self, condition: TimeInStateCondition, agent_context: Dict) -> bool:
        """Evaluates if the agent has been in its current state for the specified duration."""
        agent_id = agent_context.get('id', 'unknown_id')
        state_entry_time = agent_context.get('state_entry_time')

        if not isinstance(state_entry_time, datetime):
            logger.warning(f"Agent {agent_id} context missing valid 'state_entry_time' (datetime object) for time_in_state condition. Condition fails.")
            return False

        # Ensure consistent timezone handling (assume UTC if naive, or use actual tz)
        if state_entry_time.tzinfo is None:
            # Assuming naive datetimes from context are UTC. Adjust if assumption is different.
            state_entry_time = state_entry_time.replace(tzinfo=timezone.utc)
            logger.debug(f"Assuming UTC for naive state_entry_time for agent {agent_id}.")

        current_time = datetime.now(timezone.utc)
        actual_duration = current_time - state_entry_time

        try:
            policy_duration = _parse_duration(condition.value)
        except ValueError as e:
            logger.error(f"Invalid duration value '{condition.value}' in policy condition: {e}. Condition fails.")
            return False

        # Perform comparison using the updated _compare helper
        result = _compare(actual_duration, condition.operator, policy_duration)
        logger.debug(f"Time in state check for agent {agent_id}: Actual duration '{actual_duration}' {condition.operator.value} Policy duration '{policy_duration}' ('{condition.value}') -> {result}")
        return result

    def _evaluate_metric_threshold(self, condition: MetricThresholdCondition, agent_context: AgentContext) -> bool:
        """Evaluates if an agent's metric meets the specified threshold."""
        agent_id = agent_context.get('id', 'unknown_id')
        agent_metrics = agent_context.get('metrics', {})

        if not isinstance(agent_metrics, dict):
            logger.warning(f"Agent {agent_id} context 'metrics' is not a dict for metric_threshold condition. Condition fails.")
            return False

        agent_metric_value = agent_metrics.get(condition.metric_name)

        if agent_metric_value is None:
            logger.warning(f"Metric '{condition.metric_name}' not found in agent {agent_id} context metrics. Condition fails.")
            # Alternatively, could have specific operators like IS_NULL, IS_NOT_NULL if needed
            return False

        # Perform comparison using the _compare helper
        # It already handles potential type coercion for numbers vs strings
        result = _compare(agent_metric_value, condition.operator, condition.value)
        logger.debug(
            f"Metric threshold check for agent {agent_id}: "
            f"Metric '{condition.metric_name}' ('{agent_metric_value}') {condition.operator.value} Policy value '{condition.value}' -> {result}"
        )
        return result

    def _evaluate_dependency_check(self, condition: DependencyCheckCondition, agent_context: AgentContext) -> bool:
        """Evaluates conditions based on an agent's dependencies."""
        agent_id = agent_context.get('id', 'unknown_id')
        agent_dependencies_all_types = agent_context.get('dependencies', {})

        if not isinstance(agent_dependencies_all_types, dict):
            logger.warning(f"Agent {agent_id} context 'dependencies' is not a dict for dependency_check condition. Condition fails.")
            return False

        # Get dependencies for the specific relationship type
        dependencies = agent_dependencies_all_types.get(condition.relationship_type, [])

        if not isinstance(dependencies, list):
            logger.warning(
                f"Agent {agent_id} context key 'dependencies[{condition.relationship_type}]' "
                f"is not a list for dependency_check condition. Condition fails."
            )
            return False

        dep_count = len(dependencies)
        condition_type = condition.condition

        logger.debug(
            f"Dependency check for agent {agent_id}, relationship '{condition.relationship_type}': "
            f"Condition type '{condition_type.value}', Dep count: {dep_count}, Cond state: '{condition.state}', Cond count: {condition.count}"
        )

        # --- State-based checks --- #
        if condition_type in [DependencyConditionType.NONE_IN_STATE, DependencyConditionType.ALL_IN_STATE, DependencyConditionType.ANY_IN_STATE]:
            if condition.state is None:
                logger.error(f"Dependency check condition '{condition_type.value}' requires a 'state' parameter in the policy. Condition fails.")
                return False
            try:
                target_state = AgentState(condition.state).value
            except ValueError:
                logger.error(f"Invalid target state '{condition.state}' specified in dependency check condition. Condition fails.")
                return False

            # Extract states from dependency list (handle missing 'state' key gracefully)
            dep_states = [dep.get('state') for dep in dependencies if isinstance(dep, dict) and 'state' in dep]

            if condition_type == DependencyConditionType.NONE_IN_STATE:
                result = all(s != target_state for s in dep_states)
                logger.debug(f"  NONE_IN_STATE '{target_state}' check -> {result}")
                return result

            if condition_type == DependencyConditionType.ALL_IN_STATE:
                if not dependencies: return True # If no dependencies, condition 'all are X' is vacuously true
                if not dep_states or len(dep_states) != dep_count: # Check if all deps had a state key
                    logger.warning(f"Could not evaluate ALL_IN_STATE for agent {agent_id} as some dependencies lack a 'state' key.")
                    return False
                result = all(s == target_state for s in dep_states)
                logger.debug(f"  ALL_IN_STATE '{target_state}' check -> {result}")
                return result

            if condition_type == DependencyConditionType.ANY_IN_STATE:
                result = any(s == target_state for s in dep_states)
                logger.debug(f"  ANY_IN_STATE '{target_state}' check -> {result}")
                return result

        # --- Count-based checks --- #
        elif condition_type in [DependencyConditionType.COUNT_EQUALS, DependencyConditionType.COUNT_GREATER_THAN, DependencyConditionType.COUNT_LESS_THAN]:
            if condition.count is None or not isinstance(condition.count, int):
                logger.error(f"Dependency check condition '{condition_type.value}' requires an integer 'count' parameter in the policy. Condition fails.")
                return False

            target_count = condition.count

            if condition_type == DependencyConditionType.COUNT_EQUALS:
                result = (dep_count == target_count)
                logger.debug(f"  COUNT_EQUALS {target_count} check (Actual: {dep_count}) -> {result}")
                return result
            if condition_type == DependencyConditionType.COUNT_GREATER_THAN:
                result = (dep_count > target_count)
                logger.debug(f"  COUNT_GREATER_THAN {target_count} check (Actual: {dep_count}) -> {result}")
                return result
            if condition_type == DependencyConditionType.COUNT_LESS_THAN:
                result = (dep_count < target_count)
                logger.debug(f"  COUNT_LESS_THAN {target_count} check (Actual: {dep_count}) -> {result}")
                return result

        else:
            # This case should ideally not be reached if Pydantic validation is correct
            logger.error(f"Unsupported dependency condition type: {condition_type}")
            return False

    def _evaluate_metadata_match(self, condition: MetadataMatchCondition, agent_context: Dict) -> bool:
        """Evaluates if an agent's metadata matches the condition."""
        agent_metadata = agent_context.get('metadata', {})
        agent_id = agent_context.get('id', 'unknown_id')

        if not isinstance(agent_metadata, dict):
            logger.warning(f"Agent {agent_id} context 'metadata' is not a dict for metadata_match condition. Condition fails.")
            return False

        agent_value = agent_metadata.get(condition.key)

        # Handle case where key might not exist
        if agent_value is None and condition.operator != OperatorType.NOT_EQUAL:
             logger.debug(f"Metadata key '{condition.key}' not found for agent {agent_id}. Condition fails unless operator is NOT_EQUAL.")
             return False
        elif agent_value is None and condition.operator == OperatorType.NOT_EQUAL:
            # If key doesn't exist, it's considered not equal to any specific value
             logger.debug(f"Metadata key '{condition.key}' not found for agent {agent_id}. Condition passes for NOT_EQUAL.")
             return True

        # Perform comparison
        result = _compare(agent_value, condition.operator, condition.value)
        logger.debug(f"Metadata match check for agent {agent_id}: Key '{condition.key}' ('{agent_value}') {condition.operator.value} '{condition.value}' -> {result}")
        return result

    def _log_audit_entry(self, audit_entry: PolicyAuditLogEntry):
        """Logs the audit entry using the dedicated audit logger."""
        try:
            # Use 'extra' to pass the structured data to the formatter
            self._audit_logger.info(
                f"Policy evaluated: {audit_entry.policy_id} on agent {audit_entry.agent_id} -> Result: {audit_entry.evaluation_result}",
                extra={"audit_data": audit_entry.model_dump(mode='json')}
            )
        except Exception as e:
            logger.error(f"Failed to log audit entry for policy {audit_entry.policy_id}: {e}", exc_info=True) 