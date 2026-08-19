# 06 — Validation, Acceptance, and Canonicalization

## Fixed validation order

Structural integrity is checked immediately after the stage that introduces a typed object. Semantic uncertainty is preserved until the relevant semantic stage; source/context incompleteness blocks execution rather than being mistaken for semantic rejection.

### S0 Policy and source coverage

Validate every `CompilerPolicyBundle` ref against the exact world snapshot. Recompute bundle、manifest、included artifact/fragment、excluded reason and partition-plan hashes. Verify source selection policy、retrieval/index/query versions、coverage boundary and trusted completeness declaration. Every deterministic semantic component emits `PolicyUsageTrace`; an interpretation-affecting config read outside the bundle is `UNVERSIONED_POLICY_INPUT` and prevents canonicalization.

Anything other than `DECLARED_COMPLETE`, or any incomplete partition plan, yields `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`. A model cannot override this.

Validate normalized governing-rule forms. Applicable OR、threshold、exception、quantified、unparsed or other unsupported logic yields `REJECTED_UNSUPPORTED_LOGIC` and no canonical output.

### S1 Requirement identity and reconciliation

Validate `PredicateIdentity` against the versioned catalog、typed subject/object/qualifiers and decision-class contract. Normalize DIRECT_ATOM/ALL_OF, recursively flatten conjunctions, dedupe and sort child semantic IDs, and reject cycles.

Validate Stage-1B independently of Stage-1A. Its receipt must account exactly once for every normalized governing obligation in the manifest using `APPLICABLE | NOT_APPLICABLE | INDETERMINATE`. Missing/duplicate/unexpected keys are not an empty success；INDETERMINATE cannot normally accept. Reconcile candidates by semantic key, not display text. Valid coverage-only omissions enter the effective Requirement set; conflicts become typed coverage findings. `UNKNOWN_SOURCE_REQUIRED` is not a schema member.

### S2 Evidence candidate integrity

Check canonical ref existence、manifest membership、owner scope、world-snapshot temporal validity、source type、authority-role legality、requirement cross-link、predicate compatibility、`OBLIGATION_APPLICABILITY | PREDICATE_STATE` target and three-state entailment vocabulary. Governing authority cannot masquerade as factual state proof.

The model supplies no canonical materiality. `INDETERMINATE` is valid analysis but proof-ineligible. Historical、unauthorized or fabricated refs remain structural failures; fuzzy repair is forbidden.

### S3 Contradiction inventory and impact

Validate `ContradictionCoveragePlan` hard limits, deterministic partition membership and every receipt. Receipt union must equal the full contradiction-eligible inventory and input hashes must match. Missing/truncated/partial partitions block the run.

Globally join determinate opposing observations by stable predicate identity and the same entailment target, including cross-partition pairs. Validate refs、truth/value、scope、time and authority. Apply versioned precedence. Derive `VALIDITY_CRITICAL | NON_BLOCKING` from affected Requirement reachability、proof eligibility and resolution state; model severity is ignored for canonical effect.

### S4 Proof selection and completeness

For every required proof role, choose an eligible determinate binding using the versioned proof policy: authority/preference tier、stable source identity、binding semantic key. Selected bindings become `CRITICAL`; unselected explanatory candidates become `SUPPORTING`; indeterminate/ineligible candidates remain analysis-only.

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
- hard limits cannot represent the complete contradiction inventory;
- partition timeout、truncation、missing receipt or coverage mismatch.

These return `RUN_BLOCKED`, not a semantic disposition. Partial contradiction results are never published as complete.

## Non-structural semantic conditions

- a Stage-1 requirement is absent but Stage-1B coverage proposes it;
- a required proof role has no determinate evidence;
- entailment is `INDETERMINATE`;
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
- materially used policy refs and the exact SourceSetManifest map through a `DecisionInterpretation` Claim to the Decision;
- IDs、ordering and edge dedupe are deterministic.

### Canonical materiality

Only deterministic proof-selected bindings and materially participating interpretation policy/manifest refs produce `critical=true` edges. Model prose/labels never control canonical materiality. Unselected support remains provenance-only or analysis-only.

`CONTRADICTED_BY` is not a direct Runtime invalidation relation and cannot be the sole provenance of an accepted DENY. Counterevidence selected to justify DENY uses an invalidation-bearing support/governance edge.

### No silent semantic repair

Canonicalizer cannot:

- invent or near-match a ref;
- add an omitted Requirement or binding;
- use model materiality/severity as canonical truth;
- resolve authority by model preference;
- coerce unsupported logic;
- add redundant direct edges;
- change the proposed outcome;
- omit policy/manifest provenance that materially produced the justification.

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

The Revision-2 hash covers at least:

- normalized request and stable predicate semantics;
- exact `CompilerPolicyBundle` refs/hashes;
- exact `SourceSetManifest` and contradiction coverage plan/receipts;
- decomposition、coverage、reconciliation and effective Requirements;
- evidence candidates、validated proof selection and canonical materiality;
- contradiction observations、global pairs、precedence and deterministic impact;
- RequirementAssessments、expected outcome and DecisionJustification;
- canonical refs/source hashes、world snapshot and stage trace;
- pipeline/compiler/schema/prompt/model metadata required for provenance.

Changing only `proposition_display` must not change the semantic proof key or canonical edge set.

## Runtime invalidation contract

Accepted graph validity depends on both enterprise evidence and interpretation state. Revisions of selected source fragments、authority/outcome/classification/source-selection/proof/partition/logic policies、predicate/decision-class contracts or the SourceSetManifest must enter the ordinary artifact-change invalidation path and make the old Decision stale when they materially participated.

`RuntimeAcceptanceService` rechecks exact mission revision、world snapshot、policy bundle、manifest and compilation hash before atomic mutation. Runtime—not the compiler model—owns later Decision status transitions.
