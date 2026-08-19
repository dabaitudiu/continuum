from __future__ import annotations

import inspect
import json

from app.compiler.benchmark import cli as benchmark_cli
from app.compiler.benchmark import model_subject as model_subject_module
from app.compiler.benchmark import report as benchmark_report
from app.compiler.benchmark.corpus import BenchmarkCaseClass, load_corpus
from app.compiler.benchmark.model_subject import (
    ModelCompilerSubject,
    build_case_runtime,
)
from app.compiler.models import (
    ClaimDraft,
    ClaimType,
    CompilationDisposition,
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
    assert not prediction.predicted_stale_after_mutation
    assert prediction.repeat_compilation_hashes == ()
    assert [call.output_schema for call in transport.invocations] == [
        DecisionProposal,
        CriticProposal,
    ]
    usage = subject.usage_summary()
    assert usage.input_tokens == 200
    assert usage.cached_input_tokens == 20
    assert usage.output_tokens == 80
    assert float(usage.actual_cost_usd) > 0


def test_paired_ablation_shares_one_reasoner_draft_and_traces_critic_effect() -> None:
    paired_subject_type = getattr(
        model_subject_module,
        "PairedAblationSubject",
        None,
    )
    assert paired_subject_type is not None
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
    subject = paired_subject_type(
        reasoner=DependencyReasoner(
            transport,
            model_name="gpt-5.6-luna",
            prompt_version="reasoner-v2",
        ),
        critic=ModelDependencyCritic(
            transport,
            model_name="gpt-5.6-luna",
            prompt_version="critic-v1",
        ),
        execution_namespace="paired-test",
    )

    evidence = subject.evaluate(case, run_index=0)

    assert [call.output_schema for call in transport.invocations] == [
        DecisionProposal,
        CriticProposal,
    ]
    assert evidence.reasoner_critical_refs == (primary_ref,)
    assert evidence.critic_added_critical_refs == (missing_ref,)
    assert evidence.reasoner_only.disposition is CompilationDisposition.ACCEPTED
    assert evidence.reasoner_only.accepted_canonical_refs == (primary_ref,)
    assert evidence.reasoner_only.mutation.terminal == "STALE"
    assert evidence.critic_on.disposition is (
        CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    )
    assert evidence.critic_on.accepted_canonical_refs == ()
    assert evidence.critic_on.mutation.terminal == "NOT_ACCEPTED"
    assert evidence.validation.findings == []
    assert len(evidence.critic_review.findings) == 1
    assert evidence.reasoner_only.accepted_dependency_edges


def test_paired_ablation_run_measures_both_arms_and_exact_critic_delta() -> None:
    runner_type = getattr(model_subject_module, "PairedAblationRunner", None)
    configuration_type = getattr(
        model_subject_module,
        "AblationRunConfiguration",
        None,
    )
    assert runner_type is not None
    assert configuration_type is not None
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
    subject = model_subject_module.PairedAblationSubject(
        reasoner=DependencyReasoner(
            transport,
            model_name="gpt-5.6-luna",
            prompt_version="reasoner-v2",
        ),
        critic=ModelDependencyCritic(
            transport,
            model_name="gpt-5.6-luna",
            prompt_version="critic-v1",
        ),
        execution_namespace="paired-run-test",
    )
    configuration = configuration_type(
        provider="OPENAI",
        model="gpt-5.6-luna",
        reasoner_prompt_version="reasoner-v2",
        critic_prompt_version="critic-v1",
        temperature=None,
        reasoning_effort="low",
        service_tier="default",
        case_set="unit-one-case",
        max_incremental_cost_usd="0.25",
    )

    observed_records = []
    run = runner_type([case]).run(
        subject,
        configuration,
        record_observer=observed_records.append,
    )

    assert len(run.records) == 1
    assert observed_records == list(run.records)
    assert run.records[0].reasoner_duration_ms >= 0
    assert run.records[0].critic_duration_ms >= 0
    assert run.reasoner_only.corrected.proposal_critical_recall == 0.5
    assert run.reasoner_only.corrected.acceptance_coverage == 1.0
    assert run.critic_on.corrected.proposal_critical_recall == 1.0
    assert run.critic_on.corrected.acceptance_coverage == 0.0
    assert run.critic_effect.required_omissions_recovered == 1
    assert run.critic_effect.false_positive_refs_added == 0
    assert run.critic_effect.correct_contradictions_added == 0
    assert run.critic_effect.accepted_case_delta == -1


def test_ablation_report_persists_both_arms_and_k3_decision(tmp_path) -> None:  # type: ignore[no-untyped-def]
    write_ablation = getattr(
        benchmark_report,
        "write_critic_ablation_report",
        None,
    )
    assert write_ablation is not None
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
    subject = model_subject_module.PairedAblationSubject(
        reasoner=DependencyReasoner(
            transport,
            model_name="gpt-5.6-luna",
            prompt_version="reasoner-v2",
        ),
        critic=ModelDependencyCritic(
            transport,
            model_name="gpt-5.6-luna",
            prompt_version="critic-v1",
        ),
        execution_namespace="paired-report-test",
    )
    configuration = model_subject_module.AblationRunConfiguration(
        provider="OPENAI",
        model="gpt-5.6-luna",
        reasoner_prompt_version="reasoner-v2",
        critic_prompt_version="critic-v1",
        temperature=None,
        reasoning_effort="low",
        service_tier="default",
        case_set="unit-one-case",
        max_incremental_cost_usd="0.25",
    )
    run = model_subject_module.PairedAblationRunner([case]).run(
        subject,
        configuration,
    )

    json_path, markdown_path = write_ablation(run, output_dir=tmp_path)
    append_evidence = getattr(
        benchmark_report,
        "append_critic_ablation_evidence",
        None,
    )
    assert append_evidence is not None
    evidence_path = tmp_path / "partial-evidence.jsonl"
    append_evidence(run.records[0], output_path=evidence_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "continuum-critic-ablation-report-v1"
    assert payload["k3_decision"] == "RETAIN_SIGNAL"
    assert payload["run"]["run_id"] == run.run_id
    assert payload["run"]["usage"]["reasoner"]["duration_ms"] >= 0
    assert payload["run"]["usage"]["critic"]["duration_ms"] >= 0
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Reasoner-only" in markdown
    assert "Current critic" in markdown
    assert "required omissions recovered" in markdown
    assert "RETAIN_SIGNAL" in markdown
    assert "Latency ms" in markdown
    evidence_lines = evidence_path.read_text(encoding="utf-8").splitlines()
    assert len(evidence_lines) == 1
    assert json.loads(evidence_lines[0])["case_id"] == case.case_id

    proposal_only_run = run.model_copy(
        update={
            "critic_effect": run.critic_effect.model_copy(
                update={"true_omission_blocks": 0}
            )
        }
    )
    proposal_only_json, _ = write_ablation(
        proposal_only_run,
        output_dir=tmp_path / "proposal-only",
    )
    proposal_only_payload = json.loads(proposal_only_json.read_text(encoding="utf-8"))
    assert proposal_only_payload["k3_decision"] == "REMOVE_OR_REDESIGN"


def test_critic_ablation_entrypoint_runs_paired_cases_with_injected_transport(
    tmp_path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    execute = benchmark_cli._run_live_openai_critic_ablation
    assert "transport" in inspect.signature(execute).parameters
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
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    observed_records = []
    run = execute(
        tmp_path / "budget.db",
        transport=transport,
        cases=[case],
        execution_namespace="injected-ablation",
        record_observer=observed_records.append,
    )

    assert len(run.records) == 1
    assert observed_records == list(run.records)
    assert run.configuration.case_set == "injected-1-case"
    assert run.critic_effect.required_omissions_recovered == 1
    assert len(transport.invocations) == 2
    serialized_prompts = "\n".join(
        invocation.system_instruction + "\n" + invocation.user_prompt
        for invocation in transport.invocations
    )
    for evaluator_only_field in (
        "ground_truth",
        "required_critical_refs",
        "forbidden_refs",
        "expected_blocking_contradictions",
        "expected_outcome_constraints",
        "expected_stale_decision_ids",
    ):
        assert evaluator_only_field not in serialized_prompts


def test_critic_ablation_cli_writes_only_the_dedicated_report(
    tmp_path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
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
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    run = benchmark_cli._run_live_openai_critic_ablation(
        tmp_path / "budget.db",
        transport=transport,
        cases=[case],
        execution_namespace="cli-ablation",
    )

    def fake_live_ablation(
        budget_path,
        *,
        execution_namespace,
        record_observer,
    ):  # type: ignore[no-untyped-def]
        for record in run.records:
            record_observer(record)
        return run

    monkeypatch.setattr(
        benchmark_cli,
        "_run_live_openai_critic_ablation",
        fake_live_ablation,
    )
    output_dir = tmp_path / "reports"
    old_report = output_dir / "module-01-dependency-compiler.json"
    output_dir.mkdir()
    old_report.write_text("historical-evidence\n", encoding="utf-8")

    exit_code = benchmark_cli.main(
        [
            "ablate-critic",
            "--output-dir",
            str(output_dir),
            "--budget-ledger",
            str(tmp_path / "budget.db"),
        ]
    )

    assert exit_code == 0
    assert old_report.read_text(encoding="utf-8") == "historical-evidence\n"
    assert (output_dir / "module-01-critic-ablation.json").exists()
    assert (output_dir / "module-01-critic-ablation.md").exists()
    evidence_paths = list(output_dir.glob("module-01-critic-ablation-evidence-*.jsonl"))
    assert len(evidence_paths) == 1
    assert len(evidence_paths[0].read_text(encoding="utf-8").splitlines()) == 1
