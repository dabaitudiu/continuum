from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter_ns

from pydantic import BaseModel, ConfigDict, Field

from app.compiler.benchmark.corpus import (
    BenchmarkCase,
    BenchmarkDomain,
    BenchmarkSource,
)
from app.compiler.benchmark.metrics import (
    CorrectedMetricSnapshot,
    EvaluationRecord,
    MetricSnapshot,
    measure,
    measure_corrected,
)
from app.compiler.benchmark.runner import (
    MutationTerminal,
    Prediction,
    RuntimeMutationEvidence,
    UsageSummary,
    evaluate_runtime_mutation,
    evaluate_runtime_mutation_evidence,
)
from app.compiler.budget import ModelPricing, ModelUsage, SettledUsageSummary
from app.compiler.canonicalization import DeterministicCanonicalizer
from app.compiler.context import CompilationContext, RiskClass
from app.compiler.models import (
    CanonicalClaim,
    CanonicalEdge,
    CompilationDisposition,
    CriticFindingType,
    CriticReview,
    DecisionCandidate,
    DecisionDraft,
    Materiality,
    ValidationReport,
)
from app.compiler.reasoner import DependencyReasoner
from app.compiler.reasoner_types import ReasoningRequest
from app.compiler.review import (
    AuthorityPrecedencePolicy,
    CompletenessCritic,
    DeterministicReviewGate,
)
from app.compiler.tools import ReadOnlySourceTools
from app.compiler.validation import DeterministicDraftValidator
from app.sources.identity import Artifact, ingest_json_revision
from app.sources.registry import InMemorySourceRegistry, WorldSnapshot

BENCHMARK_TIME = datetime(2026, 8, 19, 0, 0, tzinfo=UTC)
BENCHMARK_SCOPE = "benchmark:v1"


@dataclass(frozen=True, slots=True)
class BenchmarkCaseRuntime:
    context: CompilationContext
    tools: ReadOnlySourceTools
    request: ReasoningRequest


class FrozenEvidenceModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AblationArmEvidence(FrozenEvidenceModel):
    predicted_critical_refs: tuple[str, ...] = ()
    accepted_canonical_refs: tuple[str, ...] = ()
    accepted_dependency_edges: tuple[CanonicalEdge, ...] = ()
    accepted_decision_candidate: DecisionCandidate | None = None
    accepted_canonical_claims: tuple[CanonicalClaim, ...] = ()
    accepted_compilation_hash: str | None = None
    detected_contradictions: tuple[tuple[str, str], ...] = ()
    detected_contradiction_severities: tuple[tuple[str, str, str], ...] = ()
    proposed_outcome: str
    disposition: CompilationDisposition
    disposition_stage: str
    repeat_compilation_hashes: tuple[str, ...] = ()
    mutation: RuntimeMutationEvidence


class PairedCaseEvidence(FrozenEvidenceModel):
    case_id: str
    domain: str
    case_class: str
    required_critical_refs: tuple[str, ...]
    known_source_refs: tuple[str, ...]
    expected_blocking_contradictions: tuple[tuple[str, str], ...]
    allowed_outcomes: tuple[str, ...]
    must_block: bool
    expected_stale_after_mutation: bool
    mutation_source_ref: str
    draft_digest: str
    reasoner_duration_ms: float = Field(ge=0)
    critic_duration_ms: float = Field(ge=0)
    draft: DecisionDraft
    validation: ValidationReport
    critic_review: CriticReview
    reasoner_critical_refs: tuple[str, ...]
    critic_added_critical_refs: tuple[str, ...]
    reasoner_only: AblationArmEvidence
    critic_on: AblationArmEvidence


class AblationRunConfiguration(FrozenEvidenceModel):
    provider: str
    model: str
    reasoner_prompt_version: str
    critic_prompt_version: str
    temperature: float | None
    reasoning_effort: str
    service_tier: str
    case_set: str
    compiler_version: str = "sdc-1"
    validation_policy_version: str = "validation-v1"
    metric_version: str = "ablation-metrics-v3"
    pricing_version: str | None = None
    evidence_source_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )
    recomputed_from_run_id: str | None = None
    cumulative_budget_usd: str = "10"
    max_incremental_cost_usd: str
    max_model_posts: int = 120


