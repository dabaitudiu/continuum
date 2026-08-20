# 10 — Test Plan

## Test pyramid

### Unit tests

Focus on deterministic code:

- source identity;
- fragment resolution;
- proposal producer/outcome immutability、entity-role binding and cross-entity rejection；
- governed-observation closure、gateway signature、executable read fence and future/mixed/bypass rejection；
- exact upstream Decision ID/final-record/envelope/outcome/status/epoch binding、supersession non-rewrite and reverse-`REQUIRES` reachability；
- `continuum-hash-v1` type/version/preimage registry completeness、ID/digest equality and full type-DAG topological sort；
- constructible universe→read-view→observation-set→proposal and CompilationCore→Envelope→Justification→FinalRecord layers with no back-reference；
- exact-ID and supersession-lineage Decision cycle checks；already-accepted immutable upstream requirement and D→D relation legality；
- temporal validity guard and exclusive authorization horizon;
- scope checks;
- separate enterprise-world/policy snapshots and exact derived-artifact envelope validation;
- PolicyUsageTrace completeness and `UNVERSIONED_POLICY_INPUT` rejection;
- SourceUniverse authority/namespace/enumeration/watermark/hash validation;
- RuleNormalizationManifest exact fragment accounting、parser/reviewer receipts and no silent omission;
- SourceSetManifest boundary、included/excluded rule inventory、retrieval version、coverage status/hash and selective guard derivation;
- stable PredicateIdentity and DIRECT_ATOM/ALL_OF normalization；P0 `NOT_EXISTS`、`EXISTS+FALSE` and retrieval absence rejection；
- trusted reusable template instantiation、per-obligation accounting、entity-bound IDs、APPLICABLE/NOT_APPLICABLE proof and INDETERMINATE;
- EvidenceCoveragePlan eligibility/no-top-K limits、one-wrapper-per-fragment receipts、preflight capacity blocking and post-call partial/protocol failure；
- EvidenceBinding cross-links、applicability-vs-state target separation、three-state entailment、proof eligibility and proof-selected materiality;
- disposition-critical verifier purpose/minimal input/independence/three-valued verdict、deterministic removal/reselection/re-reduction and only-CONFIRMED proof/contradiction semantics；
- scalable fragment contradiction partition/receipt union、actual-match output、cross-partition entity-aware join、precedence and impact;
- deterministic RequirementAssessment truth table, support paths, blocking IDs, and one-assessment-per-requirement;
- deterministic proof-role selection and opposite-truth conflict preservation;
- transitive Source → Claim → Claim → Decision and reverse-indexed Decision `REQUIRES` reachability;
- deterministic `APPROVE | DENY | REVIEW` acceptance rules;
- proposal outcome mismatch rejects without replacement；
- `DecisionValidityEnvelope` observation/upstream/verification/semantic-sequence/component-epoch binding and authorization denial across relevant ChangeSets；
- contiguous owner-scope sequence assignment/range proof/replay and zero required Decision-row writes in publication；
- immutable SideEffect intent-core hash plus contiguous transition hashing/head CAS；`ReauthorizeForExecutionTxn` exact envelope/range/upstream/horizon/policy check plus atomic appended transition to `EXECUTING | CANCELLED_STALE_AUTHORIZATION`；
- disjoint INPUT_REJECTION / EXECUTION_FAILURE / SEMANTIC_RESULT records；model/protocol failure has no proposal-admission disposition；
- immutable proposed business outcome versus proposal-admission disposition serialization/UI/audit mapping；
- deterministic minimal DecisionJustification independent of proposition display、case/domain/local-ID order;
- unsupported-logic and unsupported-predicate typed fail-closed results;
- canonical edge normalization;
- duplicate edge handling;
- materiality rules;
- compilation-core/envelope/justification/final-record hashing;
- schema rejection.

### Property tests

Useful invariants:

