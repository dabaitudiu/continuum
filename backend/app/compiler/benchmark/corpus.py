from __future__ import annotations

import json
from collections import Counter
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.sources.identity import ArtifactType, SourceRef, SourceType, TrustClass


SCHEMA_VERSION = "continuum-dependency-bench-v1"


class BenchmarkDomain(StrEnum):
    VENDOR_ONBOARDING = "vendor-onboarding"
    PRODUCTION_RELEASE = "production-release"
    PRIVILEGED_ACCESS = "privileged-access"


class BenchmarkCaseClass(StrEnum):
    CLEAN_POSITIVE = "clean-positive"
    CLEAN_NEGATIVE = "clean-negative"
    CRITICAL_OMISSION = "critical-omission"
    IRRELEVANT_DISTRACTOR = "irrelevant-distractor"
    OBSOLETE_REVISION = "obsolete-revision"
    CONFLICTING_SOURCES = "conflicting-sources"
    NEAR_DUPLICATE = "near-duplicate"
    PROMPT_INJECTION = "prompt-injection"
    MULTIPLE_DEPENDENCIES = "multiple-dependencies"
    NARROW_CLAUSE = "narrow-clause"


class AdversarialTag(StrEnum):
    PROMPT_INJECTION = "prompt-injection"
    NEAR_MATCH = "near-match"
    OBSOLETE_REVISION = "obsolete-revision"
    CONTRADICTORY_AUTHORITY = "contradictory-authority"
    CRITICAL_OMISSION = "critical-omission"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BenchmarkSource(FrozenModel):
    source_ref: str = Field(min_length=1, max_length=2048)
    artifact_id: str = Field(min_length=1, max_length=256)
    artifact_type: ArtifactType
    logical_key: str = Field(min_length=1, max_length=256)
    revision_label: str = Field(min_length=1, max_length=128)
    parser_version: str = Field(min_length=1, max_length=128)
    logical_path: str = Field(min_length=1, max_length=512)
    source_type: SourceType
    trust_class: TrustClass
    authority_rank: int = Field(ge=0)
    content: Any
    current: bool

    @model_validator(mode="after")
    def _ref_matches_source_fields(self) -> BenchmarkSource:
        parsed = SourceRef.parse(self.source_ref)
        if (
            parsed.artifact_id != self.artifact_id
            or parsed.revision_label != self.revision_label
            or parsed.logical_path != self.logical_path
            or parsed.representation_id is None
        ):
            raise ValueError("source_ref does not match benchmark source identity fields")
        return self


class BenchmarkContradiction(FrozenModel):
    source_ref_a: str = Field(min_length=1, max_length=2048)
    source_ref_b: str = Field(min_length=1, max_length=2048)
    topic: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def _distinct_refs(self) -> BenchmarkContradiction:
        if self.source_ref_a == self.source_ref_b:
            raise ValueError("contradiction refs must be distinct")
        return self


class ExpectedOutcomeConstraints(FrozenModel):
    allowed_outcomes: list[str] = Field(min_length=1, max_length=10)
    must_block: bool

    @field_validator("allowed_outcomes")
    @classmethod
    def _unique_outcomes(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or value != value.strip() for value in values):
            raise ValueError("allowed outcomes must be trimmed")
        if len(values) != len(set(values)):
            raise ValueError("allowed outcomes must be unique")
        return values


class BenchmarkGroundTruth(FrozenModel):
    required_critical_refs: list[str] = Field(default_factory=list, max_length=20)
    acceptable_supporting_refs: list[str] = Field(default_factory=list, max_length=20)
    forbidden_or_irrelevant_refs: list[str] = Field(default_factory=list, max_length=20)
    expected_outcome_constraints: ExpectedOutcomeConstraints
    blocking_contradictions: list[BenchmarkContradiction] = Field(
        default_factory=list,
        max_length=10,
    )


class BenchmarkMutation(FrozenModel):
    source_ref: str = Field(min_length=1, max_length=2048)
    mutation_kind: str = Field(min_length=1, max_length=128)
    replacement_content: Any
    expected_stale_decision_ids: list[str] = Field(default_factory=list, max_length=10)
    expected_unchanged_decision_ids: list[str] = Field(
        default_factory=list,
        max_length=10,
    )