class AblationStageUsage(FrozenEvidenceModel):
    settled_calls: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    actual_cost_usd: str = "0"
    duration_ms: float = Field(default=0, ge=0)


class AblationUsage(FrozenEvidenceModel):
    reasoner: AblationStageUsage = AblationStageUsage()
    critic: AblationStageUsage = AblationStageUsage()
    total: AblationStageUsage = AblationStageUsage()


class AblationArmMetrics(FrozenEvidenceModel):
    legacy: MetricSnapshot
    corrected: CorrectedMetricSnapshot


class CriticEffectSummary(FrozenEvidenceModel):
    required_omissions_recovered: int
    false_positive_refs_added: int
    correct_contradictions_added: int
    incorrect_contradictions_added: int
    accepted_case_delta: int
    true_omission_blocks: int
    correct_contradiction_blocks: int
    spurious_blocks_added: int
    unsafe_accepted_cases: int


class PairedAblationRun(FrozenEvidenceModel):
    schema_version: str = "continuum-critic-ablation-v1"
    run_id: str
    configuration: AblationRunConfiguration
    records: tuple[PairedCaseEvidence, ...]
    reasoner_only: AblationArmMetrics
    critic_on: AblationArmMetrics
    critic_effect: CriticEffectSummary
    usage: AblationUsage = AblationUsage()


def build_case_runtime(
    case: BenchmarkCase,
    *,
    execution_id: str,
) -> BenchmarkCaseRuntime:
    registry = InMemorySourceRegistry()
    by_artifact: defaultdict[str, list[BenchmarkSource]] = defaultdict(list)
    for source in case.sources:
        by_artifact[source.artifact_id].append(source)

    current_revisions: dict[str, str] = {}
    current_representations: dict[str, str] = {}
    for artifact_id, artifact_sources in sorted(by_artifact.items()):
        first = artifact_sources[0]
        artifact = Artifact(
            artifact_id=artifact_id,
            artifact_type=first.artifact_type,
            logical_key=first.logical_key,
            owner_scope=BENCHMARK_SCOPE,
            trust_class=first.trust_class,
            source_type=first.source_type,
            authority_rank=first.authority_rank,
            created_at=BENCHMARK_TIME,
        )
        registry.add_artifact(artifact)
        by_revision: defaultdict[str, list[BenchmarkSource]] = defaultdict(list)
        for source in artifact_sources:
            _same_artifact_metadata(first, source)
            by_revision[source.revision_label].append(source)

        current_count = 0
        for revision_label, revision_sources in sorted(by_revision.items()):
            fragments = {
                _top_level_key(source.logical_path): source.content
                for source in revision_sources
            }
            ingested = ingest_json_revision(
                artifact,
                revision_label=revision_label,
                value=fragments,
                created_at=BENCHMARK_TIME,
                valid_from=BENCHMARK_TIME,
                parser_version=revision_sources[0].parser_version,
            )
            actual_refs = {
                str(ingested.fragment_at(source.logical_path).source_ref())
                for source in revision_sources
            }
            expected_refs = {source.source_ref for source in revision_sources}
            if actual_refs != expected_refs:
                raise ValueError(
                    f"committed source identity is not reproducible: {case.case_id}"
                )
            registry.add_revision(ingested.revision)
            registry.add_representation(
                ingested.representation,
                ingested.fragments,
                fragment_values=ingested.fragment_values,
            )
            current_flags = {source.current for source in revision_sources}
            if len(current_flags) != 1:
                raise ValueError(
                    "all fragments in a revision must share current status"
                )
            if True in current_flags:
                current_count += 1
                current_revisions[artifact_id] = ingested.revision.revision_id
                current_representations[ingested.revision.revision_id] = (
                    ingested.representation.representation_id
                )
        if current_count != 1:
            raise ValueError(
                f"artifact requires exactly one current revision: {artifact_id}"
            )

    world_snapshot_id = f"world:{case.case_id}"
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id=world_snapshot_id,
            owner_scope=BENCHMARK_SCOPE,
            current_revisions=current_revisions,
            current_representations=current_representations,
            created_at=BENCHMARK_TIME,
        )
    )
    context = CompilationContext(
        source_registry=registry,
        world_snapshot_id=world_snapshot_id,
        owner_scope=BENCHMARK_SCOPE,
        allowed_source_refs=frozenset(source.source_ref for source in case.sources),
        risk_class=RiskClass.HIGH,
        allow_historical=True,
        decision_context={
            "benchmark_case_id": case.case_id,
            "task": case.task,
        },
    )
    return BenchmarkCaseRuntime(
        context=context,
        tools=ReadOnlySourceTools(context),
        request=ReasoningRequest(
            request_id=f"request:{case.case_id}",
            execution_id=execution_id,
            decision_type=case.decision_type,
            task=case.task,
            risk_class=RiskClass.HIGH,
            outcome_options=("APPROVED", "DENIED", "NEEDS_HUMAN_REVIEW"),
        ),
    )


