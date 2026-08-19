from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from google.cloud import firestore

from app.compiler.models import CompilationResult, DecisionDraft
from app.compiler.repository import (
    CompilationAggregate,
    CompilationRequestRecord,
    CompilerRepositoryError,
    add_draft,
    add_result,
    create_aggregate,
)


Result = TypeVar("Result")


class TransactionRunner(Protocol):
    def __call__(self, callback: Callable[[Any], Result]) -> Result: ...


class FirestoreCompilerRepository:
    store_kind = "firestore"

    def __init__(
        self,
        client: Any,
        *,
        collection: str = "compiler_requests",
        transaction_runner: TransactionRunner | None = None,
    ) -> None:
        self._client = client
        self._requests = client.collection(collection)
        self._transaction_runner = transaction_runner or self._run_transaction

    @classmethod
    def from_environment(
        cls,
        *,
        project: str | None = None,
        database: str | None = None,
        collection: str = "compiler_requests",
    ) -> "FirestoreCompilerRepository":
        options: dict[str, str] = {}
        if project:
            options["project"] = project
        if database:
            options["database"] = database
        return cls(firestore.Client(**options), collection=collection)

    def create_request(
        self,
        request: CompilationRequestRecord,
    ) -> CompilationAggregate:
        reference = self._requests.document(request.request_id)

        def create(transaction: Any) -> CompilationAggregate:
            document = _transaction_get(transaction, reference)
            if document.exists:
                existing = _from_document(request.request_id, document)
                if existing.request == request:
                    return existing
                raise CompilerRepositoryError(
                    "COMPILATION_REQUEST_CONFLICT",
                    "request_id already identifies a different request",
                )
            aggregate = create_aggregate(request)
            transaction.create(reference, _document(aggregate))
            _project_outbox(transaction, reference, aggregate)
            return aggregate

        return self._transaction_runner(create).model_copy(deep=True)

    def put_draft(
        self,
        request_id: str,
        draft: DecisionDraft,
    ) -> CompilationAggregate:
        return self._transition(request_id, lambda value: add_draft(value, draft))

    def put_result(
        self,
        request_id: str,
        result: CompilationResult,
    ) -> CompilationAggregate:
        return self._transition(request_id, lambda value: add_result(value, result))

    def get(self, request_id: str) -> CompilationAggregate:
        reference = self._requests.document(request_id)

        def get(transaction: Any) -> CompilationAggregate:
            return _from_document(request_id, _transaction_get(transaction, reference))

        return self._transaction_runner(get).model_copy(deep=True)

    def list_recent(self, limit: int) -> list[CompilationAggregate]:
        if limit < 1:
            raise ValueError("limit must be positive")
        documents = (
            self._requests.order_by(
                "created_at",
                direction=firestore.Query.DESCENDING,
            )
            .limit(limit)
            .stream()
        )
        return [
            _from_document(document.id, document).model_copy(deep=True)
            for document in documents
        ]

    def _transition(self, request_id, transition):  # type: ignore[no-untyped-def]
        reference = self._requests.document(request_id)

        def update(transaction: Any) -> CompilationAggregate:
            current = _from_document(
                request_id,
                _transaction_get(transaction, reference),
            )
            updated = transition(current)
            if updated != current:
                transaction.set(reference, _document(updated))
                _project_outbox(transaction, reference, updated)
            return updated

        return self._transaction_runner(update).model_copy(deep=True)

    def _run_transaction(self, callback: Callable[[Any], Result]) -> Result:
        transaction = self._client.transaction()

        @firestore.transactional
        def execute(active_transaction: Any) -> Result:
            return callback(active_transaction)

        return execute(transaction)


def _transaction_get(transaction: Any, reference: Any) -> Any:
    result = transaction.get(reference)
    return result if hasattr(result, "exists") else next(iter(result))


def _from_document(request_id: str, document: Any) -> CompilationAggregate:
    if not document.exists:
        raise CompilerRepositoryError(
            "COMPILATION_REQUEST_NOT_FOUND",
            f"compilation request does not exist: {request_id}",
        )
    data = document.to_dict() or {}
    payload = data.get("aggregate_json")
    if not isinstance(payload, str):
        raise CompilerRepositoryError(
            "COMPILATION_PERSISTENCE_CORRUPT",
            f"compiler aggregate is missing: {request_id}",
        )
    return CompilationAggregate.model_validate_json(payload)


def _document(aggregate: CompilationAggregate) -> dict[str, Any]:
    return {
        "request_id": aggregate.request.request_id,
        "mission_id": aggregate.request.mission_id,
        "state": aggregate.state.value,
        "created_at": aggregate.request.created_at,
        "updated_at": aggregate.updated_at,
        "aggregate_json": aggregate.model_dump_json(),
    }


def _project_outbox(
    transaction: Any,
    reference: Any,
    aggregate: CompilationAggregate,
) -> None:
    for event in aggregate.outbox:
        transaction.set(
            reference.collection("outbox").document(event.event_id),
            event.model_dump(mode="python"),
        )
