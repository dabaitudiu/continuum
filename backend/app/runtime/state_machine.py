from app.runtime.entities import (
    Mission,
    MissionStatus,
    WorkItem,
    WorkStatus,
    utc_now,
)
from app.runtime.errors import RuntimeDomainError


MISSION_TRANSITIONS: dict[MissionStatus, set[MissionStatus]] = {
    MissionStatus.CREATED: {MissionStatus.RUNNING, MissionStatus.CANCELLED},
    MissionStatus.RUNNING: {
        MissionStatus.WAITING,
        MissionStatus.REVALIDATING,
        MissionStatus.BLOCKED,
        MissionStatus.COMPLETED,
        MissionStatus.FAILED,
        MissionStatus.CANCELLED,
    },
    MissionStatus.WAITING: {
        MissionStatus.RUNNING,
        MissionStatus.REVALIDATING,
        MissionStatus.BLOCKED,
        MissionStatus.FAILED,
        MissionStatus.CANCELLED,
    },
    MissionStatus.REVALIDATING: {
        MissionStatus.RUNNING,
        MissionStatus.WAITING,
        MissionStatus.BLOCKED,
        MissionStatus.FAILED,
        MissionStatus.CANCELLED,
    },
    MissionStatus.BLOCKED: {
        MissionStatus.RUNNING,
        MissionStatus.REVALIDATING,
        MissionStatus.FAILED,
        MissionStatus.CANCELLED,
    },
    MissionStatus.COMPLETED: set(),
    MissionStatus.FAILED: set(),
    MissionStatus.CANCELLED: set(),
}


WORK_TRANSITIONS: dict[WorkStatus, set[WorkStatus]] = {
    WorkStatus.PENDING: {WorkStatus.DISPATCHED, WorkStatus.CANCELLED},
    WorkStatus.DISPATCHED: {
        WorkStatus.RUNNING,
        WorkStatus.FAILED,
        WorkStatus.CANCELLED,
    },
    WorkStatus.RUNNING: {
        WorkStatus.SUCCEEDED,
        WorkStatus.WAITING,
        WorkStatus.FAILED,
        WorkStatus.CANCELLED,
    },
    WorkStatus.WAITING: {WorkStatus.PENDING, WorkStatus.CANCELLED},
    WorkStatus.SUCCEEDED: set(),
    WorkStatus.FAILED: set(),
    WorkStatus.CANCELLED: set(),
}


class MissionStateMachine:
    @staticmethod
    def transition(mission: Mission, target: MissionStatus) -> Mission:
        if target not in MISSION_TRANSITIONS[mission.status]:
            raise RuntimeDomainError(
                "INVALID_MISSION_TRANSITION",
                f"cannot transition mission from {mission.status} to {target}",
            )
        return mission.model_copy(
            update={"status": target, "updated_at": utc_now()},
            deep=True,
        )


class WorkStateMachine:
    @staticmethod
    def transition(
        work_item: WorkItem,
        target: WorkStatus,
        *,
        has_open_commitment: bool = False,
    ) -> WorkItem:
        if target not in WORK_TRANSITIONS[work_item.status]:
            raise RuntimeDomainError(
                "INVALID_WORK_TRANSITION",
                f"cannot transition work from {work_item.status} to {target}",
            )
        if target is WorkStatus.WAITING and not has_open_commitment:
            raise RuntimeDomainError(
                "COMMITMENT_INVARIANT_VIOLATION",
                "waiting work requires an open commitment",
            )
        attempt = work_item.attempt + (
            1
            if work_item.status is WorkStatus.PENDING
            and target is WorkStatus.DISPATCHED
            else 0
        )
        return work_item.model_copy(
            update={
                "status": target,
                "attempt": attempt,
                "updated_at": utc_now(),
            },
            deep=True,
        )
