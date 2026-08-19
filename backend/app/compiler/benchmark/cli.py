from __future__ import annotations

import argparse
import os
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.compiler.benchmark.corpus import load_corpus
from app.compiler.benchmark.model_subject import ModelCompilerSubject
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
    failed_evidence_run,
)
from app.compiler.budget import SQLiteBudgetLedger
from app.compiler.prompts import CRITIC_PROMPT_VERSION, REASONER_PROMPT_VERSION
from app.compiler.reasoner import (
    AdkGeminiTransport,
    DependencyReasoner,
    OpenAIResponsesTransport,
    ReasonerError,
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
    args = parser.parse_args(argv)

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
