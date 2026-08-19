from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.compiler.context import CompilationContext, RiskClass
from app.compiler.models import (
    CompilationDisposition,
    ContradictionProposal,
    ContradictionResolution,
    CriticProposal,
    DecisionDraft,
    Materiality,
)
from app.compiler.review import AuthorityPrecedencePolicy, DeterministicReviewGate
from app.sources.identity import (
    Artifact,
    ArtifactType,
    SourceType,
    TrustClass,
    ingest_json_revision,
)
from app.sources.registry import InMemorySourceRegistry, WorldSnapshot


NOW = datetime(2026, 8, 19, 16, 0, tzinfo=UTC)


@dataclass
class ReviewFixture:
    context: CompilationContext
    draft: DecisionDraft
    refs: dict[str, str]


def _fixture() -> ReviewFixture:
    registry = InMemorySourceRegistry()
    refs: dict[str, str] = {}
    current_sources = []
    artifacts: dict[str, Artifact] = {}

    def add(
        name: str,
        artifact_type: ArtifactType,
        source_type: SourceType,
        trust: TrustClass,
        authority_rank: int,
        value: object,
        *,
        revision_label: str = "r1",
        current: bool = True,
        artifact_id: str | None = None,
    ) -> None:
        resolved_artifact_id = artifact_id or f"{source_type.value.lower()}:{name}"
        artifact = artifacts.get(resolved_artifact_id)
        if artifact is None:
            artifact = Artifact(
                artifact_id=resolved_artifact_id,
                artifact_type=artifact_type,
                logical_key=name,
                owner_scope="tenant:alpha",
                trust_class=trust,
                source_type=source_type,
                authority_rank=authority_rank,
                created_at=NOW,
            )
            registry.add_artifact(artifact)
            artifacts[resolved_artifact_id] = artifact
        ingested = ingest_json_revision(
            artifact,
            revision_label=revision_label,
            value={"position": value},
            created_at=NOW,
            valid_from=NOW,
            parser_version="json-v1",
        )
        registry.add_revision(ingested.revision)
        registry.add_representation(
            ingested.representation,
            ingested.fragments,
            fragment_values=ingested.fragment_values,
        )
        refs[name] = str(ingested.fragment_at("$.position").source_ref())
        if current:
            current_sources[:] = [
                pair for pair in current_sources if pair[0].artifact_id != artifact.artifact_id
            ]
            current_sources.append((artifact, ingested))

    add(
        "policy-old",
        ArtifactType.POLICY,
        SourceType.POLICY,
        TrustClass.AUTHORITATIVE,
        100,
        "approval allowed",
        revision_label="v12",
        current=False,
        artifact_id="policy:access",
    )
    add(
        "policy-current",
        ArtifactType.POLICY,
        SourceType.POLICY,
        TrustClass.AUTHORITATIVE,
        100,
        "approval denied",
        revision_label="v13",
        artifact_id="policy:access",
    )
    add("signed", ArtifactType.HUMAN_APPROVAL, SourceType.HUMAN_APPROVAL, TrustClass.AUTHORITATIVE, 90, "approved")
    add("draft", ArtifactType.HUMAN_APPROVAL, SourceType.HUMAN_APPROVAL, TrustClass.UNTRUSTED, 10, "denied")
    add("record", ArtifactType.RECORD, SourceType.STRUCTURED_RECORD, TrustClass.AUTHORITATIVE, 80, "enabled")
    add("cache", ArtifactType.TOOL_SNAPSHOT, SourceType.TOOL_SNAPSHOT, TrustClass.VERIFIED, 80, "disabled")
    add("global", ArtifactType.POLICY, SourceType.POLICY, TrustClass.AUTHORITATIVE, 100, "denied")
    add("mission", ArtifactType.POLICY, SourceType.POLICY, TrustClass.AUTHORITATIVE, 50, "approved")
    add("equal-a", ArtifactType.DOCUMENT, SourceType.DOCUMENT, TrustClass.VERIFIED, 40, "approved")
    add("equal-b", ArtifactType.DOCUMENT, SourceType.DOCUMENT, TrustClass.VERIFIED, 40, "denied")

    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id="world:contradictions",
            owner_scope="tenant:alpha",
            current_revisions={
                artifact.artifact_id: ingested.revision.revision_id
                for artifact, ingested in current_sources
            },
            current_representations={
                ingested.revision.revision_id: ingested.representation.representation_id
                for _, ingested in current_sources
            },
            created_at=NOW,
        )
    )
    context = CompilationContext(
        source_registry=registry,
        world_snapshot_id="world:contradictions",
        owner_scope="tenant:alpha",
        allowed_source_refs=frozenset(refs.values()),
        risk_class=RiskClass.HIGH,
        allow_historical=True,
    )
    draft = DecisionDraft.model_validate(
        {
            "request_id": "request-1",
            "decision_type": "ACCESS_REVIEW",
            "proposed_outcome": "APPROVED",
            "claims": [],
            "decision_dependencies": [],
            "unresolved_questions": [],
            "rationale_summary": "Conflicting sources were evaluated.",
            "model_metadata": {
                "provider": "OPENAI",
                "model_name": "gpt-5.6-luna",
                "prompt_version": "reasoner-v1",
                "temperature": 0.0,
                "execution_id": "execution-1",
            },
        }
    )
    return ReviewFixture(context=context, draft=draft, refs=refs)


