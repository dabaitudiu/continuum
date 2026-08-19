# Module 01 failure analysis v1

**Date:** 2026-08-19

**Status:** **REDESIGN REQUIRED**

**Scope:** Experiment 0 only — persisted-evidence reproduction and failure taxonomy

**Model calls in this analysis:** 0

## Executive conclusion

The committed OpenAI run is reproducible, but its headline metrics mix three different objects:

1. a reasoner/critic **proposal union**;
2. the much smaller set of **accepted canonical edges**;
3. a Runtime mutation evaluator that maps every blocked compilation to `predicted_stale=false`.

This explains the apparently paradoxical `98.21%` recall and `80.56%` stale escape without exonerating the compiler. The compiler still accepts only `20/120` cases, detects `0/12` contradictions, over-promotes supporting evidence, and fails the P0 quality gate. However, the `80.56%` number is not evidence that 58 accepted Runtime decisions remained `VALID`: all 58 were blocked before Runtime and no decision or mutation event existed. Every accepted case was directionally correct under mutation (`20/20`; `14/14` material mutations became `STALE`, `6/6` unrelated mutations stayed non-stale).

Two benchmark/evaluator defects must be fixed without overwriting the historical report:

- documented “accepted critical precision” is implemented over `predicted_critical_refs`, which is `reasoner critical refs ∪ critic recovered refs` and includes invalid refs;
- blocked compilations are counted as stale escapes even though Runtime contains no decision to escape.

A third benchmark coverage flaw makes the `0%` unnecessary-invalidation result weak evidence: none of the 51 supporting refs promoted to CRITICAL is selected as the unrelated mutation target.

These findings require evaluator/evidence-schema repair before any paid ablation. They do not justify changing a P0 threshold, deleting cases, starting Module 02, or declaring Module 01 done.

## Evidence freeze and reproduction

Inputs:

- report JSON SHA-256: `d9926ea8f43e742e73cc87d8832ad3c14954d9df062f702fc9ef3d5ac7ac9e20`;
- report Markdown SHA-256: `ea11b05fb7e8e93c610b035e91814ba70981c299beeeb7c1d01513454166464f`;
- ordered 120-case file-hash manifest digest: `981b8366a6b7183f9623e943de9b4bb33a1852ae521fa61eaa19c7d142ed09f7`;
- live run: `benchmark:d2e4e30e3fc04abe`;
- provider/model: OpenAI / `gpt-5.6-luna`;
- prompts: `reasoner-v2` / `critic-v1`;
- temperature: `null` because the Responses request did not send temperature;
- pricing: `openai-2026-08-19-v2`;
- recorded cost: `$0.419523600`, 272 settled calls.

Offline reproduction loaded the committed JSON through `BenchmarkReport`, recomputed every run with `measure(records)`, and recomputed every gate with `evaluate_gate(metrics)`. All five persisted runs matched exactly; no model transport was constructed.

```text
deterministic_reference / document-level / 120 records: metrics match, gate match
deterministic_reference / single-pass    / 120 records: metrics match, gate match
deterministic_reference / full-pipeline  / 120 records: metrics match, gate match
live_openai            / full-pipeline   / 120 records: metrics match, gate match
live_gemini            / full-pipeline   /   0 records: BLOCKED as persisted
```

The committed OpenAI metrics remain historical evidence and are not rewritten:

| Metric | Persisted result | P0 target | Result |
|---|---:|---:|---:|
| proposal-union critical recall | 165/168 = 98.21% | >=92% | PASS |
| proposal-union critical precision | 165/252 = 65.48% | >=82% | FAIL |
| contradiction recall | 0/12 | >=90% | FAIL |
| critical contradiction severity | 0/12 | >=90% | FAIL |
| outcome compliance | 51/120 = 42.50% | 100% | FAIL |
| must-block compliance | 32/120 = 26.67% | 100% | FAIL |
| legacy stale escape | 58/72 = 80.56% | <2% | FAIL |
| legacy unnecessary invalidation | 0/48 | <8% | PASS, weak coverage |
| accepted cases | 20/120 = 16.67% | reported diagnostic | NOT READY |

## Metric reconciliation

