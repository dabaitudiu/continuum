from __future__ import annotations

from dataclasses import dataclass, field

from app.compiler.models import (
    CanonicalCompilation,
    CompilationDisposition,
    CriticReview,
    DecisionDraft,
    ModelMetadata,
    ValidationReport,
)
from app.compiler.service import CompilerService


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
