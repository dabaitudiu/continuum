from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.compiler.benchmark.corpus import BenchmarkDomain


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvaluationRecord(FrozenModel):
    case_id: str = Field(min_length=1)
    domain: BenchmarkDomain
    required_critical_refs: tuple[str, ...] = ()
    known_source_refs: tuple[str, ...] = ()
    expected_blocking_contradictions: tuple[tuple[str, str], ...] = ()
    allowed_outcomes: tuple[str, ...]
    must_block: bool
    expected_stale_after_mutation: bool
    predicted_critical_refs: tuple[str, ...] = ()
    accepted_canonical_refs: tuple[str, ...] = ()
    detected_contradictions: tuple[tuple[str, str], ...] = ()
    detected_contradiction_severities: tuple[tuple[str, str, str], ...] = ()
    predicted_outcome: str
    compilation_disposition: str
    predicted_stale_after_mutation: bool
    repeat_compilation_hashes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_unique_sets(self) -> EvaluationRecord:
        for name in (
            "required_critical_refs",
            "known_source_refs",
            "predicted_critical_refs",
            "accepted_canonical_refs",
        ):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must be unique")
        return self


class MetricCounts(FrozenModel):
    recovered_critical: int = Field(ge=0)
    required_critical: int = Field(ge=0)
    predicted_critical: int = Field(ge=0)
    unsupported_accepted: int = Field(ge=0)
    accepted_canonical: int = Field(ge=0)
    detected_blocking_contradictions: int = Field(ge=0)
    expected_blocking_contradictions: int = Field(ge=0)
    detected_critical_contradictions: int = Field(ge=0)
    expected_critical_contradictions: int = Field(ge=0)
    compliant_outcomes: int = Field(ge=0)
    evaluated_outcomes: int = Field(ge=0)
    compliant_blocking_dispositions: int = Field(ge=0)
    evaluated_blocking_dispositions: int = Field(ge=0)
    stale_escapes: int = Field(ge=0)
    expected_stale: int = Field(ge=0)
    unnecessary_invalidations: int = Field(ge=0)
    expected_unchanged: int = Field(ge=0)
    deterministic_records: int = Field(ge=0)
    repeated_records: int = Field(ge=0)


class MetricSnapshot(FrozenModel):
    critical_recall: float = Field(ge=0.0, le=1.0)
    critical_precision: float = Field(ge=0.0, le=1.0)
    unsupported_reference_rate: float = Field(ge=0.0, le=1.0)
    contradiction_recall: float = Field(ge=0.0, le=1.0)
    contradiction_severity_recall: float = Field(ge=0.0, le=1.0)
    outcome_compliance: float = Field(ge=0.0, le=1.0)
    blocking_disposition_compliance: float = Field(ge=0.0, le=1.0)
    stale_escape_rate: float = Field(ge=0.0, le=1.0)
    unnecessary_invalidation_rate: float = Field(ge=0.0, le=1.0)
    compilation_determinism: float = Field(ge=0.0, le=1.0)
    domain_critical_recall: dict[BenchmarkDomain, float]
    counts: MetricCounts


class CorrectedMetricCounts(FrozenModel):
    canonical_recovered_critical: int = Field(ge=0)
    canonical_selected_critical: int = Field(ge=0)
    required_critical: int = Field(ge=0)
    accepted_cases: int = Field(ge=0)
    total_cases: int = Field(ge=0)
    accepted_expected_stale: int = Field(ge=0)
    accepted_stale_escapes: int = Field(ge=0)
    accepted_expected_unchanged: int = Field(ge=0)
    accepted_unnecessary_invalidations: int = Field(ge=0)
    not_accepted_expected_stale: int = Field(ge=0)