class ModelCompilerSubject:
    """Runs the real reasoner→validator→critic→canonicalizer benchmark path."""

    def __init__(
        self,
        *,
        reasoner: DependencyReasoner,
        critic: CompletenessCritic,
        reasoner_pricing: ModelPricing | None = None,
        critic_pricing: ModelPricing | None = None,
        compiler_version: str = "sdc-1",
        validation_policy_version: str = "validation-v1",
        execution_namespace: str = "benchmark",
        settled_usage_supplier: Callable[[], SettledUsageSummary] | None = None,
    ) -> None:
        self._reasoner = reasoner
        self._review_gate = DeterministicReviewGate(
            critic=critic,
            precedence_policy=AuthorityPrecedencePolicy(),
        )
        self._canonicalizer = DeterministicCanonicalizer(
            compiler_version=compiler_version,
            validation_policy_version=validation_policy_version,
        )
        self._reasoner_pricing = reasoner_pricing
        self._critic_pricing = critic_pricing
        self._execution_namespace = execution_namespace
        self._settled_usage_supplier = settled_usage_supplier
        self._input_tokens = 0
        self._cached_input_tokens = 0
        self._output_tokens = 0
        self._cost_usd = Decimal(0)

    def predict(self, case: BenchmarkCase, *, run_index: int) -> Prediction:
        runtime = build_case_runtime(
            case,
            execution_id=(
                f"{self._execution_namespace}:{case.case_id}:run:{run_index}"
            ),
        )
        draft = self._reasoner.propose(runtime.request, runtime.tools)
        self._record_usage(draft.model_metadata, self._reasoner_pricing)
        validation = DeterministicDraftValidator().validate(
            draft,
            runtime.context,
        )
        review = CriticReview()
        if validation.disposition is None:
            review = self._review_gate.review(draft, runtime.context)
            if review.model_metadata is not None:
                self._record_usage(review.model_metadata, self._critic_pricing)

        draft_critical = {
            dependency.source_ref
            for claim in draft.claims
            for dependency in claim.dependencies
            if dependency.materiality is Materiality.CRITICAL
        } | {
            dependency.source_ref
            for dependency in draft.decision_dependencies
            if dependency.materiality is Materiality.CRITICAL
        }
        known_refs = {source.source_ref for source in case.sources}
        critic_recovered = {
            finding.candidate_ref
            for finding in review.findings
            if finding.finding_type is CriticFindingType.MISSING_DEPENDENCY
            and finding.severity is Materiality.CRITICAL
            and finding.candidate_ref in known_refs
        }
        critical_refs = tuple(sorted(draft_critical | critic_recovered))

        accepted_refs: tuple[str, ...] = ()
        accepted_edges: tuple[tuple[str, str, str], ...] = ()
        repeat_hashes: tuple[str, ...] = ()
        if validation.disposition is None and review.disposition is None:
            compilation = self._canonicalizer.compile(
                draft,
                runtime.context,
                validation,
                review,
            )
            accepted_refs = tuple(
                sorted(
                    {
                        edge.source_id
                        for edge in compilation.canonical_edges
                        if edge.source_kind == "SOURCE_FRAGMENT"
                        and edge.materiality is Materiality.CRITICAL
                    }
                )
            )
            accepted_edges = tuple(
                sorted(
                    (
                        edge.source_id,
                        edge.relation.value,
                        edge.materiality.value,
                    )
                    for edge in compilation.canonical_edges
                    if edge.source_kind == "SOURCE_FRAGMENT"
                )
            )
            variants = (
                draft,
                draft.model_copy(
                    update={
                        "claims": [
                            claim.model_copy(
                                update={
                                    "dependencies": list(reversed(claim.dependencies))
                                },
                                deep=True,
                            )
                            for claim in reversed(draft.claims)
                        ],
                        "decision_dependencies": list(
                            reversed(draft.decision_dependencies)
                        ),
                    },
                    deep=True,
                ),
                draft.model_validate(draft.model_dump(mode="json")),
            )
            repeated: list[str] = []
            for variant in variants:
                variant_validation = DeterministicDraftValidator().validate(
                    variant,
                    runtime.context,
                )
                if variant_validation.disposition is not None:
                    repeated.append(f"blocked:{variant_validation.disposition.value}")
                    continue
                repeated.append(
                    self._canonicalizer.compile(
                        variant,
                        runtime.context,
                        variant_validation,
                        review,
                    ).compilation_hash
                )
            repeat_hashes = tuple(repeated)
        contradictions = tuple(
            (finding.source_ref_a, finding.source_ref_b)
            for finding in review.contradictions
        )
        disposition = (
            validation.disposition
            or review.disposition
            or CompilationDisposition.ACCEPTED
        )
        prediction = Prediction(
            critical_refs=critical_refs,
            accepted_canonical_refs=accepted_refs,
            accepted_dependency_edges=accepted_edges,
            detected_contradictions=contradictions,
            detected_contradiction_severities=tuple(
                (
                    finding.source_ref_a,
                    finding.source_ref_b,
                    finding.severity.value,
                )
                for finding in review.contradictions
            ),
            proposed_outcome=draft.proposed_outcome,
            compilation_disposition=disposition,
            repeat_compilation_hashes=repeat_hashes,
        )
        return prediction.model_copy(
            update={
                "predicted_stale_after_mutation": evaluate_runtime_mutation(
                    case,
                    prediction,
                )
            }
        )

    def usage_summary(self) -> UsageSummary:
        if self._settled_usage_supplier is not None:
            settled = self._settled_usage_supplier()
            return UsageSummary(
                input_tokens=settled.usage.input_tokens,
                cached_input_tokens=settled.usage.cached_input_tokens,
                cache_write_tokens=settled.usage.cache_write_tokens,
                output_tokens=settled.usage.output_tokens,
                actual_cost_usd=str(settled.actual_cost_usd),
            )
        return UsageSummary(
            input_tokens=self._input_tokens,
            cached_input_tokens=self._cached_input_tokens,
            cache_write_tokens=0,
            output_tokens=self._output_tokens,
            actual_cost_usd=str(self._cost_usd),
        )

    def _record_usage(self, metadata, pricing: ModelPricing | None) -> None:  # type: ignore[no-untyped-def]
        usage = ModelUsage(
            input_tokens=metadata.input_tokens,
            cached_input_tokens=metadata.cached_input_tokens,
            output_tokens=metadata.output_tokens,
        )
        self._input_tokens += usage.input_tokens
        self._cached_input_tokens += usage.cached_input_tokens
        self._output_tokens += usage.output_tokens
        if pricing is not None:
            self._cost_usd += pricing.cost(usage)


