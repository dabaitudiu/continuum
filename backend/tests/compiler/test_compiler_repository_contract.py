from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import pytest

from app.compiler.models import CompilationDisposition, CompilationResult, DecisionDraft
from app.compiler.repository import (
    CompilationRequestRecord,
    CompilationState,
    CompilerRepositoryError,
)
from app.compiler.repository_firestore import FirestoreCompilerRepository
from app.compiler.repository_memory import InMemoryCompilerRepository
from app.compiler.repository_sqlite import SQLiteCompilerRepository


NOW = datetime(2026, 8, 19, 18, 0, tzinfo=UTC)


def _request(
    request_id: str = "request-1",
    *,
    created_at: datetime = NOW,
) -> CompilationRequestRecord:
    return CompilationRequestRecord(
        request_id=request_id,
        mission_id="mission-1",
        work_item_id="work-1",
        agent_id="security-agent",
        world_snapshot_id="world-13",
        expected_mission_revision=7,
        decision_type="PRIVILEGED_ACCESS_REVIEW",
        risk_class="HIGH",
        owner_scope="tenant:alpha",
        allowed_source_refs=["policy:access@v13!rep-v13#section/training"],
        created_at=created_at,
    )


def _draft(request_id: str = "request-1") -> DecisionDraft:
    return DecisionDraft.model_validate(
        {
            "request_id": request_id,
            "decision_type": "PRIVILEGED_ACCESS_REVIEW",
            "proposed_outcome": "APPROVED",
            "claims": [],
            "decision_dependencies": [],
            "unresolved_questions": [],
            "rationale_summary": "The evidence was reviewed.",
            "model_metadata": {
                "provider": "OPENAI",
                "model_name": "gpt-5.6-luna",
                "prompt_version": "reasoner-v1",
                "temperature": 0.0,
                "execution_id": "execution-1:reasoner:1",
            },
        }
    )


def _result(
    request_id: str = "request-1",
    *,
    status: CompilationDisposition = CompilationDisposition.ACCEPTED,
) -> CompilationResult:
    accepted = status is CompilationDisposition.ACCEPTED
    return CompilationResult(
        compilation_id=f"compilation:{request_id}",
        request_id=request_id,
        status=status,
        decision_candidate=(
            {
                "decision_id": f"decision:{request_id}",
                "decision_type": "PRIVILEGED_ACCESS_REVIEW",
                "outcome": "APPROVED",
                "rationale_summary": "The evidence was reviewed.",
            }
            if accepted
            else None
        ),
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
        compilation_hash="a" * 64 if accepted else None,
    )


class FakeDocumentSnapshot:
    def __init__(self, data: dict[str, Any] | None, document_id: str = "") -> None:
        self.exists = data is not None
        self.id = document_id
        self._data = deepcopy(data)

    def to_dict(self) -> dict[str, Any] | None:
        return deepcopy(self._data)


class FakeDocumentReference:
    def __init__(self, client: "FakeFirestoreClient", path: str) -> None:
        self.client = client
        self.path = path

    def collection(self, name: str) -> "FakeCollectionReference":
        return FakeCollectionReference(self.client, f"{self.path}/{name}")


class FakeCollectionReference:
    def __init__(self, client: "FakeFirestoreClient", path: str) -> None:
        self.client = client
        self.path = path

    def document(self, document_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self.client, f"{self.path}/{document_id}")

    def order_by(self, field: str, *, direction: Any) -> "FakeQuery":
        return FakeQuery(self.client, self.path, field)


class FakeQuery:
    def __init__(self, client: "FakeFirestoreClient", path: str, field: str) -> None:
        self.client = client
        self.path = path
        self.field = field
        self.count = 20

    def limit(self, value: int) -> "FakeQuery":
        self.count = value
        return self

    def stream(self) -> list[FakeDocumentSnapshot]:
        prefix = f"{self.path}/"
        rows = [
            (path.removeprefix(prefix), data)
            for path, data in self.client.documents.items()
            if path.startswith(prefix) and "/" not in path.removeprefix(prefix)
        ]
        rows.sort(key=lambda row: (row[1][self.field], row[0]), reverse=True)
        return [
            FakeDocumentSnapshot(data, document_id)
            for document_id, data in rows[: self.count]
        ]


class FakeTransaction:
    def __init__(self, client: "FakeFirestoreClient") -> None:
        self.client = client
        self.writes: list[tuple[str, str, dict[str, Any]]] = []

    def get(self, reference: FakeDocumentReference) -> FakeDocumentSnapshot:
        return FakeDocumentSnapshot(self.client.documents.get(reference.path))

    def create(self, reference: FakeDocumentReference, data: dict[str, Any]) -> None:
        if reference.path in self.client.documents:
            raise CompilerRepositoryError("COMPILATION_REQUEST_CONFLICT", "exists")
        self.writes.append(("create", reference.path, deepcopy(data)))

    def set(self, reference: FakeDocumentReference, data: dict[str, Any]) -> None:
        self.writes.append(("set", reference.path, deepcopy(data)))

    def commit(self) -> None:
        for operation, path, data in self.writes:
            if operation == "create" and path in self.client.documents:
                raise CompilerRepositoryError("COMPILATION_REQUEST_CONFLICT", "exists")
            self.client.documents[path] = deepcopy(data)


