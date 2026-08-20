# Module 01 — Current Critic Ablation

> **SUPERSEDED EVALUATOR OUTPUT — PRESERVED, NOT ACCEPTANCE EVIDENCE.**
> `ablation-metrics-v2` excluded critic-proposed unknown refs from its
> false-positive count. The immutable live responses and costs remain valid;
> `module-01-critic-ablation.md` recomputes derived metrics with v3.

Generated: `2026-08-19T10:58:49.429149+00:00`

**Experiment status:** COMPLETE

**K3 decision:** **REMOVE_OR_REDESIGN**

## Locked configuration

- Run ID: `critic-ablation:5a46d0ad415c344b`
- Cases: `30` from `variance-subset-30`
- Provider/model: `OPENAI` / `gpt-5.6-luna`
- Prompts: `reasoner-v2` / `critic-v1`
- Temperature: `None`
- Reasoning/service tier: `low` / `default`
- Metric version: `ablation-metrics-v2`

Both arms consume the same persisted reasoner draft per case. The only arm difference is critic off/on.

## Metrics

| Metric | Reasoner-only | Current critic | Delta |
|---|---:|---:|---:|
| Proposal critical recall | 100.00% | 100.00% | +0.00 pp |
| Proposal critical precision | 71.19% | 71.19% | +0.00 pp |
| Canonical critical recall | 28.57% | 11.90% | -16.67 pp |
| Canonical critical precision | 66.67% | 71.43% | +4.76 pp |
| Contradiction recall | 0.00% | 0.00% | +0.00 pp |
| Critical contradiction severity | 0.00% | 0.00% | +0.00 pp |
| Outcome compliance | 40.00% | 40.00% | +0.00 pp |
| Must-block compliance | 36.67% | 20.00% | -16.67 pp |
| Acceptance coverage | 26.67% | 10.00% | -16.67 pp |
| Legacy stale escape | 88.89% | 94.44% | +5.56 pp |
| Accepted-only stale escape | 0.00% | 0.00% | +0.00 pp |
| Legacy unnecessary invalidation | 0.00% | 0.00% | +0.00 pp |
| Accepted-only unnecessary invalidation | 0.00% | 0.00% | +0.00 pp |
| Compilation determinism | 100.00% | 100.00% | +0.00 pp |

| Count | Reasoner-only | Current critic | Delta |
|---|---:|---:|---:|
| Accepted cases | 8 | 3 | -5 |

## Required K3 questions

1. **How many required omissions were recovered?** 0.
2. **How many false-positive refs were added?** 0.
3. **Did the critic identify contradictions?** Correct additions: 0; incorrect additions: 0.
4. **Did it improve Runtime stale behavior?** Accepted-only stale escape moved from 0.00% to 0.00%; acceptance coverage moved from 26.67% to 10.00%.
5. **Is the second model call worth it?** Decision: REMOVE_OR_REDESIGN. Critic calls/cost: 8 / $0.008218800.

## Critic effect

- required omissions recovered: 0
- true omission blocks: 0
- correct contradiction blocks: 0
- spurious blocks added: 5
- unsafe accepted cases: 0

## Usage

| Stage | Calls | Input | Cached read | Cache write | Output | Latency ms | Cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Reasoner | 30 | 46240 | 0 | 46150 | 38294 | 333994.40 | 0.057508300 |
| Critic | 8 | 22176 | 0 | 22152 | 2230 | 36191.45 | 0.008218800 |
| Total | 38 | 68416 | 0 | 68302 | 40524 | 370185.84 | 0.065727100 |

## Decision reasons

- required omissions recovered: 0
- false-positive refs added: 0
- correct contradictions added: 0
- correct safety-direction blocks: 0
- spurious blocks added: 5
- unsafe accepted cases: 0

This is an ablation decision, not Module 01 acceptance. Live Gemini and every P0 row remain independently required.
