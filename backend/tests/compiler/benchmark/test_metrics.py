from __future__ import annotations

from app.compiler.benchmark import metrics as benchmark_metrics
from app.compiler.benchmark.corpus import BenchmarkDomain
from app.compiler.benchmark.metrics import (
    EvaluationRecord,
    evaluate_gate,
    measure,
)


def _record(
    *,
    case_id: str,
    domain: BenchmarkDomain,
    required: tuple[str, ...],
    predicted: tuple[str, ...],
    known: tuple[str, ...],
    accepted: tuple[str, ...] | None = None,
    expected_contradictions: tuple[tuple[str, str], ...] = (),
    detected_contradictions: tuple[tuple[str, str], ...] = (),
    expected_stale: bool = True,
    predicted_stale: bool = True,
    hashes: tuple[str, ...] = ("same", "same"),
    allowed_outcomes: tuple[str, ...] = ("APPROVED",),
    predicted_outcome: str = "APPROVED",
    must_block: bool = False,
    disposition: str = "ACCEPTED",
    detected_severities: tuple[tuple[str, str, str], ...] = (),
) -> EvaluationRecord:
    return EvaluationRecord(
        case_id=case_id,
        domain=domain,
        required_critical_refs=required,
        known_source_refs=known,
        expected_blocking_contradictions=expected_contradictions,
        allowed_outcomes=allowed_outcomes,
        must_block=must_block,
        expected_stale_after_mutation=expected_stale,
        predicted_critical_refs=predicted,
        accepted_canonical_refs=predicted if accepted is None else accepted,
        detected_contradictions=detected_contradictions,
        detected_contradiction_severities=detected_severities,
        predicted_outcome=predicted_outcome,
        compilation_disposition=disposition,
        predicted_stale_after_mutation=predicted_stale,
        repeat_compilation_hashes=hashes,
    )


def test_literal_metrics_are_computed_from_counts_not_case_averages() -> None:
    records = [
        _record(
            case_id="vendor-1",
            domain=BenchmarkDomain.VENDOR_ONBOARDING,
            required=("a", "b"),
            predicted=("a", "x"),
            known=("a", "b", "x"),
            accepted=("a", "x", "fabricated"),
            expected_contradictions=(("a", "b"),),
            detected_contradictions=(("b", "a"),),
            detected_severities=(("b", "a", "CRITICAL"),),
            expected_stale=True,
            predicted_stale=False,
            hashes=("h1", "h1"),
        ),
        _record(
            case_id="release-1",
            domain=BenchmarkDomain.PRODUCTION_RELEASE,
            required=("c",),
            predicted=("c",),
            known=("c", "d"),
            expected_stale=False,
            predicted_stale=True,
            hashes=("h2", "changed"),
        ),
    ]

    metrics = measure(records)

    assert metrics.critical_recall == 2 / 3
    assert metrics.critical_precision == 2 / 3
    assert metrics.unsupported_reference_rate == 1 / 4
    assert metrics.contradiction_recall == 1.0
    assert metrics.contradiction_severity_recall == 1.0
    assert metrics.outcome_compliance == 1.0
    assert metrics.blocking_disposition_compliance == 1.0
    assert metrics.stale_escape_rate == 1.0
    assert metrics.unnecessary_invalidation_rate == 1.0
    assert metrics.compilation_determinism == 0.5
    assert metrics.domain_critical_recall == {
        BenchmarkDomain.VENDOR_ONBOARDING: 0.5,
        BenchmarkDomain.PRODUCTION_RELEASE: 1.0,
    }


def test_contradiction_pairs_are_order_insensitive_and_duplicate_safe() -> None:
    record = _record(
        case_id="access-1",
        domain=BenchmarkDomain.PRIVILEGED_ACCESS,
        required=("a",),
        predicted=("a",),
        known=("a", "b", "c"),
        expected_contradictions=(("a", "b"), ("a", "c")),
        detected_contradictions=(("b", "a"), ("a", "b")),
    )

    metrics = measure([record])

    assert metrics.contradiction_recall == 0.5


