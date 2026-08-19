from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from statistics import fmean
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.compiler.acceptance import RuntimeAcceptanceService
from app.compiler.benchmark.corpus import (
    BenchmarkCase,
    BenchmarkCaseClass,
    BenchmarkCorpus,
)
from app.compiler.benchmark.metrics import (
    EvaluationRecord,
    GateResult,
    MetricSnapshot,
    evaluate_gate,
    measure,
)
from app.compiler.context import RiskClass
from app.compiler.models import (
    CanonicalEdge,
    CompilationDisposition,
    CompilationResult,
    DecisionCandidate,
    DecisionDraft,
    DependencyRelation,
    Materiality,
    ModelMetadata,
)
from app.compiler.repository import CompilationRequestRecord
from app.compiler.repository_memory import InMemoryCompilerRepository
from app.domain.invalidation import InvalidationService
from app.domain.models import DecisionStatus, DomainEvent, GraphSnapshot, WorldArtifact
from app.repository.graph_adapter import RuntimeGraphRepositoryAdapter
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.runtime.entities import Mission, RuntimeSnapshot
from app.sources.identity import SourceRef


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BaselineKind(StrEnum):
    DOCUMENT_LEVEL = "document-level"
    SINGLE_PASS = "single-pass"
    FULL_PIPELINE = "full-pipeline"


class EvidenceLane(StrEnum):
    DETERMINISTIC_REFERENCE = "deterministic_reference"
    LIVE_OPENAI = "live_openai"
    LIVE_GEMINI = "live_gemini"


class EvidenceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class RunConfiguration(FrozenModel):
    baseline: BaselineKind
    evidence_lane: EvidenceLane
    provider: str = Field(min_length=1)
    reasoner_model: str = Field(min_length=1)
    critic_model: str | None = None
    reasoner_prompt_version: str = Field(min_length=1)
    critic_prompt_version: str | None = None
    temperature: float = Field(ge=0.0, le=2.0)
    pricing_version: str | None = None
    cumulative_budget_usd: str | None = None


class Prediction(FrozenModel):
    critical_refs: tuple[str, ...] = ()
    accepted_canonical_refs: tuple[str, ...] = ()
    accepted_dependency_edges: tuple[tuple[str, str, str], ...] = ()
    detected_contradictions: tuple[tuple[str, str], ...] = ()
    detected_contradiction_severities: tuple[tuple[str, str, str], ...] = ()
    proposed_outcome: str
    compilation_disposition: CompilationDisposition
    predicted_stale_after_mutation: bool | None = None
    repeat_compilation_hashes: tuple[str, ...] = ()


class BenchmarkSubject(Protocol):
    def predict(self, case: BenchmarkCase, *, run_index: int) -> Prediction: ...


class VarianceSummary(FrozenModel):
    case_count: int = Field(ge=0)
    runs_per_case: int = Field(ge=1)
    total_observations: int = Field(ge=0)
    run_critical_recalls: list[float]
    mean_critical_recall: float = Field(ge=0.0, le=1.0)
    worst_run_critical_recall: float = Field(ge=0.0, le=1.0)


class UsageSummary(FrozenModel):
    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    actual_cost_usd: str = "0"


class BenchmarkRun(FrozenModel):
    run_id: str = Field(min_length=1)
    configuration: RunConfiguration
    status: EvidenceStatus
    records: list[EvaluationRecord] = Field(default_factory=list)
    metrics: MetricSnapshot | None = None
    gate: GateResult | None = None
    variance: VarianceSummary | None = None
    usage: UsageSummary = Field(default_factory=UsageSummary)
    blocked_reason: str | None = None
    failure_reason: str | None = None


class DocumentLevelSubject:
    def predict(self, case: BenchmarkCase, *, run_index: int) -> Prediction:
        refs = tuple(source.source_ref for source in case.sources)
        return _prediction(case, refs, accepted=refs)


