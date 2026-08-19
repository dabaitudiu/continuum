from __future__ import annotations

from collections import Counter

from app.compiler.benchmark.corpus import (
    AdversarialTag,
    BenchmarkDomain,
    load_corpus,
)
from app.sources.identity import SourceRef


def test_committed_corpus_has_exactly_120_unique_cases_across_three_domains() -> None:
    corpus = load_corpus()

    assert len(corpus.cases) == 120
    assert len({case.case_id for case in corpus.cases}) == 120
    assert Counter(case.domain for case in corpus.cases) == {
        BenchmarkDomain.VENDOR_ONBOARDING: 40,
        BenchmarkDomain.PRODUCTION_RELEASE: 40,
        BenchmarkDomain.PRIVILEGED_ACCESS: 40,
    }


def test_every_ground_truth_ref_is_parseable_and_present_in_case_sources() -> None:
    corpus = load_corpus()

    for case in corpus.cases:
        source_refs = {source.source_ref for source in case.sources}
        truth_refs = {
            *case.ground_truth.required_critical_refs,
            *case.ground_truth.acceptable_supporting_refs,
            *case.ground_truth.forbidden_or_irrelevant_refs,
        }
        for contradiction in case.ground_truth.blocking_contradictions:
            truth_refs.update((contradiction.source_ref_a, contradiction.source_ref_b))
        assert truth_refs <= source_refs, case.case_id
        for source_ref in source_refs:
            assert str(SourceRef.parse(source_ref)) == source_ref


def test_every_case_defines_a_replayable_mutation_expectation() -> None:
    corpus = load_corpus()

    for case in corpus.cases:
        source_refs = {source.source_ref for source in case.sources}
        assert case.mutation.source_ref in source_refs, case.case_id
        expected = {
            *case.mutation.expected_stale_decision_ids,
            *case.mutation.expected_unchanged_decision_ids,
        }
        assert expected == {f"decision:{case.case_id}"}, case.case_id


def test_each_required_adversarial_class_has_at_least_ten_cases() -> None:
    counts: Counter[AdversarialTag] = Counter(
        tag
        for case in load_corpus().cases
        for tag in case.adversarial_tags
    )

    for tag in AdversarialTag:
        assert counts[tag] >= 10, (tag, counts[tag])


def test_variance_subset_is_exactly_thirty_cases_balanced_by_domain() -> None:
    subset = [case for case in load_corpus().cases if case.variance_subset]

    assert len(subset) == 30
    assert Counter(case.domain for case in subset) == {
        BenchmarkDomain.VENDOR_ONBOARDING: 10,
        BenchmarkDomain.PRODUCTION_RELEASE: 10,
        BenchmarkDomain.PRIVILEGED_ACCESS: 10,
    }


def test_case_files_validate_against_the_versioned_schema_contract() -> None:
    corpus = load_corpus()

    assert corpus.schema_path.name == "schema.json"
    assert corpus.schema_version == "continuum-dependency-bench-v1"
    assert all(case.schema_version == corpus.schema_version for case in corpus.cases)