def test_zero_denominators_have_conservative_explicit_semantics() -> None:
    record = _record(
        case_id="vendor-empty",
        domain=BenchmarkDomain.VENDOR_ONBOARDING,
        required=(),
        predicted=(),
        known=("context",),
        accepted=(),
        expected_stale=False,
        predicted_stale=False,
        hashes=(),
    )

    metrics = measure([record])

    assert metrics.critical_recall == 1.0
    assert metrics.critical_precision == 1.0
    assert metrics.unsupported_reference_rate == 0.0
    assert metrics.contradiction_recall == 1.0
    assert metrics.stale_escape_rate == 0.0
    assert metrics.unnecessary_invalidation_rate == 0.0
    assert metrics.compilation_determinism == 0.0


def test_gate_reports_every_failed_target_including_domain_floor() -> None:
    record = _record(
        case_id="vendor-bad",
        domain=BenchmarkDomain.VENDOR_ONBOARDING,
        required=("a", "b"),
        predicted=("a", "irrelevant"),
        known=("a", "b", "irrelevant"),
        accepted=("a", "unknown"),
        expected_contradictions=(("a", "b"),),
        detected_contradictions=(),
        allowed_outcomes=("DENIED",),
        predicted_outcome="APPROVED",
        must_block=True,
        disposition="ACCEPTED",
        expected_stale=True,
        predicted_stale=False,
        hashes=("one", "two"),
    )

    gate = evaluate_gate(measure([record]))

    assert not gate.passed
    failed = {row.metric for row in gate.rows if not row.passed}
    assert {
        "critical_recall",
        "critical_precision",
        "unsupported_reference_rate",
        "contradiction_recall",
        "contradiction_severity_recall",
        "outcome_compliance",
        "blocking_disposition_compliance",
        "stale_escape_rate",
        "compilation_determinism",
        "domain_critical_recall:vendor-onboarding",
    } <= failed


def test_correct_refs_cannot_hide_wrong_outcome_or_downgraded_contradiction() -> None:
    record = _record(
        case_id="access-wrong-outcome",
        domain=BenchmarkDomain.PRIVILEGED_ACCESS,
        required=("a", "b"),
        predicted=("a", "b"),
        known=("a", "b"),
        expected_contradictions=(("a", "b"),),
        detected_contradictions=(("a", "b"),),
        detected_severities=(("a", "b", "SUPPORTING"),),
        allowed_outcomes=("NEEDS_HUMAN_REVIEW",),
        predicted_outcome="APPROVED",
        must_block=True,
        disposition="ACCEPTED",
    )

    gate = evaluate_gate(measure([record]))

    assert not gate.passed
    failed = {row.metric for row in gate.rows if not row.passed}
    assert {
        "contradiction_severity_recall",
        "outcome_compliance",
        "blocking_disposition_compliance",
    } <= failed


def test_corrected_metrics_separate_canonical_quality_from_acceptance_coverage() -> (
    None
):
    measure_corrected = getattr(benchmark_metrics, "measure_corrected", None)
    assert measure_corrected is not None
    accepted = _record(
        case_id="accepted",
        domain=BenchmarkDomain.VENDOR_ONBOARDING,
        required=("required-a",),
        predicted=("required-a", "support-a"),
        known=("required-a", "support-a"),
        accepted=("required-a",),
        expected_stale=True,
        predicted_stale=True,
    )
    blocked = _record(
        case_id="blocked",
        domain=BenchmarkDomain.PRODUCTION_RELEASE,
        required=("required-b",),
        predicted=("required-b", "invalid-b"),
        known=("required-b",),
        accepted=(),
        expected_stale=True,
        predicted_stale=False,
        disposition="REJECTED_INVALID_REFERENCE",
        hashes=(),
    )

    corrected = measure_corrected(
        [accepted, blocked],
        mutation_terminals={
            "accepted": "STALE",
            "blocked": "NOT_ACCEPTED",
        },
    )

    assert corrected.proposal_critical_precision == 0.5
    assert corrected.canonical_critical_precision == 1.0
    assert corrected.canonical_critical_recall == 0.5
    assert corrected.acceptance_coverage == 0.5
    assert corrected.accepted_stale_escape_rate == 0.0
    assert corrected.counts.not_accepted_expected_stale == 1
