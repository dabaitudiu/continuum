from datetime import UTC, datetime

import pytest

from app.runtime.entities import (
    Mission,
    MissionStatus,
    WorkItem,
    WorkStatus,
)
from app.runtime.errors import RuntimeDomainError
from app.runtime.state_machine import MissionStateMachine, WorkStateMachine


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (MissionStatus.CREATED, MissionStatus.RUNNING),
        (MissionStatus.CREATED, MissionStatus.CANCELLED),
        (MissionStatus.RUNNING, MissionStatus.WAITING),
        (MissionStatus.RUNNING, MissionStatus.REVALIDATING),
        (MissionStatus.RUNNING, MissionStatus.BLOCKED),
        (MissionStatus.RUNNING, MissionStatus.COMPLETED),
        (MissionStatus.WAITING, MissionStatus.RUNNING),
        (MissionStatus.WAITING, MissionStatus.REVALIDATING),
        (MissionStatus.REVALIDATING, MissionStatus.WAITING),
        (MissionStatus.REVALIDATING, MissionStatus.RUNNING),
        (MissionStatus.BLOCKED, MissionStatus.RUNNING),
        (MissionStatus.BLOCKED, MissionStatus.REVALIDATING),
    ],
)
def test_allowed_mission_transitions_return_updated_copy(
    current: MissionStatus,
    target: MissionStatus,
) -> None:
    mission = Mission(mission_id="m-1", status=current)

    transitioned = MissionStateMachine.transition(mission, target)

    assert transitioned.status is target
    assert mission.status is current
    assert transitioned.updated_at >= mission.updated_at


@pytest.mark.parametrize(
    "terminal",
    [MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED],
)
def test_terminal_mission_cannot_restart(terminal: MissionStatus) -> None:
    mission = Mission(mission_id="m-1", status=terminal)

    with pytest.raises(RuntimeDomainError) as raised:
        MissionStateMachine.transition(mission, MissionStatus.RUNNING)

    assert raised.value.code == "INVALID_MISSION_TRANSITION"


def test_unlisted_mission_transition_is_rejected() -> None:
    mission = Mission(mission_id="m-1", status=MissionStatus.CREATED)

    with pytest.raises(RuntimeDomainError) as raised:
        MissionStateMachine.transition(mission, MissionStatus.COMPLETED)

    assert raised.value.code == "INVALID_MISSION_TRANSITION"


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (WorkStatus.PENDING, WorkStatus.DISPATCHED),
        (WorkStatus.DISPATCHED, WorkStatus.RUNNING),
        (WorkStatus.RUNNING, WorkStatus.SUCCEEDED),
        (WorkStatus.RUNNING, WorkStatus.WAITING),
        (WorkStatus.RUNNING, WorkStatus.FAILED),
        (WorkStatus.PENDING, WorkStatus.CANCELLED),
        (WorkStatus.WAITING, WorkStatus.PENDING),
    ],
)
def test_allowed_work_transitions(
    current: WorkStatus,
    target: WorkStatus,
) -> None:
    work = WorkItem(
        work_item_id="w-1",
        mission_id="m-1",
        work_type="SECURITY_REVIEW",
        status=current,
    )

    transitioned = WorkStateMachine.transition(
        work,
        target,
        has_open_commitment=target is WorkStatus.WAITING,
    )

    assert transitioned.status is target


def test_dispatch_increments_attempt_exactly_once() -> None:
    work = WorkItem(
        work_item_id="w-1",
        mission_id="m-1",
        work_type="SECURITY_REVIEW",
    )

    dispatched = WorkStateMachine.transition(work, WorkStatus.DISPATCHED)

    assert dispatched.attempt == 1
    assert work.attempt == 0


def test_non_dispatch_transition_does_not_increment_attempt() -> None:
    work = WorkItem(
        work_item_id="w-1",
        mission_id="m-1",
        work_type="SECURITY_REVIEW",
        status=WorkStatus.DISPATCHED,
        attempt=3,
    )

    running = WorkStateMachine.transition(work, WorkStatus.RUNNING)

    assert running.attempt == 3


def test_waiting_work_requires_open_commitment() -> None:
    work = WorkItem(
        work_item_id="w-1",
        mission_id="m-1",
        work_type="SECURITY_REVIEW",
        status=WorkStatus.RUNNING,
    )

    with pytest.raises(RuntimeDomainError) as raised:
        WorkStateMachine.transition(
            work,
            WorkStatus.WAITING,
            has_open_commitment=False,
        )

    assert raised.value.code == "COMMITMENT_INVARIANT_VIOLATION"


def test_terminal_work_cannot_transition() -> None:
    work = WorkItem(
        work_item_id="w-1",
        mission_id="m-1",
        work_type="SECURITY_REVIEW",
        status=WorkStatus.SUCCEEDED,
    )

    with pytest.raises(RuntimeDomainError) as raised:
        WorkStateMachine.transition(work, WorkStatus.RUNNING)

    assert raised.value.code == "INVALID_WORK_TRANSITION"


def test_runtime_entities_use_timezone_aware_timestamps() -> None:
    mission = Mission(mission_id="m-1")
    work = WorkItem(
        work_item_id="w-1",
        mission_id="m-1",
        work_type="SECURITY_REVIEW",
    )

    assert mission.created_at.tzinfo is UTC
    assert mission.updated_at.tzinfo is UTC
    assert work.created_at.tzinfo is UTC
    assert mission.created_at <= datetime.now(UTC)
