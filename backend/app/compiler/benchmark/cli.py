from __future__ import annotations

import argparse
import os
import sys
import uuid
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.compiler.benchmark.corpus import BenchmarkCase, load_corpus
from app.compiler.benchmark.model_subject import (
    AblationRunConfiguration,
    AblationStageUsage,
    AblationUsage,
    ModelCompilerSubject,
    PairedAblationRun,
    PairedAblationRunner,
    PairedAblationSubject,
    PairedCaseEvidence,
)
from app.compiler.benchmark.report import (
    append_critic_ablation_evidence,
    write_critic_ablation_report,
    write_report_bundle,
)
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
    failed_evidence_run,
)
from app.compiler.budget import (
    ScopedBudgetLedger,
    SettledUsageSummary,
    SQLiteBudgetLedger,
)
from app.compiler.prompts import CRITIC_PROMPT_VERSION, REASONER_PROMPT_VERSION
from app.compiler.reasoner import (
    AdkGeminiTransport,
    DependencyReasoner,
    OpenAIResponsesTransport,
    ReasonerError,
    StructuredModelTransport,
    openai_luna_pricing,
)
from app.compiler.review import ModelDependencyCritic


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="continuum-dependency-bench")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument(
        "--suite",
        choices=(
            "document",
            "single",
            "full",
            "all",
            "evidence",
            "live-openai",
            "live-gemini",
        ),
        default="all",
    )
    run_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[4] / "docs" / "reports",
    )
    run_parser.add_argument(
        "--budget-ledger",
        type=Path,
        default=Path(__file__).resolve().parents[3]
        / "data"
        / "openai-benchmark-budget.db",
    )
    ablation_parser = subparsers.add_parser("ablate-critic")
    ablation_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[4] / "docs" / "reports",
    )
    ablation_parser.add_argument(
        "--budget-ledger",
        type=Path,
        default=Path(__file__).resolve().parents[3]
        / "data"
        / "openai-benchmark-budget.db",
    )
    args = parser.parse_args(argv)

    if args.command == "ablate-critic":
        execution_suffix = uuid.uuid4().hex
        execution_namespace = f"critic-ablation-openai-{execution_suffix}"
        evidence_path = (
            args.output_dir
            / f"module-01-critic-ablation-evidence-{execution_suffix}.jsonl"
        )
        try:
            ablation = _run_live_openai_critic_ablation(
                args.budget_ledger,
                execution_namespace=execution_namespace,
                record_observer=lambda record: append_critic_ablation_evidence(
                    record,
                    output_path=evidence_path,
                ),
            )
        except ReasonerError as error:
            print(f"{error.code}: {error.message}", file=sys.stderr)
            if evidence_path.exists():
                print(
                    f"Partial evidence: {evidence_path}",
                    file=sys.stderr,
                )
            return 1
        write_critic_ablation_report(ablation, output_dir=args.output_dir)
        return 0

    runner = BenchmarkRunner(load_corpus())
    suites = {
        "document": (
            DocumentLevelSubject(),
            _configuration(BaselineKind.DOCUMENT_LEVEL),
        ),
        "single": (
            SinglePassReferenceSubject(),
            _configuration(BaselineKind.SINGLE_PASS),
        ),
        "full": (
            FullPipelineReferenceSubject(),
            _configuration(BaselineKind.FULL_PIPELINE),
        ),
    }
    if args.suite == "live-openai":
        runs = [_run_live_openai(runner, args.budget_ledger)]
    elif args.suite == "live-gemini":
        runs = [_run_live_gemini(runner)]
    else:
        selected = (
            suites.values()
            if args.suite in {"all", "evidence"}
            else (suites[args.suite],)
        )
        runs = [runner.run(subject, config) for subject, config in selected]
        if args.suite == "evidence":
            runs.extend(
                (
                    _run_live_openai(runner, args.budget_ledger),
                    _run_live_gemini(runner),
                )
            )
    write_report_bundle(runs, output_dir=args.output_dir)
    return 0 if all(run.status is EvidenceStatus.PASS for run in runs) else 1


def _configuration(baseline: BaselineKind) -> RunConfiguration:
    is_full = baseline is BaselineKind.FULL_PIPELINE
    return RunConfiguration(
        baseline=baseline,
        evidence_lane=EvidenceLane.DETERMINISTIC_REFERENCE,
        provider="REFERENCE",
        reasoner_model="deterministic-reference-v1",
        critic_model="deterministic-reference-critic-v1" if is_full else None,
        reasoner_prompt_version=REASONER_PROMPT_VERSION,
        critic_prompt_version=CRITIC_PROMPT_VERSION if is_full else None,
        temperature=0.0,
    )


