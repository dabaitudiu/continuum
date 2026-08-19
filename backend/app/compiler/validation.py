from __future__ import annotations

from collections.abc import Iterable

from app.compiler.context import CompilationContext
from app.compiler.models import (
    ClaimType,
    CompilationDisposition,
    DecisionDraft,
    DependencyRef,
    DependencyRelation,
    FindingSeverity,
    Materiality,
    ResolvedDependency,
    ValidationFinding,
    ValidationReport,
    ValidationStage,
)
from app.sources.identity import SourceRef
from app.sources.registry import ResolvedSource, SourceRegistryError


_REFERENCE_CODES = {
    "UNKNOWN_SOURCE_ARTIFACT",
    "UNKNOWN_SOURCE_REVISION",
    "UNKNOWN_PARSED_REPRESENTATION",
    "UNKNOWN_SOURCE_FRAGMENT",
    "UNKNOWN_WORLD_SNAPSHOT",
}
_TEMPORAL_CODES = {
    "STALE_SOURCE_REFERENCE",
    "STALE_PARSED_REPRESENTATION",
    "UNQUALIFIED_HISTORICAL_REFERENCE",
}
_STAGE_ORDER = {
    ValidationStage.SCHEMA: 1,
    ValidationStage.REFERENCE: 2,
    ValidationStage.SCOPE: 3,
    ValidationStage.TEMPORAL: 4,
    ValidationStage.TYPE_RULE: 5,
    ValidationStage.CLAIM_SUPPORT: 6,
    ValidationStage.DECISION_SUPPORT: 7,
    ValidationStage.SECURITY: 8,
}


class DeterministicDraftValidator:
    """Resolve V2–V4 dependencies against the bound source snapshot."""

    def validate(
        self,
        draft: DecisionDraft,
        context: object,
    ) -> ValidationReport:
        if not isinstance(context, CompilationContext):
            raise TypeError("validator requires CompilationContext")

        findings: list[ValidationFinding] = []
        resolved_dependencies: list[ResolvedDependency] = []
        for target_kind, target_local_id, dependency in _dependencies(draft):
            if dependency.source_ref not in context.allowed_source_refs:
                findings.append(
                    _finding(
                        sequence=len(findings),
                        stage=ValidationStage.SCOPE,
                        code="UNAUTHORIZED_SOURCE_REFERENCE",
                        message="source ref is outside the request-scoped allowlist",
                        source_ref=dependency.source_ref,
                        claim_local_id=(
                            target_local_id if target_kind == "CLAIM" else None
                        ),
                    )
                )
                continue
            try:
                parsed_ref = SourceRef.parse(dependency.source_ref)
            except ValueError:
                findings.append(
                    _finding(
                        sequence=len(findings),
                        stage=ValidationStage.REFERENCE,
                        code="SOURCE_REF_INVALID",
                        message="source ref is not a canonical parseable identifier",
                        source_ref=dependency.source_ref,
                        claim_local_id=(
                            target_local_id if target_kind == "CLAIM" else None
                        ),
                    )
                )
                continue

            try:
                resolved = context.source_registry.resolve(
                    parsed_ref,
                    context.world_snapshot_id,
                    request_scope=context.owner_scope,
                    allow_historical=context.allow_historical,
                )
            except SourceRegistryError as error:
                stage = _stage_for_registry_error(error.code)
                findings.append(
                    _finding(
                        sequence=len(findings),
                        stage=stage,
                        code=error.code,
                        message=error.message,
                        source_ref=dependency.source_ref,
                        claim_local_id=(
                            target_local_id if target_kind == "CLAIM" else None
                        ),
                    )
                )
                continue

            resolved_dependencies.append(
                _resolved_dependency(
                    dependency,
                    resolved,
                    target_kind=target_kind,
                    target_local_id=target_local_id,
                )
            )

        early_disposition = _disposition(findings)
        if early_disposition is None:
            findings.extend(
                _type_rule_findings(
                    draft,
                    resolved_dependencies,
                    sequence_start=len(findings),
                )
            )
            findings.extend(
                _claim_graph_findings(
                    draft,
                    sequence_start=len(findings),
                )
            )
            findings.extend(
                _support_findings(
                    draft,
                    context,
                    resolved_dependencies,
                    sequence_start=len(findings),
                )
            )

        findings.sort(
            key=lambda finding: (
                _STAGE_ORDER[finding.stage],
                finding.source_ref or "",
                finding.code,
            )
        )
        disposition = _disposition(findings)
        return ValidationReport(
            findings=findings,
            resolved_dependencies=(
                [] if disposition is not None else resolved_dependencies
            ),
            disposition=disposition,
        )


