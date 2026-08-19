from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from app.compiler.context import CompilationContext, RiskClass
from app.compiler.models import (
    CompilationDisposition,
    CriticFindingType,
    CriticProposal,
    DecisionDraft,
    DependencyRelation,
    IrrelevantDependencyProposal,
    Materiality,
    MissingDependencyProposal,
    UnsupportedClaimProposal,
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

NOW = datetime(2026, 8, 19, 15, 0, tzinfo=UTC)


def _case() -> tuple[CompilationContext, DecisionDraft, dict[str, str]]:
    registry = InMemorySourceRegistry()
    sources = []
    refs: dict[str, str] = {}
    for name, value in (
        ("manager", {"approved": True}),
        ("training", {"status": "CURRENT"}),
        ("mfa", {"enrolled": True}),
    ):
        artifact = Artifact(
            artifact_id=f"record:{name}",
            artifact_type=ArtifactType.RECORD,
            logical_key=name,
            owner_scope="tenant:alpha",
            trust_class=TrustClass.VERIFIED,
            source_type=SourceType.STRUCTURED_RECORD,
            authority_rank=70,
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
        refs[name] = str(ingested.fragments[0].source_ref())
        sources.append((artifact, ingested))
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id="world:access",
            owner_scope="tenant:alpha",
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
        world_snapshot_id="world:access",
        owner_scope="tenant:alpha",
        allowed_source_refs=frozenset(refs.values()),
        risk_class=RiskClass.HIGH,
    )
    draft = DecisionDraft.model_validate(
        {
            "request_id": "request-access",
            "decision_type": "PRIVILEGED_ACCESS_REVIEW",
            "proposed_outcome": "APPROVED",
            "claims": [
                {
                    "claim_local_id": "c1",
                    "claim_type": "FACT",
                    "statement": "Manager approval exists.",
                    "dependencies": [
                        {
                            "source_ref": refs["manager"],
                            "relation": "SUPPORTED_BY",
                            "materiality": "CRITICAL",
                        }
                    ],
                    "derived_from_claims": [],
                    "materiality": "CRITICAL",
                    "confidence": 0.99,
                }
            ],
            "decision_dependencies": [],
            "unresolved_questions": [],
            "rationale_summary": "Manager approval was evaluated.",
            "model_metadata": {
                "provider": "OPENAI",
                "model_name": "gpt-5.6-luna",
                "prompt_version": "reasoner-v1",
                "temperature": 0.0,
                "execution_id": "execution-1",
            },
        }
    )
    return context, draft, refs


@dataclass
class FixedCritic:
    proposal: CriticProposal

    def review(
        self, draft: DecisionDraft, context: CompilationContext
    ) -> CriticProposal:
        return self.proposal


def _review(
    proposal: CriticProposal,
    context: CompilationContext,
    draft: DecisionDraft,
):  # type: ignore[no-untyped-def]
    return DeterministicReviewGate(
        critic=FixedCritic(proposal),
        precedence_policy=AuthorityPrecedencePolicy(),
    ).review(draft, context)


def test_critical_missing_dependency_blocks_acceptance() -> None:
    context, draft, refs = _case()

    review = _review(
        CriticProposal(
            missing_dependencies=[
                MissingDependencyProposal(
                    candidate_ref=refs["training"],
                    severity=Materiality.CRITICAL,
                    why="Current training is required.",
                    claim_local_id="c1",
                )
            ]
        ),
        context,
        draft,
    )

    assert review.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    assert review.findings[0].finding_type is CriticFindingType.MISSING_DEPENDENCY
    assert review.findings[0].candidate_ref == refs["training"]


@pytest.mark.parametrize(
    ("severity", "blocked"),
    [(Materiality.SUPPORTING, False), (Materiality.CONTEXTUAL, False)],
)
def test_noncritical_omission_is_recorded_without_blocking(
    severity: Materiality,
    blocked: bool,
) -> None:
    context, draft, refs = _case()
    review = _review(
        CriticProposal(
            missing_dependencies=[
                MissingDependencyProposal(
                    candidate_ref=refs["mfa"],
                    severity=severity,
                    why="Useful additional context.",
                )
            ]
        ),
        context,
        draft,
    )

    assert (review.disposition is not None) is blocked
    assert review.findings[0].severity is severity


def test_unknown_source_required_sentinel_blocks_without_inventing_a_ref() -> None:
    context, draft, _ = _case()
    review = _review(
        CriticProposal(
            missing_dependencies=[
                MissingDependencyProposal(
                    candidate_ref="UNKNOWN_SOURCE_REQUIRED",
                    severity=Materiality.CRITICAL,
                    why="A current background check is required but absent.",
                )
            ]
        ),
        context,
        draft,
    )

    assert review.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    assert review.findings[0].candidate_ref == "UNKNOWN_SOURCE_REQUIRED"


@pytest.mark.parametrize(
    "candidate_ref",
    [
        "record:invented@r1!rep-invented#$.status",
        "record:mfa@r1!invented-representation#$.enrolled",
    ],
)
def test_critic_fabricated_candidate_ref_is_a_deterministic_rejection(
    candidate_ref: str,
) -> None:
    context, draft, _ = _case()
    context = CompilationContext(
        source_registry=context.source_registry,
        world_snapshot_id=context.world_snapshot_id,
        owner_scope=context.owner_scope,
        allowed_source_refs=frozenset({*context.allowed_source_refs, candidate_ref}),
        risk_class=context.risk_class,
    )

    review = _review(
        CriticProposal(
            missing_dependencies=[
                MissingDependencyProposal(
                    candidate_ref=candidate_ref,
                    severity=Materiality.CRITICAL,
                    why="Fabricated candidate.",
                )
            ]
        ),
        context,
        draft,
    )

    assert review.disposition is CompilationDisposition.REJECTED_INVALID_REFERENCE
    assert review.findings[0].finding_type is CriticFindingType.MISSING_DEPENDENCY


def test_critic_candidate_outside_request_allowlist_is_rejected() -> None:
    context, draft, refs = _case()
    restricted = CompilationContext(
        source_registry=context.source_registry,
        world_snapshot_id=context.world_snapshot_id,
        owner_scope=context.owner_scope,
        allowed_source_refs=frozenset({refs["manager"]}),
        risk_class=context.risk_class,
    )

    review = _review(
        CriticProposal(
            missing_dependencies=[
                MissingDependencyProposal(
                    candidate_ref=refs["training"],
                    severity=Materiality.CRITICAL,
                    why="Training is required.",
                )
            ]
        ),
        restricted,
        draft,
    )

    assert review.disposition is CompilationDisposition.REJECTED_INVALID_REFERENCE


def test_dependency_already_cited_is_not_treated_as_missing() -> None:
    context, draft, refs = _case()

    review = _review(
        CriticProposal(
            missing_dependencies=[
                MissingDependencyProposal(
                    candidate_ref=refs["manager"],
                    severity=Materiality.CRITICAL,
                    why="Manager approval is required.",
                    claim_local_id="c1",
                )
            ]
        ),
        context,
        draft,
    )

    assert review.disposition is None
    assert review.findings == []


@pytest.mark.parametrize(
    ("claim_local_id", "relation", "materiality"),
    [
        ("c1", DependencyRelation.CONTRADICTED_BY, Materiality.CRITICAL),
        ("c1", DependencyRelation.SUPPORTED_BY, Materiality.CONTEXTUAL),
        (None, DependencyRelation.SUPPORTED_BY, Materiality.CRITICAL),
    ],
)
def test_same_ref_on_wrong_typed_edge_cannot_suppress_critical_omission(
    claim_local_id: str | None,
    relation: DependencyRelation,
    materiality: Materiality,
) -> None:
    context, draft, refs = _case()
    misplaced = draft.model_copy(
        update={
            "claims": [
                draft.claims[0].model_copy(
                    update={
                        "dependencies": [
                            draft.claims[0]
                            .dependencies[0]
                            .model_copy(
                                update={
                                    "relation": relation,
                                    "materiality": materiality,
                                }
                            )
                        ]
                    }
                )
            ]
        },
        deep=True,
    )

    review = _review(
        CriticProposal(
            missing_dependencies=[
                MissingDependencyProposal(
                    candidate_ref=refs["manager"],
                    severity=Materiality.CRITICAL,
                    why="Manager approval must support the original claim.",
                    claim_local_id=claim_local_id,
                    expected_relation=DependencyRelation.SUPPORTED_BY,
                    expected_materiality=Materiality.CRITICAL,
                )
            ]
        ),
        context,
        misplaced,
    )

    assert review.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    assert review.findings[0].expected_relation is DependencyRelation.SUPPORTED_BY
    assert review.findings[0].expected_materiality is Materiality.CRITICAL


def test_unsupported_critical_claim_blocks_and_irrelevant_dependency_warns() -> None:
    context, draft, refs = _case()

    review = _review(
        CriticProposal(
            unsupported_claims=[
                UnsupportedClaimProposal(
                    claim_local_id="c1",
                    severity=Materiality.CRITICAL,
                    why="The fragment proves approval exists but not that it is current.",
                )
            ],
            irrelevant_dependencies=[
                IrrelevantDependencyProposal(
                    source_ref=refs["manager"],
                    why="The approval does not prove training status.",
                )
            ],
        ),
        context,
        draft,
    )

    assert review.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    assert {finding.finding_type for finding in review.findings} == {
        CriticFindingType.UNSUPPORTED_CLAIM,
        CriticFindingType.IRRELEVANT_DEPENDENCY,
    }