class PairedAblationSubject:
    """Evaluate critic off/on against one immutable live reasoner draft."""

    def __init__(
        self,
        *,
        reasoner: DependencyReasoner,
        critic: CompletenessCritic,
        compiler_version: str = "sdc-1",
        validation_policy_version: str = "validation-v1",
        execution_namespace: str = "benchmark-ablation",
    ) -> None:
        self._reasoner = reasoner
        self._review_gate = DeterministicReviewGate(
            critic=critic,
            precedence_policy=AuthorityPrecedencePolicy(),
        )
        self._canonicalizer = DeterministicCanonicalizer(
            compiler_version=compiler_version,
            validation_policy_version=validation_policy_version,
        )
        self._execution_namespace = execution_namespace

    def evaluate(self, case: BenchmarkCase, *, run_index: int) -> PairedCaseEvidence:
        runtime = build_case_runtime(
            case,
            execution_id=(
                f"{self._execution_namespace}:{case.case_id}:run:{run_index}"
            ),
        )
        reasoner_started = perf_counter_ns()
        draft = self._reasoner.propose(runtime.request, runtime.tools)
        reasoner_duration_ms = (perf_counter_ns() - reasoner_started) / 1_000_000
        validation = DeterministicDraftValidator().validate(draft, runtime.context)
        critic_review = CriticReview()
        critic_duration_ms = 0.0
        if validation.disposition is None:
            critic_started = perf_counter_ns()
            critic_review = self._review_gate.review(draft, runtime.context)
            critic_duration_ms = (perf_counter_ns() - critic_started) / 1_000_000

        reasoner_refs = _draft_critical_refs(draft)
        critic_added = _critic_added_critical_refs(
            critic_review,
            reasoner_refs,
        )
        reasoner_only = self._evaluate_arm(
            case,
            draft,
            runtime,
            validation,
            CriticReview(),
            predicted_critical_refs=reasoner_refs,
        )
        critic_on = self._evaluate_arm(
            case,
            draft,
            runtime,
            validation,
            critic_review,
            predicted_critical_refs=tuple(
                sorted(set(reasoner_refs) | set(critic_added))
            ),
        )
        return PairedCaseEvidence(
            case_id=case.case_id,
            domain=case.domain.value,
            case_class=case.case_class.value,
            required_critical_refs=tuple(case.ground_truth.required_critical_refs),
            known_source_refs=tuple(source.source_ref for source in case.sources),
            expected_blocking_contradictions=tuple(
                (finding.source_ref_a, finding.source_ref_b)
                for finding in case.ground_truth.blocking_contradictions
            ),
            allowed_outcomes=tuple(
                case.ground_truth.expected_outcome_constraints.allowed_outcomes
            ),
            must_block=case.ground_truth.expected_outcome_constraints.must_block,
            expected_stale_after_mutation=bool(
                case.mutation.expected_stale_decision_ids
            ),
            mutation_source_ref=case.mutation.source_ref,
            draft_digest=_digest(draft.model_dump(mode="json")),
            reasoner_duration_ms=reasoner_duration_ms,
            critic_duration_ms=critic_duration_ms,
            draft=draft,
            validation=validation,
            critic_review=critic_review,
            reasoner_critical_refs=reasoner_refs,
            critic_added_critical_refs=critic_added,
            reasoner_only=reasoner_only,
            critic_on=critic_on,
        )

    def _evaluate_arm(
        self,
        case: BenchmarkCase,
        draft: DecisionDraft,
        runtime: BenchmarkCaseRuntime,
        validation: ValidationReport,
        review: CriticReview,
        *,
        predicted_critical_refs: tuple[str, ...],
    ) -> AblationArmEvidence:
        disposition = (
            validation.disposition
            or review.disposition
            or CompilationDisposition.ACCEPTED
        )
        canonical_edges: tuple[CanonicalEdge, ...] = ()
        canonical_claims: tuple[CanonicalClaim, ...] = ()
        decision_candidate: DecisionCandidate | None = None
        compilation_hash: str | None = None
        accepted_refs: tuple[str, ...] = ()
        repeat_hashes: tuple[str, ...] = ()
        if disposition is CompilationDisposition.ACCEPTED:
            compilation = self._canonicalizer.compile(
                draft,
                runtime.context,
                validation,
                review,
            )
            canonical_edges = tuple(compilation.canonical_edges)
            canonical_claims = tuple(compilation.canonical_claims)
            decision_candidate = compilation.decision_candidate
            compilation_hash = compilation.compilation_hash
            accepted_refs = tuple(
                sorted(
                    {
                        edge.source_id
                        for edge in canonical_edges
                        if edge.source_kind == "SOURCE_FRAGMENT"
                        and edge.materiality is Materiality.CRITICAL
                    }
                )
            )
            repeat_hashes = _repeat_compilation_hashes(
                draft,
                runtime,
                review,
                self._canonicalizer,
            )
        contradictions = tuple(
            (finding.source_ref_a, finding.source_ref_b)
            for finding in review.contradictions
        )
        prediction = Prediction(
            critical_refs=predicted_critical_refs,
            accepted_canonical_refs=accepted_refs,
            accepted_dependency_edges=tuple(
                sorted(
                    (
                        edge.source_id,
                        edge.relation.value,
                        edge.materiality.value,
                    )
                    for edge in canonical_edges
                    if edge.source_kind == "SOURCE_FRAGMENT"
                )
            ),
            accepted_decision_candidate=decision_candidate,
            accepted_canonical_claims=canonical_claims,
            accepted_canonical_edges=canonical_edges,
            accepted_compilation_hash=compilation_hash,
            detected_contradictions=contradictions,
            detected_contradiction_severities=tuple(
                (
                    finding.source_ref_a,
                    finding.source_ref_b,
                    finding.severity.value,
                )
                for finding in review.contradictions
            ),
            proposed_outcome=draft.proposed_outcome,
            compilation_disposition=disposition,
            repeat_compilation_hashes=repeat_hashes,
        )
        return AblationArmEvidence(
            predicted_critical_refs=predicted_critical_refs,
            accepted_canonical_refs=accepted_refs,
            accepted_dependency_edges=canonical_edges,
            accepted_decision_candidate=decision_candidate,
            accepted_canonical_claims=canonical_claims,
            accepted_compilation_hash=compilation_hash,
            detected_contradictions=prediction.detected_contradictions,
            detected_contradiction_severities=(
                prediction.detected_contradiction_severities
            ),
            proposed_outcome=draft.proposed_outcome,
            disposition=disposition,
            disposition_stage=(
                "VALIDATOR"
                if validation.disposition is not None
                else "CRITIC"
                if review.disposition is not None
                else "ACCEPTED"
            ),
            repeat_compilation_hashes=repeat_hashes,
            mutation=evaluate_runtime_mutation_evidence(case, prediction),
        )


