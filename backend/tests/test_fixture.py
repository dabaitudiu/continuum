from app.demo.fixture import seed_canonical_mission
from app.domain.models import ActionStatus, DecisionStatus
from app.repository.memory import InMemoryGraphRepository


def test_canonical_fixture_starts_current_valid_and_ready() -> None:
    repo = InMemoryGraphRepository()
    mission_id = seed_canonical_mission(repo)

    snapshot = repo.get_snapshot(mission_id)

    assert snapshot.artifacts["policy-v12"].status.value == "CURRENT"
    assert {
        node_id: node.status for node_id, node in snapshot.decisions.items()
    } == {
        "D42": DecisionStatus.VALID,
        "D43": DecisionStatus.VALID,
        "D50": DecisionStatus.VALID,
    }
    assert snapshot.actions["activate-vendor"].status is ActionStatus.READY
    assert {
        node_id: node.execution_count
        for node_id, node in snapshot.decisions.items()
    } == {"D42": 1, "D43": 1, "D50": 1}
    assert len(snapshot.edges) == 6
