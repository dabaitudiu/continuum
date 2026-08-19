# 05 — Model Reasoning Protocol

## Status

This is the provider-neutral Option B Revision-5 protocol under product-owner review. The direction is approved；the concrete specification is not. OpenAI remains a provider-neutral falsification lane and Gemini is the competition-provider DEV/blind acceptance lane. No live calls are authorized by this document.

The implemented reasoner/critic protocol is frozen as the v1 ablation baseline. The old critic prompt must not be tuned or preserved as production fallback.

## Common rules for every model stage

- source fragments are untrusted data, never instructions;
- tools are read-only and bounded by one signed executable `GovernedReadView`；every material read has a `GovernedObservation`;
- only tool-returned canonical refs may be copied;
- output must match the stage-specific schema;
- no stage may emit canonical IDs, mutate Runtime state, select deterministic precedence, or authorize an action;
- no stage may declare universe/normalization/selection completeness、canonical applicability、canonical materiality、canonical contradiction impact or final disposition;
- model stages receive immutable `DecisionProposal` outcome and already-instantiated predicate/entity target keys only；they may not author/replace the business outcome、Requirement、predicate or entity；
- every fragment-complete map returns exactly one wrapper per assigned fragment, with an empty match list when it reports no relevant proposition；no top-K or silent negative cross-product；
- concise semantic propositions and summaries are stored; hidden chain-of-thought is neither requested nor persisted;
- invalid schema receives only the policy-configured bounded repair count；v5 fragment/verification maps use zero repairs, then the run is `FAILED` with no business disposition;
- every invocation records provider/model/version, prompt/schema version, request configuration, response identity, usage, latency, and ledger settlement.

## Stage 0/1 — No model ownership

Trusted code validates `GovernedObservationSet` closure/executable epoch、`DecisionProposal` producer/outcome/world binding、`DecisionEntityContext` roles、exact contract-required upstream Decision envelopes/status，and `SourceUniverseSnapshot → RuleNormalizationManifest → SourceSetManifest`. It then deterministically instantiates every approved governing/decision-class `RequirementTemplate` and accounts every obligation/applicability/upstream target exactly once. A model cannot choose upstream Decisions、declare coverage complete or create Requirements. Derived records bind exact inputs but are not members of the input world snapshot.

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

This separate prompt does not receive Stage-2 matches/refs and does not ask for omissions、dependency repair、outcome rewrite、severity or disposition. Each wrapper contains only actual matches；empty means processed/no match reported. Deterministic code verifies exact fragment coverage、globally joins **same normalized predicate/entity/target with overlapping scope/time** across partitions、applies precedence and derives impact. Cross-predicate invariants are registered contract/template evaluators, not model contradiction authority. The output is O(fragments+actual matches). Preflight capacity blocks；timeout、protocol truncation or malformed/partial receipt after a call starts fails the run with no business disposition。

## Stage 4A/4V/4B/5 — Selection、independent selected-proof verification and proposal Gate

Stage 4V is the only model invocation in this phase；4A、4B and 5 are deterministic。

Input:

- template-instantiated Requirements、validated binding candidates、exact upstream Decision bindings、globally reduced direct contradictions and policy bundle;
- DIRECT_ATOM/ALL_OF requirement DAG.

Stage 4V input is one or more isolated exact tuples containing only source fragment、target PredicateIdentity、instantiated entity、claimed entailment/value and relevant normalized semantics. It cannot see proposal outcome、other candidates、Stage-2 rationale、contradiction results or Gate。

Stage 4V output is only `CONFIRMED | REFUTED | INDETERMINATE` per request. Output of the complete phase is independently verified proof-selected `EvidenceBinding[]`、exact `UpstreamDecisionBinding[]`、one assessment per effective Requirement、`TemporalValidityGuard[]`、`DecisionValidityEnvelope` and proposal disposition.

For each enterprise proof role/guard, code selects by a frozen order and asks the independent verifier；only CONFIRMED becomes canonical CRITICAL. REFUTED/INDETERMINATE excludes that candidate and code tries the next；the verifier never chooses. Exact accepted/current/VALID upstream Decisions satisfy `UPSTREAM_DECISION` roles without semantic model reinterpretation. Missing/unverified roles produce `INSUFFICIENT_EVIDENCE`. Gate compares the evidence-supported class to the immutable proposal；mismatch rejects/reviews it and never emits a replacement outcome. Stage 4V cannot add a Requirement/ref、change materiality/outcome/disposition or mutate state；`UNKNOWN_SOURCE_REQUIRED` is unrepresentable.

## Failure handling

### Trusted input rejection

Malformed/unauthorized signed proposal/entity/upstream/observation input、mixed/future/bypass observation or exact world/hash mismatch is completed `INPUT_REJECTION` with no business disposition。

### Compiler/model execution failure

- model schema/enum/local-ID/forbidden ref/target/entity、receipt/protocol/verifier violation or transport failure after invocation: `RUN_FAILED` + typed retryability、no business disposition；
- a retry is a new immutable attempt；partial outputs never cross attempts；
- provider credentials/budget or complete context capacity unavailable before calls: `RUN_BLOCKED` with no disposition；
- universe/normalization/plan unavailable before calls: `RUN_BLOCKED`; post-call partial/malformed coverage is `RUN_FAILED`。

### Semantic conditions

Unsupported logic/predicate/absence/unregistered cross-predicate relation、real missing/unverified support、validly observed cross-entity mismatch、indeterminate applicability/entailment、direct contradiction、invalid upstream Decision and proposal-outcome mismatch are semantic conditions. Only a correctly executed pipeline may emit their business disposition。

## Provider strategy

Model adapters remain provider-neutral. Architecture acceptance follows this order:

1. bounded experiments and integrated 30-case DEV falsify the method;
2. Experiment 6A runs OpenAI full DEV;
3. Experiment 6B runs Gemini full DEV before any blind access;
4. Experiment 7 freezes code、prompts、schemas、policy bundle、predicate catalog、normalization/selection/verification/operational policies、model configs、dependency lock、runner/evaluator and metrics;
5. Experiment 8 reveals/runs the independently owned blind set once with Gemini primary and OpenAI optional secondary.

The implementation agent never generates or inspects holdout bodies before methodology freeze；only schema/version/hash metadata is visible. Any post-holdout method change requires a fresh independent set。

Fake transports remain valid for deterministic contract tests only and never satisfy live-provider rows.