class SinglePassReferenceSubject:
    """A transparent non-model fixture that approximates common one-pass errors."""

    def predict(self, case: BenchmarkCase, *, run_index: int) -> Prediction:
        critical = list(case.ground_truth.required_critical_refs)
        forbidden = list(case.ground_truth.forbidden_or_irrelevant_refs)
        if case.case_class in {
            BenchmarkCaseClass.CRITICAL_OMISSION,
            BenchmarkCaseClass.MULTIPLE_DEPENDENCIES,
        }:
            critical = critical[:-1]
        elif case.case_class is BenchmarkCaseClass.OBSOLETE_REVISION:
            critical = forbidden[:1]
        elif case.case_class in {
            BenchmarkCaseClass.NEAR_DUPLICATE,
            BenchmarkCaseClass.PROMPT_INJECTION,
            BenchmarkCaseClass.NARROW_CLAUSE,
        }:
            critical.extend(forbidden[:1])
        return _prediction(case, tuple(critical), accepted=tuple(critical))


class FullPipelineReferenceSubject:
    """Oracle-like deterministic harness; validates metrics plumbing, not model quality."""

    def predict(self, case: BenchmarkCase, *, run_index: int) -> Prediction:
        critical = tuple(case.ground_truth.required_critical_refs)
        contradictions = tuple(
            (finding.source_ref_a, finding.source_ref_b)
            for finding in case.ground_truth.blocking_contradictions
        )
        return _prediction(
            case,
            critical,
            accepted=critical,
            contradictions=contradictions,
            contradiction_severities=tuple(
                (source_a, source_b, "CRITICAL")
                for source_a, source_b in contradictions
            ),
            proposed_outcome=(
                case.ground_truth.expected_outcome_constraints.allowed_outcomes[0]
                if case.ground_truth.expected_outcome_constraints.must_block
                else case.proposed_outcome
            ),
            disposition=(
                CompilationDisposition.NEEDS_HUMAN_REVIEW
                if case.ground_truth.expected_outcome_constraints.must_block
                else CompilationDisposition.ACCEPTED
            ),
        )


class BenchmarkRunner:
    def __init__(self, corpus: BenchmarkCorpus, *, variance_runs: int = 3) -> None:
        if variance_runs < 1:
            raise ValueError("variance_runs must be positive")
        self._corpus = corpus
        self._variance_runs = variance_runs

    def run(
        self,
        subject: BenchmarkSubject,
        configuration: RunConfiguration,
    ) -> BenchmarkRun:
        records = [
            self._evaluate(subject, case, run_index=0) for case in self._corpus.cases
        ]
        metrics = measure(records)
        gate = evaluate_gate(metrics)
        variance = self._run_variance(subject)
        usage_factory = getattr(subject, "usage_summary", None)
        usage = UsageSummary() if usage_factory is None else usage_factory()
        run_id = _digest(
            {
                "schema": self._corpus.schema_version,
                "configuration": configuration.model_dump(mode="json"),
            }
        )[:16]
        return BenchmarkRun(
            run_id=f"benchmark:{run_id}",
            configuration=configuration,
            status=EvidenceStatus.PASS if gate.passed else EvidenceStatus.FAIL,
            records=records,
            metrics=metrics,
            gate=gate,
            variance=variance,
            usage=usage,
        )

    def _run_variance(self, subject: BenchmarkSubject) -> VarianceSummary:
        subset = [case for case in self._corpus.cases if case.variance_subset]
        run_recalls: list[float] = []
        for run_index in range(1, self._variance_runs + 1):
            records = [
                self._evaluate(subject, case, run_index=run_index) for case in subset
            ]
            run_recalls.append(measure(records).critical_recall)
        return VarianceSummary(
            case_count=len(subset),
            runs_per_case=self._variance_runs,
            total_observations=len(subset) * self._variance_runs,
            run_critical_recalls=run_recalls,
            mean_critical_recall=fmean(run_recalls),
            worst_run_critical_recall=min(run_recalls),
        )

    @staticmethod
    def _evaluate(
        subject: BenchmarkSubject,
        case: BenchmarkCase,
        *,
        run_index: int,
    ) -> EvaluationRecord:
        prediction = subject.predict(case, run_index=run_index)
        expected_stale = bool(case.mutation.expected_stale_decision_ids)
        predicted_stale = evaluate_runtime_mutation(case, prediction)
        return EvaluationRecord(
            case_id=case.case_id,
            domain=case.domain,
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
            expected_stale_after_mutation=expected_stale,
            predicted_critical_refs=prediction.critical_refs,
            accepted_canonical_refs=prediction.accepted_canonical_refs,
            detected_contradictions=prediction.detected_contradictions,
            detected_contradiction_severities=(
                prediction.detected_contradiction_severities
            ),
            predicted_outcome=prediction.proposed_outcome,
            compilation_disposition=prediction.compilation_disposition.value,
            predicted_stale_after_mutation=predicted_stale,
            repeat_compilation_hashes=prediction.repeat_compilation_hashes,
        )