- canonicalization idempotence;
- edge ordering independence;
- adding unrelated source fragments cannot alter deterministic validation of existing refs;
- duplicate proposal dependencies do not create duplicate canonical edges;
- paraphrasing display text cannot change semantic IDs、proof selection or Runtime edges;
- adding an unselected candidate cannot override a higher-precedence stable proof;
- every complete partitioning of the same inventory reduces to the same contradiction set;
- incomplete receipt union can never have completed contradiction status.
- incomplete Evidence receipt union can never have completed discovery status；
- model match count/output grows with fragments + actual matches, not fragments × predicates；
- changing proposal outcome never lets compiler canonicalize a different outcome under the same proposal ID；
- time passage to exact exclusive horizon denies authorization without source mutation；
- any uncovered newer semantic sequence denies side-effect execution start；
- any relevant intervening ChangeSet or invalid upstream Decision denies authorization even if the Decision row still says VALID；
- publishing an epoch never requires materializing per-Decision stale/certificate rows；
- N0/N1 share primary Evidence/contradiction outputs；only verification/removal/reselection/re-reduction differs；
- every accepted sequence log is gapless、unique、ordered and predecessor-hash linked；broken replay prefix never exposes a governed read fence；
- after `EXECUTING`, later sequence changes never rewrite history or permit duplicate logical external effects；
- changing an irrelevant inventory artifact may change audit manifest hash but not selective Runtime guard/edge set;
- semantically relevant catalog/rule/selection changes alter only matching coverage guards.
- every registered hash type has exactly one preimage rule；adding any removed reverse edge makes the type graph cyclic；
- creating a proposal、envelope、justification、final record or ledger transition never changes an ancestor digest；
- append-only SideEffect transitions form one contiguous non-forking chain and never change `intent_core_hash`；
- every accepted D→D `REQUIRES` edge strictly targets an already-accepted exact node, and both exact-ID/lineage graphs remain acyclic；

### Integration tests

Use fake model outputs but real compiler pipeline and persistence.

Cases:

