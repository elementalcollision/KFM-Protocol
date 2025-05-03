import logging
from enum import Enum
from typing import Dict, Set, List, Tuple, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """Defines the possible lifecycle states for an agent."""
    NEW = "new"
    EXPERIMENTAL = "experimental"
    CANDIDATE = "candidate"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    KILLED = "killed"

# Define allowed transitions based on the Mermaid diagram in Subtask 3.1
# Format: {current_state: {allowed_next_state1, allowed_next_state2, ...}}
ALLOWED_TRANSITIONS: Dict[AgentState, Set[AgentState]] = {
    AgentState.NEW: {AgentState.EXPERIMENTAL},
    AgentState.EXPERIMENTAL: {AgentState.CANDIDATE, AgentState.KILLED},
    AgentState.CANDIDATE: {AgentState.STABLE, AgentState.KILLED}, # Assuming CANDIDATE can also revert to EXPERIMENTAL? Subtask 3.1 diagram implies yes, but 3.2 example doesn't. Let's follow 3.1 diagram.
    AgentState.STABLE: {AgentState.DEPRECATED},
    AgentState.DEPRECATED: {AgentState.ARCHIVED, AgentState.KILLED},
    AgentState.ARCHIVED: {AgentState.KILLED},
    AgentState.KILLED: set(), # Terminal state
}
# Note: Let's clarify the CANDIDATE -> EXPERIMENTAL transition possibility later if needed.

class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    def __init__(self, from_state: AgentState, to_state: AgentState):
        self.from_state = from_state
        self.to_state = to_state
        message = f"Invalid transition from {from_state.value} to {to_state.value}"
        super().__init__(message)

class StateMachine:
    """Manages the lifecycle state of an agent and enforces valid transitions."""

    def __init__(self, initial_state: AgentState = AgentState.NEW):
        if not isinstance(initial_state, AgentState):
            raise TypeError("Initial state must be an instance of AgentState Enum")
        self._current_state = initial_state
        # Initialize history with the starting state
        self._state_history: List[Tuple[Optional[AgentState], AgentState, datetime, Optional[Dict]]] = [
            (None, initial_state, datetime.now(), None) # (from_state, to_state, timestamp, context)
        ]
        # Initialize hooks list
        self._transition_hooks: List[Callable[[Optional[AgentState], AgentState, Optional[Dict]], None]] = []
        logger.info(f"State machine initialized in state: {self._current_state.value}")

    @property
    def current_state(self) -> AgentState:
        """Returns the current state of the machine."""
        return self._current_state

    def validate_transition(self, to_state: AgentState) -> bool:
        """Checks if transitioning to the target state is allowed from the current state."""
        if not isinstance(to_state, AgentState):
            logger.warning(f"Invalid target state type for validation: {type(to_state)}")
            return False

        allowed_next_states = ALLOWED_TRANSITIONS.get(self._current_state, set())
        is_allowed = to_state in allowed_next_states
        if not is_allowed:
            logger.debug(f"Validation failed: Transition from {self._current_state.value} to {to_state.value} is not allowed.")
        return is_allowed

    def transition_to(self, to_state: AgentState, context: Optional[Dict] = None):
        """
        Attempts to transition the state machine to the target state.
        Logs the transition to the internal history.
        Raises InvalidTransitionError if the transition is not allowed.

        Args:
            to_state: The target AgentState.
            context: Optional dictionary containing metadata about the transition 
                     (e.g., justification, triggering_entity_id).
        """
        if self.validate_transition(to_state):
            old_state = self._current_state
            self._current_state = to_state
            timestamp = datetime.now()
            # Log to history first
            self._state_history.append((old_state, self._current_state, timestamp, context))
            logger.info(f"State transitioned from {old_state.value} to {self._current_state.value}", extra=context or {})
            
            # Trigger registered hooks
            for hook in self._transition_hooks:
                try:
                    hook(old_state, self._current_state, context)
                except Exception as e:
                    # Log hook errors but don't let them stop the process
                    logger.error(f"Error executing transition hook {hook.__name__}: {e}", exc_info=True)
        else:
            logger.warning(f"Attempted invalid transition from {self._current_state.value} to {to_state.value}", extra=context or {})
            raise InvalidTransitionError(from_state=self._current_state, to_state=to_state)

    def register_transition_hook(
        self,
        hook_function: Callable[[Optional[AgentState], AgentState, Optional[Dict]], None]
    ) -> None:
        """
        Registers a callback function to be called after a successful state transition.
        The hook function will receive (from_state, to_state, context) as arguments.
        Args:
            hook_function: The callback function to register.
        """
        if not callable(hook_function):
            raise TypeError("Hook function must be callable")
        self._transition_hooks.append(hook_function)
        logger.info(f"Registered transition hook: {hook_function.__name__}")

    @property
    def state_history(self) -> List[Tuple[Optional[AgentState], AgentState, datetime, Optional[Dict]]]:
        """Returns a copy of the state transition history."""
        return self._state_history.copy()

# Example usage (optional, for testing/illustration)
# if __name__ == "__main__":
#     sm = StateMachine()
#     print(f"Initial state: {sm.current_state.value}")
#     try:
#         sm.transition_to(AgentState.EXPERIMENTAL)
#         print(f"Current state: {sm.current_state.value}")
#         sm.transition_to(AgentState.CANDIDATE)
#         print(f"Current state: {sm.current_state.value}")
#         sm.transition_to(AgentState.NEW) # Should fail
#     except InvalidTransitionError as e:
#         print(f"Transition failed: {e}")
 