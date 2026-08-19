from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.compiler.context import CompilationContext
from app.compiler.models import (
    CompilationDisposition,
    ContradictionFinding,
    ContradictionProposal,
    ContradictionResolution,
    CriticOutcome,
    CriticFinding,
    CriticFindingType,
    CriticProposal,
    CriticReview,
    DecisionDraft,
    Materiality,
    ModelMetadata,
)
from app.compiler.prompts import CRITIC_SYSTEM_INSTRUCTION, critic_user_prompt
from app.compiler.reasoner import (
    ModelInvocation,
    ReasonerError,
    StructuredModelTransport,
    StructuredOutputError,
)
from app.compiler.tools import ReadOnlySourceTools
from app.sources.identity import SourceRef, SourceType, TrustClass
from app.sources.registry import ResolvedSource, SourceRegistryError


class CompletenessCritic(Protocol):
    def review(
        self,
        draft: DecisionDraft,
        context: CompilationContext,
    ) -> CriticProposal | CriticOutcome: ...


class ModelDependencyCritic:
    """Provider-neutral second pass; it proposes findings but owns no policy."""

    def __init__(
        self,
        transport: StructuredModelTransport,
        *,
        model_name: str,
        prompt_version: str,
        temperature: float = 0.0,
    ) -> None:
        self._transport = transport
        self._model_name = model_name
        self._prompt_version = prompt_version
        self._temperature = temperature

    def review(
        self,
        draft: DecisionDraft,
        context: CompilationContext,
    ) -> CriticOutcome:
        tools = ReadOnlySourceTools(context)
        execution_root = draft.model_metadata.execution_id.split(":reasoner:", 1)[0]
        schema_feedback: str | None = None
        for attempt in (1, 2):
            invocation = ModelInvocation(
                call_id=f"{execution_root}:critic:{attempt}",
                model_name=self._model_name,
                prompt_version=self._prompt_version,
                system_instruction=CRITIC_SYSTEM_INSTRUCTION,
                user_prompt=critic_user_prompt(
                    draft,
                    tools,
                    schema_feedback=schema_feedback,
                ),
                output_schema=CriticProposal,
                temperature=self._temperature,
                tools=tools.model_tool_functions(),
            )
            try:
                response = self._transport.generate(invocation)
            except StructuredOutputError as error:
                schema_feedback = str(error)
                if attempt == 2:
                    raise ReasonerError(
                        "MODEL_SCHEMA_INVALID",
                        f"critic output remained invalid after retry: {error}",
                    ) from error
                continue
            if not isinstance(response.parsed, CriticProposal):
                schema_feedback = "provider returned an object that is not a CriticProposal"
                if attempt == 2:
                    raise ReasonerError("MODEL_SCHEMA_INVALID", schema_feedback)
                continue
            return CriticOutcome(
                proposal=response.parsed,
                model_metadata=ModelMetadata(
                    provider=response.provider,
                    model_name=response.model_name,
                    model_version=response.model_version,
                    prompt_version=self._prompt_version,
                    temperature=self._temperature,
                    execution_id=response.execution_id,
                    response_id=response.response_id,
                    input_tokens=response.input_tokens,
                    cached_input_tokens=response.cached_input_tokens,
                    output_tokens=response.output_tokens,
                ),
            )
        raise AssertionError("critic retry loop exhausted")