- valid decision compiles;
- unknown ref rejected;
- stale revision rejected;
- cross-scope ref rejected;
- malformed signed input is typed INPUT_REJECTION；model-emitted forbidden ref/schema/target and transport failure are RUN_FAILED with null proposal-admission disposition；
- W18 bypass/mixed observation cannot enter a W17/E17 proposal；
- D42 exact VALID binding satisfies D50；D42 STALE/SUPERSEDED invalidates D50→activation and never auto-binds D42'；
- a domain-proposal/rationale omission is supplied by trusted template instantiation and flows downstream;
- a missing/duplicate template/obligation receipt cannot appear as complete accounting;
- Alice Requirement cannot use Bob evidence；Vendor-A cannot use Vendor-B evidence；
- Evidence/applicability fragment inventory has no silent top-K；preflight capacity blocks and post-call missing/partial receipt fails execution；
- INDETERMINATE obligation applicability prevents normal acceptance;
- a Requirement without determinate proof evidence reaches contradiction and completeness before gate rejection;
- INDETERMINATE evidence cannot satisfy a DIRECT_ATOM;
- governing authority cannot masquerade as factual state evidence;
- equal-authority contradiction reaches a dedicated typed pass；both material sides must verify CONFIRMED before it becomes a blocking contradiction;
- model SUPPORTING/severity advisory cannot suppress selected-proof materiality or blocking contradiction impact;
- cross-partition contradiction is joined, while missing partition blocks the run;
- contradiction output emits one wrapper/ref plus actual matches and remains inside declared v5 call/token/output limits；
- direct same-predicate conflicts are detected；registered cross-predicate constraint violations and unsupported relations are separate paths；
- primary interpreter falsely reads “training expired” as true；Stage 4V refutes it and deterministic selection retries/fails closed；
- contradiction observer hallucinates one side；Stage 4V REFUTED removes/re-reduces it, while INDETERMINATE emits semantic uncertainty rather than confirmed contradiction；
- incomplete/unknown SourceUniverse/SourceSet and incomplete/review-required normalization fail closed;
- applicable unsupported OR/threshold/exception logic cannot canonicalize;
- a transitive Claim support path is accepted without redundant direct source edges;
- selected applicability fact、material policy/rule/coverage guard revision makes affected Decision stale；unrelated whole-manifest change does not;
- only requirement-DAG roots connect to Decision; intermediate Claim → Decision edges are not duplicated;
- reasoner-only and old-critic baselines cannot call Runtime acceptance;
- no replacement failure falls back to old critic;
- runtime revision changes after compile → accept fails.
- source bytes unchanged but temporal horizon expires → authorization denied/Decision stale；
- enterprise、new-rule membership、policy、catalog/selector races publish ChangeSets without Decision fan-out and cannot authorize across a relevant intersection；
- material absence obligation produces `ABSENCE_PROOF_NOT_SUPPORTED_P0` with no canonical graph；
- proposal proof implies another outcome → supplied proposal rejected, no substitute Decision。
- immutable APPROVED proposal + insufficient evidence → `REJECTED_INCOMPLETE_REQUIREMENTS` admission result, UI/audit says NOT ADMITTED and never business DENIED；
- sequence 187 intent、relevant publication 188、then execution start → `CANCELLED_STALE_AUTHORIZATION` and external adapter call count 0；
- crash before reauthorization、between check/commit、after `EXECUTING`/before call、after call/before `COMMITTED` and unknown outcome all follow the normative idempotency/reconciliation table；
- sequence publication CAS assigns exactly next value；range 188…194 rejects gap、duplicate、reorder、bad predecessor and pointer/log mismatch；recovery exposes only verified prefix；
- observation-set hash is sealed before proposal and unchanged by proposal/signature creation；SourceUniverseSnapshot contains no read-view descendant；completeness/gateway attestations contain no snapshot/observation/signature descendant and detached signing leaves ancestors byte-identical；
- every registered hash profile maps to exactly one preimage/stratum；collapsed strata topologically sort, while ChangeSet/Decision/SideEffectTransition instance edges reject self/future/non-decreasing ordinals；
- accepted hash layering recomputes `CompilationCore → Envelope → Justification → FinalRecord` exactly and rejects legacy/cyclic `compilation_hash` use；
- direct Decision self-cycle、two-node edge-insertion cycle、supersession-lineage cycle and concurrent unaccepted mutual refs all fail before canonical writes；
- D→D `AUTHORIZES` is rejected；`D50 --REQUIRES--> D42` plus `D50 --AUTHORIZES--> activation` preserves transitive invalidation；
- intent core remains byte-identical across `NONE→INTENDED→EXECUTING→COMMITTED`；wrong predecessor、gap、fork、illegal edge or mutable rewrite blocks；

### Live Gemini contract tests

Credential-gated and explicitly separate from unit CI.

Must test:

- structured output schema;
- only allowed refs cited;
- model output cannot contain Requirement/outcome/entity-authoring fields；
- Evidence output returns exactly one wrapper per assigned fragment with only plan target keys；
- binding output uses three-state entailment and omits canonical materiality;
- deterministic proof selection derives CRITICAL/SUPPORTING;
- multiple source fragments;
- missing evidence case;
- contradiction case;
- paired clean/injected semantic-invariance case.
- disposition-critical verification schema/minimal-context/independence cases for selected proof、applicability and both contradiction sides；

### Benchmark tests

Run Continuum Dependency Bench and publish metrics.

## Regression fixtures

Every discovered model failure becomes a fixture:

```text
bench/regressions/YYYY-MM-DD-case-name/
```

Include:

- source artifacts;
- expected critical refs;
- observed bad output;
- fixed prompt/compiler version.

New Option B regression fixtures must be method-level and must not branch on benchmark case IDs or known source refs. Required cases:

- a proposal/rationale omission is deterministically recovered from trusted templates and cannot silently accept;
- selected proof becomes CRITICAL regardless of model advisory wording;
- unselected/contextual evidence remains SUPPORTING/analysis-only;
- genuinely absent evidence becomes `INSUFFICIENT_EVIDENCE` and blocks at the gate;
- ambiguous evidence remains INDETERMINATE and cannot satisfy a gate;
- contradiction missed by v1 is found and typed;
- equal-authority conflict cannot silently accept;
- model severity cannot downgrade validity-critical conflict;
- complete contradiction partition union detects cross-partition conflict;
- preflight partition capacity returns RUN_BLOCKED；post-call incomplete union returns RUN_FAILED rather than zero contradictions;
- complete Evidence fragment union finds applicability/state candidates without top-K；preflight dense capacity blocks and post-call partial union fails；
- contradiction map output is O(fragments+actual matches), not a negative cross-product；
- wrong-entity evidence never satisfies/canonicalizes a Requirement；model-invented entity/target is execution failure with null proposal-admission disposition；
- model-invented target/ref/schema violation is execution failure，not business rejection；
- a critical fragment mutation makes an accepted Decision stale;
- a counterevidence fragment mutation makes an accepted DENY Decision stale;
- an unselected failed/satisfied sibling fragment mutation leaves that DENY Decision valid;
- supporting/irrelevant fragment mutation leaves it valid;
- stale historical evidence cannot authorize acceptance;
- SourceSet cannot declare complete without authoritative complete SourceUniverse root;
- every fragment has exactly one normalization accounting outcome；silent parser omission cannot accept;
- APPLICABLE all-true and NOT_APPLICABLE stable-false proof；unsupported N/A becomes INDETERMINATE;
- applicability true→false and false→true both stale prior accepted Decisions;
- relevant new governing source/selector/catalog/rule/eligibility change stales affected Decision;
- unrelated inventory/supporting content change does not stale merely because manifest hash changed;
- derived records never join their input world snapshot and future events reach guards without historical mutation;
- material unregistered predicate yields `REJECTED_UNSUPPORTED_PREDICATE`;
- `NOT_EXISTS`/empty-retrieval absence yields `ABSENCE_PROOF_NOT_SUPPORTED_P0`；
- time-sensitive proof missing horizon is insufficient；exact expiry denies authorization without source revision；
- valid proposal whose proof supports another class is rejected without outcome substitution；
- uncovered semantic-epoch races for enterprise/new-rule/policy/catalog changes deny authorization；
- `D50 --REQUIRES--> D42`、`D50 --AUTHORIZES--> activation`、reverse stale propagation and D42' supersession non-rewrite；
- governed W17/W18 future/mixed/bypass observations are input rejected；
- epoch publication has zero required Decision writes；authorization intersects every intervening ChangeSet under unchanged pointer；
- flaky/malformed primary、contradiction or verifier call yields retryable RUN_FAILED and null proposal-admission disposition；
- selected false proof is independently REFUTED/INDETERMINATE、reselected or fails closed；
- APPROVED proposal with insufficient evidence is not admitted and is never serialized/rendered/audited as business DENIED；accepted canonical outcome is exact proposal outcome；
- provisional critical contradiction requires both model sides CONFIRMED；REFUTED side removes/recomputes and INDETERMINATE becomes typed semantic uncertainty；
- N0/N1 report false contradiction block、confirmed contradiction precision、human-review false-positive and paired resource delta from identical primary outputs；
- `INTENDED→EXECUTING` final reauthorization cancels on relevant intervening sequence and issues no call；all five crash/unknown-outcome points preserve idempotency/reconciliation；
- owner-scope sequence assignment and 188…194 range/replay reject gap、duplicate、reorder、bad predecessor and pointer mismatch；
- P0-38 direct cycle fixtures：proposal↔observation-set、universe↔read-view、compilation↔envelope/final and mutable intent-record hash；
- P0-39 fixtures：direct self-cycle、two-node insertion、supersession-mediated lineage cycle、uncommitted mutual refs and illegal D→D `AUTHORIZES`；
- direct contradiction/registered cross-predicate constraint/unsupported relation metrics cannot share a denominator；
- operational metrics retain blocked missions and publish per-domain/class median/p95 calls、tokens、latency and cost；
- K6 fixtures contain zero case-specific predicates/rules/dependency templates and new in-scope cases reuse frozen schemas；
- paraphrased equivalent Requirement selects identical Runtime proof;
- paired injection cannot suppress Requirements/evidence/contradictions or flip outcome/disposition/mutation quality;
- prompt injection cannot create an authority edge;
- unsupported OR/threshold/exception/quantified logic returns typed no-canonical result;
- semantic incompleteness cannot skip contradiction/completeness;
- existing transitive Claim/Decision dependency semantics satisfy completeness;
- A/B/N0/N1 ablation routing and metrics are isolated correctly;
- method-blind DEV annotation is frozen before replacement output、versioned/hashed/append-only and unavailable to production;
- experiment order is OpenAI DEV → Gemini DEV → freeze → Gemini-primary blind；production/agents cannot access blind bodies.