class CorrectedMetricSnapshot(FrozenModel):
    proposal_critical_recall: float = Field(ge=0.0, le=1.0)
    proposal_critical_precision: float = Field(ge=0.0, le=1.0)
    canonical_critical_recall: float = Field(ge=0.0, le=1.0)
    canonical_critical_precision: float = Field(ge=0.0, le=1.0)
    unsupported_reference_rate: float = Field(ge=0.0, le=1.0)
    contradiction_recall: float = Field(ge=0.0, le=1.0)
    contradiction_severity_recall: float = Field(ge=0.0, le=1.0)
    outcome_compliance: float = Field(ge=0.0, le=1.0)
    blocking_disposition_compliance: float = Field(ge=0.0, le=1.0)
    acceptance_coverage: float = Field(ge=0.0, le=1.0)
    legacy_stale_escape_rate: float = Field(ge=0.0, le=1.0)
    accepted_stale_escape_rate: float = Field(ge=0.0, le=1.0)
    legacy_unnecessary_invalidation_rate: float = Field(ge=0.0, le=1.0)
    accepted_unnecessary_invalidation_rate: float = Field(ge=0.0, le=1.0)
    compilation_determinism: float = Field(ge=0.0, le=1.0)
    counts: CorrectedMetricCounts


class GateComparison(StrEnum):
    MINIMUM = "MINIMUM"
    MAXIMUM_EXCLUSIVE = "MAXIMUM_EXCLUSIVE"
    EXACT = "EXACT"


class GateRow(FrozenModel):
    metric: str
    value: float
    target: float
    comparison: GateComparison
    passed: bool


class GateResult(FrozenModel):
    passed: bool
    rows: list[GateRow]


def measure(records: list[EvaluationRecord]) -> MetricSnapshot:
    recovered_critical = 0
    required_critical = 0
    predicted_critical = 0
    unsupported_accepted = 0
    accepted_canonical = 0
    detected_blocking_contradictions = 0
    expected_blocking_contradictions = 0
    detected_critical_contradictions = 0
    expected_critical_contradictions = 0
    compliant_outcomes = 0
    evaluated_outcomes = 0
    compliant_blocking_dispositions = 0
    evaluated_blocking_dispositions = 0
    stale_escapes = 0
    expected_stale = 0
    unnecessary_invalidations = 0
    expected_unchanged = 0
    deterministic_records = 0
    repeated_records = 0
    domain_recovered: defaultdict[BenchmarkDomain, int] = defaultdict(int)
    domain_required: defaultdict[BenchmarkDomain, int] = defaultdict(int)

    for record in records:
        required = set(record.required_critical_refs)
        predicted = set(record.predicted_critical_refs)
        accepted = set(record.accepted_canonical_refs)
        known = set(record.known_source_refs)
        recovered = len(required & predicted)
        recovered_critical += recovered
        required_critical += len(required)
        predicted_critical += len(predicted)
        unsupported_accepted += len(accepted - known)
        accepted_canonical += len(accepted)
        domain_recovered[record.domain] += recovered
        domain_required[record.domain] += len(required)

        expected_pairs = {
            _pair(source_a, source_b)
            for source_a, source_b in record.expected_blocking_contradictions
        }
        detected_pairs = {
            _pair(source_a, source_b)
            for source_a, source_b in record.detected_contradictions
        }
        detected_blocking_contradictions += len(expected_pairs & detected_pairs)
        expected_blocking_contradictions += len(expected_pairs)
        detected_critical_pairs = {
            _pair(source_a, source_b)
            for source_a, source_b, severity in record.detected_contradiction_severities
            if severity == "CRITICAL"
        }
        detected_critical_contradictions += len(
            expected_pairs & detected_critical_pairs
        )
        expected_critical_contradictions += len(expected_pairs)

        evaluated_outcomes += 1
        if record.predicted_outcome in record.allowed_outcomes:
            compliant_outcomes += 1
        evaluated_blocking_dispositions += 1
        did_block = record.compilation_disposition != "ACCEPTED"
        if did_block is record.must_block:
            compliant_blocking_dispositions += 1

        if record.expected_stale_after_mutation:
            expected_stale += 1
            if not record.predicted_stale_after_mutation:
                stale_escapes += 1
        else:
            expected_unchanged += 1
            if record.predicted_stale_after_mutation:
                unnecessary_invalidations += 1

        if len(record.repeat_compilation_hashes) >= 2:
            repeated_records += 1
            if len(set(record.repeat_compilation_hashes)) == 1:
                deterministic_records += 1

    counts = MetricCounts(
        recovered_critical=recovered_critical,
        required_critical=required_critical,
        predicted_critical=predicted_critical,
        unsupported_accepted=unsupported_accepted,
        accepted_canonical=accepted_canonical,
        detected_blocking_contradictions=detected_blocking_contradictions,
        expected_blocking_contradictions=expected_blocking_contradictions,
        detected_critical_contradictions=detected_critical_contradictions,
        expected_critical_contradictions=expected_critical_contradictions,
        compliant_outcomes=compliant_outcomes,
        evaluated_outcomes=evaluated_outcomes,
        compliant_blocking_dispositions=compliant_blocking_dispositions,
        evaluated_blocking_dispositions=evaluated_blocking_dispositions,
        stale_escapes=stale_escapes,
        expected_stale=expected_stale,
        unnecessary_invalidations=unnecessary_invalidations,
        expected_unchanged=expected_unchanged,
        deterministic_records=deterministic_records,
        repeated_records=repeated_records,
    )
    return MetricSnapshot(
        critical_recall=_ratio(recovered_critical, required_critical, empty=1.0),
        critical_precision=_ratio(
            recovered_critical,
            predicted_critical,
            empty=1.0,
        ),
        unsupported_reference_rate=_ratio(
            unsupported_accepted,
            accepted_canonical,
            empty=0.0,
        ),
        contradiction_recall=_ratio(
            detected_blocking_contradictions,
            expected_blocking_contradictions,
            empty=1.0,
        ),
        contradiction_severity_recall=_ratio(
            detected_critical_contradictions,
            expected_critical_contradictions,
            empty=1.0,
        ),
        outcome_compliance=_ratio(
            compliant_outcomes,
            evaluated_outcomes,
            empty=0.0,
        ),
        blocking_disposition_compliance=_ratio(
            compliant_blocking_dispositions,
            evaluated_blocking_dispositions,
            empty=0.0,
        ),
        stale_escape_rate=_ratio(stale_escapes, expected_stale, empty=0.0),
        unnecessary_invalidation_rate=_ratio(
            unnecessary_invalidations,
            expected_unchanged,
            empty=0.0,
        ),
        compilation_determinism=_ratio(
            deterministic_records,
            repeated_records,
            empty=0.0,
        ),
        domain_critical_recall={
            domain: _ratio(
                domain_recovered[domain],
                domain_required[domain],
                empty=1.0,
            )
            for domain in domain_required
        },
        counts=counts,
    )