The persisted schema supports several additional offline diagnostics:

| Object being measured | Recovered/selected | Precision | Corpus-level recall/coverage |
|---|---:|---:|---:|
| proposal union (`reasoner ∪ critic`) | 165/252 | 65.48% | 165/168 = 98.21% |
| accepted canonical critical refs | 34/45 | 75.56% | 34/168 = 20.24% |
| accepted compilations | 20/120 cases | — | 16.67% case coverage |
| accepted expected-stale decisions | 14/14 became `STALE` | 100% directional correctness | 14/72 = 19.44% acceptance coverage |
| accepted expected-unchanged decisions | 6/6 remained non-stale | 100% directional correctness | 6/48 = 12.50% acceptance coverage |

The canonical precision is still below P0. The reconciliation only shows that `65.48%` is proposal-union precision, not the “accepted critical precision” described in `09_EVALUATION_BENCHMARK.md`.

Code-path evidence:

- `ModelCompilerSubject` unions draft CRITICAL refs with valid critic missing-dependency candidates before recording `critical_refs` (`model_subject.py:212-230`).
- critic findings are not applied to the draft; CRITICAL missing findings make review blocking (`review.py:156-208`, `review.py:281-296`).
- canonicalization consumes only the validator's resolved **draft** dependencies (`canonicalization.py:35-88`).
- `measure` uses the proposal union as both recall and precision input (`metrics.py:126-138`, `metrics.py:203-209`).
- `accepted_canonical_refs` is only used for unsupported-accepted counts (`metrics.py:129-136`, `metrics.py:210-213`).

## Cross-cutting counts by domain

| Domain | Cases | Recovered required | Predicted refs | Extra refs | Accepted cases | Accepted refs | Outcome correct | Block correct | Legacy stale escapes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| privileged access | 40 | 56/56 | 82 | 26 | 10 | 21 | 20/40 | 14/40 | 19/24 |
| production release | 40 | 55/56 | 79 | 24 | 8 | 19 | 18/40 | 12/40 | 17/24 |
| vendor onboarding | 40 | 54/56 | 91 | 37 | 2 | 5 | 13/40 | 6/40 | 22/24 |

Vendor onboarding is the weakest domain by acceptance, precision-error volume, outcome compliance, and legacy stale-escape count. This does not trigger K4 because recall itself is not vendor-only; it does reject any claim that the current method generalizes adequately.

## Cross-cutting counts by case class

| Case class | Recovered required | Predicted extras | Accepted cases | Outcome correct | Block correct | Legacy stale escapes |
|---|---:|---:|---:|---:|---:|---:|
| clean positive | 12/12 | 14 | 5/12 | 7/12 | 5/12 | 7/12 |
| clean negative | 11/12 | 8 | 0/12 | 2/12 | 0/12 | 12/12 |
| critical omission | 24/24 | 0 | 4/12 | 8/12 | 4/12 | 8/12 |
| irrelevant distractor | 11/12 | 14 | 1/12 | 5/12 | 1/12 | 0/0 |
| obsolete revision | 12/12 | 1 | 0/12 | 0/12 | 0/12 | 12/12 |
| conflicting sources | 23/24 | 0 | 0/12 | 12/12 | 12/12 | 0/0 |
| near duplicate | 12/12 | 14 | 2/12 | 5/12 | 2/12 | 0/0 |
| prompt injection | 12/12 | 12 | 3/12 | 5/12 | 3/12 | 0/0 |
| multiple dependencies | 36/36 | 0 | 5/12 | 7/12 | 5/12 | 7/12 |
| narrow clause | 12/12 | 24 | 0/12 | 0/12 | 0/12 | 12/12 |

The omission row is specifically `24/24` proposal-union recovery and `4/12` accepted, matching the current acceptance matrix. It must not be interpreted as 24 refs entering canonical graphs.

## A. Precision-failure taxonomy

There are 87 proposal-union false positives (`252 - 165`). The following primary classes are mutually exclusive and sum to 87:

