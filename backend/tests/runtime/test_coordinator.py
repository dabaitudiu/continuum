from pathlib import Path

import pytest

from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.repository.runtime_sqlite import SQLiteRuntimeRepository
from app.demo.runtime_fixture import seed_runtime_demo
from app.runtime.coordinator import RuntimeCoordinator
from app.runtime.entities import (
    AuditEvent,
    CommitmentStatus,
    InboxRecord,
    MissionStatus,
    OutboxMessage,
    RuntimeEvent,
    WorkStatus,
)
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation


def document_event(
    mission_id: str,
    event_id: str,
    document_type: str,
) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=event_id,
        event_type="vendor.document.uploaded",
        mission_id=mission_id,
        producer="enterprise-simulator",
        correlation_id=event_id,
        payload={
            "vendor_id": "ACME",
            "document_id": f"document:{event_id}",
            "document_type": document_type,
        },
    )


def waiting_demo() -> tuple[RuntimeCoordinator, str]:
    coordinator = RuntimeCoordinator(InMemoryRuntimeRepository())
    created = coordinator.create_demo("create-1")
    mission_id = created.snapshot.mission.mission_id
    coordinator.start(mission_id, "start-1")
    return coordinator, mission_id


def test_create_demo_is_idempotent_and_seeds_canonical_graph() -> None:
    coordinator = RuntimeCoordinator(InMemoryRuntimeRepository())

    first = coordinator.create_demo("create-1")
    second = coordinator.create_demo("create-1")

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.snapshot == first.snapshot
    assert first.snapshot.mission.status is MissionStatus.CREATED
    assert first.snapshot.mission.event_sequence == 1
    assert set(first.snapshot.graph.decisions) == {"D42", "D43", "D50"}
    assert [item.work_type for item in first.snapshot.work_items] == [
        "VENDOR_INTAKE"
    ]


def test_distinct_create_request_gets_distinct_mission_namespace() -> None:
    coordinator = RuntimeCoordinator(InMemoryRuntimeRepository())

    first = coordinator.create_demo("create-1")
    second = coordinator.create_demo("create-2")

    assert first.snapshot.mission.mission_id != second.snapshot.mission.mission_id


def test_start_is_idempotent_and_waits_on_pen_test_commitment() -> None:
    coordinator = RuntimeCoordinator(InMemoryRuntimeRepository())
    created = coordinator.create_demo("create-1")
    mission_id = created.snapshot.mission.mission_id

    first = coordinator.start(mission_id, "start-1")
    second = coordinator.start(mission_id, "start-1")

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.snapshot == first.snapshot
    assert first.snapshot.mission.status is MissionStatus.WAITING
    assert first.snapshot.mission.revision == 1
    assert len(first.snapshot.commitments) == 1
    commitment = first.snapshot.commitments[0]
    assert commitment.status is CommitmentStatus.OPEN
    assert commitment.predicate == {
        "vendor_id": "ACME",
        "document_type": "PEN_TEST",
    }
    work_by_type = {item.work_type: item for item in first.snapshot.work_items}
    assert work_by_type["VENDOR_INTAKE"].status is WorkStatus.SUCCEEDED
    assert work_by_type["REVIEW_PEN_TEST"].status is WorkStatus.WAITING
    assert work_by_type["REVIEW_PEN_TEST"].commitment_ids == [
        commitment.commitment_id
    ]


def test_start_from_noncreated_state_is_rejected_without_mutation() -> None:
    coordinator, mission_id = waiting_demo()
    before = coordinator.get(mission_id)

    with pytest.raises(RuntimeDomainError) as raised:
        coordinator.start(mission_id, "start-2")

    assert raised.value.code == "INVALID_MISSION_TRANSITION"
    assert coordinator.get(mission_id) == before