def _dependencies(
    draft: DecisionDraft,
) -> Iterable[tuple[str, str, DependencyRef]]:
    for claim in draft.claims:
        for dependency in claim.dependencies:
            yield "CLAIM", claim.claim_local_id, dependency
    for dependency in draft.decision_dependencies:
        yield "DECISION", draft.request_id, dependency


def _stage_for_registry_error(code: str) -> ValidationStage:
    if code == "UNAUTHORIZED_SOURCE_REFERENCE":
        return ValidationStage.SCOPE
    if code in _TEMPORAL_CODES:
        return ValidationStage.TEMPORAL
    if code in _REFERENCE_CODES:
        return ValidationStage.REFERENCE
    return ValidationStage.REFERENCE


def _finding(
    *,
    sequence: int,
    stage: ValidationStage,
    code: str,
    message: str,
    source_ref: str | None,
    claim_local_id: str | None,
) -> ValidationFinding:
    return ValidationFinding(
        finding_id=f"validation:{sequence:04d}:{code.lower()}",
        stage=stage,
        code=code,
        severity=FindingSeverity.ERROR,
        message=message,
        claim_local_id=claim_local_id,
        source_ref=source_ref,
        blocking=True,
    )


def _resolved_dependency(
    dependency: DependencyRef,
    resolved: ResolvedSource,
    *,
    target_kind: str,
    target_local_id: str,
) -> ResolvedDependency:
    return ResolvedDependency(
        proposed_ref=dependency.source_ref,
        canonical_ref=str(resolved.ref),
        target_kind=target_kind,
        target_local_id=target_local_id,
        relation=dependency.relation,
        materiality=dependency.materiality,
        purpose=dependency.purpose,
        artifact_type=resolved.artifact.artifact_type.value,
        source_type=resolved.artifact.source_type.value,
        trust_class=resolved.artifact.trust_class.value,
        authority_rank=resolved.artifact.authority_rank,
        revision_id=resolved.revision.revision_id,
        revision_label=resolved.revision.revision_label,
        representation_id=resolved.representation.representation_id,
        source_hash=resolved.revision.content_hash,
        fragment_hash=resolved.fragment.text_hash,
        is_historical=resolved.is_historical,
    )


def _disposition(
    findings: list[ValidationFinding],
) -> CompilationDisposition | None:
    if any(
        finding.stage in {ValidationStage.REFERENCE, ValidationStage.SCOPE}
        for finding in findings
    ):
        return CompilationDisposition.REJECTED_INVALID_REFERENCE
    if any(finding.stage is ValidationStage.TEMPORAL for finding in findings):
        return CompilationDisposition.REJECTED_STALE_SOURCE
    if any(finding.stage is ValidationStage.TYPE_RULE for finding in findings):
        return CompilationDisposition.REJECTED_SCHEMA
    if any(
        finding.stage
        in {ValidationStage.CLAIM_SUPPORT, ValidationStage.DECISION_SUPPORT}
        for finding in findings
    ):
        return CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    return None


