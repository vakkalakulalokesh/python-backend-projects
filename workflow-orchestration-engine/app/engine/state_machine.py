from __future__ import annotations

from enum import Enum


class ExecutionState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


VALID_TRANSITIONS: dict[ExecutionState, list[ExecutionState]] = {
    ExecutionState.PENDING: [ExecutionState.RUNNING, ExecutionState.CANCELLED],
    ExecutionState.RUNNING: [
        ExecutionState.COMPLETED,
        ExecutionState.FAILED,
        ExecutionState.CANCELLED,
        ExecutionState.TIMED_OUT,
    ],
    ExecutionState.COMPLETED: [],
    ExecutionState.FAILED: [ExecutionState.PENDING],
    ExecutionState.CANCELLED: [],
    ExecutionState.TIMED_OUT: [ExecutionState.PENDING],
}


class ExecutionStateMachine:
    def __init__(self, current_state: str) -> None:
        self.state = ExecutionState(current_state)

    def can_transition_to(self, target: ExecutionState) -> bool:
        return target in VALID_TRANSITIONS[self.state]

    def transition_to(self, target: ExecutionState) -> ExecutionState:
        if not self.can_transition_to(target):
            raise ValueError(f"Invalid transition: {self.state} -> {target}")
        self.state = target
        return self.state
