from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from openai import InternalServerError
from app.compiler.benchmark.cli import _openai_client, _reasoner_error_evidence, main
from app.compiler.benchmark.corpus import load_corpus
from app.compiler.benchmark.report import write_report_bundle
from app.compiler.benchmark.runner import (
    BaselineKind,
    BenchmarkRunner,
    DocumentLevelSubject,
    EvidenceLane,
    EvidenceStatus,
    FullPipelineReferenceSubject,
    RunConfiguration,
    SinglePassReferenceSubject,
    UsageSummary,
    blocked_evidence_run,
    evaluate_runtime_mutation,
)
from app.compiler.models import CompilationDisposition
from app.compiler.reasoner import ReasonerError


def _configuration(
    baseline: BaselineKind,
    *,
    lane: EvidenceLane = EvidenceLane.DETERMINISTIC_REFERENCE,
) -> RunConfiguration:
    return RunConfiguration(
        baseline=baseline,
        evidence_lane=lane,
        provider="REFERENCE",
        reasoner_model="deterministic-reference-v1",
        critic_model=(
            "deterministic-reference-critic-v1"
            if baseline is BaselineKind.FULL_PIPELINE
            else None
        ),
        reasoner_prompt_version="reasoner-v1",
        critic_prompt_version=(
            "critic-v1" if baseline is BaselineKind.FULL_PIPELINE else None
        ),
        temperature=0.0,
    )


def test_document_level_baseline_marks_every_read_source_critical() -> None:
    corpus = load_corpus()

    run = BenchmarkRunner(corpus).run(
        DocumentLevelSubject(),
        _configuration(BaselineKind.DOCUMENT_LEVEL),
    )

    assert run.status is EvidenceStatus.FAIL
    assert len(run.records) == 120
    assert run.metrics is not None
    assert run.metrics.critical_recall == 1.0
    assert run.metrics.critical_precision < 0.82
    assert run.metrics.unnecessary_invalidation_rate == 1.0
    first = run.records[0]
    first_case = corpus.cases[0]
    assert set(first.predicted_critical_refs) == {
        source.source_ref for source in first_case.sources
    }


def test_full_pipeline_reference_improves_recall_and_contradiction_detection() -> None:
    runner = BenchmarkRunner(load_corpus())
    single = runner.run(
        SinglePassReferenceSubject(),
        _configuration(BaselineKind.SINGLE_PASS),
    )
    full = runner.run(
        FullPipelineReferenceSubject(),
        _configuration(BaselineKind.FULL_PIPELINE),
    )

    assert single.metrics is not None
    assert full.metrics is not None
    assert full.metrics.critical_recall > single.metrics.critical_recall
    assert full.metrics.contradiction_recall > single.metrics.contradiction_recall
    assert full.metrics.outcome_compliance == 1.0
    assert full.metrics.blocking_disposition_compliance == 1.0
    assert full.metrics.contradiction_severity_recall == 1.0
    assert full.gate is not None and full.gate.passed
    assert full.status is EvidenceStatus.PASS


def test_variance_protocol_runs_three_times_for_balanced_thirty_case_subset() -> None:
    run = BenchmarkRunner(load_corpus()).run(
        FullPipelineReferenceSubject(),
        _configuration(BaselineKind.FULL_PIPELINE),
    )

    assert run.variance is not None
    assert run.variance.case_count == 30
    assert run.variance.runs_per_case == 3
    assert run.variance.total_observations == 90
    assert len(run.variance.run_critical_recalls) == 3
    assert run.variance.mean_critical_recall == 1.0
    assert run.variance.worst_run_critical_recall == 1.0
    assert run.configuration.reasoner_model == "deterministic-reference-v1"
    assert run.configuration.reasoner_prompt_version == "reasoner-v1"


def test_mutation_metric_is_read_from_runtime_not_subject_self_report() -> None:
    case = next(
        case
        for case in load_corpus().cases
        if case.mutation.expected_stale_decision_ids
    )
    prediction = FullPipelineReferenceSubject().predict(case, run_index=0)
    lied = prediction.model_copy(update={"predicted_stale_after_mutation": False})

    assert evaluate_runtime_mutation(case, lied)


