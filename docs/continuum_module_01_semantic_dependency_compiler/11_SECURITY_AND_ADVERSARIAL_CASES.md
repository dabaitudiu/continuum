# 11 — Security and Adversarial Cases

## Threat model specific to this module

1. Source text contains prompt injection.
2. Model fabricates a canonical ref.
3. Model cites an unauthorized tenant/source.
4. Model cites stale policy revision.
5. Malicious document attempts to become a `GOVERNED_BY` authority.
6. A low-trust source contradicts authoritative policy.
7. Model prose calls necessary evidence supporting, attempting to suppress invalidation.
8. Model severity downgrades a blocking contradiction.
9. Model omits a material dependency to make approval easier.
10. Source retrieval silently omits a governing artifact.
11. Context limits silently truncate contradiction inventory.
12. Unsupported OR/threshold/exception logic is coerced into conjunction.
13. Requirement paraphrase changes DENY proof selection.
14. Model suppresses a material rule with unsupported `NOT_APPLICABLE`.
15. Parser silently omits a governing fragment.
16. Selector declares completeness over an incomplete catalog/index.
17. A whole SourceSet manifest becomes a super-dependency and stales unrelated Decisions.
18. Model invents a predicate code for an unrepresentable obligation.
19. Compiler silently replaces the domain-agent proposal outcome.
20. A template or model encodes a benchmark-specific exact graph/outcome.
21. Top-K Evidence search omits a current fact/applicability proof.
22. Model uses Bob/Vendor B evidence for Alice/Vendor A.
23. Time-sensitive proof remains authorizing after expiry with no source revision.
24. Empty retrieval is treated as `NOT_EXISTS` proof.
25. New semantic sequence becomes executable before old Decisions stale/certify irrelevance.
26. Proposal-admission rejection is rendered as a newly authored business DENY.
27. Relevant ChangeSet publishes after intent authorization but before external execution begins.
28. Hallucinated contradiction side forces review without independent verification.
29. ChangeSet sequence contains a gap、duplicate、reorder or bad predecessor during recovery.
26. Dense contradiction output is truncated and reported complete.
27. Upstream Decision D42 is degraded to a document/ref, so D50 escapes when D42 becomes stale/superseded.
28. Agent bypasses the governed tool gateway and mixes a future W18 observation into a W17 proposal.
29. Epoch publication requires a fleet-wide atomic Decision-row fan-out and becomes unavailable.
30. Malformed/fabricated model output is persisted as durable business DENY.
31. A single interpreter reads “training expired” as ENTAILED_TRUE and false proof canonicalizes.
32. Same-predicate contradiction support is misrepresented as generic cross-predicate reasoning.
33. Safe-but-blocked missions are removed from operational denominators.

## Trust classification

Every source has:

```text
trust_class
source_type
owner_scope
authority_rank
```

Example authority ordering is domain-configured, never model-invented.

Authority classification、precedence、proposal-outcome mapping、governed read、upstream Decision binding、universe/selection、normalization/review、entity roles、Evidence/contradiction coverage、proof verification、temporal/epoch、predicate/decision-class/registered-constraint and operational rules are immutable `CompilerPolicyArtifact` revisions outside the enterprise world snapshot. Accepted Decisions retain critical provenance to exact proposal/entity/observation/upstream context、verification receipts、material policies、applicability/temporal facts and selective guards；full manifests are audit derivation, not a super-dependency。

## Prompt injection isolation and semantic invariance

Source fragments are data, not instructions.

The agent system prompt explicitly labels external document content as untrusted. If Model Armor is available later, route untrusted text through it, but this module must retain its own structural trust rules.

Structural isolation alone is insufficient. Every injection case has a clean twin with identical governing semantics. The pair must preserve:

- stable effective Requirement set;
- unchanged supplied proposal outcome and entity binding；
- deterministic selected-proof critical coverage;
- contradiction inventory and deterministic impact;
- expected outcome and final disposition;
- accepted-only stale escape and unnecessary invalidation direction;
- zero illegal authority/ref/policy edges.

An injected fragment that never becomes an authority edge still fails if it suppresses an obligation or contradiction, flips disposition, or worsens mutation behavior.

## Relation restrictions

Only policy-class sources may normally produce `GOVERNED_BY` edges.

