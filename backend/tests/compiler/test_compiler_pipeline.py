from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.compiler.canonicalization import DeterministicCanonicalizer
from app.compiler.context import CompilationContext, RiskClass
from app.compiler.models import (
    CanonicalCompilation,
    CompilationDisposition,
    CriticReview,
    CriticProposal,
    DecisionDraft,
    Materiality,
    MissingDependencyProposal,
    ModelMetadata,
    ValidationReport,
)
from app.compiler.review import AuthorityPrecedencePolicy, DeterministicReviewGate
from app.compiler.service import CompilerService
from app.compiler.validation import DeterministicDraftValidator
from app.sources.identity import (
    Artifact,
    ArtifactType,
    SourceType,
    TrustClass,
    ingest_json_revision,
)
from app.sources.registry import InMemorySourceRegistry, WorldSnapshot


def _draft() -> DecisionDraft:
    return DecisionDraft.model_validate(
        {
            "request_id": "request-1",
            "decision_type": "RELEASE_REVIEW",
            "proposed_outcome": "APPROVED",
            "claims": [
                {
                    "claim_local_id": "c1",
                    "claim_type": "FACT",
                    "statement": "The release test suite passed.",
                    "dependencies": [
                        {
                            "source_ref": "record:test@r9!rep-r9#$.status",
                            "relation": "SUPPORTED_BY",
                            "materiality": "CRITICAL",
                            "purpose": "Establishes test status",
                        }
                    ],
                    "derived_from_claims": [],
                    "materiality": "CRITICAL",
                    "confidence": 0.99,
                }
            ],
            "decision_dependencies": [],
            "unresolved_questions": [],
            "rationale_summary": "The release evidence satisfies the gate.",
            "model_metadata": {
                "provider": "GOOGLE",
                "model_name": "gemini-3.5-flash",
                "prompt_version": "reasoner-v1",
                "temperature": 0.0,
                "execution_id": "execution-1",
            },
        }
    )


@dataclass
class RecordingValidator:
    calls: list[str]

    def validate(self, draft: DecisionDraft, context: object) -> ValidationReport:
        self.calls.append("validate")
        return ValidationReport()


@dataclass
class RecordingReviewer:
    calls: list[str]

    def review(self, draft: DecisionDraft, context: object) -> CriticReview:
        self.calls.append("review")
        return CriticReview()


@dataclass
class RecordingCanonicalizer:
    calls: list[str]

    def compile(
        self,
        draft: DecisionDraft,
        context: object,
        validation: ValidationReport,
        review: CriticReview,
    ) -> CanonicalCompilation:
        self.calls.append("canonicalize")
        return CanonicalCompilation(
            compilation_id="compilation-1",
            compilation_hash="a" * 64,
            decision_candidate={
                "decision_id": "decision-1",
                "decision_type": draft.decision_type,
                "outcome": draft.proposed_outcome,
                "rationale_summary": draft.rationale_summary,
            },
        )


@dataclass
class RuntimeMutationTrap:
    calls: list[str] = field(default_factory=list)

    def mutate(self) -> None:
        self.calls.append("mutated")


def test_compiler_runs_read_only_stages_in_fixed_order_without_runtime_mutation() -> None:
    calls: list[str] = []
    runtime = RuntimeMutationTrap()
    service = CompilerService(
        validator=RecordingValidator(calls),
        reviewer=RecordingReviewer(calls),
        canonicalizer=RecordingCanonicalizer(calls),
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
    )

    result = service.compile(_draft(), context={"runtime": runtime})

    assert calls == ["validate", "review", "canonicalize"]
    assert runtime.calls == []
    assert result.status is CompilationDisposition.ACCEPTED
    assert result.compilation_hash == "a" * 64
    assert result.model_metadata == ModelMetadata.model_validate(
        _draft().model_metadata
    )


def test_blocking_validation_stops_before_probabilistic_review_and_canonicalization() -> None:
    class BlockingValidator(RecordingValidator):
        def validate(self, draft: DecisionDraft, context: object) -> ValidationReport:
            self.calls.append("validate")
            return ValidationReport(
                disposition=CompilationDisposition.REJECTED_INVALID_REFERENCE,
            )

    calls: list[str] = []
    service = CompilerService(
        validator=BlockingValidator(calls),
        reviewer=RecordingReviewer(calls),
        canonicalizer=RecordingCanonicalizer(calls),
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
    )

    result = service.compile(_draft(), context={})

    assert calls == ["validate"]
    assert result.status is CompilationDisposition.REJECTED_INVALID_REFERENCE
    assert result.canonical_edges == []
    assert result.compilation_hash is None