class FakeFirestoreClient:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}

    def collection(self, name: str) -> FakeCollectionReference:
        return FakeCollectionReference(self, name)

    def run_transaction(self, callback: Callable[[FakeTransaction], Any]) -> Any:
        transaction = FakeTransaction(self)
        result = callback(transaction)
        transaction.commit()
        return result


@pytest.fixture(params=("memory", "sqlite", "firestore"))
def repository(request, tmp_path: Path):  # type: ignore[no-untyped-def]
    if request.param == "memory":
        yield InMemoryCompilerRepository()
    elif request.param == "sqlite":
        repo = SQLiteCompilerRepository(tmp_path / "compiler.db")
        yield repo
        repo.close()
    else:
        client = FakeFirestoreClient()
        yield FirestoreCompilerRepository(
            client,
            transaction_runner=client.run_transaction,
        )


def test_request_draft_result_are_immutable_and_copy_isolated(repository) -> None:  # type: ignore[no-untyped-def]
    request = _request()
    created = repository.create_request(request)
    with_draft = repository.put_draft(request.request_id, _draft())
    completed = repository.put_result(request.request_id, _result())

    created.request.allowed_source_refs.append("tampered")
    with_draft.draft.claims.append({})  # type: ignore[arg-type]
    completed.result.canonical_edges.append({})  # type: ignore[union-attr,arg-type]
    loaded = repository.get(request.request_id)

    assert loaded.state is CompilationState.COMPILED
    assert loaded.request.allowed_source_refs == [
        "policy:access@v13!rep-v13#section/training"
    ]
    assert loaded.draft is not None and loaded.draft.claims == []
    assert loaded.result is not None and loaded.result.canonical_edges == []


def test_duplicate_identical_writes_are_idempotent_without_duplicate_events(
    repository,
) -> None:  # type: ignore[no-untyped-def]
    request = _request()
    first = repository.create_request(request)
    second = repository.create_request(request)
    repository.put_draft(request.request_id, _draft())
    repository.put_draft(request.request_id, _draft())
    repository.put_result(request.request_id, _result())
    final = repository.put_result(request.request_id, _result())

    assert first == second
    assert [event.event_type for event in final.outbox] == [
        "compiler.requested",
        "compiler.draft.received",
        "compiler.accepted",
    ]


def test_conflicting_duplicate_and_out_of_order_writes_are_rejected(repository) -> None:  # type: ignore[no-untyped-def]
    repository.create_request(_request())

    with pytest.raises(CompilerRepositoryError) as out_of_order:
        repository.put_result("request-1", _result())
    with pytest.raises(CompilerRepositoryError) as conflicting_request:
        repository.create_request(
            _request().model_copy(update={"mission_id": "different"})
        )
    repository.put_draft("request-1", _draft())
    with pytest.raises(CompilerRepositoryError) as conflicting_draft:
        repository.put_draft(
            "request-1",
            _draft().model_copy(update={"proposed_outcome": "DENIED"}),
        )

    assert out_of_order.value.code == "COMPILATION_STATE_CONFLICT"
    assert conflicting_request.value.code == "COMPILATION_REQUEST_CONFLICT"
    assert conflicting_draft.value.code == "COMPILATION_DRAFT_CONFLICT"


@pytest.mark.parametrize(
    ("status", "event_type"),
    [
        (CompilationDisposition.ACCEPTED, "compiler.accepted"),
        (CompilationDisposition.NEEDS_HUMAN_REVIEW, "compiler.review.required"),
        (CompilationDisposition.REJECTED_SCHEMA, "compiler.rejected"),
    ],
)
def test_result_disposition_selects_auditable_outbox_event(
    repository,
    status: CompilationDisposition,
    event_type: str,
) -> None:  # type: ignore[no-untyped-def]
    repository.create_request(_request())
    repository.put_draft("request-1", _draft())

    aggregate = repository.put_result("request-1", _result(status=status))

    assert aggregate.outbox[-1].event_type == event_type
    assert aggregate.outbox[-1].payload["status"] == status.value


def test_recent_query_is_ordered_limited_and_returns_aggregates(repository) -> None:  # type: ignore[no-untyped-def]
    for index in range(3):
        repository.create_request(
            _request(
                f"request-{index}",
                created_at=NOW + timedelta(minutes=index),
            )
        )

    recent = repository.list_recent(2)

    assert [item.request.request_id for item in recent] == [
        "request-2",
        "request-1",
    ]


def test_unknown_request_is_a_structured_error(repository) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CompilerRepositoryError) as raised:
        repository.get("missing")

    assert raised.value.code == "COMPILATION_REQUEST_NOT_FOUND"
