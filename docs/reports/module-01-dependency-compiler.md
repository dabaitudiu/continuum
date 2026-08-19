# Module 01 — Semantic Dependency Compiler Benchmark

Generated: `2026-08-19T04:14:42.429976+00:00`

> `deterministic_reference` validates corpus/metric/runner plumbing only. It is not live-model acceptance evidence.

| Evidence lane | Baseline | Status | Recall | Precision | Contradiction | Stale escape | Unnecessary | Determinism | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| deterministic_reference | document-level | FAIL | 100.00% | 43.75% | 0.00% | 0.00% | 100.00% | 100.00% | 0 |
| deterministic_reference | single-pass | FAIL | 78.57% | 73.33% | 0.00% | 14.29% | 66.67% | 100.00% | 0 |
| deterministic_reference | full-pipeline | PASS | 100.00% | 100.00% | 100.00% | 0.00% | 0.00% | 100.00% | 0 |
| live_openai | full-pipeline | BLOCKED | — | — | — | — | — | — | — |
| live_gemini | full-pipeline | BLOCKED | — | — | — | — | — | — | — |

## Blocked evidence

- `live_openai`: OPENAI_API_KEY is not configured
- `live_gemini`: Gemini API key or configured Vertex credentials are not configured

## Acceptance interpretation

Metric PASS in a deterministic reference lane does not turn the Live OpenAI or Live Gemini rows green. Missing credentials remain BLOCKED, not SKIPPED-as-PASS.
