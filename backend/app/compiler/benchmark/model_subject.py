from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.compiler.benchmark.corpus import BenchmarkCase, BenchmarkSource
from app.compiler.benchmark.runner import Prediction, UsageSummary
from app.compiler.budget import ModelPricing, ModelUsage
from app.compiler.canonicalization import DeterministicCanonicalizer
from app.compiler.context import CompilationContext, RiskClass
from app.compiler.models import (
    CriticFindingType,
    CriticReview,
    Materiality,
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
                raise ValueError("all fragments in a revision must share current status")
            if True in current_flags:
                current_count += 1
                current_revisions[artifact_id] = ingested.revision.revision_id
                current_representations[ingested.revision.revision_id] = (
                    ingested.representation.representation_id
                )
        if current_count != 1:
            raise ValueError(f"artifact requires exactly one current revision: {artifact_id}")

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
        allowed_source_refs=frozenset(
            source.source_ref for source in case.sources
        ),
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
        self._input_tokens = 0
        self._cached_input_tokens = 0
        self._output_tokens = 0
        self._cost_usd = Decimal("0")

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
            result_payload: object = compilation.model_dump(mode="json")
        else:
            result_payload = {
                "draft": draft.model_dump(mode="json"),
                "validation": validation.model_dump(mode="json"),
                "review": review.model_dump(mode="json"),
            }
        deterministic_hash = _digest(result_payload)
        contradictions = tuple(
            (finding.source_ref_a, finding.source_ref_b)
            for finding in review.contradictions
        )
        return Prediction(
            critical_refs=critical_refs,
            accepted_canonical_refs=accepted_refs,
            detected_contradictions=contradictions,
            predicted_stale_after_mutation=(
                case.mutation.source_ref in critical_refs
            ),
            repeat_compilation_hashes=(
                deterministic_hash,
                deterministic_hash,
                deterministic_hash,
            ),
        )

    def usage_summary(self) -> UsageSummary:
        return UsageSummary(
            input_tokens=self._input_tokens,
            cached_input_tokens=self._cached_input_tokens,
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
        raise ValueError(f"benchmark authoring only supports top-level fields: {logical_path}")
    return logical_path[2:]


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = ["ModelCompilerSubject", "build_case_runtime"]