@dataclass
class FixedCritic:
    proposal: CriticProposal

    def review(self, draft: DecisionDraft, context: CompilationContext) -> CriticProposal:
        return self.proposal


def _review(
    fixture: ReviewFixture,
    contradiction: ContradictionProposal,
    *,
    overrides: frozenset[tuple[str, str]] = frozenset(),
):  # type: ignore[no-untyped-def]
    return DeterministicReviewGate(
        critic=FixedCritic(CriticProposal(possible_contradictions=[contradiction])),
        precedence_policy=AuthorityPrecedencePolicy(explicit_overrides=overrides),
    ).review(fixture.draft, fixture.context)


def _contradiction(
    ref_a: str,
    ref_b: str,
    *,
    a_supports: bool,
    b_supports: bool,
    severity: Materiality = Materiality.CRITICAL,
) -> ContradictionProposal:
    return ContradictionProposal(
        claim_or_topic="Whether access may be approved",
        source_ref_a=ref_a,
        source_ref_b=ref_b,
        severity=severity,
        source_a_supports_outcome=a_supports,
        source_b_supports_outcome=b_supports,
    )


def test_current_policy_revision_precedes_obsolete_revision_and_can_reject() -> None:
    fixture = _fixture()
    review = _review(
        fixture,
        _contradiction(
            fixture.refs["policy-old"],
            fixture.refs["policy-current"],
            a_supports=True,
            b_supports=False,
        ),
    )

    assert review.disposition is CompilationDisposition.REJECTED_CONTRADICTION
    assert review.contradictions[0].resolution is ContradictionResolution.SOURCE_B_PRECEDES
    assert review.contradictions[0].precedence_rule_applied == "CURRENT_REVISION"


def test_signed_human_approval_precedes_draft_approval() -> None:
    fixture = _fixture()
    review = _review(
        fixture,
        _contradiction(
            fixture.refs["signed"],
            fixture.refs["draft"],
            a_supports=True,
            b_supports=False,
        ),
    )

    assert review.disposition is None
    assert review.contradictions[0].resolution is ContradictionResolution.SOURCE_A_PRECEDES
    assert review.contradictions[0].precedence_rule_applied == "SIGNED_APPROVAL"


def test_canonical_record_precedes_cached_tool_snapshot() -> None:
    fixture = _fixture()
    review = _review(
        fixture,
        _contradiction(
            fixture.refs["record"],
            fixture.refs["cache"],
            a_supports=True,
            b_supports=False,
        ),
    )

    assert review.disposition is None
    assert review.contradictions[0].precedence_rule_applied == "CANONICAL_RECORD"


def test_mission_override_only_precedes_when_explicitly_configured() -> None:
    fixture = _fixture()
    pair = (fixture.refs["mission"], fixture.refs["global"])
    without_override = _review(
        fixture,
        _contradiction(pair[0], pair[1], a_supports=True, b_supports=False),
    )
    with_override = _review(
        fixture,
        _contradiction(pair[0], pair[1], a_supports=True, b_supports=False),
        overrides=frozenset({pair}),
    )

    assert without_override.contradictions[0].precedence_rule_applied == "AUTHORITY_RANK"
    assert without_override.disposition is CompilationDisposition.REJECTED_CONTRADICTION
    assert with_override.contradictions[0].precedence_rule_applied == "MISSION_OVERRIDE"
    assert with_override.disposition is None


def test_unresolved_material_contradiction_requires_human_review() -> None:
    fixture = _fixture()
    review = _review(
        fixture,
        _contradiction(
            fixture.refs["equal-a"],
            fixture.refs["equal-b"],
            a_supports=True,
            b_supports=False,
        ),
    )

    assert review.disposition is CompilationDisposition.NEEDS_HUMAN_REVIEW
    assert review.contradictions[0].resolution is ContradictionResolution.UNRESOLVED
    assert review.contradictions[0].precedence_rule_applied is None


def test_unresolved_contextual_contradiction_is_recorded_but_not_blocking() -> None:
    fixture = _fixture()
    review = _review(
        fixture,
        _contradiction(
            fixture.refs["equal-a"],
            fixture.refs["equal-b"],
            a_supports=True,
            b_supports=False,
            severity=Materiality.CONTEXTUAL,
        ),
    )

    assert review.disposition is None
    assert review.contradictions[0].resolution is ContradictionResolution.UNRESOLVED