def blocked_evidence_run(
    configuration: RunConfiguration,
    *,
    reason: str,
) -> BenchmarkRun:
    if not reason.strip():
        raise ValueError("blocked evidence requires a reason")
    run_id = _digest(
        {
            "configuration": configuration.model_dump(mode="json"),
            "blocked_reason": reason,
        }
    )[:16]
    return BenchmarkRun(
        run_id=f"benchmark:{run_id}",
        configuration=configuration,
        status=EvidenceStatus.BLOCKED,
        blocked_reason=reason,
    )


def failed_evidence_run(
    configuration: RunConfiguration,
    *,
    reason: str,
) -> BenchmarkRun:
    if not reason.strip():
        raise ValueError("failed evidence requires a reason")
    run_id = _digest(
        {
            "configuration": configuration.model_dump(mode="json"),
            "failure_reason": reason,
        }
    )[:16]
    return BenchmarkRun(
        run_id=f"benchmark:{run_id}",
        configuration=configuration,
        status=EvidenceStatus.FAIL,
        failure_reason=reason,
    )


def _prediction(
    case: BenchmarkCase,
    critical: tuple[str, ...],
    *,
    accepted: tuple[str, ...],
    contradictions: tuple[tuple[str, str], ...] = (),
    contradiction_severities: tuple[tuple[str, str, str], ...] = (),
    proposed_outcome: str | None = None,
    disposition: CompilationDisposition = CompilationDisposition.ACCEPTED,
) -> Prediction:
    normalized_critical = tuple(sorted(set(critical)))
    normalized_accepted = tuple(sorted(set(accepted)))
    payload = {
        "case_id": case.case_id,
        "critical": normalized_critical,
        "accepted": normalized_accepted,
        "contradictions": contradictions,
        "outcome": proposed_outcome or case.proposed_outcome,
        "disposition": disposition.value,
    }
    hashes = (
        _digest(dict(payload)),
        _digest(dict(reversed(tuple(payload.items())))),
        _digest(json.loads(json.dumps(payload))),
    )
    return Prediction(
        critical_refs=normalized_critical,
        accepted_canonical_refs=normalized_accepted,
        detected_contradictions=contradictions,
        detected_contradiction_severities=contradiction_severities,
        proposed_outcome=proposed_outcome or case.proposed_outcome,
        compilation_disposition=disposition,
        repeat_compilation_hashes=(
            hashes if disposition is CompilationDisposition.ACCEPTED else ()
        ),
    )