def test_wrong_event_is_recorded_but_does_not_wake_mission() -> None:
    coordinator, mission_id = waiting_demo()

    result = coordinator.process_event(
        document_event(mission_id, "evt-wrong", "SOC2")
    )

    assert result.duplicate is False
    assert result.result == {"matched_commitment_ids": []}
    assert result.snapshot.mission.status is MissionStatus.WAITING
    assert result.snapshot.commitments[0].status is CommitmentStatus.OPEN
    assert next(
        item
        for item in result.snapshot.work_items
        if item.work_type == "REVIEW_PEN_TEST"
    ).status is WorkStatus.WAITING
    assert result.snapshot.audit_events[-1].event_type == "event.ignored"


def test_matching_event_satisfies_and_wakes_exactly_once() -> None:
    coordinator, mission_id = waiting_demo()

    first = coordinator.process_event(
        document_event(mission_id, "evt-pen-1", "PEN_TEST")
    )
    second = coordinator.process_event(
        document_event(mission_id, "evt-pen-1", "PEN_TEST")
    )

    assert first.snapshot.mission.status is MissionStatus.RUNNING
    assert first.snapshot.commitments[0].status is CommitmentStatus.SATISFIED
    assert first.snapshot.commitments[0].satisfied_by_event_id == "evt-pen-1"
    review_work = next(
        item
        for item in first.snapshot.work_items
        if item.work_type == "REVIEW_PEN_TEST"
    )
    assert review_work.status is WorkStatus.PENDING
    assert second.duplicate is True
    assert second.snapshot == first.snapshot
    assert len(
        [
            event
            for event in second.snapshot.audit_events
            if event.event_type == "commitment.satisfied"
        ]
    ) == 1


def test_audit_sequence_is_contiguous_across_create_start_ignore_and_wake() -> None:
    coordinator, mission_id = waiting_demo()
    coordinator.process_event(document_event(mission_id, "evt-wrong", "SOC2"))
    final = coordinator.process_event(
        document_event(mission_id, "evt-pen-1", "PEN_TEST")
    )

    sequences = [event.event_sequence for event in final.snapshot.audit_events]

    assert sequences == list(range(1, len(sequences) + 1))
    assert final.snapshot.mission.event_sequence == sequences[-1]
    assert len(final.snapshot.outbox) == len(final.snapshot.audit_events)


def test_read_methods_return_isolated_ordered_views() -> None:
    coordinator, mission_id = waiting_demo()

    snapshot = coordinator.get(mission_id)
    timeline = coordinator.timeline(mission_id)
    commitments = coordinator.commitments(mission_id)
    snapshot.mission.status = MissionStatus.FAILED
    timeline[0].payload["corrupted"] = True
    commitments[0].predicate["document_type"] = "CORRUPTED"

    assert coordinator.get(mission_id).mission.status is MissionStatus.WAITING
    assert "corrupted" not in coordinator.timeline(mission_id)[0].payload
    assert coordinator.commitments(mission_id)[0].predicate["document_type"] == "PEN_TEST"


def test_sqlite_restart_preserves_waiting_then_wake_flow(tmp_path: Path) -> None:
    path = tmp_path / "coordinator.db"
    first_repo = SQLiteRuntimeRepository(path)
    first = RuntimeCoordinator(first_repo)
    created = first.create_demo("create-1")
    mission_id = created.snapshot.mission.mission_id
    waiting = first.start(mission_id, "start-1")
    assert waiting.snapshot.mission.status is MissionStatus.WAITING
    first_repo.close()

    second_repo = SQLiteRuntimeRepository(path)
    second = RuntimeCoordinator(second_repo)
    woke = second.process_event(
        document_event(mission_id, "evt-pen-1", "PEN_TEST")
    )

    assert woke.snapshot.mission.status is MissionStatus.RUNNING
    assert woke.snapshot.commitments[0].status is CommitmentStatus.SATISFIED
    second_repo.close()


def test_unknown_mission_has_stable_error() -> None:
    coordinator = RuntimeCoordinator(InMemoryRuntimeRepository())

    with pytest.raises(RuntimeDomainError) as raised:
        coordinator.get("missing")

    assert raised.value.code == "MISSION_NOT_FOUND"