def measure_corrected(
    records: list[EvaluationRecord],
    *,
    mutation_terminals: dict[str, str],
) -> CorrectedMetricSnapshot:
    """Separate proposal quality, canonical quality, and Runtime coverage."""
    if set(mutation_terminals) != {record.case_id for record in records}:
        raise ValueError("mutation terminals must classify every record exactly once")
    legacy = measure(records)
    canonical_recovered = 0
    canonical_selected = 0
    required_critical = 0
    accepted_cases = 0
    accepted_expected_stale = 0
    accepted_stale_escapes = 0
    accepted_expected_unchanged = 0
    accepted_unnecessary_invalidations = 0
    not_accepted_expected_stale = 0

    for record in records:
        terminal = mutation_terminals[record.case_id]
        if terminal not in {"STALE", "VALID", "NOT_ACCEPTED"}:
            raise ValueError(f"unknown mutation terminal: {terminal}")
        accepted = record.compilation_disposition == "ACCEPTED"
        if accepted is (terminal == "NOT_ACCEPTED"):
            raise ValueError("mutation terminal conflicts with compilation disposition")
        required = set(record.required_critical_refs)
        canonical = set(record.accepted_canonical_refs)
        canonical_recovered += len(required & canonical)
        canonical_selected += len(canonical)
        required_critical += len(required)

        if not accepted:
            if canonical:
                raise ValueError(
                    "non-accepted compilation cannot expose canonical refs"
                )
            if record.expected_stale_after_mutation:
                not_accepted_expected_stale += 1
            continue
        accepted_cases += 1
        if record.expected_stale_after_mutation:
            accepted_expected_stale += 1
            if terminal != "STALE":
                accepted_stale_escapes += 1
        else:
            accepted_expected_unchanged += 1
            if terminal == "STALE":
                accepted_unnecessary_invalidations += 1

    counts = CorrectedMetricCounts(
        canonical_recovered_critical=canonical_recovered,
        canonical_selected_critical=canonical_selected,
        required_critical=required_critical,
        accepted_cases=accepted_cases,
        total_cases=len(records),
        accepted_expected_stale=accepted_expected_stale,
        accepted_stale_escapes=accepted_stale_escapes,
        accepted_expected_unchanged=accepted_expected_unchanged,
        accepted_unnecessary_invalidations=accepted_unnecessary_invalidations,
        not_accepted_expected_stale=not_accepted_expected_stale,
    )
    return CorrectedMetricSnapshot(
        proposal_critical_recall=legacy.critical_recall,
        proposal_critical_precision=legacy.critical_precision,
        canonical_critical_recall=_ratio(
            canonical_recovered,
            required_critical,
            empty=1.0,
        ),
        canonical_critical_precision=_ratio(
            canonical_recovered,
            canonical_selected,
            empty=1.0,
        ),
        unsupported_reference_rate=legacy.unsupported_reference_rate,
        contradiction_recall=legacy.contradiction_recall,
        contradiction_severity_recall=legacy.contradiction_severity_recall,
        outcome_compliance=legacy.outcome_compliance,
        blocking_disposition_compliance=legacy.blocking_disposition_compliance,
        acceptance_coverage=_ratio(accepted_cases, len(records), empty=0.0),
        legacy_stale_escape_rate=legacy.stale_escape_rate,
        accepted_stale_escape_rate=_ratio(
            accepted_stale_escapes,
            accepted_expected_stale,
            empty=0.0,
        ),
        legacy_unnecessary_invalidation_rate=(legacy.unnecessary_invalidation_rate),
        accepted_unnecessary_invalidation_rate=_ratio(
            accepted_unnecessary_invalidations,
            accepted_expected_unchanged,
            empty=0.0,
        ),
        compilation_determinism=legacy.compilation_determinism,
        counts=counts,
    )


