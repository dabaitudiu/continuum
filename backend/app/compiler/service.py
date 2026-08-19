from __future__ import annotations

from typing import Protocol

from app.compiler.models import (
    CanonicalCompilation,
    CompilationDisposition,
    CompilationResult,
    CriticReview,
    DecisionDraft,
    ValidationReport,
)


class DraftValidator(Protocol):
    def validate(self, draft: DecisionDraft, context: object) -> ValidationReport: ...


class DraftReviewer(Protocol):
    def review(self, draft: DecisionDraft, context: object) -> CriticReview: ...


class DraftCanonicalizer(Protocol):
    def compile(
        self,
        draft: DecisionDraft,
        context: object,
        validation: ValidationReport,
        review: CriticReview,
    ) -> CanonicalCompilation: ...


class CompilerService:
    """Runs compiler stages without owning or invoking runtime mutation."""

    def __init__(
        self,
        *,
        validator: DraftValidator,
        reviewer: DraftReviewer,
        canonicalizer: DraftCanonicalizer,
        compiler_version: str,
        validation_policy_version: str,
    ) -> None:
        self._validator = validator
        self._reviewer = reviewer
        self._canonicalizer = canonicalizer
        self._compiler_version = compiler_version
        self._validation_policy_version = validation_policy_version

    def compile(self, draft: DecisionDraft, context: object) -> CompilationResult:
        validation = self._validator.validate(draft, context)
        if validation.disposition is not None:
            return self._blocked_result(
                draft,
                status=validation.disposition,
                validation=validation,
            )

        review = self._reviewer.review(draft, context)
        if review.disposition is not None:
            return self._blocked_result(
                draft,
                status=review.disposition,
                validation=validation,
                review=review,
            )

        canonical = self._canonicalizer.compile(
            draft,
            context,
            validation,
            review,
        )
        return CompilationResult(
            compilation_id=canonical.compilation_id,
            request_id=draft.request_id,
            status=CompilationDisposition.ACCEPTED,
            decision_candidate=canonical.decision_candidate,
            canonical_claims=canonical.canonical_claims,
            canonical_edges=canonical.canonical_edges,
            validation_findings=validation.findings,
            critic_findings=review.findings,
            contradictions=review.contradictions,
            compiler_version=self._compiler_version,
            validation_policy_version=self._validation_policy_version,
            compilation_hash=canonical.compilation_hash,
            model_metadata=draft.model_metadata,
            critic_model_metadata=review.model_metadata,
        )

    def _blocked_result(
        self,
        draft: DecisionDraft,
        *,
        status: CompilationDisposition,
        validation: ValidationReport,
        review: CriticReview | None = None,
    ) -> CompilationResult:
        return CompilationResult(
            compilation_id=f"blocked:{draft.request_id}",
            request_id=draft.request_id,
            status=status,
            validation_findings=validation.findings,
            critic_findings=[] if review is None else review.findings,
            contradictions=[] if review is None else review.contradictions,
            compiler_version=self._compiler_version,
            validation_policy_version=self._validation_policy_version,
            model_metadata=draft.model_metadata,
            critic_model_metadata=None if review is None else review.model_metadata,
        )
