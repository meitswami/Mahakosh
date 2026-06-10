from enum import StrEnum


class WorkflowState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.PENDING: {WorkflowState.QUEUED, WorkflowState.CANCELLED},
    WorkflowState.QUEUED: {WorkflowState.RUNNING, WorkflowState.CANCELLED},
    WorkflowState.RUNNING: {
        WorkflowState.WAITING,
        WorkflowState.PAUSED,
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
        WorkflowState.CANCELLED,
    },
    WorkflowState.WAITING: {
        WorkflowState.RUNNING,
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
        WorkflowState.CANCELLED,
    },
    WorkflowState.PAUSED: {
        WorkflowState.RUNNING,
        WorkflowState.CANCELLED,
    },
    WorkflowState.COMPLETED: set(),
    WorkflowState.FAILED: {WorkflowState.QUEUED, WorkflowState.CANCELLED},
    WorkflowState.CANCELLED: set(),
}


class WorkflowStateMachine:
    def __init__(self, initial_state: WorkflowState = WorkflowState.PENDING) -> None:
        self._state = initial_state

    @property
    def state(self) -> WorkflowState:
        return self._state

    def can_transition(self, target: WorkflowState) -> bool:
        return target in VALID_TRANSITIONS.get(self._state, set())

    def transition(self, target: WorkflowState) -> WorkflowState:
        if not self.can_transition(target):
            raise ValueError(
                f"Invalid transition from '{self._state.value}' to '{target.value}'"
            )
        self._state = target
        return self._state

    def is_terminal(self) -> bool:
        return self._state in {WorkflowState.COMPLETED, WorkflowState.CANCELLED}

    def is_active(self) -> bool:
        return self._state in {
            WorkflowState.QUEUED,
            WorkflowState.RUNNING,
            WorkflowState.WAITING,
        }
