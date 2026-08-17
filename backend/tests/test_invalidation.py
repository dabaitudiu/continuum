from copy import deepcopy

import pytest

from app.demo.fixture import seed_alternate_mission, seed_canonical_mission
from app.domain.invalidation import InvalidationService
from app.domain.models import (
    ActionStatus,
    ArtifactStatus,
    DecisionStatus,
    DependencyEdge,
    DomainEvent,
    RelationType,
)
from app.repository.memory import InMemoryGraphRepository


def policy_v13_event(event_id: str = "evt-1") -> DomainEvent:
    return DomainEvent(
        event_id=event_id,
        event_type="policy.version.changed",
        payload={
            "logical_key": "security-policy",
            "old_artifact_id": "policy-v12",
            "new_artifact_id": "policy-v13",
            "old_version": "v12",
            "new_version": "v13",
        },
    )


def canonical_runtime(
) -> tuple[InMemoryGraphRepository, str, InvalidationService]:
    repo = InMemoryGraphRepository()
    mission_id = seed_canonical_mission(repo)
    return repo, mission_id, InvalidationService(repo)


def test_policy_v13_invalidates_only_security_dependent_branch() -> None:
    _, mission_id, service = canonical_runtime()

    snapshot = service.process_artifact_change(
        mission_id,
        policy_v13_event("evt-1"),
    )

    assert snapshot.decisions["D42"].status is DecisionStatus.STALE
    assert snapshot.decisions["D50"].status is DecisionStatus.STALE
    assert snapshot.decisions["D43"].status is DecisionStatus.VALID
    assert snapshot.actions["activate-vendor"].status is ActionStatus.BLOCKED
    assert snapshot.artifacts["policy-v12"].status is ArtifactStatus.SUPERSEDED
    assert snapshot.artifacts["policy-v13"].status is ArtifactStatus.CURRENT
    assert snapshot.cause_by_node_id == {
        "D42": "policy-v12",
        "D50": "D42",
        "activate-vendor": "D50",
    }


def test_alternate_ids_and_artifact_type_use_same_rules() -> None:
    repo = InMemoryGraphRepository()
    mission_id, event = seed_alternate_mission(repo)

    snapshot = InvalidationService(repo).process_artifact_change(
        mission_id,
        event,
    )

    assert snapshot.decisions["risk-review-X"].status is DecisionStatus.STALE
    assert snapshot.decisions["release-Z"].status is DecisionStatus.STALE
    assert snapshot.decisions["budget-Y"].status is DecisionStatus.VALID
    assert snapshot.actions["publish-Q"].status is ActionStatus.BLOCKED


def test_noncritical_edge_does_not_propagate() -> None:
    repo, mission_id, service = canonical_runtime()
    snapshot = repo.get_snapshot(mission_id)
    edge = next(edge for edge in snapshot.edges if edge.edge_id == "D42-D50")
    edge.critical = False
    repo.save_snapshot(snapshot)

    result = service.process_artifact_change(mission_id, policy_v13_event())

    assert result.decisions["D42"].status is DecisionStatus.STALE
    assert result.decisions["D50"].status is DecisionStatus.VALID
    assert result.actions["activate-vendor"].status is ActionStatus.READY


def test_non_validity_relation_does_not_propagate() -> None:
    repo, mission_id, service = canonical_runtime()
    snapshot = repo.get_snapshot(mission_id)
    edge = next(edge for edge in snapshot.edges if edge.edge_id == "D42-D50")
    edge.relation_type = RelationType.SUPPORTED_BY
    repo.save_snapshot(snapshot)

    result = service.process_artifact_change(mission_id, policy_v13_event())

    assert result.decisions["D42"].status is DecisionStatus.STALE
    assert result.decisions["D50"].status is DecisionStatus.VALID


def test_cycle_terminates_and_invalidates_each_reachable_decision() -> None:
    repo, mission_id, service = canonical_runtime()
    snapshot = repo.get_snapshot(mission_id)
    snapshot.edges.append(
        DependencyEdge(
            edge_id="D50-D42-cycle",
            from_node_id="D50",
            to_node_id="D42",
            relation_type=RelationType.REQUIRES,
            critical=True,
        )
    )
    repo.save_snapshot(snapshot)

    result = service.process_artifact_change(mission_id, policy_v13_event())

    assert result.decisions["D42"].status is DecisionStatus.STALE
    assert result.decisions["D50"].status is DecisionStatus.STALE
    assert len(result.events) == 1


def test_duplicate_event_returns_same_state_without_new_event() -> None:
    repo, mission_id, service = canonical_runtime()
    first = service.process_artifact_change(
        mission_id,
        policy_v13_event("evt-duplicate"),
    )

    second = service.process_artifact_change(
        mission_id,
        policy_v13_event("evt-duplicate"),
    )

    assert second == first
    assert len(second.events) == 1


def test_mismatched_artifact_version_is_rejected_without_mutation() -> None:
    repo, mission_id, service = canonical_runtime()
    before = deepcopy(repo.get_snapshot(mission_id))
    event = policy_v13_event()
    event.payload["old_version"] = "v11"

    with pytest.raises(ValueError, match="old artifact version"):
        service.process_artifact_change(mission_id, event)

    assert repo.get_snapshot(mission_id) == before


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda event: event.payload.pop("new_version"), "missing fields"),
        (
            lambda event: event.payload.update(old_artifact_id="unknown-policy"),
            "unknown old artifact",
        ),
        (
            lambda event: event.payload.update(logical_key="other-policy"),
            "logical key",
        ),
    ],
)
def test_invalid_artifact_identity_is_rejected_without_mutation(
    mutation,  # type: ignore[no-untyped-def]
    message: str,
) -> None:
    repo, mission_id, service = canonical_runtime()
    before = deepcopy(repo.get_snapshot(mission_id))
    event = policy_v13_event()
    mutation(event)

    with pytest.raises(ValueError, match=message):
        service.process_artifact_change(mission_id, event)

    assert repo.get_snapshot(mission_id) == before


def test_superseded_old_artifact_is_rejected_without_mutation() -> None:
    repo, mission_id, service = canonical_runtime()
    snapshot = repo.get_snapshot(mission_id)
    snapshot.artifacts["policy-v12"].status = ArtifactStatus.SUPERSEDED
    repo.save_snapshot(snapshot)
    before = deepcopy(repo.get_snapshot(mission_id))

    with pytest.raises(ValueError, match="not current"):
        service.process_artifact_change(mission_id, policy_v13_event())

    assert repo.get_snapshot(mission_id) == before
