from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from statistics import fmean
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

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
    detected_contradictions: tuple[tuple[str, str], ...] = ()
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
            self._evaluate(subject, case, run_index=0)
            for case in self._corpus.cases
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
                self._evaluate(subject, case, run_index=run_index)
                for case in subset
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
        predicted_stale = prediction.predicted_stale_after_mutation
        if predicted_stale is None:
            predicted_stale = case.mutation.source_ref in prediction.critical_refs
        return EvaluationRecord(
            case_id=case.case_id,
            domain=case.domain,
            required_critical_refs=tuple(
                case.ground_truth.required_critical_refs
            ),
            known_source_refs=tuple(source.source_ref for source in case.sources),
            expected_blocking_contradictions=tuple(
                (finding.source_ref_a, finding.source_ref_b)
                for finding in case.ground_truth.blocking_contradictions
            ),
            expected_stale_after_mutation=expected_stale,
            predicted_critical_refs=prediction.critical_refs,
            accepted_canonical_refs=prediction.accepted_canonical_refs,
            detected_contradictions=prediction.detected_contradictions,
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


def _prediction(
    case: BenchmarkCase,
    critical: tuple[str, ...],
    *,
    accepted: tuple[str, ...],
    contradictions: tuple[tuple[str, str], ...] = (),
) -> Prediction:
    normalized_critical = tuple(sorted(set(critical)))
    normalized_accepted = tuple(sorted(set(accepted)))
    canonical_hash = _digest(
        {
            "case_id": case.case_id,
            "critical": normalized_critical,
            "accepted": normalized_accepted,
            "contradictions": contradictions,
        }
    )
    return Prediction(
        critical_refs=normalized_critical,
        accepted_canonical_refs=normalized_accepted,
        detected_contradictions=contradictions,
        repeat_compilation_hashes=(canonical_hash, canonical_hash, canonical_hash),
    )


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
]
