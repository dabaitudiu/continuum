from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ArtifactStatus(StrEnum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"


class EvidenceStatus(StrEnum):
    VALID = "VALID"


class DecisionStatus(StrEnum):
    VALID = "VALID"
    STALE = "STALE"
    REVALIDATING = "REVALIDATING"
    INVALID = "INVALID"
    SUPERSEDED = "SUPERSEDED"


class ActionStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class RelationType(StrEnum):
    SUPPORTED_BY = "SUPPORTED_BY"
    GOVERNED_BY = "GOVERNED_BY"
    DERIVED_FROM = "DERIVED_FROM"
    REQUIRES = "REQUIRES"
    AUTHORIZES = "AUTHORIZES"
    CONTRADICTED_BY = "CONTRADICTED_BY"


class WorldArtifact(BaseModel):
    artifact_id: str
    artifact_type: str
    logical_key: str
    version: str
    supersedes_artifact_id: str | None = None
    status: ArtifactStatus = ArtifactStatus.CURRENT


class EvidenceNode(BaseModel):
    evidence_id: str
    kind: str
    revision: str
    artifact_id: str | None = None
    source_ref: str | None = None
    status: EvidenceStatus = EvidenceStatus.VALID


class ClaimNode(BaseModel):
    claim_id: str
    claim_type: str
    statement: str
    materiality: str
    confidence: float = Field(ge=0.0, le=1.0)
    compilation_id: str


class DecisionNode(BaseModel):
    decision_id: str
    decision_type: str
    outcome: str
    status: DecisionStatus = DecisionStatus.VALID
    supersedes_decision_id: str | None = None
    execution_count: int = Field(default=1, ge=0)
    compilation_id: str | None = None
    compilation_hash: str | None = None
    world_snapshot_id: str | None = None


class ActionNode(BaseModel):
    action_id: str
    action_type: str
    status: ActionStatus = ActionStatus.READY


class DependencyEdge(BaseModel):
    edge_id: str
    from_node_id: str
    to_node_id: str
    relation_type: RelationType
    critical: bool = True


class DomainEvent(BaseModel):
    event_id: str
    event_type: str
    payload: dict[str, str]


class DispatchRecord(BaseModel):
    dispatch_id: str
    request_id: str
    decision_id: str
    work_type: str
    status: str = "DISPATCHED"


class RevalidationPlan(BaseModel):
    stale_decision_ids: list[str] = Field(default_factory=list)
    runnable_decision_ids: list[str] = Field(default_factory=list)
    waiting_decision_ids: list[str] = Field(default_factory=list)
    blocked_action_ids: list[str] = Field(default_factory=list)
    retained_decision_ids: list[str] = Field(default_factory=list)
    cause_by_node_id: dict[str, str] = Field(default_factory=dict)


class GraphSnapshot(BaseModel):
    mission_id: str
    artifacts: dict[str, WorldArtifact] = Field(default_factory=dict)
    evidences: dict[str, EvidenceNode] = Field(default_factory=dict)
    claims: dict[str, ClaimNode] = Field(default_factory=dict)
    decisions: dict[str, DecisionNode] = Field(default_factory=dict)
    actions: dict[str, ActionNode] = Field(default_factory=dict)
    edges: list[DependencyEdge] = Field(default_factory=list)
    events: list[DomainEvent] = Field(default_factory=list)
    dispatches: list[DispatchRecord] = Field(default_factory=list)
    cause_by_node_id: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
