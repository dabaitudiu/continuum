import sqlite3
from pathlib import Path

import pytest

from app.domain.models import (
    DecisionNode,
    DependencyEdge,
    RelationType,
    WorldArtifact,
)
from app.repository.runtime_sqlite import SQLiteRuntimeRepository
from app.runtime.entities import (
    Commitment,
    SideEffectRecord,
    WorkItem,
)
from app.runtime.errors import RuntimeDomainError
from tests.repository.runtime_contract import (
    RuntimeRepositoryContract,
    runtime_snapshot,
    transition_mutation,
)


class TestSQLiteRuntimeRepository(RuntimeRepositoryContract):
    @pytest.fixture(autouse=True)
    def close_repositories(self):  # type: ignore[no-untyped-def]
        self._repositories: list[SQLiteRuntimeRepository] = []
        yield
        for repository in self._repositories:
            repository.close()

    def make_repo(self, tmp_path: Path) -> SQLiteRuntimeRepository:
        repository = SQLiteRuntimeRepository(tmp_path / "runtime.db")
        self._repositories.append(repository)
        return repository


def test_new_instance_recovers_complete_runtime_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "runtime.db"
    first = SQLiteRuntimeRepository(path)
    snapshot = runtime_snapshot()
    snapshot.graph.artifacts["policy-v12"] = WorldArtifact(
        artifact_id="policy-v12",
        artifact_type="SECURITY_POLICY",
        logical_key="security-policy",
        version="v12",
    )
    snapshot.graph.decisions["D42"] = DecisionNode(
        decision_id="D42",
        decision_type="SECURITY_REVIEW",
        outcome="APPROVED",
    )
    snapshot.graph.edges.append(
        DependencyEdge(
            edge_id="policy-D42",
            from_node_id="policy-v12",
            to_node_id="D42",
            relation_type=RelationType.GOVERNED_BY,
        )
    )
    first.create(snapshot)
    mutation = transition_mutation(snapshot, message_id="request-1")
    mutation.work_upserts = [
        WorkItem(
            work_item_id="work-1",
            mission_id="m-1",
            work_type="SECURITY_REVIEW",
        )
    ]
    mutation.commitment_upserts = [
        Commitment(
            commitment_id="commitment-1",
            mission_id="m-1",
            work_item_id="work-1",
            event_type="vendor.document.uploaded",
            predicate={"document_type": "PEN_TEST"},
        )
    ]
    mutation.side_effect_upserts = [
        SideEffectRecord(
            side_effect_id="effect-1",
            mission_id="m-1",
            effect_type="ACTIVATE_VENDOR",
            idempotency_key="activate:ACME",
            authorization_decision_id="D42",
        )
    ]
    expected = first.commit("m-1", 0, mutation)
    first.close()

    second = SQLiteRuntimeRepository(path)

    assert second.load("m-1") == expected
    second.close()


def test_two_repository_instances_cannot_overwrite_same_revision(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime.db"
    first = SQLiteRuntimeRepository(path)
    second = SQLiteRuntimeRepository(path)
    first.create(runtime_snapshot())
    first_base = first.load("m-1")
    second_base = second.load("m-1")
    first.commit(
        "m-1",
        first_base.mission.revision,
        transition_mutation(first_base, message_id="request-1"),
    )

    with pytest.raises(RuntimeDomainError) as raised:
        second.commit(
            "m-1",
            second_base.mission.revision,
            transition_mutation(second_base, message_id="request-2"),
        )

    assert raised.value.code == "REVISION_CONFLICT"
    assert second.load("m-1").mission.revision == 1
    first.close()
    second.close()


def test_canonical_entities_are_queryable_in_normalized_tables(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime.db"
    repo = SQLiteRuntimeRepository(path)
    snapshot = runtime_snapshot()
    snapshot.work_items.append(
        WorkItem(
            work_item_id="work-1",
            mission_id="m-1",
            work_type="SECURITY_REVIEW",
        )
    )
    snapshot.commitments.append(
        Commitment(
            commitment_id="commitment-1",
            mission_id="m-1",
            work_item_id="work-1",
            event_type="vendor.document.uploaded",
            predicate={"document_type": "PEN_TEST"},
        )
    )
    repo.create(snapshot)
    repo.close()

    connection = sqlite3.connect(path)
    work_row = connection.execute(
        "SELECT status, work_type FROM work_items WHERE work_item_id = ?",
        ("work-1",),
    ).fetchone()
    commitment_row = connection.execute(
        "SELECT status, event_type FROM commitments WHERE commitment_id = ?",
        ("commitment-1",),
    ).fetchone()
    connection.close()

    assert work_row == ("PENDING", "SECURITY_REVIEW")
    assert commitment_row == ("OPEN", "vendor.document.uploaded")
