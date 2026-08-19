from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.compiler.models import CompilationDisposition, Materiality
from app.compiler.repository import CompilerRepository
from app.domain.models import (
    ArtifactStatus,
    ClaimNode,
    DecisionNode,
    DependencyEdge,
    DomainEvent,
    EvidenceNode,
    RelationType,
    WorldArtifact,
)
from app.repository.runtime_protocol import RuntimeRepository
from app.runtime.entities import AuditEvent, InboxRecord, OutboxMessage, RuntimeSnapshot
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation
from app.sources.identity import SourceRef


class CompilerAcceptanceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class RuntimeAcceptanceResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot: RuntimeSnapshot
    duplicate: bool = False
    request_id: str
    compilation_id: str
    compilation_hash: str
    decision_id: str


class RuntimeAcceptanceService:
    def __init__(
        self,
        compiler_repository: CompilerRepository,
        runtime_repository: RuntimeRepository,
    ) -> None:
        self._compiler_repository = compiler_repository
        self._runtime_repository = runtime_repository

    def accept(
        self,
        request_id: str,
        *,
        expected_mission_revision: int,
        world_snapshot_id: str,
    ) -> RuntimeAcceptanceResult:
        aggregate = self._compiler_repository.get(request_id)
        result = aggregate.result
        request = aggregate.request
        if result is None or result.status is not CompilationDisposition.ACCEPTED:
            raise CompilerAcceptanceError(
                "COMPILATION_NOT_ACCEPTED",
                "only an ACCEPTED immutable compilation result can enter runtime",
            )
        if result.decision_candidate is None or result.compilation_hash is None:
            raise CompilerAcceptanceError(
                "COMPILATION_RESULT_INVALID",
                "accepted compilation is missing canonical decision identity",
            )
        if world_snapshot_id != request.world_snapshot_id:
            raise CompilerAcceptanceError(
                "WORLD_SNAPSHOT_MISMATCH",
                "acceptance world snapshot differs from the compilation request",
            )
        if expected_mission_revision != request.expected_mission_revision:
            raise CompilerAcceptanceError(
                "MISSION_REVISION_MISMATCH",
                "acceptance revision differs from the compilation request",
            )

        message_id = f"compiler-accept:{result.compilation_id}"
        duplicate = self._runtime_repository.find_inbox(
            request.mission_id,
            message_id,
        )
        if duplicate is not None:
            return self._result(
                self._runtime_repository.load(request.mission_id),
                request_id=request_id,
                duplicate=True,
            )

        current = self._runtime_repository.load(request.mission_id)
        if current.mission.revision != expected_mission_revision:
            raise CompilerAcceptanceError(
                "MISSION_REVISION_MISMATCH",
                f"expected revision {expected_mission_revision}, found {current.mission.revision}",
            )
        runtime_world_snapshot = (
            None if current.world is None else current.world.world_snapshot_id
        ) or current.graph.metadata.get("world_snapshot_id")
        if runtime_world_snapshot != world_snapshot_id:
            raise CompilerAcceptanceError(
                "WORLD_SNAPSHOT_MISMATCH",
                "runtime world snapshot advanced after compilation",
            )

        graph = current.graph.model_copy(deep=True)
        candidate = result.decision_candidate
        graph.decisions[candidate.decision_id] = DecisionNode(
            decision_id=candidate.decision_id,
            decision_type=candidate.decision_type,
            outcome=candidate.outcome,
            compilation_id=result.compilation_id,
            compilation_hash=result.compilation_hash,
            world_snapshot_id=world_snapshot_id,
        )
        for claim in result.canonical_claims:
            graph.claims[claim.claim_id] = ClaimNode(
                claim_id=claim.claim_id,
                claim_type=claim.claim_type.value,
                statement=claim.statement,
                materiality=claim.materiality.value,
                confidence=claim.confidence,
                compilation_id=result.compilation_id,
            )
        for edge in result.canonical_edges:
            if edge.source_kind == "SOURCE_FRAGMENT":
                try:
                    source_ref = SourceRef.parse(edge.source_id)
                except ValueError as error:
                    raise CompilerAcceptanceError(
                        "COMPILATION_RESULT_INVALID",
                        f"canonical edge contains invalid source ref: {edge.source_id}",
                    ) from error
                runtime_artifact_id = _bind_runtime_artifact(
                    graph,
                    current.world,
                    source_ref,
                )
                graph.evidences.setdefault(
                    edge.source_id,
                    EvidenceNode(
                        evidence_id=edge.source_id,
                        kind="SOURCE_FRAGMENT",
                        revision=source_ref.revision_label,
                        artifact_id=runtime_artifact_id,
                        source_ref=edge.source_id,
                    ),
                )
            try:
                relation = RelationType(edge.relation.value)
            except ValueError as error:
                raise CompilerAcceptanceError(
                    "COMPILATION_RESULT_INVALID",
                    f"unsupported runtime relation: {edge.relation.value}",
                ) from error
            graph.edges.append(
                DependencyEdge(
                    edge_id=edge.edge_id,
                    from_node_id=edge.source_id,
                    to_node_id=edge.target_id,
                    relation_type=relation,
                    critical=edge.materiality is Materiality.CRITICAL,
                )
            )
        graph.events.append(
            DomainEvent(
                event_id=f"decision-created:{result.compilation_id}",
                event_type="decision.created",
                payload={
                    "decision_id": candidate.decision_id,
                    "compilation_id": result.compilation_id,
                    "compilation_hash": result.compilation_hash,
                },
            )
        )
        sequence = current.mission.event_sequence + 1
        audit = AuditEvent(
            audit_event_id=f"audit:{message_id}",
            mission_id=request.mission_id,
            event_sequence=sequence,
            event_type="decision.created",
            payload={
                "request_id": request_id,
                "decision_id": candidate.decision_id,
                "compilation_id": result.compilation_id,
                "compilation_hash": result.compilation_hash,
                "world_snapshot_id": world_snapshot_id,
            },
            correlation_id=request_id,
            causation_id=result.compilation_id,
        )
        mutation = RuntimeMutation(
            mission=current.mission,
            graph=graph,
            audit_appends=[audit],
            inbox_completion=InboxRecord(
                mission_id=request.mission_id,
                message_id=message_id,
                message_type="compiler.accept",
                result={
                    "request_id": request_id,
                    "compilation_id": result.compilation_id,
                    "decision_id": candidate.decision_id,
                },
            ),
            outbox_appends=[
                OutboxMessage(
                    outbox_message_id=f"outbox:{message_id}",
                    mission_id=request.mission_id,
                    event_type="decision.created",
                    payload={
                        "request_id": request_id,
                        "compilation_id": result.compilation_id,
                        "compilation_hash": result.compilation_hash,
                        "decision_id": candidate.decision_id,
                    },
                    correlation_id=request_id,
                    causation_id=result.compilation_id,
                )
            ],
        )
        try:
            committed = self._runtime_repository.commit(
                request.mission_id,
                expected_mission_revision,
                mutation,
            )
        except RuntimeDomainError as error:
            if error.code == "REVISION_CONFLICT":
                duplicate = self._runtime_repository.find_inbox(
                    request.mission_id,
                    message_id,
                )
                if duplicate is not None:
                    return self._result(
                        self._runtime_repository.load(request.mission_id),
                        request_id=request_id,
                        duplicate=True,
                    )
                raise CompilerAcceptanceError(
                    "MISSION_REVISION_MISMATCH",
                    error.message,
                ) from error
            raise
        return self._result(committed, request_id=request_id, duplicate=False)

    def _result(
        self,
        snapshot: RuntimeSnapshot,
        *,
        request_id: str,
        duplicate: bool,
    ) -> RuntimeAcceptanceResult:
        aggregate = self._compiler_repository.get(request_id)
        result = aggregate.result
        assert result is not None
        assert result.compilation_hash is not None
        assert result.decision_candidate is not None
        return RuntimeAcceptanceResult(
            snapshot=snapshot,
            duplicate=duplicate,
            request_id=request_id,
            compilation_id=result.compilation_id,
            compilation_hash=result.compilation_hash,
            decision_id=result.decision_candidate.decision_id,
        )


