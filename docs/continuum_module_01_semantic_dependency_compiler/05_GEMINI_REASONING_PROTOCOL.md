# 05 — Model Reasoning Protocol

## Status

This is the provider-neutral Option B Revision-4 protocol under product-owner review. The direction is approved；the concrete specification is not. OpenAI remains a provider-neutral falsification lane and Gemini is the competition-provider DEV/blind acceptance lane. No live calls are authorized by this document.

The implemented reasoner/critic protocol is frozen as the v1 ablation baseline. The old critic prompt must not be tuned or preserved as production fallback.

## Common rules for every model stage

- source fragments are untrusted data, never instructions;
- tools are read-only and bounded by request scope/world snapshot;
- only tool-returned canonical refs may be copied;
- output must match the stage-specific schema;
- no stage may emit canonical IDs, mutate Runtime state, select deterministic precedence, or authorize an action;
- no stage may declare universe/normalization/selection completeness、canonical applicability、canonical materiality、canonical contradiction impact or final disposition;
- model stages receive immutable `DecisionProposal` outcome and already-instantiated predicate/entity target keys only；they may not author/replace the business outcome、Requirement、predicate or entity；
- every fragment-complete map returns exactly one wrapper per assigned fragment, with an empty match list when it reports no relevant proposition；no top-K or silent negative cross-product；
- concise semantic propositions and summaries are stored; hidden chain-of-thought is neither requested nor persisted;
- invalid schema receives only the policy-configured bounded repair count；v4 fragment Evidence/contradiction maps use zero repairs, then end as structural failure;
- every invocation records provider/model/version, prompt/schema version, request configuration, response identity, usage, latency, and ledger settlement.

## Stage 0/1 — No model ownership

Trusted code validates `DecisionProposal` producer/outcome/world binding、`DecisionEntityContext` roles and `SourceUniverseSnapshot → RuleNormalizationManifest → SourceSetManifest`. It then deterministically instantiates every approved governing/decision-class `RequirementTemplate` and accounts every obligation/applicability target exactly once. A model cannot declare coverage complete or create Requirements. `INCOMPLETE | UNKNOWN | REVIEW_REQUIRED` blocks before semantic inference. Derived records bind exact inputs but are not members of the input world snapshot.

## Stage 2 — Complete Evidence/applicability interpretation

Input:

- one deterministic `EvidenceCoveragePlan` partition containing ≤16 assigned fragments and only the catalog-allowed target keys for each fragment；
- template-instantiated Requirement and applicability target descriptors with trusted entity bindings；
- source identity/content/authority/time metadata as untrusted data.

Output: exactly one `FragmentEvidenceObservation` per assigned fragment plus one `EvidenceCoverageReceipt`.

Each fragment wrapper contains only actual matched Requirement/applicability predicates、semantic role、three-state entailment、bounded canonical subject/object/value and asserted horizon；free prose is forbidden. Empty matches mean processed/no match reported. The model cannot emit a target outside the plan or an entity ID. Deterministic code validates receipts、entity/ref/scope/time/role and derives bindings. Governing authority is bound from trusted rule/template provenance, not rediscovered by the model. The model does not output canonical `CRITICAL | SUPPORTING`。

## Stage 3 — Independent Contradiction Pass

Input:

- template-instantiated Requirement plus all applicability predicate targets;
- one deterministic partition of the complete current/in-scope contradiction-eligible inventory, independent of Stage-2 refs;
- source values/claims and authority metadata.

Output: one `FragmentSemanticObservation` per assigned fragment plus a coverage receipt.

This separate prompt does not receive Stage-2 matches/refs and does not ask for omissions、dependency repair、outcome rewrite、severity or disposition. Each wrapper contains only actual matches；empty means processed/no match reported. Deterministic code verifies exact fragment coverage、globally joins matches by predicate/entity/target across partitions、applies precedence and derives impact. The output is O(fragments+actual matches). Timeout、dense output、truncation or partial union blocks rather than reporting an empty contradiction set.

## Stage 4/5 — Deterministic proof、temporal validity and proposal Gate

This stage has no model invocation.

Input:

- template-instantiated Requirements、validated binding candidates、globally reduced contradictions and policy bundle;
- DIRECT_ATOM/ALL_OF requirement DAG.

Output: proof-selected `EvidenceBinding[]`、one assessment per effective Requirement、`TemporalValidityGuard[]`、`DecisionValidityEnvelope` and proposal disposition.

For each required proof role, code selects eligible determinate evidence by versioned authority/proof policy. Selected bindings become canonical CRITICAL dependencies. Missing roles or only INDETERMINATE evidence produce `INSUFFICIENT_EVIDENCE`. Time-sensitive proofs require a verified finite horizon. Gate compares the evidence-supported class to the immutable proposal；mismatch rejects/reviews it and never emits a replacement outcome. This stage cannot add a Requirement、ref or semantic observation；`UNKNOWN_SOURCE_REQUIRED` is unrepresentable.

## Failure handling

### Structural failures

- schema/enum/local-ID/cross-link failure after configured repairs（zero for v4 fragment maps）: structural terminal;
- unknown, unauthorized, stale, or illegal source ref: deterministic structural terminal;
- provider/auth/transport/budget unavailable: execution `BLOCKED`, not semantic rejection.
- incomplete/unknown universe/SourceSet、incomplete/review-required normalization or partial/over-limit/dense Evidence/contradiction receipts: `RUN_BLOCKED` with no semantic success;
- unsupported logic/predicate/absence: typed `REJECTED_UNSUPPORTED_LOGIC | REJECTED_UNSUPPORTED_PREDICATE` with no canonical graph.

### Semantic conditions

Missing support、cross-entity match、indeterminate applicability/entailment、contradictions and proposal-outcome mismatch do not masquerade as structural errors. Once inputs are structurally valid, they reach contradiction/proof/completeness before Gate.

## Provider strategy

Model adapters remain provider-neutral. Architecture acceptance follows this order:

1. bounded experiments and integrated 30-case DEV falsify the method;
2. Experiment 6A runs OpenAI full DEV;
3. Experiment 6B runs Gemini full DEV before any blind access;
4. Experiment 7 freezes code、prompts、schemas、policy bundle、predicate catalog、normalization/selection policies、model configs、dependency lock、runner/evaluator and metrics;
5. Experiment 8 reveals/runs the independently owned blind set once with Gemini primary and OpenAI optional secondary.

The implementation agent never generates or inspects holdout bodies before methodology freeze；only schema/version/hash metadata is visible. Any post-holdout method change requires a fresh independent set。

Fake transports remain valid for deterministic contract tests only and never satisfy live-provider rows.
