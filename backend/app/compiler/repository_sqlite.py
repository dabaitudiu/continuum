from __future__ import annotations

import sqlite3
from pathlib import Path
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


SCHEMA = """
CREATE TABLE IF NOT EXISTS compiler_requests (
    request_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    state TEXT NOT NULL,
    aggregate_json TEXT NOT NULL
);
"""


class SQLiteCompilerRepository:
    store_kind = "sqlite"

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self._path,
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA)
        self._lock = RLock()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def create_request(
        self,
        request: CompilationRequestRecord,
    ) -> CompilationAggregate:
        with self._transaction():
            existing = self._load_optional(request.request_id)
            if existing is not None:
                if existing.request == request:
                    return existing
                raise CompilerRepositoryError(
                    "COMPILATION_REQUEST_CONFLICT",
                    "request_id already identifies a different request",
                )
            aggregate = create_aggregate(request)
            self._connection.execute(
                "INSERT INTO compiler_requests VALUES (?, ?, ?, ?)",
                (
                    request.request_id,
                    request.created_at.isoformat(),
                    aggregate.state.value,
                    aggregate.model_dump_json(),
                ),
            )
            return aggregate.model_copy(deep=True)

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
        with self._lock:
            return self._require(request_id).model_copy(deep=True)

    def list_recent(self, limit: int) -> list[CompilationAggregate]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT aggregate_json FROM compiler_requests
                ORDER BY created_at DESC, request_id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                CompilationAggregate.model_validate_json(row[0])
                for row in rows
            ]

    def _transition(self, request_id, transition):  # type: ignore[no-untyped-def]
        with self._transaction():
            current = self._require(request_id)
            updated = transition(current)
            if updated != current:
                self._connection.execute(
                    """
                    UPDATE compiler_requests SET state = ?, aggregate_json = ?
                    WHERE request_id = ?
                    """,
                    (updated.state.value, updated.model_dump_json(), request_id),
                )
            return updated.model_copy(deep=True)

    def _require(self, request_id: str) -> CompilationAggregate:
        value = self._load_optional(request_id)
        if value is None:
            raise CompilerRepositoryError(
                "COMPILATION_REQUEST_NOT_FOUND",
                f"compilation request does not exist: {request_id}",
            )
        return value

    def _load_optional(self, request_id: str) -> CompilationAggregate | None:
        row = self._connection.execute(
            "SELECT aggregate_json FROM compiler_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        return (
            None
            if row is None
            else CompilationAggregate.model_validate_json(row[0])
        )

    def _transaction(self):  # type: ignore[no-untyped-def]
        return _SQLiteTransaction(self._connection, self._lock)


class _SQLiteTransaction:
    def __init__(self, connection: sqlite3.Connection, lock: RLock) -> None:
        self.connection = connection
        self.lock = lock

    def __enter__(self) -> None:
        self.lock.acquire()
        self.connection.execute("BEGIN IMMEDIATE")

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore[no-untyped-def]
        try:
            self.connection.execute("COMMIT" if exc_type is None else "ROLLBACK")
        finally:
            self.lock.release()