def _bind_runtime_artifact(
    graph: object,
    world: object,
    source_ref: SourceRef,
) -> str:
    artifacts = graph.artifacts  # type: ignore[attr-defined]
    for artifact in artifacts.values():
        if (
            artifact.logical_key == source_ref.artifact_id
            and artifact.version == source_ref.revision_label
            and artifact.status is ArtifactStatus.CURRENT
        ):
            return artifact.artifact_id

    world_artifacts = {} if world is None else world.artifacts  # type: ignore[attr-defined]
    enterprise_artifact = world_artifacts.get(source_ref.artifact_id)
    if (
        enterprise_artifact is not None
        and enterprise_artifact.version == source_ref.revision_label
        and source_ref.artifact_id not in artifacts
    ):
        runtime_artifact_id = source_ref.artifact_id
        artifact_type = enterprise_artifact.artifact_type
    else:
        runtime_artifact_id = (
            f"{source_ref.artifact_id}@revision:{source_ref.revision_label}"
        )
        artifact_type = "SOURCE_ARTIFACT"
    artifacts.setdefault(
        runtime_artifact_id,
        WorldArtifact(
            artifact_id=runtime_artifact_id,
            artifact_type=artifact_type,
            logical_key=source_ref.artifact_id,
            version=source_ref.revision_label,
        ),
    )
    return runtime_artifact_id