def test_create_rejects_existing_deterministic_namespace_without_inbox() -> None:
    repository = InMemoryRuntimeRepository()
    snapshot = seed_runtime_demo("create-1")
    snapshot.inbox = []
    repository.create(snapshot)
    coordinator = RuntimeCoordinator(repository)

    with pytest.raises(RuntimeDomainError) as raised:
        coordinator.create_demo("create-1")

    assert raised.value.code == "MISSION_ALREADY_EXISTS"


def test_create_returns_duplicate_when_another_writer_wins_create_race() -> None:
    repository = CreateRaceRepository()
    coordinator = RuntimeCoordinator(repository)

    result = coordinator.create_demo("create-1")

    assert result.duplicate is True
    assert result.result["status"] == "CREATED"


def test_create_race_without_matching_inbox_preserves_conflict() -> None:
    repository = CreateRaceRepository(drop_inbox=True)
    coordinator = RuntimeCoordinator(repository)

    with pytest.raises(RuntimeDomainError) as raised:
        coordinator.create_demo("create-1")

    assert raised.value.code == "MISSION_ALREADY_EXISTS"


def test_create_propagates_nonabsence_repository_error() -> None:
    coordinator = RuntimeCoordinator(FailingLoadRepository())

    with pytest.raises(RuntimeDomainError) as raised:
        coordinator.create_demo("create-1")

    assert raised.value.code == "DATABASE_UNAVAILABLE"


def test_matching_commitment_does_not_clear_independent_mission_blocker() -> None:
    repository = InMemoryRuntimeRepository()
    coordinator = RuntimeCoordinator(repository)
    created = coordinator.create_demo("create-1")
    mission_id = created.snapshot.mission.mission_id
    coordinator.start(mission_id, "start-1")
    waiting = repository.load(mission_id)
    blocked_mission = waiting.mission.model_copy(
        update={"status": MissionStatus.BLOCKED}
    )
    repository.commit(
        mission_id,
        waiting.mission.revision,
        RuntimeMutation(
            mission=blocked_mission,
            audit_appends=[
                AuditEvent(
                    audit_event_id="audit:block-1",
                    mission_id=mission_id,
                    event_sequence=waiting.mission.event_sequence + 1,
                    event_type="mission.blocked",
                    correlation_id="block-1",
                    causation_id="block-1",
                )
            ],
            inbox_completion=InboxRecord(
                mission_id=mission_id,
                message_id="block-1",
                message_type="mission.block",
                result={"status": "BLOCKED"},
            ),
            outbox_appends=[
                OutboxMessage(
                    outbox_message_id="outbox:block-1",
                    mission_id=mission_id,
                    event_type="mission.blocked",
                    correlation_id="block-1",
                    causation_id="block-1",
                )
            ],
        ),
    )

    result = coordinator.process_event(
        document_event(mission_id, "evt-pen-1", "PEN_TEST")
    )

    assert result.snapshot.mission.status is MissionStatus.BLOCKED
    assert result.snapshot.commitments[0].status is CommitmentStatus.SATISFIED
    assert result.snapshot.audit_events[-1].event_type == "commitment.satisfied"
    assert not any(
        event.causation_id == "evt-pen-1"
        and event.event_type == "mission.resumed"
        for event in result.snapshot.audit_events
    )


class CreateRaceRepository(InMemoryRuntimeRepository):
    def __init__(self, *, drop_inbox: bool = False) -> None:
        super().__init__()
        self._drop_inbox = drop_inbox

    def create(self, snapshot):  # type: ignore[no-untyped-def]
        raced = snapshot.model_copy(deep=True)
        if self._drop_inbox:
            raced.inbox = []
        super().create(raced)
        raise RuntimeDomainError(
            "MISSION_ALREADY_EXISTS",
            "another writer created the mission",
        )


class FailingLoadRepository(InMemoryRuntimeRepository):
    def load(self, mission_id):  # type: ignore[no-untyped-def]
        raise RuntimeDomainError(
            "DATABASE_UNAVAILABLE",
            f"cannot load {mission_id}",
        )
