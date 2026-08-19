# 06 — Validation, Acceptance, and Canonicalization

## Fixed validation order

Structural integrity is checked immediately after the stage that introduces a typed object. Semantic uncertainty is preserved until the relevant semantic stage; source/context incompleteness blocks execution rather than being mistaken for semantic rejection.

### S0 Universe、normalization、policy and source coverage

Validate the input `EnterpriseWorldSnapshot` and separate `CompilerPolicySnapshot/Bundle`。Validate authoritative registry、namespace enumeration、watermarks、attestation and hash in `SourceUniverseSnapshot`；then recompute fragment-complete normalization and SourceSet selection/partition hashes. Every deterministic semantic component emits `PolicyUsageTrace`；an interpretation-affecting config read outside the bundle is `UNVERSIONED_POLICY_INPUT` and prevents canonicalization. Derived manifests bind these inputs but cannot be members of the input world snapshot。

Anything other than complete universe、normalization、selection and partition coverage yields `RUN_BLOCKED`. A model cannot override this；silent parser omission cannot become `NO_GOVERNING_RULE`。

Validate normalized governing-rule forms and catalog representability. Unsupported logic yields `REJECTED_UNSUPPORTED_LOGIC`；material unregistered semantics yields `REJECTED_UNSUPPORTED_PREDICATE`；unparsed/review-required normalization blocks. No result has canonical output。

### S1 Requirement identity and reconciliation

Validate `PredicateIdentity` against the versioned catalog、typed subject/object/qualifiers and decision-class contract. Normalize DIRECT_ATOM/ALL_OF, recursively flatten conjunctions, dedupe and sort child semantic IDs, and reject cycles.

Validate Stage-1B independently of Stage-1A. Its receipt must account exactly once for every normalized obligation and retain a Requirement candidate for every representable obligation. Treat proposed applicability as advisory：Stage 1C emits provisional proof candidates only. Missing/ambiguous proof is INDETERMINATE；all supported Requirements remain available for binding/contradiction. Reconcile by semantic key, not display text。`UNKNOWN_SOURCE_REQUIRED` and invented codes are not schema members。

### S2 Evidence candidate integrity

Check canonical enterprise ref existence、manifest membership、owner scope、world-snapshot temporal validity、source type、authority-role legality、requirement cross-link、predicate compatibility、`NORMALIZED_OBLIGATION | REQUIREMENT_PREDICATE` target and three-state entailment vocabulary. Applicability predicate bindings remain separately typed。Governing authority cannot masquerade as applicability or factual state proof.

The model supplies no canonical materiality. `INDETERMINATE` is valid analysis but proof-ineligible. Historical、unauthorized or fabricated refs remain structural failures; fuzzy repair is forbidden.

### S3 Contradiction inventory and impact

Validate `ContradictionCoveragePlan` hard limits, deterministic partition membership and every receipt. Receipt union must equal the full contradiction-eligible inventory and input hashes must match. Missing/truncated/partial partitions block the run.

Globally join determinate opposing observations by stable predicate identity and the same entailment target, including applicability predicates and cross-partition pairs. Validate refs、truth/value、scope、time and authority. Apply versioned precedence. Derive `VALIDITY_CRITICAL | NON_BLOCKING` from affected applicability/Requirement reachability、proof eligibility and resolution state；model severity is ignored。

### S4 Proof selection and completeness

First reduce applicability contradictions/precedence and finalize APPLICABLE/N/A justifications or INDETERMINATE. This determines the effective Requirement set. Then, for every required proof role, choose an eligible determinate binding using authority/preference tier、stable source identity and binding semantic key. Selected bindings become `CRITICAL`；unselected explanatory candidates become `SUPPORTING`；indeterminate/ineligible candidates remain analysis-only。

Compute one assessment per reconciled effective Requirement. DIRECT_ATOM uses selected role evidence and contradiction state. ALL_OF uses the fixed conjunction truth table. Compute support paths、blocking IDs and deterministic finding templates. Do not demand redundant direct evidence on derived Requirements.

### S5 Outcome and acceptance

Compute expected `APPROVE | DENY | REVIEW` from root assessments and compare it with the untrusted proposal through the versioned outcome policy. For accepted APPROVE/DENY, emit a `DecisionJustification` whose proof selection excludes display text、case/domain/local IDs and iteration order.

## Early structural errors

- invalid schema after one bounded repair;
- duplicate/unknown local IDs、invalid predicate identity or requirement cycle;
- fabricated、unauthorized、cross-scope or stale ref;
- illegal source role/authority relation;
- manifest/world/hash mismatch;
- inconsistent typed cross-link.

These may terminate early with an exact stage trace and no canonical output.

