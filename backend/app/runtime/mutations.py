from pydantic import BaseModel, Field

from app.domain.models import GraphSnapshot
from app.runtime.entities import (
    AuditEvent,
    Commitment,
    InboxRecord,
    Mission,
    OutboxMessage,
    SideEffectRecord,
    WorkItem,
)


class RuntimeMutation(BaseModel):
    mission: Mission
    work_upserts: list[WorkItem] = Field(default_factory=list)
    commitment_upserts: list[Commitment] = Field(default_factory=list)
    side_effect_upserts: list[SideEffectRecord] = Field(default_factory=list)
    graph: GraphSnapshot | None = None
    audit_appends: list[AuditEvent] = Field(default_factory=list)
    inbox_completion: InboxRecord
    outbox_appends: list[OutboxMessage] = Field(default_factory=list)