def evaluate_gate(metrics: MetricSnapshot) -> GateResult:
    rows = [
        _minimum("critical_recall", metrics.critical_recall, 0.92),
        _minimum("critical_precision", metrics.critical_precision, 0.82),
        _exact(
            "unsupported_reference_rate",
            metrics.unsupported_reference_rate,
            0.0,
        ),
        _minimum("contradiction_recall", metrics.contradiction_recall, 0.90),
        _minimum(
            "contradiction_severity_recall",
            metrics.contradiction_severity_recall,
            0.90,
        ),
        _exact("outcome_compliance", metrics.outcome_compliance, 1.0),
        _exact(
            "blocking_disposition_compliance",
            metrics.blocking_disposition_compliance,
            1.0,
        ),
        _maximum_exclusive("stale_escape_rate", metrics.stale_escape_rate, 0.02),
        _maximum_exclusive(
            "unnecessary_invalidation_rate",
            metrics.unnecessary_invalidation_rate,
            0.08,
        ),
        _exact("compilation_determinism", metrics.compilation_determinism, 1.0),
    ]
    rows.extend(
        _minimum(
            f"domain_critical_recall:{domain.value}",
            metrics.domain_critical_recall.get(domain, 0.0),
            0.88,
        )
        for domain in BenchmarkDomain
    )
    return GateResult(passed=all(row.passed for row in rows), rows=rows)


def _ratio(numerator: int, denominator: int, *, empty: float) -> float:
    return empty if denominator == 0 else numerator / denominator


def _pair(source_a: str, source_b: str) -> tuple[str, str]:
    return tuple(sorted((source_a, source_b)))  # type: ignore[return-value]


def _minimum(metric: str, value: float, target: float) -> GateRow:
    return GateRow(
        metric=metric,
        value=value,
        target=target,
        comparison=GateComparison.MINIMUM,
        passed=value >= target,
    )


def _maximum_exclusive(metric: str, value: float, target: float) -> GateRow:
    return GateRow(
        metric=metric,
        value=value,
        target=target,
        comparison=GateComparison.MAXIMUM_EXCLUSIVE,
        passed=value < target,
    )


def _exact(metric: str, value: float, target: float) -> GateRow:
    return GateRow(
        metric=metric,
        value=value,
        target=target,
        comparison=GateComparison.EXACT,
        passed=value == target,
    )


__all__ = [
    "CorrectedMetricCounts",
    "CorrectedMetricSnapshot",
    "EvaluationRecord",
    "GateResult",
    "MetricSnapshot",
    "evaluate_gate",
    "measure",
    "measure_corrected",
]