| Primary category | Count | Privileged | Release | Vendor | Interpretation |
|---|---:|---:|---:|---:|---|
| supporting fact promoted to CRITICAL | 51 | 19 | 15 | 17 | Ref is explicitly labeled acceptable supporting ground truth, but appears in predicted CRITICAL union. |
| invalid/fabricated ref | 20 | 3 | 3 | 14 | Altered canonical ref, claim ID such as `c1`, or other ref absent from the case inventory. Deterministic validation prevents acceptance. |
| broad scope selected | 12 | 4 | 4 | 4 | `wide-policy#$.scope` is selected instead of remaining non-material context. |
| semantic overreach | 4 | 0 | 2 | 2 | Unrelated `wide-policy#$.appendix` fragment is promoted to CRITICAL. |

By case class:

| Case class | Supporting promoted | Invalid ref | Broad scope | Semantic overreach |
|---|---:|---:|---:|---:|
| clean positive | 12 | 2 | 0 | 0 |
| clean negative | 7 | 1 | 0 | 0 |
| irrelevant distractor | 11 | 3 | 0 | 0 |
| near duplicate | 9 | 5 | 0 | 0 |
| prompt injection | 12 | 0 | 0 | 0 |
| narrow clause | 0 | 8 | 12 | 4 |
| obsolete revision | 0 | 1 | 0 | 0 |

Required diagnostic lenses:

- **Relevant but noncritical / CRITICAL-vs-SUPPORTING confusion:** 51 refs. These are not hallucinated facts; they are useful secondary facts whose materiality is wrong.
- **Near-duplicate selection:** 0 actual `$.near_match` refs were selected. The 12 near-duplicate cases still contain 14 false positives—9 supporting promotions and 5 invalid refs—so that class fails for other reasons.
- **Broad authority:** 16 exact fragments from `wide-policy` were over-selected (12 scope plus 4 unrelated appendix). There are no whole-document refs, so K2 is not yet triggered.
- **Supporting fact promoted:** 51 proposal-union events; 11 survive into accepted canonical graphs. Those 11 are all acceptable supporting refs, yielding canonical precision `34/45 = 75.56%`.
- **Obsolete historical ref:** 0 historical refs appear as CRITICAL proposal-union extras, but two cases end in `REJECTED_STALE_SOURCE`. The report omits noncritical draft refs and validation findings, so the exact stale ref and materiality cannot be reconstructed.
- **Semantic overreach:** 4 strict unrelated-appendix events; under a broader definition, all 16 `wide-policy` over-selections are semantic overreach.

Representative cases:

- `privileged-access-001`: required primary plus an acceptable-supporting MFA record is accepted as two CRITICAL refs. This is a canonical materiality error, not a validator escape.
- `production-release-010`: the binding clause and broad `$.scope` are predicted CRITICAL; compilation is nevertheless rejected incomplete.
- `vendor-onboarding-011`: a malformed copy of the primary ref is emitted alongside known refs; deterministic validation rejects it.
- `privileged-access-007`: the model emits claim IDs `c1` and `c2` as if they were source refs; the actual near-match clause is not selected.

## B. Contradiction-failure taxonomy

All 12 contradiction cases have expected outcome `NEEDS_HUMAN_REVIEW` and `must_block=true`.

| Category | Count | Domain distribution | Result |
|---|---:|---|---|
| both conflicting sources selected, contradiction unnoticed | 11 | privileged 4, release 3, vendor 4 | no contradiction finding or severity |
| one side omitted | 1 | release 1 (`production-release-016`) | no contradiction finding |
| detected with wrong severity | 0 | — | no contradiction was detected at all |
| detected but disposition accepted | 0 | — | no contradiction was detected |
| precedence incorrectly resolved | 0 evaluable | — | no proposal reached a recorded precedence result |
| reasoner/critic responsibility confusion | 12 | 4/domain | correct NHR outcome and blocked state, but disposition is always `REJECTED_INCOMPLETE_DEPENDENCIES`, never contradiction-related |

Examples:

- `privileged-access-006` selects both equal-rank current authorities, outputs `NEEDS_HUMAN_REVIEW`, but records zero contradiction pairs and blocks as incomplete.
- `production-release-016` recovers only one of two contradictory authorities and also records no contradiction.