class PairedAblationRunner:
    def __init__(self, cases: list[BenchmarkCase]) -> None:
        if not cases:
            raise ValueError("paired ablation requires at least one case")
        case_ids = [case.case_id for case in cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("paired ablation case IDs must be unique")
        self._cases = tuple(cases)

    def run(
        self,
        subject: PairedAblationSubject,
        configuration: AblationRunConfiguration,
        *,
        usage: AblationUsage | None = None,
        record_observer: Callable[[PairedCaseEvidence], None] | None = None,
    ) -> PairedAblationRun:
        collected_records: list[PairedCaseEvidence] = []
        for case in self._cases:
            record = subject.evaluate(case, run_index=0)
            collected_records.append(record)
            if record_observer is not None:
                record_observer(record)
        records = tuple(collected_records)
        return self.summarize(records, configuration, usage=usage)

    def summarize(
        self,
        records: tuple[PairedCaseEvidence, ...],
        configuration: AblationRunConfiguration,
        *,
        usage: AblationUsage | None = None,
    ) -> PairedAblationRun:
        expected_case_ids = tuple(case.case_id for case in self._cases)
        if tuple(record.case_id for record in records) != expected_case_ids:
            raise ValueError(
                "paired evidence must exactly match the runner's frozen case order"
            )
        reasoner_records = [
            _evaluation_record(record, record.reasoner_only) for record in records
        ]
        critic_records = [
            _evaluation_record(record, record.critic_on) for record in records
        ]
        reasoner_metrics = _arm_metrics(reasoner_records, records, arm="reasoner")
        critic_metrics = _arm_metrics(critic_records, records, arm="critic")
        effect = _critic_effect(records)
        reasoner_duration_ms = sum(record.reasoner_duration_ms for record in records)
        critic_duration_ms = sum(record.critic_duration_ms for record in records)
        observed_usage = usage or AblationUsage(
            reasoner=AblationStageUsage(duration_ms=reasoner_duration_ms),
            critic=AblationStageUsage(duration_ms=critic_duration_ms),
            total=AblationStageUsage(
                duration_ms=reasoner_duration_ms + critic_duration_ms
            ),
        )
        run_id = _digest(
            {
                "schema_version": "continuum-critic-ablation-v1",
                "configuration": configuration.model_dump(mode="json"),
                "case_ids": [record.case_id for record in records],
                "draft_digests": [record.draft_digest for record in records],
            }
        )[:16]
        return PairedAblationRun(
            run_id=f"critic-ablation:{run_id}",
            configuration=configuration,
            records=records,
            reasoner_only=reasoner_metrics,
            critic_on=critic_metrics,
            critic_effect=effect,
            usage=observed_usage,
        )


def recompute_paired_case_derived_evidence(
    record: PairedCaseEvidence,
) -> PairedCaseEvidence:
    """Rebuild evaluator-derived proposal refs from immutable model evidence."""
    if record.draft_digest != _digest(record.draft.model_dump(mode="json")):
        raise ValueError("paired evidence draft digest does not match its raw draft")
    reasoner_refs = _draft_critical_refs(record.draft)
    critic_added = _critic_added_critical_refs(
        record.critic_review,
        reasoner_refs,
    )
    return record.model_copy(
        update={
            "reasoner_critical_refs": reasoner_refs,
            "critic_added_critical_refs": critic_added,
            "reasoner_only": record.reasoner_only.model_copy(
                update={"predicted_critical_refs": reasoner_refs}
            ),
            "critic_on": record.critic_on.model_copy(
                update={
                    "predicted_critical_refs": tuple(
                        sorted(set(reasoner_refs) | set(critic_added))
                    )
                }
            ),
        }
    )


def _evaluation_record(
    evidence: PairedCaseEvidence,
    arm: AblationArmEvidence,
) -> EvaluationRecord:
    return EvaluationRecord(
        case_id=evidence.case_id,
        domain=BenchmarkDomain(evidence.domain),
        required_critical_refs=evidence.required_critical_refs,
        known_source_refs=evidence.known_source_refs,
        expected_blocking_contradictions=(evidence.expected_blocking_contradictions),
        allowed_outcomes=evidence.allowed_outcomes,
        must_block=evidence.must_block,
        expected_stale_after_mutation=evidence.expected_stale_after_mutation,
        predicted_critical_refs=arm.predicted_critical_refs,
        accepted_canonical_refs=arm.accepted_canonical_refs,
        detected_contradictions=arm.detected_contradictions,
        detected_contradiction_severities=(arm.detected_contradiction_severities),
        predicted_outcome=arm.proposed_outcome,
        compilation_disposition=arm.disposition.value,
        predicted_stale_after_mutation=(
            arm.mutation.terminal is MutationTerminal.STALE
        ),
        repeat_compilation_hashes=arm.repeat_compilation_hashes,
    )


def _arm_metrics(
    evaluation_records: list[EvaluationRecord],
    evidence_records: tuple[PairedCaseEvidence, ...],
    *,
    arm: str,
) -> AblationArmMetrics:
    mutation_terminals = {
        evidence.case_id: (
            evidence.reasoner_only.mutation.terminal.value
            if arm == "reasoner"
            else evidence.critic_on.mutation.terminal.value
        )
        for evidence in evidence_records
    }
    return AblationArmMetrics(
        legacy=measure(evaluation_records),
        corrected=measure_corrected(
            evaluation_records,
            mutation_terminals=mutation_terminals,
        ),
    )


def _critic_effect(
    records: tuple[PairedCaseEvidence, ...],
) -> CriticEffectSummary:
    recovered = 0
    false_positive = 0
    correct_contradictions = 0
    incorrect_contradictions = 0
    accepted_delta = 0
    true_omission_blocks = 0
    correct_contradiction_blocks = 0
    spurious_blocks = 0
    unsafe_accepted = 0
    for record in records:
        required = set(record.required_critical_refs)
        reasoner = set(record.reasoner_critical_refs)
        critic_added = set(record.critic_added_critical_refs)
        recovered_for_case = len((required - reasoner) & critic_added)
        recovered += recovered_for_case
        false_positive += len(critic_added - required)
        expected_pairs = {
            tuple(sorted(pair)) for pair in record.expected_blocking_contradictions
        }
        reasoner_pairs = {
            tuple(sorted(pair)) for pair in record.reasoner_only.detected_contradictions
        }
        critic_pairs = {
            tuple(sorted(pair)) for pair in record.critic_on.detected_contradictions
        }
        added_pairs = critic_pairs - reasoner_pairs
        correct_for_case = len(added_pairs & expected_pairs)
        correct_contradictions += correct_for_case
        incorrect_contradictions += len(added_pairs - expected_pairs)
        accepted_delta += int(
            record.critic_on.disposition is CompilationDisposition.ACCEPTED
        ) - int(record.reasoner_only.disposition is CompilationDisposition.ACCEPTED)
        newly_blocked = (
            record.reasoner_only.disposition is CompilationDisposition.ACCEPTED
            and record.critic_on.disposition is not CompilationDisposition.ACCEPTED
        )
        if newly_blocked and recovered_for_case:
            true_omission_blocks += 1
        elif newly_blocked and correct_for_case:
            correct_contradiction_blocks += 1
        elif newly_blocked:
            spurious_blocks += 1
        if (
            record.must_block
            and record.critic_on.disposition is CompilationDisposition.ACCEPTED
        ):
            unsafe_accepted += 1
    return CriticEffectSummary(
        required_omissions_recovered=recovered,
        false_positive_refs_added=false_positive,
        correct_contradictions_added=correct_contradictions,
        incorrect_contradictions_added=incorrect_contradictions,
        accepted_case_delta=accepted_delta,
        true_omission_blocks=true_omission_blocks,
        correct_contradiction_blocks=correct_contradiction_blocks,
        spurious_blocks_added=spurious_blocks,
        unsafe_accepted_cases=unsafe_accepted,
    )


def _draft_critical_refs(draft: DecisionDraft) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                dependency.source_ref
                for claim in draft.claims
                for dependency in claim.dependencies
                if dependency.materiality is Materiality.CRITICAL
            }
            | {
                dependency.source_ref
                for dependency in draft.decision_dependencies
                if dependency.materiality is Materiality.CRITICAL
            }
        )
    )