def test_compiler_preserves_critic_model_metadata_in_accepted_result() -> None:
    class MetadataReviewer(RecordingReviewer):
        def review(self, draft: DecisionDraft, context: object) -> CriticReview:
            self.calls.append("review")
            return CriticReview(
                model_metadata={
                    "provider": "OPENAI",
                    "model_name": "gpt-5.6-luna",
                    "model_version": "gpt-5.6-luna-2026-08-01",
                    "prompt_version": "critic-v1",
                    "temperature": 0.0,
                    "execution_id": "execution-1:critic:1",
                    "response_id": "critic-response-1",
                }
            )

    calls: list[str] = []
    service = CompilerService(
        validator=RecordingValidator(calls),
        reviewer=MetadataReviewer(calls),
        canonicalizer=RecordingCanonicalizer(calls),
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
    )

    result = service.compile(_draft(), context={})

    assert result.status is CompilationDisposition.ACCEPTED
    assert result.critic_model_metadata is not None
    assert result.critic_model_metadata.prompt_version == "critic-v1"


def _real_pipeline_case() -> tuple[CompilationContext, DecisionDraft, str]:
    now = datetime(2026, 8, 19, 17, 0, tzinfo=UTC)
    artifact = Artifact(
        artifact_id="policy:access",
        artifact_type=ArtifactType.POLICY,
        logical_key="access-policy",
        owner_scope="tenant:alpha",
        trust_class=TrustClass.AUTHORITATIVE,
        source_type=SourceType.POLICY,
        authority_rank=100,
        created_at=now,
    )
    ingested = ingest_json_revision(
        artifact,
        revision_label="v13",
        value={"training": "required", "mfa": "required"},
        created_at=now,
        valid_from=now,
        parser_version="json-v1",
    )
    training_ref = str(ingested.fragment_at("$.training").source_ref())
    mfa_ref = str(ingested.fragment_at("$.mfa").source_ref())
    registry = InMemorySourceRegistry()
    registry.add_artifact(artifact)
    registry.add_revision(ingested.revision)
    registry.add_representation(
        ingested.representation,
        ingested.fragments,
        fragment_values=ingested.fragment_values,
    )
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id="world:access",
            owner_scope="tenant:alpha",
            current_revisions={artifact.artifact_id: ingested.revision.revision_id},
            current_representations={
                ingested.revision.revision_id: ingested.representation.representation_id,
            },
            created_at=now,
        )
    )
    context = CompilationContext(
        source_registry=registry,
        world_snapshot_id="world:access",
        owner_scope="tenant:alpha",
        allowed_source_refs=frozenset({training_ref, mfa_ref}),
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
                    "claim_type": "RULE",
                    "statement": "Current training is required.",
                    "dependencies": [
                        {
                            "source_ref": training_ref,
                            "relation": "GOVERNED_BY",
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
            "rationale_summary": "Training policy was evaluated.",
            "model_metadata": {
                "provider": "OPENAI",
                "model_name": "gpt-5.6-luna",
                "prompt_version": "reasoner-v1",
                "temperature": 0.0,
                "execution_id": "execution-access:reasoner:1",
            },
        }
    )
    return context, draft, mfa_ref


@dataclass
class FixedProposalCritic:
    proposal: CriticProposal

    def review(
        self,
        draft: DecisionDraft,
        context: CompilationContext,
    ) -> CriticProposal:
        return self.proposal


def _real_service(proposal: CriticProposal) -> CompilerService:
    return CompilerService(
        validator=DeterministicDraftValidator(),
        reviewer=DeterministicReviewGate(
            critic=FixedProposalCritic(proposal),
            precedence_policy=AuthorityPrecedencePolicy(),
        ),
        canonicalizer=DeterministicCanonicalizer(
            compiler_version="sdc-1",
            validation_policy_version="validation-v1",
        ),
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
    )


def test_real_pipeline_canonicalizes_only_after_validation_and_review_pass() -> None:
    context, draft, _ = _real_pipeline_case()

    result = _real_service(CriticProposal()).compile(draft, context)

    assert result.status is CompilationDisposition.ACCEPTED
    assert result.compilation_hash is not None
    assert result.canonical_edges


def test_real_pipeline_never_canonicalizes_a_critical_critic_omission() -> None:
    context, draft, missing_ref = _real_pipeline_case()
    proposal = CriticProposal(
        missing_dependencies=[
            MissingDependencyProposal(
                candidate_ref=missing_ref,
                severity=Materiality.CRITICAL,
                why="MFA policy was omitted.",
            )
        ]
    )

    result = _real_service(proposal).compile(draft, context)

    assert result.status is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    assert result.compilation_hash is None
    assert result.canonical_edges == []