The outcome field shows that the reasoner recognizes “review” at a coarse semantic level, but the structured contradiction pass fails to identify the source pair. The persisted record cannot assign responsibility between reasoner and critic because it stores neither raw draft contradiction semantics nor critic output.

## C. Outcome-failure taxonomy

Outcome confusion matrix:

| Allowed | Predicted APPROVED | Predicted DENIED | Predicted HUMAN_REVIEW |
|---|---:|---:|---:|
| APPROVED | 37 | 0 | 59 |
| DENIED | 0 | 2 | 10 |
| HUMAN_REVIEW | 0 | 0 | 12 |

All 69 outcome failures are over-abstention to `NEEDS_HUMAN_REVIEW`; there is no unsafe APPROVED or incorrect DENIED in this run. Of those 69 failures, 67 have all ground-truth required refs present in the proposal union, so missing union-level coverage does not explain the outcome.

By domain:

| Domain | Correct | APPROVED→review | DENIED→review |
|---|---:|---:|---:|
| privileged access | 20/40 | 16 | 4 |
| production release | 18/40 | 20 | 2 |
| vendor onboarding | 13/40 | 23 | 4 |

Required lenses:

- APPROVED when DENIED/review required: 0.
- DENIED when approval permitted: 0.
- outcome ignores contradiction: 0 at categorical level; all 12 contradiction cases output review, but without a structured contradiction finding.
- outcome inconsistent with cited claims / ignores missing critical evidence: not provable from the persisted schema because raw claims, unresolved questions, and reasoner-only refs were not retained.

## D. Must-block taxonomy

The `26.67%` compliance result is dominated by false blocking, not unsafe acceptance:

| Population | Correct | Incorrect |
|---|---:|---:|
| 12 cases that must block | 12 blocked | 0 accepted |
| 108 cases that must not block | 20 accepted | 88 falsely blocked |

False-block disposition breakdown:

| Disposition | Count | Privileged | Release | Vendor |
|---|---:|---:|---:|---:|
| `REJECTED_INCOMPLETE_DEPENDENCIES` | 71 | 24 | 22 | 25 |
| `REJECTED_INVALID_REFERENCE` | 13 | 2 | 3 | 8 |
| `REJECTED_SCHEMA` | 2 | 0 | 2 | 0 |
| `REJECTED_STALE_SOURCE` | 2 | 0 | 1 | 1 |

Unsafe-acceptance lenses:

- missing critical dependency but accepted: 0 of the three proposal-union misses;
- contradiction exists but accepted: 0/12;
- stale-source rejection absent: 0 observed escapes among the two explicit stale dispositions;
- invalid authority relation accepted: not reconstructible because accepted edge relations are absent from `EvaluationRecord`;
- critic finding fails to propagate: not reconstructible because critic findings and stage ownership are absent.

All 12 required-block cases are counted correct even though they block for the wrong recorded reason (`REJECTED_INCOMPLETE_DEPENDENCIES`). Must-block compliance therefore cannot substitute for contradiction recall.

## E. Stale-escape taxonomy

The full analysis is in `docs/reports/module-01-stale-escape-analysis.md`.

Summary:

- 58/72 expected-stale records are labeled escapes;
- all 58 have non-`ACCEPTED` dispositions;
- all 58 have zero canonical refs and zero Runtime edges;
- `evaluate_runtime_mutation` returns `False` before creating Runtime state for any non-accepted prediction (`runner.py:363-366`);
- therefore the final state is **Decision absent**, not `DecisionStatus.VALID`;
- 57/58 still contain the exact mutated ref in `predicted_critical_refs`; the only extraction miss is `vendor-onboarding-012`;
- all 14 accepted expected-stale decisions become `STALE`;
- all 6 accepted expected-unchanged decisions remain non-stale.

Legacy escape disposition counts: 46 incomplete, 8 invalid ref, 2 schema, 2 stale source. Primary root cause is evaluator conflation of compilation coverage with runtime staleness; secondary root cause is the compiler's 16.67% acceptance coverage.

## Benchmark/evidence integrity findings

### Confirmed evaluator defect 1 — precision object mismatch