def _type_rule_findings(
    draft: DecisionDraft,
    resolved_dependencies: list[ResolvedDependency],
    *,
    sequence_start: int,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for dependency in resolved_dependencies:
        valid_source = True
        if dependency.relation is DependencyRelation.GOVERNED_BY:
            valid_source = dependency.source_type == "POLICY"
        elif dependency.relation is DependencyRelation.AUTHORIZES:
            valid_source = dependency.source_type == "HUMAN_APPROVAL"
        if valid_source:
            continue
        findings.append(
            _finding(
                sequence=sequence_start + len(findings),
                stage=ValidationStage.TYPE_RULE,
                code="RELATION_SOURCE_TYPE_INVALID",
                message=(
                    f"{dependency.relation.value} is not allowed from "
                    f"{dependency.source_type}"
                ),
                source_ref=dependency.canonical_ref,
                claim_local_id=(
                    dependency.target_local_id
                    if dependency.target_kind == "CLAIM"
                    else None
                ),
            )
        )
    return findings


def _claim_graph_findings(
    draft: DecisionDraft,
    *,
    sequence_start: int,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    claim_ids = {claim.claim_local_id for claim in draft.claims}
    graph = {
        claim.claim_local_id: tuple(claim.derived_from_claims)
        for claim in draft.claims
    }
    for claim in draft.claims:
        for derived_id in claim.derived_from_claims:
            if derived_id not in claim_ids:
                findings.append(
                    _finding(
                        sequence=sequence_start + len(findings),
                        stage=ValidationStage.TYPE_RULE,
                        code="UNKNOWN_DERIVED_CLAIM",
                        message=f"derived claim does not exist: {derived_id}",
                        source_ref=None,
                        claim_local_id=claim.claim_local_id,
                    )
                )
            elif derived_id == claim.claim_local_id:
                findings.append(
                    _finding(
                        sequence=sequence_start + len(findings),
                        stage=ValidationStage.TYPE_RULE,
                        code="DERIVED_CLAIM_SELF_REFERENCE",
                        message="a claim cannot derive from itself",
                        source_ref=None,
                        claim_local_id=claim.claim_local_id,
                    )
                )
    if not findings and _has_cycle(graph):
        findings.append(
            _finding(
                sequence=sequence_start,
                stage=ValidationStage.TYPE_RULE,
                code="DERIVED_CLAIM_CYCLE",
                message="derived claim graph contains a cycle",
                source_ref=None,
                claim_local_id=None,
            )
        )
    return findings


def _has_cycle(graph: dict[str, tuple[str, ...]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dependency in graph.get(node, ()):
            if dependency in graph and visit(dependency):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in sorted(graph))


def _support_findings(
    draft: DecisionDraft,
    context: CompilationContext,
    resolved_dependencies: list[ResolvedDependency],
    *,
    sequence_start: int,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    supported_claim_ids = {
        dependency.target_local_id
        for dependency in resolved_dependencies
        if dependency.target_kind == "CLAIM"
    }
    for claim in draft.claims:
        if (
            claim.materiality is Materiality.CRITICAL
            and claim.claim_type in {ClaimType.FACT, ClaimType.RULE}
            and claim.claim_local_id not in supported_claim_ids
            and not claim.derived_from_claims
        ):
            findings.append(
                _finding(
                    sequence=sequence_start + len(findings),
                    stage=ValidationStage.CLAIM_SUPPORT,
                    code="CRITICAL_CLAIM_UNSUPPORTED",
                    message="critical fact or rule has no source or derived support",
                    source_ref=None,
                    claim_local_id=claim.claim_local_id,
                )
            )

    has_critical_path = any(
        dependency.materiality is Materiality.CRITICAL
        for dependency in resolved_dependencies
    )
    if context.risk_class.value == "HIGH" and not has_critical_path:
        findings.append(
            _finding(
                sequence=sequence_start + len(findings),
                stage=ValidationStage.DECISION_SUPPORT,
                code="HIGH_RISK_DECISION_UNSUPPORTED",
                message="high-risk outcome has no critical dependency path",
                source_ref=None,
                claim_local_id=None,
            )
        )

    for index, question in enumerate(draft.unresolved_questions):
        if not question.blocking:
            continue
        findings.append(
            _finding(
                sequence=sequence_start + len(findings),
                stage=ValidationStage.DECISION_SUPPORT,
                code="BLOCKING_QUESTION_UNRESOLVED",
                message=f"blocking unresolved question {index + 1}: {question.question}",
                source_ref=None,
                claim_local_id=None,
            )
        )
    return findings