def test_gate_rejects_a_subject_with_non_deterministic_compilation_hashes() -> None:
    class NonDeterministicSubject(FullPipelineReferenceSubject):
        def predict(self, case, *, run_index):  # type: ignore[no-untyped-def]
            prediction = super().predict(case, run_index=run_index)
            if (
                prediction.compilation_disposition
                is not CompilationDisposition.ACCEPTED
            ):
                return prediction
            return prediction.model_copy(
                update={"repeat_compilation_hashes": ("first", "second")}
            )

    run = BenchmarkRunner(load_corpus()).run(
        NonDeterministicSubject(),
        _configuration(BaselineKind.FULL_PIPELINE),
    )

    assert run.gate is not None and not run.gate.passed
    determinism = next(
        row for row in run.gate.rows if row.metric == "compilation_determinism"
    )
    assert not determinism.passed


def test_missing_live_credentials_are_blocked_evidence_not_a_pass() -> None:
    run = blocked_evidence_run(
        _configuration(
            BaselineKind.FULL_PIPELINE,
            lane=EvidenceLane.LIVE_OPENAI,
        ),
        reason="OPENAI_API_KEY is not configured",
    )

    assert run.status is EvidenceStatus.BLOCKED
    assert run.metrics is None
    assert run.gate is None
    assert "OPENAI_API_KEY" in (run.blocked_reason or "")


def test_executed_model_schema_failure_is_fail_not_blocked() -> None:
    usage = UsageSummary(
        input_tokens=100,
        cache_write_tokens=20,
        output_tokens=10,
        actual_cost_usd="0.000037000",
    )
    run = _reasoner_error_evidence(
        _configuration(
            BaselineKind.FULL_PIPELINE,
            lane=EvidenceLane.LIVE_OPENAI,
        ),
        ReasonerError("MODEL_SCHEMA_INVALID", "typed output was invalid"),
        usage=usage,
    )

    assert run.status is EvidenceStatus.FAIL
    assert run.blocked_reason is None
    assert "MODEL_SCHEMA_INVALID" in (run.failure_reason or "")
    assert run.usage == usage


def test_report_bundle_separates_evidence_lanes_and_records_configuration(
    tmp_path: Path,
) -> None:
    runner = BenchmarkRunner(load_corpus())
    reference = runner.run(
        FullPipelineReferenceSubject(),
        _configuration(BaselineKind.FULL_PIPELINE),
    )
    blocked = blocked_evidence_run(
        _configuration(
            BaselineKind.FULL_PIPELINE,
            lane=EvidenceLane.LIVE_GEMINI,
        ),
        reason="Gemini credentials are not configured",
    )

    json_path, markdown_path = write_report_bundle(
        [reference, blocked],
        output_dir=tmp_path,
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert {run["configuration"]["evidence_lane"] for run in payload["runs"]} == {
        "deterministic_reference",
        "live_gemini",
    }
    assert payload["runs"][0]["configuration"]["reasoner_prompt_version"]
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "deterministic_reference" in markdown
    assert "live_gemini" in markdown
    assert "BLOCKED" in markdown
    assert "compiler-lab-product-report.md" in markdown


def test_cli_returns_nonzero_for_a_failed_metric_gate_and_zero_for_reference_pass(
    tmp_path: Path,
) -> None:
    assert main(["run", "--suite", "document", "--output-dir", str(tmp_path)]) == 1
    assert main(["run", "--suite", "full", "--output-dir", str(tmp_path)]) == 0


def test_live_openai_cli_without_key_writes_blocked_not_pass_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main(["run", "--suite", "live-openai", "--output-dir", str(tmp_path)])

    payload = json.loads(
        (tmp_path / "module-01-dependency-compiler.json").read_text(encoding="utf-8")
    )
    run = payload["runs"][0]
    assert exit_code == 1
    assert run["status"] == "BLOCKED"
    assert run["configuration"]["evidence_lane"] == "live_openai"
    assert run["configuration"]["cumulative_budget_usd"] == "10"
    assert run["configuration"]["reasoner_prompt_version"] == "reasoner-v2"
    assert "OPENAI_API_KEY" in run["blocked_reason"]


def test_openai_client_disables_sdk_level_retries(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-local-http-mock")
    requests = 0

    def fail_once(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(
            500,
            request=request,
            json={"error": {"message": "synthetic failure", "type": "server_error"}},
        )

    http_client = httpx.Client(transport=httpx.MockTransport(fail_once))
    client = _openai_client(http_client=http_client)

    with pytest.raises(InternalServerError):
        client.responses.create(model="gpt-5.6-luna", input="test")

    assert client.max_retries == 0
    assert requests == 1