`critical_precision` is proposal-union precision, while the benchmark specification calls for accepted-critical precision. The historical metric must remain unchanged and be relabeled; a corrected report must add separate proposal and canonical metrics.

### Confirmed evaluator defect 2 — blocked-as-stale-escape

The boolean return type cannot distinguish:

- accepted and still `VALID` after a material change;
- rejected/no Runtime decision/no mutation executed.

The corrected evaluator needs a terminal enum such as `STALE`, `VALID`, `NOT_ACCEPTED`, `EVALUATION_ERROR`, plus separate acceptance coverage. The P0 stale-escape rate must be computed only over accepted runnable decisions, while low acceptance remains a separate hard failure rather than disappearing.

### Confirmed benchmark coverage flaw — unrelated mutation misses promoted support

All 51 acceptable-supporting false positives are never used as mutation targets. The 48 expected-unchanged cases consist of:

- 12 contradiction cases that intentionally do not enter Runtime;
- 36 cases mutating a forbidden distractor, near-match, or injection fragment.

Thus `0%` unnecessary invalidation does not test the dominant materiality failure. Existing cases must not be deleted or relabeled. Add paired mutations for supporting refs in a future version and preserve the old result.

### Evidence schema gap

`EvaluationRecord` omits:

- raw reasoner draft and reasoner-only critical refs;
- critic additions and critic findings;
- validator findings and which stage chose the disposition;
- accepted dependency edges, including relation, materiality, and target;
- Runtime receipt, mutation event ID, and terminal `DecisionStatus`.

The old report therefore cannot answer reasoner-versus-critic responsibility or reconstruct accepted relation chains exactly. Experiment 1 must first add immutable stage-level evidence. This is benchmark instrumentation, not permission to redesign compiler semantics.

## Root-cause hypotheses and falsification tests

| ID | Hypothesis | Current support | Evidence that would falsify it |
|---|---|---|---|
| H1 | Apparent high recall is inflated by unioning critic candidates with reasoner refs, while those candidates never enter the canonical graph. | Confirmed by code path; proposal recall 98.21%, canonical corpus recall 20.24%. | Paired raw traces show critic candidates are already in the reasoner draft and accepted canonical coverage remains near 98%. |
| H2 | The reasoner systematically promotes useful secondary facts from SUPPORTING to CRITICAL. | 51 such proposal events; 11 accepted. | Reasoner-only traces show those 51 are added solely by critic, or carry SUPPORTING materiality before evaluator transformation. |
| H3 | The general-purpose critic overblocks because missing/unsupported findings default to CRITICAL without a requirement model. | 83 incomplete dispositions; only 20 accepted. | Critic-off/on pairing shows no accepted-count loss, or nearly every critic block corresponds to a true ground-truth omission and improves safety. |
| H4 | A critic asked to find omissions, irrelevant refs, unsupported claims, contradictions, severity, and outcome support does not reliably bind contradiction pairs. | 0/12 contradictions despite 11/12 cases containing both refs in union. | Current critic detects correctly paired CRITICAL contradictions on the frozen subset without prompt/schema change. |
| H5 | The reasoner uses HUMAN_REVIEW as a generic uncertainty fallback rather than deriving the categorical outcome from evidence. | All 69 errors are over-abstentions; 67 include full required union. | Raw drafts show deterministic blocking questions or actual contradictions that ground truth omitted, consistently reviewed by humans as valid. |
| H6 | Runtime relation/materiality or fragment-to-artifact mapping causes the 80.56% escape. | Refuted for accepted records: 20/20 mutation directions correct. | Persisted accepted edges replay with exact relations and any material mutation leaves an accepted decision `VALID`. |
| H7 | The current unrelated-mutation suite cannot detect supporting-ref over-invalidation. | Confirmed: 0/51 promoted supporting refs are mutated. | Existing mutation targets are shown to cover those promoted refs, or paired support mutations produce the same zero rate. |
| H8 | Invalid refs arise from source-ref/claim-ID schema confusion and imperfect copying of opaque IDs. | 20 invalid extras, including `c1`, `claim-3`, and altered canonical IDs. | Stage traces show all invalid refs originate outside reasoner dependencies or are report transformation artifacts. |

## Proposed experiment sequence

