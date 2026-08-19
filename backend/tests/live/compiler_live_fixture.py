from __future__ import annotations

from datetime import UTC, datetime

from app.compiler.context import CompilationContext, RiskClass
from app.compiler.reasoner import ReasoningRequest
from app.compiler.tools import ReadOnlySourceTools
from app.sources.identity import (
    Artifact,
    ArtifactType,
    SourceType,
    TrustClass,
    ingest_json_revision,
)
from app.sources.registry import InMemorySourceRegistry, WorldSnapshot


NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def build_live_access_case() -> tuple[
    ReadOnlySourceTools,
    CompilationContext,
    set[str],
    ReasoningRequest,
]:
    registry = InMemorySourceRegistry()
    sources = []
    refs: set[str] = set()
    for artifact_id, artifact_type, source_type, logical_key, value in (
        (
            "policy:privileged-access",
            ArtifactType.POLICY,
            SourceType.POLICY,
            "privileged-access-policy",
            {"training_rule": "Privileged access requires CURRENT security training."},
        ),
        (
            "record:employee-training",
            ArtifactType.RECORD,
            SourceType.STRUCTURED_RECORD,
            "employee-training",
            {"training_status": "CURRENT"},
        ),
    ):
        artifact = Artifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            logical_key=logical_key,
            owner_scope="tenant:live-eval",
            trust_class=TrustClass.AUTHORITATIVE,
            source_type=source_type,
            authority_rank=100,
            created_at=NOW,
        )
        ingested = ingest_json_revision(
            artifact,
            revision_label="r1",
            value=value,
            created_at=NOW,
            valid_from=NOW,
            parser_version="json-v1",
        )
        registry.add_artifact(artifact)
        registry.add_revision(ingested.revision)
        registry.add_representation(
            ingested.representation,
            ingested.fragments,
            fragment_values=ingested.fragment_values,
        )
        refs.update(str(fragment.source_ref()) for fragment in ingested.fragments)
        sources.append((artifact, ingested))
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id="world:live-access",
            owner_scope="tenant:live-eval",
            current_revisions={
                artifact.artifact_id: ingested.revision.revision_id
                for artifact, ingested in sources
            },
            current_representations={
                ingested.revision.revision_id: ingested.representation.representation_id
                for _, ingested in sources
            },
            created_at=NOW,
        )
    )
    context = CompilationContext(
        source_registry=registry,
        world_snapshot_id="world:live-access",
        owner_scope="tenant:live-eval",
        allowed_source_refs=frozenset(refs),
        risk_class=RiskClass.HIGH,
        decision_context={
            "mission_id": "mission:live-access",
            "subject": "employee:123",
        },
    )
    return (
        ReadOnlySourceTools(context),
        context,
        refs,
        ReasoningRequest(
            request_id="request:live-access",
            execution_id="live-openai-access",
            decision_type="PRIVILEGED_ACCESS_REVIEW",
            task=(
                "Decide APPROVED only if the policy requires current training and "
                "the employee record proves it is current. Cite both exact source "
                "fragments as CRITICAL dependencies."
            ),
            risk_class=RiskClass.HIGH,
        ),
    )
