from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.compiler.context import RiskClass
from app.compiler.models import CompilationDisposition, CompilationResult, DecisionDraft


class CompilationState(StrEnum):
    REQUESTED = "REQUESTED"
    DRAFT_RECEIVED = "DRAFT_RECEIVED"
    COMPILED = "COMPILED"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CompilationRequestRecord(FrozenModel):
    request_id: str = Field(min_length=1, max_length=256)
    mission_id: str = Field(min_length=1, max_length=256)
    work_item_id: str = Field(min_length=1, max_length=256)
    agent_id: str = Field(min_length=1, max_length=256)
    world_snapshot_id: str = Field(min_length=1, max_length=256)
    expected_mission_revision: int = Field(ge=0)
    decision_type: str = Field(min_length=1, max_length=128)
    risk_class: RiskClass
    owner_scope: str = Field(min_length=1, max_length=256)
    allowed_source_refs: list[str] = Field(min_length=1, max_length=500)
    allow_historical: bool = False
    created_at: datetime

    @field_validator("allowed_source_refs")
    @classmethod
    def _unique_allowed_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or value != value.strip() for value in values):
            raise ValueError("allowed source refs must be trimmed")
        if len(values) != len(set(values)):
            raise ValueError("allowed source refs must be unique")
        return values


class CompilerOutboxEvent(FrozenModel):
    event_id: str = Field(min_length=1, max_length=512)
    request_id: str = Field(min_length=1, max_length=256)
    mission_id: str = Field(min_length=1, max_length=256)
    event_type: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CompilationAggregate(FrozenModel):
    request: CompilationRequestRecord
    state: CompilationState
    draft: DecisionDraft | None = None
    result: CompilationResult | None = None
    outbox: list[CompilerOutboxEvent] = Field(default_factory=list)
    updated_at: datetime


class CompilerRepositoryError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class CompilerRepository(Protocol):
    def create_request(
        self,
        request: CompilationRequestRecord,
    ) -> CompilationAggregate: ...

    def put_draft(
        self,
        request_id: str,
        draft: DecisionDraft,
    ) -> CompilationAggregate: ...

    def put_result(
        self,
        request_id: str,
        result: CompilationResult,
    ) -> CompilationAggregate: ...

    def get(self, request_id: str) -> CompilationAggregate: ...

    def list_recent(self, limit: int) -> list[CompilationAggregate]: ...


def create_aggregate(request: CompilationRequestRecord) -> CompilationAggregate:
    return CompilationAggregate(
        request=request,
        state=CompilationState.REQUESTED,
        outbox=[
            _event(
                request,
                sequence=1,
                event_type="compiler.requested",
                payload={"world_snapshot_id": request.world_snapshot_id},
                created_at=request.created_at,
            )
        ],
        updated_at=request.created_at,
    )


def add_draft(
    aggregate: CompilationAggregate,
    draft: DecisionDraft,
) -> CompilationAggregate:
    if draft.request_id != aggregate.request.request_id:
        raise CompilerRepositoryError(
            "COMPILATION_DRAFT_CONFLICT",
            "draft request_id does not match compilation request",
        )
    if aggregate.draft is not None:
        if aggregate.draft == draft:
            return aggregate
        raise CompilerRepositoryError(
            "COMPILATION_DRAFT_CONFLICT",
            "an immutable draft already exists for the request",
        )
    if aggregate.state is not CompilationState.REQUESTED:
        raise CompilerRepositoryError(
            "COMPILATION_STATE_CONFLICT",
            f"cannot attach draft in state {aggregate.state}",
        )
    now = datetime.now(UTC)
    return aggregate.model_copy(
        update={
            "state": CompilationState.DRAFT_RECEIVED,
            "draft": draft,
            "outbox": [
                *aggregate.outbox,
                _event(
                    aggregate.request,
                    sequence=len(aggregate.outbox) + 1,
                    event_type="compiler.draft.received",
                    payload={"model_provider": draft.model_metadata.provider},
                    created_at=now,
                ),
            ],
            "updated_at": now,
        },
        deep=True,
    )


def add_result(
    aggregate: CompilationAggregate,
    result: CompilationResult,
) -> CompilationAggregate:
    if result.request_id != aggregate.request.request_id:
        raise CompilerRepositoryError(
            "COMPILATION_RESULT_CONFLICT",
            "result request_id does not match compilation request",
        )
    if aggregate.result is not None:
        if aggregate.result == result:
            return aggregate
        raise CompilerRepositoryError(
            "COMPILATION_RESULT_CONFLICT",
            "an immutable result already exists for the request",
        )
    if aggregate.state is not CompilationState.DRAFT_RECEIVED:
        raise CompilerRepositoryError(
            "COMPILATION_STATE_CONFLICT",
            f"cannot attach result in state {aggregate.state}",
        )
    event_type = _result_event_type(result.status)
    now = datetime.now(UTC)
    return aggregate.model_copy(
        update={
            "state": CompilationState.COMPILED,
            "result": result,
            "outbox": [
                *aggregate.outbox,
                _event(
                    aggregate.request,
                    sequence=len(aggregate.outbox) + 1,
                    event_type=event_type,
                    payload={
                        "status": result.status.value,
                        "compilation_id": result.compilation_id,
                    },
                    created_at=now,
                ),
            ],
            "updated_at": now,
        },
        deep=True,
    )


def _event(
    request: CompilationRequestRecord,
    *,
    sequence: int,
    event_type: str,
    payload: dict[str, Any],
    created_at: datetime,
) -> CompilerOutboxEvent:
    return CompilerOutboxEvent(
        event_id=f"compiler-outbox:{request.request_id}:{sequence}",
        request_id=request.request_id,
        mission_id=request.mission_id,
        event_type=event_type,
        payload=payload,
        created_at=created_at,
    )


def _result_event_type(status: CompilationDisposition) -> str:
    if status is CompilationDisposition.ACCEPTED:
        return "compiler.accepted"
    if status is CompilationDisposition.NEEDS_HUMAN_REVIEW:
        return "compiler.review.required"
    return "compiler.rejected"


__all__ = [
    "CompilationAggregate",
    "CompilationRequestRecord",
    "CompilationState",
    "CompilerOutboxEvent",
    "CompilerRepository",
    "CompilerRepositoryError",
]