1. **Experiment 0 — complete:** offline reproduction, taxonomy, evaluator audit. No model calls.
2. **Instrumentation repair:** version the evidence schema; preserve the old report; add reasoner-only refs, critic additions, findings, canonical edges, and mutation terminal state. Add corrected metrics alongside legacy metrics.
3. **Experiment 1:** paired current reasoner-only versus current reasoner+critic on the existing 30-case frozen variance subset. Exact design follows below.
4. Do not start minimal-critical prompt/schema redesign until Experiment 1 answers K3.
5. Do not execute a full 120-case paid ablation unless the 30-case subset shows pre-registered positive signal.

## Experiment 1 — exact pre-registered ablation design

### Experiment identity

```text
EXPERIMENT: module-01-exp-01-current-critic-ablation
METHOD VERSION: reasoner-v2 / critic-v1 / sdc-1 / validation-v1
PROVIDER/MODEL: OpenAI / gpt-5.6-luna
STATUS AT PRE-REGISTRATION: DESIGN ONLY — NOT EXECUTED
```

### Hypothesis

The current critic materially improves true omission recovery or contradiction handling beyond the current reasoner, without creating enough false positives/false blocks to erase that safety benefit.

Null/K3 hypothesis: any apparent improvement is only proposal-union accounting, or the critic provides no correct omission/contradiction signal and mainly reduces acceptance.

### Cases

Use the existing `variance_subset=true` set: exactly 30 frozen cases, 10/domain, with exactly one of each case class per domain (`001` through `010` in privileged access, production release, and vendor onboarding). Do not select cases based on current failures and do not alter ground truth.

### Paired execution

For each case, in fixed case-ID order:

1. make one live reasoner call using the current context/source inventory;
2. persist the raw validated `DecisionDraft`, response metadata, usage, and a canonical draft digest;
3. fork that exact immutable draft into two deterministic arms:
   - **A reasoner-only:** validator → empty `CriticReview` → canonicalizer;
   - **B current critic:** validator → current live critic when validation permits → current review gate → same canonicalizer;
4. assert both arms have the same draft digest, source snapshot, model version, prompt context digest, validator version, canonicalizer version, and metric version;
5. run the same Runtime mutation evaluator and record a terminal enum, exact accepted edges, event ID, and final decision status.

Sharing one reasoner output is required: making two independent reasoner calls would introduce sampling variance, so critic would no longer be the only changed variable.

### Locked settings

- reasoner prompt `reasoner-v2`;
- critic prompt `critic-v1`;
- model `gpt-5.6-luna`;
- Responses reasoning effort `low`;
- service tier `default`;
- temperature omitted and recorded as `null`;
- SDK automatic retries `0`;
- current bounded schema-correction retry: at most one per reasoner or critic;
- max input reservation 250,000 tokens and max output 8,192 tokens;
- identical deterministic validator, precedence policy, canonicalizer, runtime acceptance, mutation evaluator, and corrected metric implementation in both arms.

### Measurements

Report both arm values and paired deltas for:

- reasoner-only and critic-added required refs;
- reasoner-only and critic-added false-positive refs;
- proposal recall and precision;
- canonical accepted recall and precision;
- contradiction recall and CRITICAL severity recall;
- outcome compliance;
- must-block compliance, including correct reason code;
- legacy stale escape for historical comparability;
- accepted-only stale escape and acceptance coverage;
- unnecessary invalidation, with mutation-target coverage disclosure;
- accepted-case count;
- call count, latency, tokens, cache read/write tokens, and cost.

The report must explicitly answer the five required K3 questions and be written to `docs/reports/module-01-critic-ablation.md` only after actual live execution.

### Calls and cost

- nominal maximum: 30 reasoner + 30 critic = 60 live calls;
- current-path expectation from the same subset: 30 reasoner + 7 critic = 37 calls;
- absolute POST ceiling including one schema retry per invocation: 120;
- previous observed cost on those same 37 primary calls: `$0.061470160`;
- hard incremental experiment cap: **$0.25**, enforced inside the existing cumulative `$10` SQLite ledger, including UNKNOWN holds;
- do not create a second ledger that bypasses cumulative accounting.

