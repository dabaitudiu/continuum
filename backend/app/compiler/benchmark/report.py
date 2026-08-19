from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.compiler.benchmark.model_subject import (
    PairedAblationRun,
    PairedCaseEvidence,
)
from app.compiler.benchmark.runner import BenchmarkRun


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "continuum-dependency-report-v1"
    generated_at: datetime
    runs: list[BenchmarkRun]


class CriticAblationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "continuum-critic-ablation-report-v1"
    generated_at: datetime
    experiment_status: str = "COMPLETE"
    k3_decision: str
    decision_reasons: list[str]
    run: PairedAblationRun


def write_report_bundle(
    runs: list[BenchmarkRun],
    *,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = BenchmarkReport(generated_at=datetime.now(UTC), runs=runs)
    json_path = output_dir / "module-01-dependency-compiler.json"
    markdown_path = output_dir / "module-01-dependency-compiler.md"
    json_path.write_text(
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def write_critic_ablation_report(
    run: PairedAblationRun,
    *,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    decision, reasons = _critic_decision(run)
    report = CriticAblationReport(
        generated_at=datetime.now(UTC),
        k3_decision=decision,
        decision_reasons=reasons,
        run=run,
    )
    json_path = output_dir / "module-01-critic-ablation.json"
    markdown_path = output_dir / "module-01-critic-ablation.md"
    json_path.write_text(
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        _critic_ablation_markdown(report),
        encoding="utf-8",
    )
    return json_path, markdown_path


def append_critic_ablation_evidence(
    record: PairedCaseEvidence,
    *,
    output_path: Path,
) -> None:
    """Durably append one completed pair without rewriting earlier evidence."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        record.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    with output_path.open("a", encoding="utf-8") as stream:
        stream.write(encoded + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _markdown(report: BenchmarkReport) -> str:
    lines = [
        "# Module 01 — Semantic Dependency Compiler Benchmark",
        "",
        f"Generated: `{report.generated_at.isoformat()}`",
        "",
        (
            "> `deterministic_reference` validates corpus/metric/runner plumbing only. "
            "It is not live-model acceptance evidence."
        ),
        "",
        "| Evidence lane | Baseline | Status | Recall | Precision | Contradiction | Critical severity | Outcome | Block gate | Stale escape | Unnecessary | Determinism | Cost USD |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    blocked_reasons: list[str] = []
    for run in report.runs:
        metrics = run.metrics
        values = (
            ("—",) * 10
            if metrics is None
            else (
                _pct(metrics.critical_recall),
                _pct(metrics.critical_precision),
                _pct(metrics.contradiction_recall),
                _pct(metrics.contradiction_severity_recall),
                _pct(metrics.outcome_compliance),
                _pct(metrics.blocking_disposition_compliance),
                _pct(metrics.stale_escape_rate),
                _pct(metrics.unnecessary_invalidation_rate),
                _pct(metrics.compilation_determinism),
                run.usage.actual_cost_usd,
            )
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    run.configuration.evidence_lane.value,
                    run.configuration.baseline.value,
                    run.status.value,
                    *values,
                )
            )
            + " |"
        )
        if run.blocked_reason:
            blocked_reasons.append(
                f"- `{run.configuration.evidence_lane.value}`: {run.blocked_reason}"
            )
    if blocked_reasons:
        lines.extend(("", "## Blocked evidence", "", *blocked_reasons))
    failure_reasons = [
        f"- `{run.configuration.evidence_lane.value}`: {run.failure_reason}"
        for run in report.runs
        if run.failure_reason
    ]
    if failure_reasons:
        lines.extend(("", "## Failed evidence", "", *failure_reasons))
    lines.extend(
        (
            "",
            "## Acceptance interpretation",
            "",
            (
                "Metric PASS in a deterministic reference lane does not turn a live lane "
                "green. Authenticated gate failures remain FAIL; missing credentials remain "
                "BLOCKED, not SKIPPED-as-PASS."
            ),
            "",
            (
                "The locally delivered Compiler Lab and runtime-acceptance evidence are "
                "documented in `docs/reports/compiler-lab-product-report.md`. They prove the "
                "deterministic product boundary, not live-model dependency quality."
            ),
            "",
        )
    )
    return "\n".join(lines)


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _critic_decision(run: PairedAblationRun) -> tuple[str, list[str]]:
    effect = run.critic_effect
    has_signal = bool(
        effect.required_omissions_recovered or effect.correct_contradictions_added
    )
    has_runtime_effect = bool(
        effect.true_omission_blocks or effect.correct_contradiction_blocks
    )
    has_adverse_signal = bool(
        effect.false_positive_refs_added
        or effect.incorrect_contradictions_added
        or effect.spurious_blocks_added
        or effect.unsafe_accepted_cases
    )
    reasons = [
        (f"required omissions recovered: {effect.required_omissions_recovered}"),
        f"false-positive refs added: {effect.false_positive_refs_added}",
        f"correct contradictions added: {effect.correct_contradictions_added}",
        (
            "correct safety-direction blocks: "
            f"{effect.true_omission_blocks + effect.correct_contradiction_blocks}"
        ),
        f"spurious blocks added: {effect.spurious_blocks_added}",
        f"unsafe accepted cases: {effect.unsafe_accepted_cases}",
    ]
    if not has_signal or not has_runtime_effect:
        return "REMOVE_OR_REDESIGN", reasons
    if has_adverse_signal:
        return "INCONCLUSIVE_MIXED_SIGNAL", reasons
    return "RETAIN_SIGNAL", reasons


def _critic_ablation_markdown(report: CriticAblationReport) -> str:
    run = report.run
    reasoner = run.reasoner_only.corrected
    critic = run.critic_on.corrected
    metrics = (
        (
            "Proposal critical recall",
            reasoner.proposal_critical_recall,
            critic.proposal_critical_recall,
        ),
        (
            "Proposal critical precision",
            reasoner.proposal_critical_precision,
            critic.proposal_critical_precision,
        ),
        (
            "Canonical critical recall",
            reasoner.canonical_critical_recall,
            critic.canonical_critical_recall,
        ),
        (
            "Canonical critical precision",
            reasoner.canonical_critical_precision,
            critic.canonical_critical_precision,
        ),
        (
            "Contradiction recall",
            reasoner.contradiction_recall,
            critic.contradiction_recall,
        ),
        (
            "Critical contradiction severity",
            reasoner.contradiction_severity_recall,
            critic.contradiction_severity_recall,
        ),
        ("Outcome compliance", reasoner.outcome_compliance, critic.outcome_compliance),
        (
            "Must-block compliance",
            reasoner.blocking_disposition_compliance,
            critic.blocking_disposition_compliance,
        ),
        (
            "Acceptance coverage",
            reasoner.acceptance_coverage,
            critic.acceptance_coverage,
        ),
        (
            "Legacy stale escape",
            reasoner.legacy_stale_escape_rate,
            critic.legacy_stale_escape_rate,
        ),
        (
            "Accepted-only stale escape",
            reasoner.accepted_stale_escape_rate,
            critic.accepted_stale_escape_rate,
        ),
        (
            "Legacy unnecessary invalidation",
            reasoner.legacy_unnecessary_invalidation_rate,
            critic.legacy_unnecessary_invalidation_rate,
        ),
        (
            "Accepted-only unnecessary invalidation",
            reasoner.accepted_unnecessary_invalidation_rate,
            critic.accepted_unnecessary_invalidation_rate,
        ),
        (
            "Compilation determinism",
            reasoner.compilation_determinism,
            critic.compilation_determinism,
        ),
    )
    lines = [
        "# Module 01 — Current Critic Ablation",
        "",
        f"Generated: `{report.generated_at.isoformat()}`",
        "",
        f"**Experiment status:** {report.experiment_status}",
        "",
        f"**K3 decision:** **{report.k3_decision}**",
        "",
        "## Locked configuration",
        "",
        f"- Run ID: `{run.run_id}`",
        f"- Cases: `{len(run.records)}` from `{run.configuration.case_set}`",
        f"- Provider/model: `{run.configuration.provider}` / `{run.configuration.model}`",
        (
            f"- Prompts: `{run.configuration.reasoner_prompt_version}` / "
            f"`{run.configuration.critic_prompt_version}`"
        ),
        f"- Temperature: `{run.configuration.temperature}`",
        f"- Reasoning/service tier: `{run.configuration.reasoning_effort}` / `{run.configuration.service_tier}`",
        f"- Metric version: `{run.configuration.metric_version}`",
        *(
            [f"- Recomputed from run: `{run.configuration.recomputed_from_run_id}`"]
            if run.configuration.recomputed_from_run_id
            else []
        ),
        *(
            [
                (
                    "- Immutable evidence SHA-256: "
                    f"`{run.configuration.evidence_source_sha256}`"
                )
            ]
            if run.configuration.evidence_source_sha256
            else []
        ),
        "",
        "Both arms consume the same persisted reasoner draft per case. The only arm difference is critic off/on.",
        *(
            [
                "",
                (
                    "**Evaluator correction:** derived critic-added refs and metrics "
                    "were recomputed from the immutable raw draft/review evidence; "
                    "the model responses and usage were not changed."
                ),
            ]
            if run.configuration.recomputed_from_run_id
            else []
        ),
        "",
        "## Metrics",
        "",
        "| Metric | Reasoner-only | Current critic | Delta |",
        "|---|---:|---:|---:|",
    ]
    for name, left, right in metrics:
        lines.append(
            f"| {name} | {_pct(left)} | {_pct(right)} | {(right - left) * 100:+.2f} pp |"
        )
    lines.extend(
        (
            "",
            "| Count | Reasoner-only | Current critic | Delta |",
            "|---|---:|---:|---:|",
            (
                f"| Accepted cases | {reasoner.counts.accepted_cases} | "
                f"{critic.counts.accepted_cases} | "
                f"{run.critic_effect.accepted_case_delta:+d} |"
            ),
            "",
            "## Mutation denominator disclosure",
            "",
            "| Coverage count | Reasoner-only | Current critic |",
            "|---|---:|---:|",
            (
                "| Accepted material mutations tested | "
                f"{reasoner.counts.accepted_expected_stale} | "
                f"{critic.counts.accepted_expected_stale} |"
            ),
            (
                "| Accepted unrelated mutations tested | "
                f"{reasoner.counts.accepted_expected_unchanged} | "
                f"{critic.counts.accepted_expected_unchanged} |"
            ),
            (
                "| Material mutations excluded because compilation was not accepted | "
                f"{reasoner.counts.not_accepted_expected_stale} | "
                f"{critic.counts.not_accepted_expected_stale} |"
            ),
            "",
            (
                "A 0% accepted-only stale escape rate is safety evidence only for "
                "the accepted material-mutation denominator above; it does not "
                "convert NOT_ACCEPTED cases into Runtime successes."
            ),
            "",
            "## Required K3 questions",
            "",
            (
                "1. **How many required omissions were recovered?** "
                f"{run.critic_effect.required_omissions_recovered}."
            ),
            (
                "2. **How many false-positive refs were added?** "
                f"{run.critic_effect.false_positive_refs_added}."
            ),
            (
                "3. **Did the critic identify contradictions?** "
                f"Correct additions: {run.critic_effect.correct_contradictions_added}; "
                f"incorrect additions: {run.critic_effect.incorrect_contradictions_added}."
            ),
            (
                "4. **Did it improve Runtime stale behavior?** "
                f"Accepted-only stale escape moved from "
                f"{_pct(reasoner.accepted_stale_escape_rate)} to "
                f"{_pct(critic.accepted_stale_escape_rate)}; acceptance coverage moved "
                f"from {_pct(reasoner.acceptance_coverage)} to "
                f"{_pct(critic.acceptance_coverage)}."
            ),
            (
                "5. **Is the second model call worth it?** "
                f"Decision: {report.k3_decision}. Critic calls/cost: "
                f"{run.usage.critic.settled_calls} / "
                f"${run.usage.critic.actual_cost_usd}."
            ),
            "",
            "## Critic effect",
            "",
            f"- required omissions recovered: {run.critic_effect.required_omissions_recovered}",
            f"- true omission blocks: {run.critic_effect.true_omission_blocks}",
            f"- correct contradiction blocks: {run.critic_effect.correct_contradiction_blocks}",
            f"- spurious blocks added: {run.critic_effect.spurious_blocks_added}",
            f"- unsafe accepted cases: {run.critic_effect.unsafe_accepted_cases}",
            "",
            "## Usage",
            "",
            "| Stage | Calls | Input | Cached read | Cache write | Output | Latency ms | Cost USD |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        )
    )
    for name, usage in (
        ("Reasoner", run.usage.reasoner),
        ("Critic", run.usage.critic),
        ("Total", run.usage.total),
    ):
        lines.append(
            "| "
            + " | ".join(
                (
                    name,
                    str(usage.settled_calls),
                    str(usage.input_tokens),
                    str(usage.cached_input_tokens),
                    str(usage.cache_write_tokens),
                    str(usage.output_tokens),
                    f"{usage.duration_ms:.2f}",
                    usage.actual_cost_usd,
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "## Decision reasons",
            "",
            *(f"- {reason}" for reason in report.decision_reasons),
            "",
            (
                "This is an ablation decision, not Module 01 acceptance. Live Gemini "
                "and every P0 row remain independently required."
            ),
            "",
        )
    )
    return "\n".join(lines)


__all__ = [
    "BenchmarkReport",
    "CriticAblationReport",
    "append_critic_ablation_evidence",
    "write_critic_ablation_report",
    "write_report_bundle",
]
