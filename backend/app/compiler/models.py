from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ClaimType(StrEnum):
    FACT = "FACT"
    RULE = "RULE"
    DERIVED_FACT = "DERIVED_FACT"
    ASSESSMENT = "ASSESSMENT"


class DependencyRelation(StrEnum):
    SUPPORTED_BY = "SUPPORTED_BY"
    GOVERNED_BY = "GOVERNED_BY"
    DERIVED_FROM = "DERIVED_FROM"
    REQUIRES = "REQUIRES"
    AUTHORIZES = "AUTHORIZES"
    CONTRADICTED_BY = "CONTRADICTED_BY"


class Materiality(StrEnum):
    CRITICAL = "CRITICAL"
    SUPPORTING = "SUPPORTING"
    CONTEXTUAL = "CONTEXTUAL"


class CompilationDisposition(StrEnum):
    ACCEPTED = "ACCEPTED"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
    REJECTED_INVALID_REFERENCE = "REJECTED_INVALID_REFERENCE"
    REJECTED_STALE_SOURCE = "REJECTED_STALE_SOURCE"
    REJECTED_CONTRADICTION = "REJECTED_CONTRADICTION"
    REJECTED_INCOMPLETE_DEPENDENCIES = "REJECTED_INCOMPLETE_DEPENDENCIES"
    REJECTED_SCHEMA = "REJECTED_SCHEMA"


class FindingSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationStage(StrEnum):
    SCHEMA = "SCHEMA"
    REFERENCE = "REFERENCE"
    SCOPE = "SCOPE"
    TEMPORAL = "TEMPORAL"
    TYPE_RULE = "TYPE_RULE"
    CLAIM_SUPPORT = "CLAIM_SUPPORT"
    DECISION_SUPPORT = "DECISION_SUPPORT"
    SECURITY = "SECURITY"


class CriticFindingType(StrEnum):
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    IRRELEVANT_DEPENDENCY = "IRRELEVANT_DEPENDENCY"


class ContradictionResolution(StrEnum):
    SOURCE_A_PRECEDES = "SOURCE_A_PRECEDES"
    SOURCE_B_PRECEDES = "SOURCE_B_PRECEDES"
    UNRESOLVED = "UNRESOLVED"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DependencyRef(FrozenModel):
    source_ref: str = Field(min_length=1, max_length=2048)
    relation: DependencyRelation
    materiality: Materiality
    purpose: str | None = Field(default=None, max_length=1000)

    @field_validator("source_ref", "purpose")
    @classmethod
    def _strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip() or value != value.strip():
            raise ValueError("dependency text must be non-empty and trimmed")
        return value


class ClaimDraft(FrozenModel):
    claim_local_id: str = Field(min_length=1, max_length=128)
    claim_type: ClaimType
    statement: str = Field(min_length=1, max_length=2000)
    dependencies: list[DependencyRef] = Field(default_factory=list, max_length=100)
    derived_from_claims: list[str] = Field(default_factory=list, max_length=100)
    materiality: Materiality
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("claim_local_id", "statement")
    @classmethod
    def _require_trimmed_text(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("claim fields must be non-empty and trimmed")
        return value

    @field_validator("derived_from_claims")
    @classmethod
    def _validate_derived_claim_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or value != value.strip() for value in values):
            raise ValueError("derived claim refs must be non-empty and trimmed")
        if len(values) != len(set(values)):
            raise ValueError("derived claim refs must be unique")
        return values