If the next worst-case reservation cannot fit either the global remaining budget or the `$0.25` experiment allocation, stop before sending. Hitting the cap makes the experiment incomplete; it does not authorize partial-result cherry-picking.

### Positive signal and decision rule

Proceed from the 30-case subset to a full 120-case paired ablation only if critic-on:

1. adds at least one ground-truth-required ref that reasoner-only omitted **or** detects at least one exact ground-truth contradiction pair with CRITICAL severity;
2. changes the deterministic result in the correct safety direction for at least one case;
3. accepts no must-block case and no unknown/unauthorized/stale authority;
4. does not improve a metric solely by adding a ref to proposal union while leaving canonical/runtime evidence unchanged;
5. has no unexplained config/digest mismatch and stays within the cost cap.

If it adds no true omission/contradiction signal, or its only effect is false positives/false blocks, K3 is supported: stop and report that the critic must be removed or redesigned. Architectural removal/replacement still requires product-owner review; it is not performed as part of this experiment.

### Stop conditions

Stop the run immediately and preserve partial immutable evidence if:

- any arm differs in anything other than critic on/off;
- draft/context/source/config digests differ;
- a model or service tier differs from the locked configuration;
- any call becomes UNKNOWN;
- incremental exposure reaches `$0.25`;
- the existing cumulative `$10` guard cannot reserve the next call;
- an evaluator integrity assertion fails;
- evidence cannot distinguish `NOT_ACCEPTED` from `VALID`.

Do not proceed to Experiment 2 on an incomplete or ambiguous ablation.

## Experiment 1 — executed result

Experiment 1 subsequently completed on the exact frozen 30-case subset without changing the method, thresholds, corpus, or ground truth. The canonical result is `docs/reports/module-01-critic-ablation.md`:

- run ID: `critic-ablation:51646ddf01693a9b`;
- immutable live evidence SHA-256: `cfd09ac11e1f0cb8b659c1bf58d244ce082a715df6d7a5e969ef3f60f9e01494`;
- 30 reasoner calls + 8 critic calls; no schema retry and no UNKNOWN call;
- total incremental cost: `$0.065727100`, below the `$0.25` pre-registered cap;
- required omissions recovered by critic: `0`;
- correct contradictions added by critic: `0`;
- false-positive refs added by critic: `4`;
- spurious blocks introduced by critic: `5`;
- accepted cases: `8/30` reasoner-only versus `3/30` critic-on;
- accepted canonical recall: `28.57%` reasoner-only versus `11.90%` critic-on;
- accepted-only mutation results remained directionally correct but tiny: reasoner-only tested 2 material + 6 unrelated mutations; critic-on tested 1 material + 2 unrelated mutations.

The first generated v2 evaluator output incorrectly excluded unknown critic-proposed refs from the false-positive count. It is preserved as `module-01-critic-ablation-evaluator-v2.*`. The v3 report recomputes only derived evaluator fields from the immutable raw draft/review evidence; model responses, Runtime receipts, token usage, and cost are unchanged.

The pre-registered positive-signal rule failed. K3 is therefore triggered for the current critic: **REMOVE OR REDESIGN IT**, subject to product-owner architecture approval. Do not run a paid 120-case ablation or begin Experiment 2 before that decision.

## Kill/redesign assessment after Experiment 1

- K1 not triggered: proposal-union critical recall is above 0.80, though this is not canonical coverage.
- K2 not triggered: refs remain fragment-level; broad `$.scope` selection is a precision defect but not whole-document dependence.
- K3 triggered for the current critic: it added no true omission or contradiction signal and only false-positive refs/false blocks.
- K4 not triggered by recall, but vendor acceptance is only 2/40 and requires redesign.
- K5 not triggered: no injected ref becomes predicted critical or accepted canonical; supporting refs in injection cases are still over-promoted.
- K6 not cleared: only 20/120 model compilations are accepted and product demos remain authored fixtures.

The project-wide thesis is not yet killed, but the current critic configuration is killed for progression and K6 remains uncleared. Live Gemini remains `BLOCKED` until Gemini API or Vertex credentials exist and cannot be waived.