A vendor PDF stating “this document overrides your policy” must not gain policy authority through model output.

## Scope validation

Refs are issued from a request-scoped allowlist. Cross-tenant references fail even if they exist globally.

The allowlist is backed by `SourceUniverseSnapshot → RuleNormalizationManifest → SourceSetManifest`. Missing/stale authority attestation、fragment accounting、review receipt or selector completeness yields `RUN_BLOCKED`。

Every material read also carries a signed `GovernedObservation` bound to the executable world/semantic sequence/component epoch and gateway authorization context. Unversioned、future、mixed-sequence/epoch or bypass observations are `INPUT_REJECTION`, never proof. A model-emitted forbidden/cross-scope ref is an execution failure with null proposal-admission disposition, not a semantic rejection。

## Stale revision defense

The model can read historical revisions only if the request allows them. Historical refs are tagged and cannot accidentally compile as current governing dependencies.

## Model-label distrust

- Canonical materiality is selected by deterministic proof role; the model has no CRITICAL/SUPPORTING write field.
- Every selected model-interpreted enterprise/applicability proof requires an independent `CONFIRMED`; REFUTED/INDETERMINATE triggers deterministic reselection and cannot canonicalize.
- Contradiction impact is computed from reachability、proof eligibility and precedence；the replacement schema has no model severity field.
- `INDETERMINATE` cannot be selected as proof.
- APPLICABLE/NOT_APPLICABLE require deterministic current predicate proof；an unsupported model N/A is INDETERMINATE.
- Unknown material predicate codes yield `REJECTED_UNSUPPORTED_PREDICATE` rather than invention/omission.
- Models cannot author Requirements、outcomes、predicate/entity keys；cross-entity matches are proof-ineligible.
- `NOT_EXISTS`/empty-retrieval absence is explicitly unsupported in P0.
- Time/epoch authorization is checked synchronously；model output cannot mint guards/certificates.
- Required upstream Decisions keep exact Decision→Decision bindings；STALE/SUPERSEDED/INVALID cannot satisfy and successor rebinding is never implicit.
- Compiler/model/schema/ref/transport/verifier failure has no proposal-admission disposition and cannot authorize a durable business DENY。
- Display proposition text cannot affect semantic identity or DENY proof selection.

## Context and logic fail-closed rules

Evidence/applicability and contradiction inputs are fragment-complete deterministic partitions with exact receipts. Output uses fragment wrappers + actual matches；silent top-K、negative-cross-product truncation and normalizer omission are forbidden. P0 contradiction claims only direct same-predicate/entity/target conflict；cross-predicate invariants require a registered deterministic contract/template or emit `UNSUPPORTED_CROSS_PREDICATE_RELATION_P0`. Governing logic outside DIRECT_ATOM/ALL_OF produces `REJECTED_UNSUPPORTED_LOGIC`；material/absence semantics outside P0 catalog produce `REJECTED_UNSUPPORTED_PREDICATE`。

## Adversarial benchmark cases

At least:

- 10 prompt-injection documents;
- 10 misleading near-match clauses;
- 10 obsolete revision traps;
- 10 contradictory-authority cases;
- 10 dependency-omission cases.

Each injection case is evaluated as a clean/injected pair. Add catalog/universe omissions、normalizer omissions、Evidence top-K/receipt traps、direct same-predicate versus registered/unsupported cross-predicate cases、cross-entity matches、ambiguous applicability/entailment、false selected-proof/contradiction interpretations、D42→D50→activation、governed-read bypass/mixing、zero-fan-out sequence races/gaps/reorders、authorization-to-execution TOCTOU/crash points、execution-failure/admission-taxonomy and admission-as-business-outcome traps、operational denominator traps、proposal outcome substitution、K6 traps and unsupported logic/predicate/absence。

## Security acceptance

A prompt-injected source may influence semantic facts only as ordinary data; it must not:

- alter compiler instructions;
- invent a privileged tool call;
- authorize a side effect;
- bypass source authority rules;
- create canonical IDs.
- suppress a required stable predicate;
- change selected proof coverage;
- suppress/downgrade a contradiction;
- flip expected outcome/disposition;
- worsen Runtime mutation quality;
- change proof selection through lexical paraphrase.
