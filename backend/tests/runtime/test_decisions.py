import pytest

from app.demo.fixture import seed_canonical_mission
from app.domain.models import DecisionStatus
from app.repository.memory import InMemoryGraphRepository
from app.runtime.decisions import DecisionService
from app.runtime.errors import RuntimeDomainError


def canonical_graph_with_d42(status: DecisionStatus):  # type: ignore[no-untyped-def]
    repo = InMemoryGraphRepository()
    mission_id = seed_canonical_mission(repo, "m-1")
    graph = repo.get_snapshot(mission_id)
    graph.decisions["D42"].status = status
    return graph


@pytest.mark.parametrize(
    "old_status",
    [DecisionStatus.STALE, DecisionStatus.REVALIDATING],
)
def test_supersede_preserves_old_decision_and_redirects_consumers(
    old_status: DecisionStatus,
) -> None:
    graph = canonical_graph_with_d42(old_status)

    result = DecisionService.supersede(
        graph,
        old_id="D42",
        new_id="D57",
        outcome="APPROVED",
    )

    assert result.decisions["D42"].status is DecisionStatus.SUPERSEDED
    assert result.decisions["D42"].outcome == "APPROVED"
    assert result.decisions["D57"].status is DecisionStatus.VALID
    assert result.decisions["D57"].supersedes_decision_id == "D42"
    assert result.decisions["D57"].execution_count == 1
    assert any(
        edge.from_node_id == "D57" and edge.to_node_id == "D50"
        for edge in result.edges
    )
    assert not any(
        edge.from_node_id == "D42" and edge.to_node_id == "D50"
        for edge in result.edges
    )
    assert any(
        edge.from_node_id == "policy-v12" and edge.to_node_id == "D42"
        for edge in result.edges
    )
    assert any(
        edge.from_node_id == "policy-v12" and edge.to_node_id == "D57"
        for edge in result.edges
    )
    assert graph.decisions["D42"].status is old_status


def test_supersede_requires_stale_or_revalidating_old_decision() -> None:
    graph = canonical_graph_with_d42(DecisionStatus.VALID)

    with pytest.raises(RuntimeDomainError) as raised:
        DecisionService.supersede(
            graph,
            old_id="D42",
            new_id="D57",
            outcome="APPROVED",
        )

    assert raised.value.code == "INVALID_DECISION_TRANSITION"


def test_supersede_rejects_unknown_old_decision() -> None:
    graph = canonical_graph_with_d42(DecisionStatus.STALE)

    with pytest.raises(RuntimeDomainError) as raised:
        DecisionService.supersede(
            graph,
            old_id="missing",
            new_id="D57",
            outcome="APPROVED",
        )

    assert raised.value.code == "DECISION_NOT_FOUND"


def test_supersede_rejects_duplicate_new_decision_id() -> None:
    graph = canonical_graph_with_d42(DecisionStatus.STALE)

    with pytest.raises(RuntimeDomainError) as raised:
        DecisionService.supersede(
            graph,
            old_id="D42",
            new_id="D43",
            outcome="APPROVED",
        )

    assert raised.value.code == "DECISION_ALREADY_EXISTS"