## Execution-blocking conditions

- credential/provider/transport/budget unavailable;
- source universe `INCOMPLETE | UNKNOWN`;
- normalization `INCOMPLETE | REVIEW_REQUIRED` or missing accounting/review receipt;
- hard limits cannot represent the complete contradiction inventory;
- partition timeout、truncation、missing receipt or coverage mismatch.

These return `RUN_BLOCKED`, not a semantic disposition. Partial contradiction results are never published as complete.

## Non-structural semantic conditions

- a Stage-1 requirement is absent but Stage-1B coverage proposes it;
- a required proof role has no determinate evidence;
- entailment is `INDETERMINATE`;
- applicability is `INDETERMINATE` or conflicts with its candidate proof;
- current authorities conflict;
- model outcome disagrees with evidence;
- model advisory materiality/severity is wrong.

Once representable effective Requirements exist, these must reach reconciliation、contradiction、proof/completeness and gate as applicable. They do not justify an early structural exit.

## Canonicalization

Canonicalization runs only after `ACCEPTED`.

### Stable proof mapping

- every selected RequirementAssessment maps to a Claim identified from stable predicate/topology semantics, not display text;
- every Stage-4 `SELECTED_PROOF` binding maps SourceFragment → DIRECT Claim through validity-bearing `SUPPORTED_BY | GOVERNED_BY`;
- every selected ALL_OF relationship maps prerequisite Claim → derived Claim;
- selected roots map Claim → Decision;
- selected applicability facts map through APPLICABLE/NOT_APPLICABLE guard Claims；
- materially used policy refs and selective boundary/rule-set/contradiction-eligibility guards map through a `DecisionInterpretation` Claim；full manifests remain audit-only derivation;
- IDs、ordering and edge dedupe are deterministic.

### Canonical materiality

Only deterministic proof-selected bindings、applicability guards and materially participating interpretation/coverage guards produce `critical=true` edges. Model prose/labels and whole-manifest inventory never control canonical materiality. Unselected support remains provenance-only or analysis-only.

`CONTRADICTED_BY` is not a direct Runtime invalidation relation and cannot be the sole provenance of an accepted DENY. Counterevidence selected to justify DENY uses an invalidation-bearing support/governance edge.

### No silent semantic repair

Canonicalizer cannot:

- invent or near-match a ref;
- add an omitted Requirement or binding;
- use model materiality/severity as canonical truth;
- resolve authority by model preference;
- coerce unsupported logic;
- invent/ignore an unsupported predicate or trust unproved NOT_APPLICABLE;
- add redundant direct edges;
- change the proposed outcome;
- omit policy/applicability/selective-coverage provenance that materially produced the justification.

## Stable DENY proof selection

APPROVE includes all necessary root closures. DENY selects one failed proof using:

```text
failure_class_priority from versioned proof policy
→ failed DIRECT predicate_semantic_key
→ sorted selected proof SourceRef identities
→ flattened canonical path topology hash
```

Human-readable proposition text is excluded. Semantically equivalent paraphrases over the same structured predicates/context must select the same Runtime critical dependency set.

## Compilation hash

The Revision-3 hash covers at least:

- normalized request and stable predicate semantics;
- exact `CompilerPolicyBundle` refs/hashes;
- exact world/universe/policy input IDs and derived `RuleNormalizationManifest`/`SourceSetManifest`/partition receipts;
- applicability candidates、validated justifications and selective coverage guards;
- decomposition、coverage、reconciliation and effective Requirements;
- evidence candidates、validated proof selection and canonical materiality;
- contradiction observations、global pairs、precedence and deterministic impact;
- RequirementAssessments、expected outcome and DecisionJustification;
- canonical refs/source hashes、world snapshot and stage trace;
- pipeline/compiler/schema/prompt/model metadata required for provenance.

Changing only `proposition_display` must not change the semantic proof key or canonical edge set.

## Runtime invalidation contract

Accepted graph validity depends on selected enterprise evidence/applicability facts and interpretation/coverage semantics. Relevant revisions of selected fragments、catalog/normalization/selection/authority/outcome/proof policies、governing rule set or contradiction eligibility enter invalidation through stable guards. A full manifest hash change caused only by irrelevant inventory/supporting content must not automatically stale all Decisions；unknown boundary impact may conservatively stale only Decisions inside that boundary and is measured。

`RuntimeAcceptanceService` rechecks exact mission revision、input world/universe/policy snapshots、derived-artifact envelope、selective guards and compilation hash before atomic mutation. Future changes reach historical derived provenance through the deterministic impact index without mutating historical snapshots. Runtime—not the compiler model—owns later Decision status transitions.
