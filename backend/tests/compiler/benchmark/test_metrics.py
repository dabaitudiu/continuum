from __future__ import annotations

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
) -> EvaluationRecord:
    return EvaluationRecord(
        case_id=case_id,
        domain=domain,
        required_critical_refs=required,
        known_source_refs=known,
        expected_blocking_contradictions=expected_contradictions,
        expected_stale_after_mutation=expected_stale,
        predicted_critical_refs=predicted,
        accepted_canonical_refs=accepted or predicted,
        detected_contradictions=detected_contradictions,
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
        "stale_escape_rate",
        "compilation_determinism",
        "domain_critical_recall:vendor-onboarding",
    } <= failed