def evaluate_runtime_mutation(case: BenchmarkCase, prediction: Prediction) -> bool:
    """Accept the predicted graph, apply the concrete mutation, and read runtime state."""
    if prediction.compilation_disposition is not CompilationDisposition.ACCEPTED:
        return False
    world_snapshot_id = f"world:{case.case_id}"
    graph = GraphSnapshot(
        mission_id=f"mission:{case.case_id}",
        artifacts={
            source.artifact_id: WorldArtifact(
                artifact_id=source.artifact_id,
                artifact_type=source.artifact_type.value,
                logical_key=source.artifact_id,
                version=source.revision_label,
            )
            for source in case.sources
            if source.current
        },
        metadata={"world_snapshot_id": world_snapshot_id},
    )
    runtime_repository = InMemoryRuntimeRepository()
    runtime_repository.create(
        RuntimeSnapshot(
            mission=Mission(mission_id=graph.mission_id),
            graph=graph,
        )
    )
    compiler_repository = InMemoryCompilerRepository()
    request_id = f"request:{case.case_id}"
    now = datetime(2026, 8, 19, tzinfo=UTC)
    compiler_repository.create_request(
        CompilationRequestRecord(
            request_id=request_id,
            mission_id=graph.mission_id,
            work_item_id=f"work:{case.case_id}",
            agent_id="benchmark-runtime-evaluator",
            world_snapshot_id=world_snapshot_id,
            expected_mission_revision=0,
            decision_type=case.decision_type,
            risk_class=RiskClass.HIGH,
            owner_scope="benchmark:v1",
            allowed_source_refs=[source.source_ref for source in case.sources],
            created_at=now,
        )
    )
    draft = DecisionDraft(
        request_id=request_id,
        decision_type=case.decision_type,
        proposed_outcome=prediction.proposed_outcome,
        rationale_summary="Benchmark runtime mutation evaluation.",
        model_metadata=ModelMetadata(
            provider="REFERENCE",
            model_name="benchmark-runtime-evaluator",
            prompt_version="benchmark-v1",
            temperature=0,
            execution_id=f"execution:{case.case_id}",
        ),
    )
    compiler_repository.put_draft(request_id, draft)
    compilation_hash = _digest(
        {
            "case_id": case.case_id,
            "accepted": prediction.accepted_canonical_refs,
            "outcome": prediction.proposed_outcome,
        }
    )
    decision_id = f"decision:{case.case_id}"
    compiler_repository.put_result(
        request_id,
        CompilationResult(
            compilation_id=f"compilation:{compilation_hash}",
            request_id=request_id,
            status=CompilationDisposition.ACCEPTED,
            decision_candidate=DecisionCandidate(
                decision_id=decision_id,
                decision_type=case.decision_type,
                outcome=prediction.proposed_outcome,
                rationale_summary="Benchmark runtime mutation evaluation.",
            ),
            canonical_edges=[
                CanonicalEdge(
                    edge_id=f"edge:{index}:{compilation_hash[:16]}",
                    source_kind="SOURCE_FRAGMENT",
                    source_id=source_ref,
                    target_kind="DECISION",
                    target_id=decision_id,
                    relation=DependencyRelation(relation),
                    materiality=Materiality(materiality),
                )
                for index, (source_ref, relation, materiality) in enumerate(
                    prediction.accepted_dependency_edges
                    or tuple(
                        (
                            source_ref,
                            DependencyRelation.SUPPORTED_BY.value,
                            Materiality.CRITICAL.value,
                        )
                        for source_ref in prediction.accepted_canonical_refs
                    )
                )
            ],
            compiler_version="benchmark-runtime-v1",
            validation_policy_version="benchmark-runtime-v1",
            compilation_hash=compilation_hash,
        ),
    )
    RuntimeAcceptanceService(
        compiler_repository,
        runtime_repository,
    ).accept(
        request_id,
        expected_mission_revision=0,
        world_snapshot_id=world_snapshot_id,
    )
    mutation_ref = SourceRef.parse(case.mutation.source_ref)
    replacement_digest = _digest(case.mutation.replacement_content)[:16]
    changed = InvalidationService(
        RuntimeGraphRepositoryAdapter(runtime_repository)
    ).process_artifact_change(
        graph.mission_id,
        DomainEvent(
            event_id=f"mutation:{case.case_id}:{replacement_digest}",
            event_type=case.mutation.mutation_kind,
            payload={
                "logical_key": mutation_ref.artifact_id,
                "old_artifact_id": mutation_ref.artifact_id,
                "new_artifact_id": (
                    f"{mutation_ref.artifact_id}@mutation:{replacement_digest}"
                ),
                "old_version": mutation_ref.revision_label,
                "new_version": f"mutation:{replacement_digest}",
                "changed_source_ref": case.mutation.source_ref,
            },
        ),
    )
    return changed.decisions[decision_id].status is DecisionStatus.STALE


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "BaselineKind",
    "BenchmarkRun",
    "BenchmarkRunner",
    "DocumentLevelSubject",
    "EvidenceLane",
    "EvidenceStatus",
    "FullPipelineReferenceSubject",
    "Prediction",
    "RunConfiguration",
    "SinglePassReferenceSubject",
    "blocked_evidence_run",
    "evaluate_runtime_mutation",
    "failed_evidence_run",
]
