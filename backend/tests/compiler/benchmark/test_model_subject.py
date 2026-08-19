from __future__ import annotations

from app.compiler.benchmark.corpus import BenchmarkCaseClass, load_corpus
from app.compiler.benchmark.model_subject import (
    ModelCompilerSubject,
    build_case_runtime,
)
from app.compiler.models import (
    ClaimDraft,
    ClaimType,
    CriticProposal,
    DecisionProposal,
    DependencyRef,
    DependencyRelation,
    Materiality,
    MissingDependencyProposal,
)
from app.compiler.reasoner import (
    DependencyReasoner,
    ModelInvocation,
    StructuredModelResponse,
    openai_luna_pricing,
)
from app.compiler.review import ModelDependencyCritic


class RecordingTransport:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.invocations: list[ModelInvocation] = []

    def generate(self, invocation: ModelInvocation) -> StructuredModelResponse:
        self.invocations.append(invocation)
        outcome = self.outcomes.pop(0)
        return StructuredModelResponse(
            parsed=outcome,  # type: ignore[arg-type]
            provider="OPENAI",
            model_name="gpt-5.6-luna",
            model_version="gpt-5.6-luna-2026-08-01",
            response_id=f"response-{len(self.invocations)}",
            execution_id=invocation.call_id,
            input_tokens=100,
            cached_input_tokens=10,
            output_tokens=40,
        )


def test_case_runtime_reconstructs_exact_committed_refs_including_history() -> None:
    case = next(
        case
        for case in load_corpus().cases
        if case.case_class is BenchmarkCaseClass.OBSOLETE_REVISION
    )

    runtime = build_case_runtime(case, execution_id="execution-test")

    assert {source.source_ref for source in runtime.tools.list_source_inventory()} == {
        source.source_ref for source in case.sources
    }
    assert runtime.context.allow_historical
    assert runtime.request.task == case.task


def test_model_subject_counts_critic_recovery_without_silently_accepting_it() -> None:
    case = next(
        case
        for case in load_corpus().cases
        if case.case_class is BenchmarkCaseClass.CRITICAL_OMISSION
    )
    primary_ref, missing_ref = case.ground_truth.required_critical_refs
    transport = RecordingTransport(
        [
            DecisionProposal(
                decision_type=case.decision_type,
                proposed_outcome=case.proposed_outcome,
                claims=[
                    ClaimDraft(
                        claim_local_id="c1",
                        claim_type=ClaimType.RULE,
                        statement="The primary current policy applies.",
                        dependencies=[
                            DependencyRef(
                                source_ref=primary_ref,
                                relation=DependencyRelation.GOVERNED_BY,
                                materiality=Materiality.CRITICAL,
                            )
                        ],
                        materiality=Materiality.CRITICAL,
                        confidence=0.99,
                    )
                ],
                rationale_summary="The primary policy was evaluated.",
            ),
            CriticProposal(
                missing_dependencies=[
                    MissingDependencyProposal(
                        candidate_ref=missing_ref,
                        severity=Materiality.CRITICAL,
                        why="The second material requirement was omitted.",
                    )
                ]
            ),
        ]
    )
    subject = ModelCompilerSubject(
        reasoner=DependencyReasoner(
            transport,
            model_name="gpt-5.6-luna",
            prompt_version="reasoner-v1",
        ),
        critic=ModelDependencyCritic(
            transport,
            model_name="gpt-5.6-luna",
            prompt_version="critic-v1",
        ),
        reasoner_pricing=openai_luna_pricing(),
        critic_pricing=openai_luna_pricing(),
    )

    prediction = subject.predict(case, run_index=1)

    assert set(prediction.critical_refs) == {primary_ref, missing_ref}
    assert prediction.accepted_canonical_refs == ()
    assert prediction.predicted_stale_after_mutation
    assert len(set(prediction.repeat_compilation_hashes)) == 1
    assert [call.output_schema for call in transport.invocations] == [
        DecisionProposal,
        CriticProposal,
    ]
    usage = subject.usage_summary()
    assert usage.input_tokens == 200
    assert usage.cached_input_tokens == 20
    assert usage.output_tokens == 80
    assert float(usage.actual_cost_usd) > 0