def _critic_added_critical_refs(
    review: CriticReview,
    reasoner_refs: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                finding.candidate_ref
                for finding in review.findings
                if finding.finding_type is CriticFindingType.MISSING_DEPENDENCY
                and finding.severity is Materiality.CRITICAL
                and finding.candidate_ref not in reasoner_refs
            }
        )
    )


def _repeat_compilation_hashes(
    draft: DecisionDraft,
    runtime: BenchmarkCaseRuntime,
    review: CriticReview,
    canonicalizer: DeterministicCanonicalizer,
) -> tuple[str, ...]:
    variants = (
        draft,
        draft.model_copy(
            update={
                "claims": [
                    claim.model_copy(
                        update={"dependencies": list(reversed(claim.dependencies))},
                        deep=True,
                    )
                    for claim in reversed(draft.claims)
                ],
                "decision_dependencies": list(reversed(draft.decision_dependencies)),
            },
            deep=True,
        ),
        draft.model_validate(draft.model_dump(mode="json")),
    )
    hashes: list[str] = []
    for variant in variants:
        validation = DeterministicDraftValidator().validate(variant, runtime.context)
        if validation.disposition is not None:
            hashes.append(f"blocked:{validation.disposition.value}")
            continue
        hashes.append(
            canonicalizer.compile(
                variant,
                runtime.context,
                validation,
                review,
            ).compilation_hash
        )
    return tuple(hashes)


def _same_artifact_metadata(first: BenchmarkSource, other: BenchmarkSource) -> None:
    fields = (
        "artifact_type",
        "logical_key",
        "source_type",
        "trust_class",
        "authority_rank",
    )
    if any(getattr(first, field) != getattr(other, field) for field in fields):
        raise ValueError(f"artifact metadata drift: {first.artifact_id}")


def _top_level_key(logical_path: str) -> str:
    if not logical_path.startswith("$.") or "." in logical_path[2:]:
        raise ValueError(
            f"benchmark authoring only supports top-level fields: {logical_path}"
        )
    return logical_path[2:]


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "AblationArmEvidence",
    "AblationRunConfiguration",
    "AblationStageUsage",
    "AblationUsage",
    "ModelCompilerSubject",
    "PairedAblationRun",
    "PairedAblationRunner",
    "PairedAblationSubject",
    "PairedCaseEvidence",
    "build_case_runtime",
    "recompute_paired_case_derived_evidence",
]
