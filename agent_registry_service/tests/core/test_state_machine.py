import pytest
from datetime import datetime
from unittest.mock import Mock # Using unittest.mock for hook testing

from agent_registry_service.core.state_machine import AgentState, StateMachine
from agent_registry_service.core.exceptions import InvalidTransitionError


def test_state_machine_initialization():
    """Test valid initialization."""
    sm = StateMachine(initial_state=AgentState.NEW)
    assert sm.current_state == AgentState.NEW

def test_state_machine_initialization_invalid():
    """Test initialization with invalid type."""
    with pytest.raises(TypeError):
        StateMachine(initial_state="NEW")


def test_valid_transition():
    """Test a single valid transition."""
    sm = StateMachine(initial_state=AgentState.NEW)
    sm.transition(AgentState.EXPERIMENTAL, justification="Begin testing")
    assert sm.current_state == AgentState.EXPERIMENTAL


def test_multiple_valid_transitions():
    """Test a sequence of valid transitions."""
    sm = StateMachine(initial_state=AgentState.NEW)
    sm.transition(AgentState.EXPERIMENTAL, justification="Begin testing")
    assert sm.current_state == AgentState.EXPERIMENTAL
    sm.transition(AgentState.CANDIDATE, justification="Promising results")
    assert sm.current_state == AgentState.CANDIDATE
    sm.transition(AgentState.STABLE, justification="Passed all tests")
    assert sm.current_state == AgentState.STABLE
    sm.transition(AgentState.DEPRECATED, justification="New version available")
    assert sm.current_state == AgentState.DEPRECATED
    sm.transition(AgentState.ARCHIVED, justification="End of life")
    assert sm.current_state == AgentState.ARCHIVED


def test_invalid_transition_rule():
    """Test a transition forbidden by the rules."""
    sm = StateMachine(initial_state=AgentState.NEW)
    with pytest.raises(InvalidTransitionError) as exc_info:
        sm.transition(AgentState.STABLE, justification="Shortcut!")
    assert sm.current_state == AgentState.NEW # State should not change
    assert "Transition from NEW to STABLE is not allowed" in str(exc_info.value)


def test_invalid_transition_terminal_state():
    """Test attempting to transition from a terminal state."""
    sm_archived = StateMachine(initial_state=AgentState.ARCHIVED)
    with pytest.raises(InvalidTransitionError):
        sm_archived.transition(AgentState.NEW, justification="Revive?")
    assert sm_archived.current_state == AgentState.ARCHIVED

    sm_killed = StateMachine(initial_state=AgentState.KILLED)
    with pytest.raises(InvalidTransitionError):
        sm_killed.transition(AgentState.EXPERIMENTAL, justification="Try again?")
    assert sm_killed.current_state == AgentState.KILLED

def test_transition_invalid_target_type():
    """Test providing a non-AgentState target."""
    sm = StateMachine(initial_state=AgentState.NEW)
    with pytest.raises(TypeError):
        sm.transition("EXPERIMENTAL", justification="Using string")
    assert sm.current_state == AgentState.NEW


def test_transition_missing_justification():
    """Test transition without providing justification."""
    sm = StateMachine(initial_state=AgentState.NEW)
    with pytest.raises(InvalidTransitionError) as exc_info:
        sm.transition(AgentState.EXPERIMENTAL, justification="")
    assert sm.current_state == AgentState.NEW
    assert "Justification is required" in str(exc_info.value)

    with pytest.raises(InvalidTransitionError) as exc_info:
        sm.transition(AgentState.EXPERIMENTAL, justification="   ") # Whitespace only
    assert sm.current_state == AgentState.NEW
    assert "Justification is required" in str(exc_info.value)

    # Test with None justification - should also fail based on implementation
    with pytest.raises(InvalidTransitionError) as exc_info:
        sm.transition(AgentState.EXPERIMENTAL, justification=None) # type: ignore
    assert sm.current_state == AgentState.NEW
    assert "Justification is required" in str(exc_info.value)

def test_is_transition_allowed_helper():
    """Test the helper method directly."""
    sm = StateMachine(initial_state=AgentState.CANDIDATE)
    assert sm.is_transition_allowed(AgentState.STABLE) is True
    assert sm.is_transition_allowed(AgentState.EXPERIMENTAL) is True
    assert sm.is_transition_allowed(AgentState.KILLED) is True
    assert sm.is_transition_allowed(AgentState.NEW) is False
    assert sm.is_transition_allowed(AgentState.DEPRECATED) is False
    assert sm.is_transition_allowed(AgentState.ARCHIVED) is False
    # Test invalid type
    assert sm.is_transition_allowed("STABLE") is False # type: ignore 

@pytest.fixture
def sm():
    """Provides a StateMachine instance for tests."""
    return StateMachine() # Starts in NEW state by default

def test_initial_state(sm: StateMachine):
    """Test that the state machine initializes in the NEW state."""
    assert sm.current_state == AgentState.NEW
    assert len(sm.state_history) == 1
    # History format: (from_state, to_state, timestamp, context)
    assert sm.state_history[0][0] is None # Initial transition has no from_state
    assert sm.state_history[0][1] == AgentState.NEW
    assert isinstance(sm.state_history[0][2], datetime)
    assert sm.state_history[0][3] is None