The synthetic normative P0-1…P0-39 counterexamples in `15_REPLACEMENT_ARCHITECTURE.md` are mandatory architecture fixtures. They verify contracts only and cannot be reported as live-model or benchmark evidence.

## Mutation tests

Artificially:

- remove one source dependency;
- flip model advisory materiality/severity text and verify canonical result is unchanged;
- change revision;
- inject unknown ref;
- duplicate a fragment;
- modify one unrelated policy clause;
- change an interpretation-policy revision;
- transition an applicability fact in both directions;
- advance trusted time to immediately before、exactly at and after `valid_until`；
- bind Alice's target to Bob's evidence and swap Vendor A/B；
- attempt compiler outcome substitution under the same proposal ID；
- advance enterprise/universe/policy/catalog semantic sequences/component epochs with exact ChangeSets、valid/invalid range proofs and optional irrelevance caches；
- keep lazy Decision row VALID while publishing a relevant ChangeSet and verify authorization denies；
- swap exact upstream envelope/status and attempt silent successor rebinding；
- mix governed observations from adjacent epochs and bypass the read gateway；
- corrupt primary/verifier schema/ref/receipt and assert proposal-admission disposition remains null；
- flip verifier verdict、exhaust candidate/call capacity and verify no unconfirmed proof canonicalizes；
- flip either contradiction-side verdict and verify confirmed conflict/uncertainty/admission recomputes without changing primary outputs；
- advance sequence after intent but before execution reauthorization；crash at each ledger/network boundary；replay same idempotency key and assert no duplicate logical effect；
- remove、duplicate、reorder or corrupt one ChangeSet between sequences 188 and 194 and assert governed reads/authorization block；
- map one admission rejection to business DENY in a serializer fixture and assert contract failure；
- add one relevant governing source and one irrelevant inventory artifact;
- change normalization/selection/catalog semantics independently;
- remove one Evidence or contradiction partition receipt；force dense-match limit；
- paraphrase a Requirement display string without changing structured semantics;
- replace determinate evidence with ambiguous text.

Compiler must behave predictably.

## Performance tests

P0 targets are modest but measurable:

- deterministic validation/canonicalization < 100 ms for a 100-node template-instantiated graph on laptop, excluding model calls and partition planning;
- source registry lookup does not scan all source text;
- Evidence/contradiction partition planning obeys v5 hard limits and never silently truncates；fragment maps remain ≤128 calls before verification；shared v6 disposition-critical verification is capped/metered and total protocol calls ≤192;
- per provider/domain/class operational gate records successful-compilation/context-block rates and median/p95 calls、input/output tokens、latency、settled cost with blocked missions retained.

## CI split

### Required on every commit

- unit;
- integration;
- type checks;
- deterministic benchmark subset.

### Scheduled/manual credential job

- live Gemini benchmark;
- variance suite;
- adversarial model cases.

Mock tests can never turn a live-Gemini acceptance row green.

The redesign sequence remains bounded: Experiments 2A/2B/2C–4、integrated A/B/N0/N1 30-case Experiment 5、6A OpenAI full DEV、6B Gemini full DEV、7 freeze、8 Gemini-primary blind. None of the paid/full/blind stages runs during architecture review；CI contains no blind bodies。
