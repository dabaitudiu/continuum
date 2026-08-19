from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.repository.runtime_firestore import FirestoreRuntimeRepository
from app.runtime.entities import Commitment, OutboxMessage, WorkItem
from app.runtime.errors import RuntimeDomainError
from tests.repository.runtime_contract import (
    RuntimeRepositoryContract,
    runtime_snapshot,
    transition_mutation,
)


class FakeDocumentSnapshot:
    def __init__(
        self,
        data: dict[str, Any] | None,
        document_id: str = "",
    ) -> None:
        self.exists = data is not None
        self.id = document_id
        self._data = deepcopy(data)

    def to_dict(self) -> dict[str, Any] | None:
        return deepcopy(self._data)


class FakeDocumentReference:
    def __init__(self, client: FakeFirestoreClient, path: str) -> None:
        self._client = client
        self.path = path

    def collection(self, name: str) -> FakeCollectionReference:
        return FakeCollectionReference(self._client, f"{self.path}/{name}")


class FakeCollectionReference:
    def __init__(self, client: FakeFirestoreClient, path: str) -> None:
        self._client = client
        self.path = path

    def document(self, document_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self._client, f"{self.path}/{document_id}")

    def order_by(self, field: str, *, direction: Any) -> FakeQuery:
        return FakeQuery(self._client, self.path).order_by(
            field,
            direction=direction,
        )

    def where(self, *, filter: Any) -> FakeQuery:
        return FakeQuery(self._client, self.path).where(filter=filter)


class FakeQuery:
    def __init__(self, client: FakeFirestoreClient, path: str) -> None:
        self._client = client
        self._path = path
        self._field = "mission_id"
        self._descending = False
        self._filter: tuple[str, str, Any] | None = None
        self._after: dict[str, Any] | None = None
        self._limit = 20

    def where(self, *, filter: Any) -> FakeQuery:
        self._filter = (
            str(filter.field_path),
            str(filter.op_string),
            filter.value,
        )
        return self

    def order_by(self, field: str, *, direction: Any) -> FakeQuery:
        self._field = field
        self._descending = direction == "DESCENDING"
        return self

    def start_after(self, values: dict[str, Any]) -> FakeQuery:
        self._after = values
        return self

    def limit(self, value: int) -> FakeQuery:
        self._limit = value
        return self

    def stream(self) -> list[FakeDocumentSnapshot]:
        prefix = f"{self._path}/"
        documents = [
            (path.removeprefix(prefix), data)
            for path, data in self._client._documents.items()
            if path.startswith(prefix) and "/" not in path.removeprefix(prefix)
        ]
        if self._filter is not None:
            field, operation, value = self._filter
            if operation == "==":
                documents = [item for item in documents if item[1].get(field) == value]
            elif operation == "<":
                documents = [
                    item
                    for item in documents
                    if item[1].get(field) is not None and item[1][field] < value
                ]
            else:
                raise AssertionError(f"unsupported fake filter: {operation}")
        if self._after is not None:
            after = self._after[self._field]
            documents = [item for item in documents if item[1][self._field] > after]
        documents.sort(
            key=lambda item: (item[1][self._field], item[0]),
            reverse=self._descending,
        )
        return [
            FakeDocumentSnapshot(data, document_id)
            for document_id, data in documents[: self._limit]
        ]


class FakeTransaction:
    def __init__(self, client: FakeFirestoreClient) -> None:
        self._client = client
        self._writes: list[tuple[str, str, dict[str, Any]]] = []

    def get(self, reference: FakeDocumentReference) -> FakeDocumentSnapshot:
        return FakeDocumentSnapshot(self._client._documents.get(reference.path))

    def create(
        self,
        reference: FakeDocumentReference,
        data: dict[str, Any],
    ) -> None:
        if reference.path in self._client._documents:
            raise RuntimeDomainError("PERSISTENCE_CONFLICT", "document exists")
        self._writes.append(("create", reference.path, deepcopy(data)))

    def set(
        self,
        reference: FakeDocumentReference,
        data: dict[str, Any],
    ) -> None:
        self._writes.append(("set", reference.path, deepcopy(data)))

    def commit(self) -> None:
        for operation, path, data in self._writes:
            if operation == "create" and path in self._client._documents:
                raise RuntimeDomainError("PERSISTENCE_CONFLICT", "document exists")
            self._client._documents[path] = deepcopy(data)


class FakeFirestoreClient:
    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}

    def collection(self, name: str) -> FakeCollectionReference:
        return FakeCollectionReference(self, name)

    def run_transaction(self, callback: Callable[[FakeTransaction], Any]) -> Any:
        transaction = FakeTransaction(self)
        result = callback(transaction)
        transaction.commit()
        return result

    def read(self, path: str) -> dict[str, Any] | None:
        return deepcopy(self._documents.get(path))


def make_repository(client: FakeFirestoreClient) -> FirestoreRuntimeRepository:
    return FirestoreRuntimeRepository(
        client,
        transaction_runner=client.run_transaction,
    )


class TestFirestoreRuntimeRepository(RuntimeRepositoryContract):
    def make_repo(self, tmp_path: Path) -> FirestoreRuntimeRepository:
        return make_repository(FakeFirestoreClient())


def test_new_repository_instance_recovers_complete_snapshot() -> None:
    client = FakeFirestoreClient()
    first = make_repository(client)
    first.create(runtime_snapshot())
    initial = first.load("m-1")
    expected = first.commit(
        "m-1",
        initial.mission.revision,
        transition_mutation(initial, message_id="request-1"),
    )

    second = make_repository(client)

    assert second.load("m-1") == expected


def test_expected_revision_is_checked_inside_transaction() -> None:
    client = FakeFirestoreClient()
    first = make_repository(client)
    second = make_repository(client)
    first.create(runtime_snapshot())
    first_base = first.load("m-1")
    second_base = second.load("m-1")
    first.commit(
        "m-1",
        first_base.mission.revision,
        transition_mutation(first_base, message_id="request-1"),
    )

    try:
        second.commit(
            "m-1",
            second_base.mission.revision,
            transition_mutation(second_base, message_id="request-2"),
        )
    except RuntimeDomainError as error:
        assert error.code == "REVISION_CONFLICT"
    else:
        raise AssertionError("stale Firestore transaction should fail")


def test_canonical_entities_are_projected_to_queryable_subcollections() -> None:
    client = FakeFirestoreClient()
    repository = make_repository(client)
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

    repository.create(snapshot)

    work = client.read("missions/m-1/work_items/work-1")
    commitment = client.read("missions/m-1/commitments/commitment-1")
    assert work is not None and work["status"] == "PENDING"
    assert commitment is not None and commitment["status"] == "OPEN"


def test_legacy_pending_outbox_projection_is_backfilled_before_sweep() -> None:
    client = FakeFirestoreClient()
    repository = make_repository(client)
    snapshot = runtime_snapshot("m-legacy")
    snapshot.outbox = [
        OutboxMessage(
            outbox_message_id="outbox:legacy",
            mission_id="m-legacy",
            event_type="mission.created",
            correlation_id="create:legacy",
            causation_id="create:legacy",
        )
    ]
    repository.create(snapshot)
    legacy = client._documents["missions/m-legacy"]
    legacy["schema_version"] = 1
    legacy.pop("has_unpublished_outbox")

    assert repository.list_pending_outbox(limit=10) == []

    migrated = repository.ensure_outbox_projection_schema(batch_size=1)

    assert migrated == 1
    assert client.read("missions/m-legacy")["schema_version"] == 2
    assert [
        item.mission.mission_id for item in repository.list_pending_outbox(limit=10)
    ] == ["m-legacy"]
