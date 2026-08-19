from __future__ import annotations

from threading import RLock

from app.compiler.models import CompilationResult, DecisionDraft
from app.compiler.repository import (
    CompilationAggregate,
    CompilationRequestRecord,
    CompilerRepositoryError,
    add_draft,
    add_result,
    create_aggregate,
)


class InMemoryCompilerRepository:
    store_kind = "memory"

    def __init__(self) -> None:
        self._aggregates: dict[str, CompilationAggregate] = {}
        self._lock = RLock()

    def create_request(
        self,
        request: CompilationRequestRecord,
    ) -> CompilationAggregate:
        with self._lock:
            existing = self._aggregates.get(request.request_id)
            if existing is not None:
                if existing.request == request:
                    return existing.model_copy(deep=True)
                raise CompilerRepositoryError(
                    "COMPILATION_REQUEST_CONFLICT",
                    "request_id already identifies a different request",
                )
            aggregate = create_aggregate(request)
            self._aggregates[request.request_id] = aggregate
            return aggregate.model_copy(deep=True)

    def put_draft(
        self,
        request_id: str,
        draft: DecisionDraft,
    ) -> CompilationAggregate:
        with self._lock:
            aggregate = add_draft(self._require(request_id), draft)
            self._aggregates[request_id] = aggregate
            return aggregate.model_copy(deep=True)

    def put_result(
        self,
        request_id: str,
        result: CompilationResult,
    ) -> CompilationAggregate:
        with self._lock:
            aggregate = add_result(self._require(request_id), result)
            self._aggregates[request_id] = aggregate
            return aggregate.model_copy(deep=True)

    def get(self, request_id: str) -> CompilationAggregate:
        with self._lock:
            return self._require(request_id).model_copy(deep=True)

    def list_recent(self, limit: int) -> list[CompilationAggregate]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            values = sorted(
                self._aggregates.values(),
                key=lambda aggregate: (
                    aggregate.request.created_at,
                    aggregate.request.request_id,
                ),
                reverse=True,
            )[:limit]
            return [value.model_copy(deep=True) for value in values]

    def _require(self, request_id: str) -> CompilationAggregate:
        try:
            return self._aggregates[request_id]
        except KeyError as error:
            raise CompilerRepositoryError(
                "COMPILATION_REQUEST_NOT_FOUND",
                f"compilation request does not exist: {request_id}",
            ) from error