class UnresolvedQuestion(FrozenModel):
    question: str = Field(min_length=1, max_length=1000)
    required_source_type: str = Field(min_length=1, max_length=128)
    blocking: bool

    @field_validator("question", "required_source_type")
    @classmethod
    def _require_trimmed_text(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("question fields must be non-empty and trimmed")
        return value


class ModelMetadata(FrozenModel):
    provider: str = Field(min_length=1, max_length=64)
    model_name: str = Field(min_length=1, max_length=128)
    prompt_version: str = Field(min_length=1, max_length=128)
    temperature: float = Field(ge=0.0, le=2.0)
    execution_id: str = Field(min_length=1, max_length=256)
    model_version: str | None = Field(default=None, max_length=128)
    response_id: str | None = Field(default=None, max_length=256)
    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    @field_validator(
        "provider",
        "model_name",
        "prompt_version",
        "execution_id",
        "model_version",
        "response_id",
    )
    @classmethod
    def _require_trimmed_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip() or value != value.strip():
            raise ValueError("model metadata fields must be non-empty and trimmed")
        return value


class DecisionProposal(FrozenModel):
    """Provider-neutral structured model output before trusted metadata is attached."""

    decision_type: str = Field(min_length=1, max_length=128)
    proposed_outcome: str = Field(min_length=1, max_length=256)
    claims: list[ClaimDraft] = Field(default_factory=list, max_length=100)
    decision_dependencies: list[DependencyRef] = Field(
        default_factory=list,
        max_length=100,
    )
    unresolved_questions: list[UnresolvedQuestion] = Field(
        default_factory=list,
        max_length=50,
    )
    rationale_summary: str = Field(min_length=1, max_length=4000)

    @field_validator("decision_type", "proposed_outcome", "rationale_summary")
    @classmethod
    def _require_trimmed_text(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("decision proposal fields must be non-empty and trimmed")
        return value

    @model_validator(mode="after")
    def _require_unique_claim_ids(self) -> DecisionProposal:
        seen: set[str] = set()
        for claim in self.claims:
            if claim.claim_local_id in seen:
                raise ValueError(f"duplicate claim_local_id: {claim.claim_local_id}")
            seen.add(claim.claim_local_id)
        return self

    def to_draft(
        self,
        *,
        request_id: str,
        model_metadata: ModelMetadata,
    ) -> DecisionDraft:
        return DecisionDraft(
            request_id=request_id,
            **self.model_dump(),
            model_metadata=model_metadata,
        )


class DecisionDraft(FrozenModel):
    request_id: str = Field(min_length=1, max_length=256)
    decision_type: str = Field(min_length=1, max_length=128)
    proposed_outcome: str = Field(min_length=1, max_length=256)
    claims: list[ClaimDraft] = Field(default_factory=list, max_length=100)
    decision_dependencies: list[DependencyRef] = Field(
        default_factory=list,
        max_length=100,
    )
    unresolved_questions: list[UnresolvedQuestion] = Field(
        default_factory=list,
        max_length=50,
    )
    rationale_summary: str = Field(min_length=1, max_length=4000)
    model_metadata: ModelMetadata

    @field_validator(
        "request_id",
        "decision_type",
        "proposed_outcome",
        "rationale_summary",
    )
    @classmethod
    def _require_trimmed_text(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("decision draft fields must be non-empty and trimmed")
        return value

    @model_validator(mode="after")
    def _require_unique_claim_ids(self) -> DecisionDraft:
        seen: set[str] = set()
        for claim in self.claims:
            if claim.claim_local_id in seen:
                raise ValueError(f"duplicate claim_local_id: {claim.claim_local_id}")
            seen.add(claim.claim_local_id)
        return self


class ValidationFinding(FrozenModel):
    finding_id: str = Field(min_length=1, max_length=256)
    stage: ValidationStage
    code: str = Field(min_length=1, max_length=128)
    severity: FindingSeverity
    message: str = Field(min_length=1, max_length=2000)
    claim_local_id: str | None = Field(default=None, max_length=128)
    source_ref: str | None = Field(default=None, max_length=2048)
    blocking: bool = False


class CriticFinding(FrozenModel):
    finding_id: str = Field(min_length=1, max_length=256)
    finding_type: CriticFindingType
    severity: Materiality
    message: str = Field(min_length=1, max_length=2000)
    candidate_ref: str | None = Field(default=None, max_length=2048)
    claim_local_id: str | None = Field(default=None, max_length=128)
    expected_relation: DependencyRelation | None = None
    expected_materiality: Materiality | None = None


class MissingDependencyProposal(FrozenModel):
    candidate_ref: str = Field(min_length=1, max_length=2048)
    severity: Materiality
    why: str = Field(min_length=1, max_length=2000)
    claim_local_id: str | None = Field(default=None, max_length=128)
    expected_relation: DependencyRelation = DependencyRelation.SUPPORTED_BY
    expected_materiality: Materiality = Materiality.CRITICAL


class UnsupportedClaimProposal(FrozenModel):
    claim_local_id: str = Field(min_length=1, max_length=128)
    severity: Materiality
    why: str = Field(min_length=1, max_length=2000)


class IrrelevantDependencyProposal(FrozenModel):
    source_ref: str = Field(min_length=1, max_length=2048)
    why: str = Field(min_length=1, max_length=2000)


class ContradictionProposal(FrozenModel):
    claim_or_topic: str = Field(min_length=1, max_length=1000)
    source_ref_a: str = Field(min_length=1, max_length=2048)
    source_ref_b: str = Field(min_length=1, max_length=2048)
    severity: Materiality
    source_a_supports_outcome: bool
    source_b_supports_outcome: bool


class CriticProposal(FrozenModel):
    missing_dependencies: list[MissingDependencyProposal] = Field(
        default_factory=list,
        max_length=100,
    )
    unsupported_claims: list[UnsupportedClaimProposal] = Field(
        default_factory=list,
        max_length=100,
    )
    irrelevant_dependencies: list[IrrelevantDependencyProposal] = Field(
        default_factory=list,
        max_length=100,
    )
    possible_contradictions: list[ContradictionProposal] = Field(
        default_factory=list,
        max_length=100,
    )


class CriticOutcome(FrozenModel):
    """Critic proposal plus transport-observed metadata attached by trusted code."""

    proposal: CriticProposal
    model_metadata: ModelMetadata


class ContradictionFinding(FrozenModel):
    finding_id: str = Field(min_length=1, max_length=256)
    claim_or_topic: str = Field(min_length=1, max_length=1000)
    source_ref_a: str = Field(min_length=1, max_length=2048)
    source_ref_b: str = Field(min_length=1, max_length=2048)
    severity: Materiality
    precedence_rule_applied: str | None = Field(default=None, max_length=256)
    resolution: ContradictionResolution


class DecisionCandidate(FrozenModel):
    decision_id: str = Field(min_length=1, max_length=256)
    decision_type: str = Field(min_length=1, max_length=128)
    outcome: str = Field(min_length=1, max_length=256)
    rationale_summary: str = Field(min_length=1, max_length=4000)


class CanonicalClaim(FrozenModel):
    claim_id: str = Field(min_length=1, max_length=256)
    claim_local_id: str = Field(min_length=1, max_length=128)
    claim_type: ClaimType
    statement: str = Field(min_length=1, max_length=2000)
    materiality: Materiality
    confidence: float = Field(ge=0.0, le=1.0)


class CanonicalEdge(FrozenModel):
    edge_id: str = Field(min_length=1, max_length=256)
    source_kind: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=2048)
    target_kind: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=256)
    relation: DependencyRelation
    materiality: Materiality
    purpose: str | None = Field(default=None, max_length=1000)


class ResolvedDependency(FrozenModel):
    proposed_ref: str = Field(min_length=1, max_length=2048)
    canonical_ref: str = Field(min_length=1, max_length=2048)
    target_kind: str = Field(min_length=1, max_length=64)
    target_local_id: str = Field(min_length=1, max_length=256)
    relation: DependencyRelation
    materiality: Materiality
    purpose: str | None = Field(default=None, max_length=1000)
    artifact_type: str = Field(min_length=1, max_length=64)
    source_type: str = Field(min_length=1, max_length=64)
    trust_class: str = Field(min_length=1, max_length=64)
    authority_rank: int = Field(ge=0)
    revision_id: str = Field(min_length=1, max_length=256)
    revision_label: str = Field(min_length=1, max_length=256)
    representation_id: str = Field(min_length=1, max_length=256)
    source_hash: str
    fragment_hash: str
    is_historical: bool

    @field_validator("source_hash", "fragment_hash")
    @classmethod
    def _validate_source_hash(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("source dependency hashes must be lowercase SHA-256")
        return value


class ValidationReport(FrozenModel):
    findings: list[ValidationFinding] = Field(default_factory=list)
    resolved_dependencies: list[ResolvedDependency] = Field(default_factory=list)
    disposition: CompilationDisposition | None = None


class CriticReview(FrozenModel):
    findings: list[CriticFinding] = Field(default_factory=list)
    contradictions: list[ContradictionFinding] = Field(default_factory=list)
    disposition: CompilationDisposition | None = None
    model_metadata: ModelMetadata | None = None


class CanonicalCompilation(FrozenModel):
    compilation_id: str = Field(min_length=1, max_length=256)
    compilation_hash: str
    decision_candidate: DecisionCandidate
    canonical_claims: list[CanonicalClaim] = Field(default_factory=list)
    canonical_edges: list[CanonicalEdge] = Field(default_factory=list)

    @field_validator("compilation_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("compilation_hash must be lowercase SHA-256")
        return value


class CompilationResult(FrozenModel):
    compilation_id: str = Field(min_length=1, max_length=256)
    request_id: str = Field(min_length=1, max_length=256)
    status: CompilationDisposition
    decision_candidate: DecisionCandidate | None = None
    canonical_claims: list[CanonicalClaim] = Field(default_factory=list)
    canonical_edges: list[CanonicalEdge] = Field(default_factory=list)
    validation_findings: list[ValidationFinding] = Field(default_factory=list)
    critic_findings: list[CriticFinding] = Field(default_factory=list)
    contradictions: list[ContradictionFinding] = Field(default_factory=list)
    compiler_version: str = Field(min_length=1, max_length=128)
    validation_policy_version: str = Field(min_length=1, max_length=128)
    compilation_hash: str | None = None
    model_metadata: ModelMetadata | None = None
    critic_model_metadata: ModelMetadata | None = None

    @field_validator("compilation_hash")
    @classmethod
    def _validate_optional_hash(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("compilation_hash must be lowercase SHA-256")
        return value