class BenchmarkCase(FrozenModel):
    schema_version: str
    case_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=500)
    domain: BenchmarkDomain
    case_class: BenchmarkCaseClass
    adversarial_tags: list[AdversarialTag] = Field(default_factory=list)
    variance_subset: bool
    decision_type: str = Field(min_length=1, max_length=128)
    task: str = Field(min_length=1, max_length=2000)
    proposed_outcome: str = Field(min_length=1, max_length=256)
    sources: list[BenchmarkSource] = Field(min_length=1, max_length=20)
    ground_truth: BenchmarkGroundTruth
    mutation: BenchmarkMutation

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError(f"unsupported benchmark schema: {value}")
        return value

    @model_validator(mode="after")
    def _validate_refs(self) -> BenchmarkCase:
        source_refs = [source.source_ref for source in self.sources]
        if len(source_refs) != len(set(source_refs)):
            raise ValueError("case source refs must be unique")
        known = set(source_refs)
        truth = {
            *self.ground_truth.required_critical_refs,
            *self.ground_truth.acceptable_supporting_refs,
            *self.ground_truth.forbidden_or_irrelevant_refs,
        }
        for contradiction in self.ground_truth.blocking_contradictions:
            truth.update(
                (contradiction.source_ref_a, contradiction.source_ref_b)
            )
        if not truth <= known:
            raise ValueError("ground-truth ref is absent from case sources")
        if self.mutation.source_ref not in known:
            raise ValueError("mutation source_ref is absent from case sources")
        expected = {
            *self.mutation.expected_stale_decision_ids,
            *self.mutation.expected_unchanged_decision_ids,
        }
        if expected != {f"decision:{self.case_id}"}:
            raise ValueError("mutation expectation must classify the case decision")
        return self


class BenchmarkCorpus(FrozenModel):
    schema_version: str
    schema_path: Path
    cases: list[BenchmarkCase]


class CorpusValidationError(ValueError):
    pass


def default_corpus_root() -> Path:
    return Path(__file__).resolve().parents[4] / "bench" / "dependency"


def load_corpus(root: Path | None = None) -> BenchmarkCorpus:
    corpus_root = (root or default_corpus_root()).resolve()
    schema_path = corpus_root / "schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CorpusValidationError(f"cannot read benchmark schema: {error}") from error
    if schema.get("$id") != SCHEMA_VERSION:
        raise CorpusValidationError("benchmark schema id does not match loader version")

    cases: list[BenchmarkCase] = []
    for path in sorted((corpus_root / "cases").glob("*/*.json")):
        try:
            cases.append(
                BenchmarkCase.model_validate_json(path.read_text(encoding="utf-8"))
            )
        except Exception as error:
            raise CorpusValidationError(f"invalid benchmark case {path}: {error}") from error
    _validate_distribution(cases)
    return BenchmarkCorpus(
        schema_version=SCHEMA_VERSION,
        schema_path=schema_path,
        cases=cases,
    )


def _validate_distribution(cases: list[BenchmarkCase]) -> None:
    if len(cases) != 120:
        raise CorpusValidationError(f"expected exactly 120 cases, found {len(cases)}")
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise CorpusValidationError("benchmark case IDs must be unique")
    domains = Counter(case.domain for case in cases)
    if any(domains[domain] != 40 for domain in BenchmarkDomain):
        raise CorpusValidationError(f"expected 40 cases per domain, found {domains}")
    adversarial = Counter(tag for case in cases for tag in case.adversarial_tags)
    if any(adversarial[tag] < 10 for tag in AdversarialTag):
        raise CorpusValidationError(
            f"each adversarial tag requires at least 10 cases, found {adversarial}"
        )
    variance = Counter(
        case.domain for case in cases if case.variance_subset
    )
    if sum(variance.values()) != 30 or any(
        variance[domain] != 10 for domain in BenchmarkDomain
    ):
        raise CorpusValidationError(
            f"variance subset must contain 10 cases per domain, found {variance}"
        )


__all__ = [
    "AdversarialTag",
    "BenchmarkCase",
    "BenchmarkCaseClass",
    "BenchmarkCorpus",
    "BenchmarkDomain",
    "BenchmarkGroundTruth",
    "BenchmarkMutation",
    "BenchmarkSource",
    "CorpusValidationError",
    "load_corpus",
]
