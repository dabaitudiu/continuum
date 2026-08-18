from pathlib import Path

from app.domain.models import ActionStatus, DecisionStatus
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.repository.runtime_sqlite import SQLiteRuntimeRepository
from app.runtime.coordinator import RuntimeCoordinator
from app.runtime.entities import (
    CommitmentStatus,
    MissionStatus,
    RuntimeEvent,
    SideEffectStatus,
    VendorStatus,
)


def started_demo() -> tuple[RuntimeCoordinator, str]:
    coordinator = RuntimeCoordinator(InMemoryRuntimeRepository())
    created = coordinator.create_demo("create-scenario")
    mission_id = created.snapshot.mission.mission_id
    coordinator.start(mission_id, "start-scenario")
    return coordinator, mission_id


def drifted_demo() -> tuple[RuntimeCoordinator, str]:
    coordinator, mission_id = started_demo()
    coordinator.upgrade_policy(mission_id, "policy-event-1")
    return coordinator, mission_id


def waiting_for_pen_test() -> tuple[RuntimeCoordinator, str]:
    coordinator, mission_id = drifted_demo()
    coordinator.revalidate_affected_branch(mission_id, "revalidate-1")
    return coordinator, mission_id


def test_policy_upgrade_invalidates_only_affected_branch() -> None:
    coordinator, mission_id = started_demo()

    result = coordinator.upgrade_policy(mission_id, "policy-event-1")

    assert result.snapshot.mission.status is MissionStatus.REVALIDATING
    assert result.snapshot.world is not None
    assert result.snapshot.world.current_policy_id == "policy-v13"
    assert result.snapshot.graph.decisions["D42"].status is DecisionStatus.STALE
    assert result.snapshot.graph.decisions["D50"].status is DecisionStatus.STALE
    assert result.snapshot.graph.decisions["D43"].status is DecisionStatus.VALID
    assert result.snapshot.graph.actions["activate-vendor"].status is ActionStatus.BLOCKED
    assert result.snapshot.commitments[0].status is CommitmentStatus.CANCELLED
    assert coordinator.upgrade_policy(mission_id, "policy-event-1").duplicate is True


def test_revalidation_creates_pen_test_commitment_only_after_v13() -> None:
    coordinator, mission_id = drifted_demo()

    result = coordinator.revalidate_affected_branch(mission_id, "revalidate-1")

    assert result.snapshot.mission.status is MissionStatus.WAITING
    open_commitments = [
        item for item in result.snapshot.commitments
        if item.status is CommitmentStatus.OPEN
    ]
    assert len(open_commitments) == 1
    assert open_commitments[0].event_type == "vendor.document.uploaded"
    assert open_commitments[0].predicate == {
        "vendor_id": "ACME",
        "document_type": "PEN_TEST",
    }
    assert result.result["execution_mode"] == "LOCAL_DETERMINISTIC"


def test_pen_test_arrival_supersedes_decisions_and_activates_once() -> None:
    coordinator, mission_id = waiting_for_pen_test()

    first = coordinator.upload_pen_test(mission_id, "pen-event-1")
    second = coordinator.upload_pen_test(mission_id, "pen-event-1")

    assert first.snapshot.mission.status is MissionStatus.COMPLETED
    assert first.snapshot.world is not None
    assert first.snapshot.world.vendor.status is VendorStatus.ACTIVE
    assert first.snapshot.commitments[-1].status is CommitmentStatus.SATISFIED
    assert first.snapshot.graph.decisions["D42"].status is DecisionStatus.SUPERSEDED
    assert first.snapshot.graph.decisions["D50"].status is DecisionStatus.SUPERSEDED
    assert first.snapshot.graph.decisions["D43"].status is DecisionStatus.VALID
    assert first.snapshot.graph.decisions["D57"].status is DecisionStatus.VALID
    assert first.snapshot.graph.decisions["D58"].status is DecisionStatus.VALID
    assert first.snapshot.graph.actions["activate-vendor"].status is ActionStatus.READY
    assert len(first.snapshot.side_effects) == 1
    assert first.snapshot.side_effects[0].status is SideEffectStatus.COMMITTED
    assert second.duplicate is True
    assert second.snapshot == first.snapshot


def test_wrong_document_event_does_not_satisfy_pen_test_wait() -> None:
    coordinator, mission_id = waiting_for_pen_test()

    result = coordinator.process_event(
        RuntimeEvent(
            event_id="wrong-document",
            event_type="vendor.document.uploaded",
            mission_id=mission_id,
            producer="enterprise-simulator",
            correlation_id="wrong-document",
            payload={
                "vendor_id": "ACME",
                "document_id": "soc2-later",
                "document_type": "SOC2",
            },
        )
    )

    assert result.result == {"matched_commitment_ids": []}
    assert result.snapshot.mission.status is MissionStatus.WAITING


def test_missing_evidence_wait_resumes_after_sqlite_restart(tmp_path: Path) -> None:
    path = tmp_path / "scenario.db"
    first_repository = SQLiteRuntimeRepository(path)
    first = RuntimeCoordinator(first_repository)
    created = first.create_demo("create-restart-scenario")
    mission_id = created.snapshot.mission.mission_id
    first.start(mission_id, "start-restart-scenario")
    first.upgrade_policy(mission_id, "policy-restart-scenario")
    first.revalidate_affected_branch(mission_id, "revalidate-restart-scenario")
    first_repository.close()

    second_repository = SQLiteRuntimeRepository(path)
    second = RuntimeCoordinator(second_repository)
    completed = second.upload_pen_test(mission_id, "pen-restart-scenario")

    assert completed.snapshot.mission.status is MissionStatus.COMPLETED
    assert completed.snapshot.world is not None
    assert completed.snapshot.world.vendor.status is VendorStatus.ACTIVE
    assert len(completed.snapshot.side_effects) == 1
    second_repository.close()