@dataclass(frozen=True, slots=True)
class AuthorityPrecedencePolicy:
    """Domain-owned deterministic precedence; the model cannot alter it."""

    explicit_overrides: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    def resolve(
        self,
        source_a: ResolvedSource,
        source_b: ResolvedSource,
    ) -> tuple[ContradictionResolution, str | None]:
        ref_a = str(source_a.ref)
        ref_b = str(source_b.ref)
        if (ref_a, ref_b) in self.explicit_overrides:
            return ContradictionResolution.SOURCE_A_PRECEDES, "MISSION_OVERRIDE"
        if (ref_b, ref_a) in self.explicit_overrides:
            return ContradictionResolution.SOURCE_B_PRECEDES, "MISSION_OVERRIDE"

        if source_a.artifact.artifact_id == source_b.artifact.artifact_id:
            if source_a.is_historical != source_b.is_historical:
                if source_a.is_historical:
                    return (
                        ContradictionResolution.SOURCE_B_PRECEDES,
                        "CURRENT_REVISION",
                    )
                return ContradictionResolution.SOURCE_A_PRECEDES, "CURRENT_REVISION"

        if (
            source_a.artifact.source_type is SourceType.HUMAN_APPROVAL
            and source_b.artifact.source_type is SourceType.HUMAN_APPROVAL
            and source_a.artifact.trust_class != source_b.artifact.trust_class
        ):
            if source_a.artifact.trust_class is TrustClass.AUTHORITATIVE:
                return ContradictionResolution.SOURCE_A_PRECEDES, "SIGNED_APPROVAL"
            if source_b.artifact.trust_class is TrustClass.AUTHORITATIVE:
                return ContradictionResolution.SOURCE_B_PRECEDES, "SIGNED_APPROVAL"

        source_types = {
            source_a.artifact.source_type,
            source_b.artifact.source_type,
        }
        if source_types == {SourceType.STRUCTURED_RECORD, SourceType.TOOL_SNAPSHOT}:
            if source_a.artifact.source_type is SourceType.STRUCTURED_RECORD:
                return ContradictionResolution.SOURCE_A_PRECEDES, "CANONICAL_RECORD"
            return ContradictionResolution.SOURCE_B_PRECEDES, "CANONICAL_RECORD"

        rank_a = source_a.artifact.authority_rank
        rank_b = source_b.artifact.authority_rank
        if rank_a > rank_b:
            return ContradictionResolution.SOURCE_A_PRECEDES, "AUTHORITY_RANK"
        if rank_b > rank_a:
            return ContradictionResolution.SOURCE_B_PRECEDES, "AUTHORITY_RANK"
        return ContradictionResolution.UNRESOLVED, None


