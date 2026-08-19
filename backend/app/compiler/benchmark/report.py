from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.compiler.benchmark.runner import BenchmarkRun


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "continuum-dependency-report-v1"
    generated_at: datetime
    runs: list[BenchmarkRun]


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


__all__ = ["BenchmarkReport", "write_report_bundle"]
