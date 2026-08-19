# 13 — Acceptance Matrix and Kill Criteria

## Rule

**All P0 rows must be PASS.** A coding agent may not rewrite P0 as “optional”, “post-gate”, “future production work”, or “outside the current product boundary”. Only the product owner can change scope.

## P0 acceptance matrix

Status vocabulary: `PASS` means the specified evidence exists and meets its target; `FAIL` means an authenticated lane ran and missed the target; `PARTIAL` means evidence is mixed or incomplete; `BLOCKED` means the required authenticated lane could not run. A deterministic reference result is never promoted to live-model evidence.

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
| Critical omission critic | omission benchmark | PARTIAL — OpenAI recovers 24/24 required omission refs, but only 4/12 omission cases compile as accepted and critic contribution is not isolated |
| Material contradiction handling | contradiction benchmark | **FAIL — OpenAI detects 0/12 blocking contradictions** |
| 3-domain benchmark >=120 cases | committed benchmark corpus | PASS — 40 cases/domain |
| Critical dependency recall >=0.92 | benchmark report | PASS — OpenAI 0.9821; every domain >=0.9643 |
| Critical dependency precision >=0.82 | benchmark report | **FAIL — OpenAI 0.6548** |
| Unsupported canonical refs = 0% | benchmark + deterministic validator | PASS — OpenAI 0% |
| Contradiction recall >=0.90 | benchmark report | **FAIL — OpenAI 0%** |
| Critical contradiction severity recall >=0.90 | benchmark report | **FAIL — OpenAI 0%** |
| Outcome constraints = 100% | benchmark report | **FAIL — OpenAI 42.50%** |
| Must-block disposition compliance = 100% | benchmark report | **FAIL — OpenAI 26.67%** |
| Unnecessary invalidation <8% in mutation eval | compiler→drift integration eval | PASS — OpenAI 0% |
| Stale escape <2% in mutation eval | compiler→drift integration eval | **FAIL — OpenAI 80.56%** |
| Runtime acceptance bound to mission/world revision | concurrency integration test | PASS |
| Audit links compilation→Decision | runtime integration test/UI read model | PASS |
| Prompt-injection adversarial set | >=10 live-model cases + findings | PASS — 12 OpenAI cases; no injected ref became critical or canonical |

## Current decision

Phases B–G are implemented and locally productized, but **Module 01 is not P0-complete**. The authenticated OpenAI run is a quality-gate `FAIL`, not a credential gap. The stop condition remains active: do not begin a full Drift Engine implementation while any P0 row is `FAIL` or `BLOCKED`.

The current report is `docs/reports/module-01-dependency-compiler.md`. OpenAI remains an additional provider-neutral falsification lane with a persisted cumulative hard cap of $10; its failure does not replace or waive the explicit live-Gemini P0 row.

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

- **K1 is not triggered:** OpenAI critical recall is 0.9821 overall, every domain is at least 0.9643, and all three variance runs score 1.00.
- **K2 is not triggered:** live proposals use exact fragment refs rather than whole-document refs. The 0.6548 precision failure is over-selection of known fragments, which is a redesign target but not evidence that broad refs are required.
- **K3 is unresolved and now the primary ablation:** the full pipeline detects 0/12 material contradictions. The report does not yet contain a live reasoner-only comparison, so it cannot show whether the critic adds value. If a bounded live ablation shows no material recall or contradiction gain, remove or redesign the critic as K3 requires.
- **K4 is not triggered:** dependency recall is not confined to vendor onboarding; access scores 1.00, release scores 0.9821, and vendor onboarding scores 0.9643.
- **K5 is not triggered in this run:** across 12 prompt-injection cases, no injected ref became a predicted critical ref or an accepted canonical ref.
- Reference mutation metrics accept predicted graphs into the real Runtime, apply the corpus replacement mutation, and read the resulting `DecisionStatus`; they do not infer staleness from ref membership. The 0.8056 stale-escape result therefore blocks progression.
- **K6 is not cleared:** the live benchmark proves the model—not a developer-authored exact graph—selects dependencies, but only 20/120 primary compilations are accepted and the four product reference cases remain server-authored. The central dependency compiler is not yet useful enough to replace authored demo graphs.
- **Whole-project kill is not yet justified by the named K1–K6 conditions, but the current compiler configuration is killed for progression.** Do not start Module 02. The next bounded evidence step is one critic/reasoner redesign plus a live single-pass ablation; if K3 then triggers or the failed P0 rows remain materially unchanged after that bounded iteration, remove the critic or narrow/redesign the module before spending on Gemini acceptance.