def _run_live_openai(
    runner: BenchmarkRunner,
    budget_path: Path,
):  # type: ignore[no-untyped-def]
    pricing = openai_luna_pricing()
    model_name = os.environ.get("CONTINUUM_OPENAI_MODEL", pricing.model_name)
    configuration = RunConfiguration(
        baseline=BaselineKind.FULL_PIPELINE,
        evidence_lane=EvidenceLane.LIVE_OPENAI,
        provider="OPENAI",
        reasoner_model=model_name,
        critic_model=model_name,
        reasoner_prompt_version=REASONER_PROMPT_VERSION,
        critic_prompt_version=CRITIC_PROMPT_VERSION,
        temperature=None,
        pricing_version=pricing.pricing_version,
        cumulative_budget_usd="10",
    )
    if not os.environ.get("OPENAI_API_KEY"):
        return blocked_evidence_run(
            configuration,
            reason="OPENAI_API_KEY is not configured",
        )
    if model_name != pricing.model_name:
        return blocked_evidence_run(
            configuration,
            reason=(
                "CONTINUUM_OPENAI_MODEL has no audited pricing entry; refusing "
                "to weaken the cumulative $10 budget gate"
            ),
        )

    ledger = SQLiteBudgetLedger(budget_path, limit_usd=Decimal(10))
    try:
        execution_namespace = f"benchmark-openai-{uuid.uuid4().hex}"
        transport = OpenAIResponsesTransport(
            client=_openai_client(),
            budget=ledger,
            pricing=pricing,
            max_input_tokens=250_000,
            max_output_tokens=8_192,
        )
        subject = ModelCompilerSubject(
            reasoner=DependencyReasoner(
                transport,
                model_name=model_name,
                prompt_version=REASONER_PROMPT_VERSION,
            ),
            critic=ModelDependencyCritic(
                transport,
                model_name=model_name,
                prompt_version=CRITIC_PROMPT_VERSION,
            ),
            reasoner_pricing=pricing,
            critic_pricing=pricing,
            execution_namespace=execution_namespace,
            settled_usage_supplier=lambda: ledger.settled_usage(
                execution_namespace + ":"
            ),
        )
        try:
            return runner.run(subject, configuration)
        except ReasonerError as error:
            return _reasoner_error_evidence(
                configuration,
                error,
                usage=subject.usage_summary(),
            )
    finally:
        ledger.close()


def _openai_client(*, http_client: Any | None = None):  # type: ignore[no-untyped-def]
    from openai import OpenAI

    kwargs: dict[str, Any] = {"max_retries": 0}
    if http_client is not None:
        kwargs["http_client"] = http_client
    return OpenAI(**kwargs)


def _run_live_gemini(runner: BenchmarkRunner):  # type: ignore[no-untyped-def]
    model_name = os.environ.get("CONTINUUM_GEMINI_MODEL", "gemini-3.5-flash")
    configuration = RunConfiguration(
        baseline=BaselineKind.FULL_PIPELINE,
        evidence_lane=EvidenceLane.LIVE_GEMINI,
        provider="GOOGLE",
        reasoner_model=model_name,
        critic_model=model_name,
        reasoner_prompt_version=REASONER_PROMPT_VERSION,
        critic_prompt_version=CRITIC_PROMPT_VERSION,
        temperature=0.0,
    )
    using_api_key = bool(
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    )
    using_vertex = (
        os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE"
        and bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))
        and bool(os.environ.get("GOOGLE_CLOUD_LOCATION"))
    )
    if not (using_api_key or using_vertex):
        return blocked_evidence_run(
            configuration,
            reason="Gemini API key or configured Vertex credentials are not configured",
        )
    transport = AdkGeminiTransport()
    subject = ModelCompilerSubject(
        reasoner=DependencyReasoner(
            transport,
            model_name=model_name,
            prompt_version=REASONER_PROMPT_VERSION,
        ),
        critic=ModelDependencyCritic(
            transport,
            model_name=model_name,
            prompt_version=CRITIC_PROMPT_VERSION,
        ),
        execution_namespace=f"benchmark-gemini-{uuid.uuid4().hex}",
    )
    try:
        return runner.run(subject, configuration)
    except ReasonerError as error:
        return _reasoner_error_evidence(configuration, error)


