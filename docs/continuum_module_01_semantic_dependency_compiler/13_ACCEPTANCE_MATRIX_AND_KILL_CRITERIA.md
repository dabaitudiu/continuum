# 13 — Acceptance Matrix and Kill Criteria

## Rule

**All P0 rows must be PASS.** A coding agent may not rewrite P0 as “optional”, “post-gate”, “future production work”, or “outside the current product boundary”. Only the product owner can change scope.

## P0 acceptance matrix

| Capability | Acceptance evidence | Status initially |
|---|---|---|
| Stable Artifact/Revision/Fragment identity | deterministic identity tests | TODO |
| World-snapshot temporal binding | stale-revision rejection tests | TODO |
| Typed Decision/Claim/Dependency IR | schema + fixture tests | TODO |
| Unknown ref rejection | validator tests | TODO |
| Cross-scope ref rejection | authorization tests | TODO |
| Relation/authority restrictions | policy-source tests | TODO |
| Deterministic canonicalization | repeated compile hash test | TODO |
| Live Gemini reasoner | authenticated integration evidence | TODO |
| Critical omission critic | omission benchmark | TODO |
| Material contradiction handling | contradiction benchmark | TODO |
| 3-domain benchmark >=120 cases | committed benchmark corpus | TODO |
| Critical dependency recall >=0.92 | benchmark report | TODO |
| Critical dependency precision >=0.82 | benchmark report | TODO |
| Unsupported canonical refs = 0% | benchmark + deterministic validator | TODO |
| Contradiction recall >=0.90 | benchmark report | TODO |
| Unnecessary invalidation <8% in mutation eval | compiler→drift integration eval | TODO |
| Stale escape <2% in mutation eval | compiler→drift integration eval | TODO |
| Runtime acceptance bound to mission/world revision | concurrency integration test | TODO |
| Audit links compilation→Decision | runtime integration test/UI read model | TODO |
| Prompt-injection adversarial set | >=10 live-model cases + findings | TODO |

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