class DeterministicReviewGate:
    def __init__(
        self,
        *,
        critic: CompletenessCritic,
        precedence_policy: AuthorityPrecedencePolicy,
    ) -> None:
        self._critic = critic
        self._precedence_policy = precedence_policy

    def review(self, draft: DecisionDraft, context: object) -> CriticReview:
        if not isinstance(context, CompilationContext):
            raise TypeError("review gate requires CompilationContext")
        critic_outcome = self._critic.review(draft, context)
        if isinstance(critic_outcome, CriticOutcome):
            proposal = critic_outcome.proposal
            model_metadata = critic_outcome.model_metadata
        else:
            proposal = critic_outcome
            model_metadata = None
        draft_refs = {
            dependency.source_ref
            for claim in draft.claims
            for dependency in claim.dependencies
        } | {dependency.source_ref for dependency in draft.decision_dependencies}
        claim_ids = {claim.claim_local_id for claim in draft.claims}
        findings: list[CriticFinding] = []
        contradictions: list[ContradictionFinding] = []
        invalid_reference = False
        invalid_schema = False
        incomplete = False
        rejected_contradiction = False
        needs_review = False

        for missing in proposal.missing_dependencies:
            if missing.candidate_ref in draft_refs:
                continue
            valid_candidate = True
            if missing.candidate_ref != "UNKNOWN_SOURCE_REQUIRED":
                valid_candidate = self._resolve(
                    missing.candidate_ref,
                    context,
                ) is not None
            if not valid_candidate:
                invalid_reference = True
            if missing.claim_local_id is not None and missing.claim_local_id not in claim_ids:
                invalid_schema = True
            findings.append(
                CriticFinding(
                    finding_id=f"critic:missing:{len(findings):04d}",
                    finding_type=CriticFindingType.MISSING_DEPENDENCY,
                    severity=missing.severity,
                    message=missing.why,
                    candidate_ref=missing.candidate_ref,
                    claim_local_id=missing.claim_local_id,
                )
            )
            if missing.severity is Materiality.CRITICAL and valid_candidate:
                incomplete = True

        for unsupported in proposal.unsupported_claims:
            if unsupported.claim_local_id not in claim_ids:
                invalid_schema = True
            findings.append(
                CriticFinding(
                    finding_id=f"critic:unsupported:{len(findings):04d}",
                    finding_type=CriticFindingType.UNSUPPORTED_CLAIM,
                    severity=unsupported.severity,
                    message=unsupported.why,
                    claim_local_id=unsupported.claim_local_id,
                )
            )
            if unsupported.severity is Materiality.CRITICAL:
                incomplete = True

        for irrelevant in proposal.irrelevant_dependencies:
            if self._resolve(irrelevant.source_ref, context) is None:
                invalid_reference = True
            findings.append(
                CriticFinding(
                    finding_id=f"critic:irrelevant:{len(findings):04d}",
                    finding_type=CriticFindingType.IRRELEVANT_DEPENDENCY,
                    severity=Materiality.SUPPORTING,
                    message=irrelevant.why,
                    candidate_ref=irrelevant.source_ref,
                )
            )

        for index, contradiction in enumerate(proposal.possible_contradictions):
            source_a = self._resolve(contradiction.source_ref_a, context)
            source_b = self._resolve(contradiction.source_ref_b, context)
            if source_a is None or source_b is None:
                invalid_reference = True
                resolution = ContradictionResolution.UNRESOLVED
                rule = None
            else:
                resolution, rule = self._precedence_policy.resolve(source_a, source_b)
                if contradiction.severity is Materiality.CRITICAL:
                    if resolution is ContradictionResolution.UNRESOLVED:
                        needs_review = True
                    elif not _winner_supports_outcome(contradiction, resolution):
                        rejected_contradiction = True
            contradictions.append(
                ContradictionFinding(
                    finding_id=f"contradiction:{index:04d}",
                    claim_or_topic=contradiction.claim_or_topic,
                    source_ref_a=contradiction.source_ref_a,
                    source_ref_b=contradiction.source_ref_b,
                    severity=contradiction.severity,
                    precedence_rule_applied=rule,
                    resolution=resolution,
                )
            )

        disposition: CompilationDisposition | None = None
        if invalid_reference:
            disposition = CompilationDisposition.REJECTED_INVALID_REFERENCE
        elif invalid_schema:
            disposition = CompilationDisposition.REJECTED_SCHEMA
        elif incomplete:
            disposition = CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
        elif rejected_contradiction:
            disposition = CompilationDisposition.REJECTED_CONTRADICTION
        elif needs_review:
            disposition = CompilationDisposition.NEEDS_HUMAN_REVIEW
        return CriticReview(
            findings=findings,
            contradictions=contradictions,
            disposition=disposition,
            model_metadata=model_metadata,
        )

    @staticmethod
    def _resolve(
        raw_ref: str,
        context: CompilationContext,
    ) -> ResolvedSource | None:
        if raw_ref not in context.allowed_source_refs:
            return None
        try:
            return context.source_registry.resolve(
                SourceRef.parse(raw_ref),
                context.world_snapshot_id,
                request_scope=context.owner_scope,
                allow_historical=context.allow_historical,
            )
        except (SourceRegistryError, ValueError):
            return None


def _winner_supports_outcome(
    contradiction: ContradictionProposal,
    resolution: ContradictionResolution,
) -> bool:
    if resolution is ContradictionResolution.SOURCE_A_PRECEDES:
        return contradiction.source_a_supports_outcome
    if resolution is ContradictionResolution.SOURCE_B_PRECEDES:
        return contradiction.source_b_supports_outcome
    raise ValueError("unresolved contradiction has no winning source")
