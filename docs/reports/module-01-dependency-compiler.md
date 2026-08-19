# Module 01 — Semantic Dependency Compiler Benchmark

Generated: `2026-08-19T09:24:14.037798+00:00`

> `deterministic_reference` validates corpus/metric/runner plumbing only. It is not live-model acceptance evidence.

| Evidence lane | Baseline | Status | Recall | Precision | Contradiction | Critical severity | Outcome | Block gate | Stale escape | Unnecessary | Determinism | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deterministic_reference | document-level | FAIL | 100.00% | 43.75% | 0.00% | 0.00% | 90.00% | 90.00% | 0.00% | 100.00% | 100.00% | 0 |
| deterministic_reference | single-pass | FAIL | 78.57% | 73.33% | 0.00% | 0.00% | 90.00% | 90.00% | 16.67% | 75.00% | 100.00% | 0 |
| deterministic_reference | full-pipeline | PASS | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0.00% | 0.00% | 100.00% | 0 |
| live_openai | full-pipeline | FAIL | 98.21% | 65.48% | 0.00% | 0.00% | 42.50% | 26.67% | 80.56% | 0.00% | 100.00% | 0.419523600 |
| live_gemini | full-pipeline | BLOCKED | — | — | — | — | — | — | — | — | — | — |

## Blocked evidence

- `live_gemini`: Gemini API key or configured Vertex credentials are not configured

## Acceptance interpretation

Metric PASS in a deterministic reference lane does not turn a live lane green. Authenticated gate failures remain FAIL; missing credentials remain BLOCKED, not SKIPPED-as-PASS.

The locally delivered Compiler Lab and runtime-acceptance evidence are documented in `docs/reports/compiler-lab-product-report.md`. They prove the deterministic product boundary, not live-model dependency quality.
