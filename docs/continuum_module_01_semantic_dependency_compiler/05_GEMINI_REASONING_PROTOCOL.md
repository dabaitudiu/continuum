# 05 — Model Reasoning Protocol

## Status

This is the provider-neutral Option B Revision-6 protocol under product-owner review. The direction and Revision-5 P0-1～P0-33 guarantees are approved；the concrete Revision-6 amendments are not. OpenAI remains a provider-neutral falsification lane and Gemini is the competition-provider DEV/blind acceptance lane. No live calls are authorized by this document.

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
- invalid schema receives only the policy-configured bounded repair count；v5 fragment maps and v6 disposition-critical verification use zero repairs, then the run is `FAILED` with no proposal-admission disposition;
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

This separate prompt does not receive Stage-2 matches/refs and does not ask for omissions、dependency repair、outcome rewrite、severity or disposition. Each wrapper contains only actual matches；empty means processed/no match reported. Deterministic code verifies exact fragment coverage、globally joins **same normalized predicate/entity/target with overlapping scope/time** across partitions、applies precedence and derives provisional impact. Cross-predicate invariants are registered contract/template evaluators, not model contradiction authority. The output is O(fragments+actual matches). Preflight capacity blocks；timeout、protocol truncation or malformed/partial receipt after a call starts fails the run with no proposal-admission disposition。

## Stage 4A/4V/4R/4B/5 — Selection、disposition-critical verification and proposal Gate

Stage 4V is the only model invocation in this phase；4A、4R、4B and 5 are deterministic。

Input:

- template-instantiated Requirements、validated binding candidates、exact upstream Decision bindings、provisional globally reduced direct contradictions and policy bundle;
- DIRECT_ATOM/ALL_OF requirement DAG.

Each Stage 4V invocation receives exactly one isolated tuple containing only purpose、preselected observation、source fragment、target PredicateIdentity、instantiated entity、claimed entailment/value and relevant normalized semantics. Purposes are selected enterprise proof、selected applicability guard、or one side of a provisional validity-critical direct contradiction. It cannot see proposal outcome、other candidates、the opposing contradiction side、Stage-2 rationale or Gate。

Stage 4V output is only `CONFIRMED | REFUTED | INDETERMINATE` per request. Output of the complete phase is independently verified proof-selected `EvidenceBinding[]`、confirmed `Contradiction[]`、typed semantic uncertainties、exact `UpstreamDecisionBinding[]`、one assessment per effective Requirement、`TemporalValidityGuard[]`、sequence-bound `DecisionValidityEnvelope` and proposal-admission disposition.

For each enterprise proof role/guard, code selects by a frozen order and asks the independent verifier；only CONFIRMED becomes canonical CRITICAL. REFUTED/INDETERMINATE excludes that proof candidate and code tries the next. A provisional critical direct contradiction requires both material sides CONFIRMED；REFUTED removes/reduces again, while INDETERMINATE yields semantic uncertainty and fail-closed admission review rather than a confirmed contradiction. Exact accepted/current/VALID upstream Decisions satisfy `UPSTREAM_DECISION` roles without semantic model reinterpretation. Gate compares the evidence-supported class to the immutable proposal；mismatch rejects admission and never emits a replacement outcome. Stage 4V cannot add a Requirement/ref/contradiction、change materiality/outcome/admission disposition or mutate state；`UNKNOWN_SOURCE_REQUIRED` is unrepresentable.

## Failure handling

### Trusted input rejection

Malformed/unauthorized signed proposal/entity/upstream/observation input、mixed/future/bypass observation or exact world/hash mismatch is completed `INPUT_REJECTION` with no proposal-admission disposition。

### Compiler/model execution failure

- model schema/enum/local-ID/forbidden ref/target/entity、receipt/protocol/verifier violation or transport failure after invocation: `RUN_FAILED` + typed retryability、no proposal-admission disposition；
- a retry is a new immutable attempt；partial outputs never cross attempts；
- provider credentials/budget or complete context capacity unavailable before calls: `RUN_BLOCKED` with no disposition；
- universe/normalization/plan unavailable before calls: `RUN_BLOCKED`; post-call partial/malformed coverage is `RUN_FAILED`。

### Semantic conditions

Unsupported logic/predicate/absence/unregistered cross-predicate relation、real missing/unverified support、validly observed cross-entity mismatch、indeterminate applicability/entailment、confirmed direct contradiction/semantic uncertainty、invalid upstream Decision and proposal-outcome mismatch are semantic conditions. Only a correctly executed pipeline may emit their proposal-admission disposition；the business outcome remains the immutable proposal value。

## Provider strategy

Model adapters remain provider-neutral. Architecture acceptance follows this order:

1. bounded experiments and integrated 30-case DEV falsify the method;
2. Experiment 6A runs OpenAI full DEV;
3. Experiment 6B runs Gemini full DEV before any blind access;
4. Experiment 7 freezes code、prompts、schemas、policy bundle、predicate catalog、normalization/selection/verification/operational policies、model configs、dependency lock、runner/evaluator and metrics;
5. Experiment 8 reveals/runs the independently owned blind set once with Gemini primary and OpenAI optional secondary.

The implementation agent never generates or inspects holdout bodies before methodology freeze；only schema/version/hash metadata is visible. Any post-holdout method change requires a fresh independent set。

Fake transports remain valid for deterministic contract tests only and never satisfy live-provider rows.
