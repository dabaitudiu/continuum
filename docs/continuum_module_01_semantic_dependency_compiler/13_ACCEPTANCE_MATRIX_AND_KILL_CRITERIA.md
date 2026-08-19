# 13 — Acceptance Matrix and Kill Criteria

## Rule

**All P0 rows must be PASS.** A coding agent may not rewrite P0 as “optional”, “post-gate”, “future production work”, or “outside the current product boundary”. Only the product owner can change scope.

## P0 acceptance matrix

Status vocabulary: `PASS` means the specified evidence exists; `PARTIAL` means implementation/reference evidence exists but the required live-model evidence does not; `BLOCKED` means the required authenticated lane could not run. A deterministic reference result is never promoted to live-model evidence.

| Capability | Acceptance evidence | Current status |
|---|---|---|
| Stable Artifact/Revision/Fragment identity | deterministic identity tests | PASS |
| World-snapshot temporal binding | stale-revision rejection tests | PASS |
| Typed Decision/Claim/Dependency IR | schema + fixture tests | PASS |
| Unknown ref rejection | validator tests | PASS |
| Cross-scope ref rejection | authorization tests | PASS |
| Relation/authority restrictions | policy-source tests | PASS |
| Deterministic canonicalization | repeated compile hash test | PASS |
| Live Gemini reasoner | authenticated integration evidence | **BLOCKED — no Gemini/Vertex credentials** |
| Critical omission critic | omission benchmark | PARTIAL — reference cases pass; live lane blocked |
| Material contradiction handling | contradiction benchmark | PARTIAL — reference cases pass; live lane blocked |
| 3-domain benchmark >=120 cases | committed benchmark corpus | PASS — 40 cases/domain |
| Critical dependency recall >=0.92 | benchmark report | PARTIAL — reference 1.00; no live score |
| Critical dependency precision >=0.82 | benchmark report | PARTIAL — reference 1.00; no live score |
| Unsupported canonical refs = 0% | benchmark + deterministic validator | PASS |
| Contradiction recall >=0.90 | benchmark report | PARTIAL — reference 1.00; no live score |
| Unnecessary invalidation <8% in mutation eval | compiler→drift integration eval | PARTIAL — reference 0%; no live score |
| Stale escape <2% in mutation eval | compiler→drift integration eval | PARTIAL — reference 0%; no live score |
| Runtime acceptance bound to mission/world revision | concurrency integration test | PASS |
| Audit links compilation→Decision | runtime integration test/UI read model | PASS |
| Prompt-injection adversarial set | >=10 live-model cases + findings | PARTIAL — corpus threshold passes; live findings blocked |

## Current decision

Phases B–G are implemented and locally productized, but **Module 01 is not P0-complete**. The stop condition remains active: do not begin a full Drift Engine implementation until authenticated live-model evidence resolves the `BLOCKED`/`PARTIAL` rows.

The current report is `docs/reports/module-01-dependency-compiler.md`. OpenAI is available as an additional provider-neutral evidence lane with a persisted cumulative hard cap of $10, but it does not replace the explicit live-Gemini P0 row.

## P1

- PDF parser against selected realistic public/sample documents.
- Source excerpt UI.
- Human-review console for compiler findings.
- Model Armor integration.
- Higher-reasoning critic model comparison.

## Kill / redesign criteria

### K1 — Critical recall cannot exceed 0.80

If after reasonable prompt/schema/critic iteration critical dependency recall remains below 0.80, the thesis that the model can reliably compile its dependencies is not ready. Redesign around stronger deterministic domain schemas or narrower mission classes.

### K2 — Broad refs are required for good recall

If the only way to reach recall is to cite whole documents, causing excessive invalidation, the granularity design has failed. Revisit fragment identity and claim decomposition.

### K3 — Critic adds little value

If two-pass critique does not materially improve recall or contradiction handling, remove it rather than preserving complexity.

### K4 — Benchmark only works on vendor onboarding

If release/access domains underperform dramatically, do not claim a generic enterprise runtime. Either fix generality or narrow the product thesis explicitly.

### K5 — Prompt injection can alter authority semantics

If untrusted document instructions can cause unauthorized authority edges or accepted unknown refs, block continuation to later modules.

### K6 — Compiler output is effectively manually authored

If real demos still require developers to predefine the exact dependency graph for each decision, the module has not solved the central problem.

## Scope-change protocol

Any proposed scope reduction must be written as:

```text
CHANGE REQUEST
- original P0 requirement
- reason it cannot be completed
- impact on competition thesis
- alternative
- explicit product-owner approval
```

No autonomous agent may approve its own scope reduction.

## Kill-criteria assessment as of 2026-08-19

- K1, K3, K4, and K5 cannot be adjudicated from deterministic fixtures; they require authenticated model runs.
- K2 is not observed in the reference lane: canonical dependencies remain fragment-level and reference mutation metrics pass, but this is not yet live evidence.
- K6 is **not cleared**: the four product reference cases are deliberately server-authored. The generic reasoner/compiler path exists, but without a passing live-model benchmark we cannot claim the central dependency graph is no longer effectively authored by developers.
- Therefore no kill decision is justified yet, and no continuation to the full Drift Engine is justified either. The next evidence action is a budget-gated OpenAI run if a key becomes available, followed by the required Gemini run when Google credentials exist.