def _run_live_openai_critic_ablation(
    budget_path: Path,
    *,
    transport: StructuredModelTransport | None = None,
    cases: list[BenchmarkCase] | None = None,
    execution_namespace: str | None = None,
    record_observer: Callable[[PairedCaseEvidence], None] | None = None,
) -> PairedAblationRun:
    if not os.environ.get("OPENAI_API_KEY"):
        raise ReasonerError(
            "MODEL_CREDENTIALS_MISSING",
            "OPENAI_API_KEY is not configured",
        )
    pricing = openai_luna_pricing()
    model_name = os.environ.get("CONTINUUM_OPENAI_MODEL", pricing.model_name)
    if model_name != pricing.model_name:
        raise ReasonerError(
            "MODEL_PRICING_UNAUDITED",
            "configured OpenAI model has no audited pricing for the experiment cap",
        )
    selected_cases = cases or [
        case for case in load_corpus().cases if case.variance_subset
    ]
    if cases is None and len(selected_cases) != 30:
        raise ValueError("critic ablation requires the frozen 30-case variance subset")
    namespace = execution_namespace or f"critic-ablation-openai-{uuid.uuid4().hex}"
    ledger: SQLiteBudgetLedger | None = None
    active_transport = transport
    try:
        if active_transport is None:
            ledger = SQLiteBudgetLedger(budget_path, limit_usd=Decimal(10))
            scoped_budget = ScopedBudgetLedger(
                ledger,
                call_id_prefix=namespace + ":",
                limit_usd=Decimal("0.25"),
                max_calls=120,
            )
            active_transport = OpenAIResponsesTransport(
                client=_openai_client(),
                budget=scoped_budget,  # type: ignore[arg-type]
                pricing=pricing,
                max_input_tokens=250_000,
                max_output_tokens=8_192,
            )
        subject = PairedAblationSubject(
            reasoner=DependencyReasoner(
                active_transport,
                model_name=model_name,
                prompt_version=REASONER_PROMPT_VERSION,
            ),
            critic=ModelDependencyCritic(
                active_transport,
                model_name=model_name,
                prompt_version=CRITIC_PROMPT_VERSION,
            ),
            execution_namespace=namespace,
        )
        configuration = AblationRunConfiguration(
            provider="OPENAI",
            model=model_name,
            reasoner_prompt_version=REASONER_PROMPT_VERSION,
            critic_prompt_version=CRITIC_PROMPT_VERSION,
            temperature=None,
            reasoning_effort="low",
            service_tier="default",
            case_set=(
                "variance-subset-30"
                if cases is None
                else f"injected-{len(selected_cases)}-case"
            ),
            pricing_version=pricing.pricing_version,
            max_incremental_cost_usd="0.25",
            max_model_posts=120,
        )
        run = PairedAblationRunner(selected_cases).run(
            subject,
            configuration,
            record_observer=record_observer,
        )
        if ledger is None:
            return run
        prefix = namespace + ":"
        reasoner_duration_ms = sum(
            record.reasoner_duration_ms for record in run.records
        )
        critic_duration_ms = sum(record.critic_duration_ms for record in run.records)
        usage = AblationUsage(
            reasoner=_ablation_usage(
                ledger.settled_usage_by_stage(prefix, "reasoner"),
                duration_ms=reasoner_duration_ms,
            ),
            critic=_ablation_usage(
                ledger.settled_usage_by_stage(prefix, "critic"),
                duration_ms=critic_duration_ms,
            ),
            total=_ablation_usage(
                ledger.settled_usage(prefix),
                duration_ms=reasoner_duration_ms + critic_duration_ms,
            ),
        )
        return run.model_copy(update={"usage": usage})
    finally:
        if ledger is not None:
            ledger.close()


def _ablation_usage(
    summary: SettledUsageSummary,
    *,
    duration_ms: float,
) -> AblationStageUsage:
    return AblationStageUsage(
        settled_calls=summary.settled_calls,
        input_tokens=summary.usage.input_tokens,
        cached_input_tokens=summary.usage.cached_input_tokens,
        cache_write_tokens=summary.usage.cache_write_tokens,
        output_tokens=summary.usage.output_tokens,
        actual_cost_usd=str(summary.actual_cost_usd),
        duration_ms=duration_ms,
    )


_BLOCKED_REASONER_CODES = frozenset(
    {
        "MODEL_BUDGET_EXHAUSTED",
        "MODEL_BUDGET_CALL_IN_PROGRESS",
        "MODEL_BUDGET_CALL_OUTCOME_UNKNOWN",
        "MODEL_TRANSPORT_ERROR",
    }
)


def _reasoner_error_evidence(
    configuration: RunConfiguration,
    error: ReasonerError,
    *,
    usage: UsageSummary | None = None,
):  # type: ignore[no-untyped-def]
    reason = f"{error.code}: {error.message}"
    if error.code in _BLOCKED_REASONER_CODES:
        return blocked_evidence_run(configuration, reason=reason, usage=usage)
    return failed_evidence_run(configuration, reason=reason, usage=usage)


if __name__ == "__main__":
    raise SystemExit(main())
