from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import GraphSnapshot


def utc_now() -> datetime:
    return datetime.now(UTC)


class MissionStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    REVALIDATING = "REVALIDATING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkStatus(StrEnum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    WAITING = "WAITING"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CommitmentStatus(StrEnum):
    OPEN = "OPEN"
    SATISFIED = "SATISFIED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class SideEffectStatus(StrEnum):
    INTENDED = "INTENDED"
    EXECUTING = "EXECUTING"
    COMMITTED = "COMMITTED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FINAL = "FAILED_FINAL"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class Mission(BaseModel):
    mission_id: str
    mission_type: str = "VENDOR_ONBOARDING"
    subject_id: str = "ACME"
    status: MissionStatus = MissionStatus.CREATED
    revision: int = Field(default=0, ge=0)
    event_sequence: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WorkItem(BaseModel):
    work_item_id: str
    mission_id: str
    work_type: str
    target_agent: str | None = None
    status: WorkStatus = WorkStatus.PENDING
    attempt: int = Field(default=0, ge=0)
    input_refs: list[str] = Field(default_factory=list)
    commitment_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Commitment(BaseModel):
    commitment_id: str
    mission_id: str
    work_item_id: str
    event_type: str
    predicate: dict[str, str]
    status: CommitmentStatus = CommitmentStatus.OPEN
    satisfied_by_event_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    satisfied_at: datetime | None = None


class SideEffectRecord(BaseModel):
    side_effect_id: str
    mission_id: str
    effect_type: str
    idempotency_key: str
    authorization_decision_id: str
    status: SideEffectStatus = SideEffectStatus.INTENDED
    request: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AuditEvent(BaseModel):
    audit_event_id: str
    mission_id: str
    event_sequence: int = Field(ge=1)
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str
    causation_id: str
    trace_id: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now)


class InboxRecord(BaseModel):
    mission_id: str
    message_id: str
    message_type: str
    result: dict[str, Any] = Field(default_factory=dict)
    processed_at: datetime = Field(default_factory=utc_now)


class OutboxMessage(BaseModel):
    outbox_message_id: str
    mission_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str
    causation_id: str
    trace_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    published_at: datetime | None = None


class RuntimeSnapshot(BaseModel):
    mission: Mission
    graph: GraphSnapshot
    work_items: list[WorkItem] = Field(default_factory=list)
    commitments: list[Commitment] = Field(default_factory=list)
    side_effects: list[SideEffectRecord] = Field(default_factory=list)
    inbox: list[InboxRecord] = Field(default_factory=list)
    outbox: list[OutboxMessage] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)
