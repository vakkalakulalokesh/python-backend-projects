from __future__ import annotations

import pytest

from app.engine.state_machine import ExecutionState, ExecutionStateMachine


def test_valid_transitions() -> None:
    sm = ExecutionStateMachine("pending")
    sm.transition_to(ExecutionState.RUNNING)
    assert sm.state == ExecutionState.RUNNING
    sm.transition_to(ExecutionState.COMPLETED)
    assert sm.state == ExecutionState.COMPLETED


def test_invalid_transition_raises() -> None:
    sm = ExecutionStateMachine("pending")
    with pytest.raises(ValueError):
        sm.transition_to(ExecutionState.COMPLETED)


def test_terminal_states_no_transitions() -> None:
    sm = ExecutionStateMachine("completed")
    assert not sm.can_transition_to(ExecutionState.RUNNING)
