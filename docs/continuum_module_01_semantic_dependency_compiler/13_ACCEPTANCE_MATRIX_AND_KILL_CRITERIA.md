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
| Complete SourceSet/context coverage | versioned manifest + fail-closed retrieval/partition tests | **PARTIAL — Revision-2 contract written; v1 has no completeness manifest evidence** |
| Interpretation-policy validity provenance | policy/manifest revision mutation tests | **PARTIAL — Revision-2 contract written; not implemented/evaluated** |
| Stable semantic Requirement/proof identity | paired paraphrase edge-set tests | **PARTIAL — Revision-2 contract written; not implemented/evaluated** |
| Unsupported logic fails closed | OR/threshold/exception/quantified fixtures | **PARTIAL — Revision-2 contract written; not implemented/evaluated** |
| Live Gemini reasoner | authenticated integration evidence | **BLOCKED — no Gemini/Vertex credentials** |
| Critical requirement completeness | omission benchmark | **FAIL — the rejected v1 critic recovered 0 reasoner omissions, added 4 false-positive refs, and introduced 5 spurious blocks; Revision 2 is under review and not implemented/evaluated** |
| Independent requirement coverage | Stage-1 omission recovery vs false-block benchmark | **PARTIAL — Revision-2 independent obligation inventory specified; no implementation/model evidence** |
| Three-state evidence entailment | TRUE/FALSE/INDETERMINATE confusion matrix | **PARTIAL — Revision-2 contract written; no model evidence** |
| Deterministic proof-selected materiality | selected-proof mutation and label-adversary tests | **PARTIAL — Revision-2 contract written; v1 materiality remains model-controlled** |
| Material contradiction handling | contradiction benchmark | **FAIL — OpenAI detects 0/12 blocking contradictions** |
| 3-domain benchmark >=120 cases | committed benchmark corpus | PASS — 40 cases/domain |
| Critical dependency recall >=0.92 | benchmark report | **FAIL — proposal union is 0.9821, but accepted canonical coverage is only 34/168 = 0.2024** |
| Critical dependency precision >=0.82 | benchmark report | **FAIL — proposal union is 0.6548; accepted canonical precision is 34/45 = 0.7556** |
| Unsupported canonical refs = 0% | benchmark + deterministic validator | PASS — OpenAI 0% |
| Contradiction recall >=0.90 | benchmark report | **FAIL — OpenAI 0%** |
| Critical contradiction severity recall >=0.90 | benchmark report | **FAIL — OpenAI 0%** |
| Complete contradiction inventory coverage | partition receipts + cross-partition benchmark | **PARTIAL — Revision-2 map/reduce contract written; no implementation evidence** |
| Outcome constraints = 100% | benchmark report | **FAIL — OpenAI 42.50%** |
| Must-block disposition compliance = 100% | benchmark report | **FAIL — OpenAI 26.67%** |
| Unnecessary invalidation <8% in mutation eval | compiler→drift integration eval | PARTIAL — accepted-only result is 0/6, but none of the 51 supporting refs promoted to CRITICAL was a mutation target |
| Stale escape <2% in mutation eval | compiler→drift integration eval | PARTIAL — accepted-only result is 0/14; the historical 80.56% counted 58 NOT_ACCEPTED cases as Runtime escapes, while acceptance coverage is only 20/120 |
| Runtime acceptance bound to mission/world revision | concurrency integration test | PASS |
| Audit links compilation→Decision | runtime integration test/UI read model | PASS |
| Prompt-injection end-to-end semantic invariance | >=10 paired clean/injected live cases + mutation evidence | **PARTIAL — legacy 12-case evidence only shows no injected ref became critical/canonical; it does not measure requirement/contradiction suppression, outcome flips, or mutation delta** |
| Blind generalization holdout | independently owned, one-time post-freeze run | **BLOCKED — no externally held blind set/evaluator evidence yet; development must not inspect bodies** |

## Current decision

Phases B–G are implemented and locally productized, but **Module 01 is not P0-complete**. The authenticated OpenAI run is a quality-gate `FAIL`, not a credential gap. The stop condition remains active: do not begin a full Drift Engine implementation while any P0 row is `FAIL` or `BLOCKED`.

The historical full report is `docs/reports/module-01-dependency-compiler.md`; its evaluator defects and corrected interpretation are preserved in `docs/reports/module-01-failure-analysis-v1.md`. The completed paired K3 evidence is `docs/reports/module-01-critic-ablation.md`. On 2026-08-19 the product owner selected Option B's direction, rejected the vague critic, and rejected the first concrete Option B specification. `15_REPLACEMENT_ARCHITECTURE.md` Revision 2 addresses the 11 P0 blockers but is awaiting review and has no implementation/model evidence. OpenAI remains a provider-neutral falsification lane with a cumulative $10 cap; it does not waive live Gemini.

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

If untrusted document instructions can suppress Requirements/contradictions、change selected critical coverage、flip outcome/disposition、worsen mutation quality、or create unauthorized authority/refs, block continuation to later modules.

### K6 — Compiler output is effectively manually authored

If real demos still require developers to predefine the exact dependency graph for each decision, the module has not solved the central problem. Versioned predicate catalogs、decision-class contracts and normalized governing rules may define reusable semantics and supported logic, but must not encode case-specific expected Requirements、source refs、proof paths or outcomes.

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
- **K3 is triggered for the current critic:** paired Experiment 1 used the same 30 live reasoner drafts in both arms. The critic recovered 0 required omissions, detected 0 contradictions, added 4 false-positive refs, introduced 5 spurious blocks, reduced acceptance from 8/30 to 3/30, and worsened accepted canonical recall from 28.57% to 11.90%. The product owner has now selected replacement Option B. The old critic is frozen as an ablation/replay baseline only and must not remain as production fallback.
- **K4 is not triggered:** dependency recall is not confined to vendor onboarding; access scores 1.00, release scores 0.9821, and vendor onboarding scores 0.9643.
- **K5 is unresolved under the expanded criterion:** 12 legacy cases show no injected ref became predicted critical/canonical, but there is no paired clean/injected evidence for requirement/contradiction suppression、outcome/disposition flips or mutation-quality delta. The old evidence is insufficient to clear K5 and does not prove K5 triggered.
- Accepted mutation records enter the real Runtime, apply the corpus replacement mutation, and read the resulting `DecisionStatus`; they do not infer staleness from ref membership. The historical 0.8056 metric is retained but is not a Runtime escape rate because 58/72 expected-stale compilations never entered Runtime. Corrected accepted-only mutation evidence is 0/14 stale escapes and 0/6 unnecessary invalidations, with inadequate acceptance and supporting-ref mutation coverage.
- **K6 is not cleared:** the live benchmark proves the model—not a developer-authored exact graph—selects dependencies, but only 20/120 primary compilations are accepted and the four product reference cases remain server-authored. Revision-2 predicate/decision contracts must also be audited to prove they contain reusable vocabulary/logic only, not hidden case-specific graphs or expected answers.
- **Whole-project kill is not yet justified by K1、K2 or K4; K3 kills the current critic, K5 is unresolved, and K6 remains uncleared.** Do not start Module 02、production v2 work or a full paid benchmark. The next step is product-owner review of Revision 2. The development agent must not create/read the blind holdout; after design approval, a separate implementation plan is still required.