def test_valid_transitions(sm: StateMachine):
    """Test a sequence of valid transitions."""
    context1 = {"user": "test", "reason": "Moving to experimental"}
    sm.transition_to(AgentState.EXPERIMENTAL, context=context1)
    assert sm.current_state == AgentState.EXPERIMENTAL
    assert len(sm.state_history) == 2
    assert sm.state_history[1] == (AgentState.NEW, AgentState.EXPERIMENTAL, sm.state_history[1][2], context1)

    context2 = {"result": "passed checks"}
    sm.transition_to(AgentState.CANDIDATE, context=context2)
    assert sm.current_state == AgentState.CANDIDATE
    assert len(sm.state_history) == 3
    assert sm.state_history[2] == (AgentState.EXPERIMENTAL, AgentState.CANDIDATE, sm.state_history[2][2], context2)

    sm.transition_to(AgentState.STABLE)
    assert sm.current_state == AgentState.STABLE
    assert len(sm.state_history) == 4
    assert sm.state_history[3][3] is None # Test transition with no context

    sm.transition_to(AgentState.DEPRECATED)
    assert sm.current_state == AgentState.DEPRECATED

    sm.transition_to(AgentState.ARCHIVED)
    assert sm.current_state == AgentState.ARCHIVED

    sm.transition_to(AgentState.KILLED)
    assert sm.current_state == AgentState.KILLED

def test_invalid_transitions(sm: StateMachine):
    """Test that invalid transitions raise InvalidTransitionError."""
    # NEW -> CANDIDATE (invalid)
    with pytest.raises(InvalidTransitionError) as excinfo:
        sm.transition_to(AgentState.CANDIDATE)
    assert excinfo.value.from_state == AgentState.NEW
    assert excinfo.value.to_state == AgentState.CANDIDATE
    assert sm.current_state == AgentState.NEW # State should not change
    assert len(sm.state_history) == 1 # History should not change

    # Transition to EXPERIMENTAL (valid)
    sm.transition_to(AgentState.EXPERIMENTAL)
    assert sm.current_state == AgentState.EXPERIMENTAL

    # EXPERIMENTAL -> STABLE (invalid)
    with pytest.raises(InvalidTransitionError):
        sm.transition_to(AgentState.STABLE)
    assert sm.current_state == AgentState.EXPERIMENTAL

    # KILLED -> anything (invalid)
    sm.transition_to(AgentState.KILLED)
    assert sm.current_state == AgentState.KILLED
    with pytest.raises(InvalidTransitionError):
        sm.transition_to(AgentState.NEW)
    assert sm.current_state == AgentState.KILLED

def test_state_history_logging(sm: StateMachine):
    """Verify the state history accurately logs transitions and context."""
    context1 = {"id": 1}
    context2 = {"id": 2, "data": "extra"}
    ts_before = datetime.now()
    sm.transition_to(AgentState.EXPERIMENTAL, context=context1)
    sm.transition_to(AgentState.CANDIDATE, context=context2)
    ts_after = datetime.now()

    history = sm.state_history
    assert len(history) == 3

    # Initial state entry
    assert history[0][0] is None
    assert history[0][1] == AgentState.NEW
    assert isinstance(history[0][2], datetime)
    assert history[0][3] is None

    # First transition
    assert history[1][0] == AgentState.NEW
    assert history[1][1] == AgentState.EXPERIMENTAL
    assert ts_before <= history[1][2] <= ts_after
    assert history[1][3] == context1

    # Second transition
    assert history[2][0] == AgentState.EXPERIMENTAL
    assert history[2][1] == AgentState.CANDIDATE
    assert ts_before <= history[2][2] <= ts_after # Timestamps should be close
    assert history[2][3] == context2

def test_transition_hooks(sm: StateMachine):
    """Test that registered hooks are called correctly."""
    mock_hook1 = Mock()
    mock_hook2 = Mock()
    error_hook = Mock(side_effect=Exception("Hook failed!"))

    sm.register_transition_hook(mock_hook1)
    sm.register_transition_hook(error_hook) # Hook that raises an error
    sm.register_transition_hook(mock_hook2)

    context = {"trigger": "test"}
    # Transition NEW -> EXPERIMENTAL
    sm.transition_to(AgentState.EXPERIMENTAL, context=context)

    # Verify hooks were called with correct arguments
    mock_hook1.assert_called_once_with(AgentState.NEW, AgentState.EXPERIMENTAL, context)
    error_hook.assert_called_once_with(AgentState.NEW, AgentState.EXPERIMENTAL, context)
    mock_hook2.assert_called_once_with(AgentState.NEW, AgentState.EXPERIMENTAL, context)

    # Verify state still transitioned despite error_hook failing
    assert sm.current_state == AgentState.EXPERIMENTAL

    # Test invalid transition - hooks should not be called
    mock_hook1.reset_mock()
    with pytest.raises(InvalidTransitionError):
        sm.transition_to(AgentState.STABLE)
    mock_hook1.assert_not_called()

def test_register_non_callable_hook(sm: StateMachine):
    """Test that registering a non-callable raises TypeError."""
    with pytest.raises(TypeError):
        sm.register_transition_hook(123) 