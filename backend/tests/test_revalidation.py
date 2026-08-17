from app.demo.fixture import seed_canonical_mission
from app.domain.invalidation import InvalidationService
from app.domain.models import DecisionStatus, DomainEvent
from app.domain.revalidation import RevalidationService
from app.repository.memory import InMemoryGraphRepository


def invalidated_canonical_runtime() -> tuple[InMemoryGraphRepository, str]:
    repo = InMemoryGraphRepository()
    mission_id = seed_canonical_mission(repo)
    InvalidationService(repo).process_artifact_change(
        mission_id,
        DomainEvent(
            event_id="evt-revalidation",
            event_type="policy.version.changed",
            payload={
                "logical_key": "security-policy",
                "old_artifact_id": "policy-v12",
                "new_artifact_id": "policy-v13",
                "old_version": "v12",
                "new_version": "v13",
            },
        ),
    )
    return repo, mission_id


def test_plan_runs_stale_root_waits_on_stale_dependent_and_retains_valid_sibling() -> None:
    repo, mission_id = invalidated_canonical_runtime()

    plan = RevalidationService(repo).plan(mission_id)

    assert plan.stale_decision_ids == ["D42", "D50"]
    assert plan.runnable_decision_ids == ["D42"]
    assert plan.waiting_decision_ids == ["D50"]
    assert plan.blocked_action_ids == ["activate-vendor"]
    assert plan.retained_decision_ids == ["D43"]
    assert plan.cause_by_node_id == {
        "D42": "policy-v12",
        "D50": "D42",
        "activate-vendor": "D50",
    }


def test_dispatch_revalidates_only_currently_runnable_root() -> None:
    repo, mission_id = invalidated_canonical_runtime()

    records = RevalidationService(repo).dispatch(mission_id, "request-1")
    snapshot = repo.get_snapshot(mission_id)

    assert [record.decision_id for record in records] == ["D42"]
    assert records[0].request_id == "request-1"
    assert records[0].work_type == "REVALIDATE_DECISION"
    assert records[0].status == "DISPATCHED"
    assert snapshot.decisions["D42"].status is DecisionStatus.REVALIDATING
    assert snapshot.decisions["D42"].execution_count == 2
    assert snapshot.decisions["D50"].status is DecisionStatus.STALE
    assert snapshot.decisions["D50"].execution_count == 1
    assert snapshot.decisions["D43"].status is DecisionStatus.VALID
    assert snapshot.decisions["D43"].execution_count == 1


def test_duplicate_dispatch_request_is_idempotent() -> None:
    repo, mission_id = invalidated_canonical_runtime()
    service = RevalidationService(repo)

    first = service.dispatch(mission_id, "request-1")
    second = service.dispatch(mission_id, "request-1")

    assert second == first
    assert repo.get_snapshot(mission_id).decisions["D42"].execution_count == 2
