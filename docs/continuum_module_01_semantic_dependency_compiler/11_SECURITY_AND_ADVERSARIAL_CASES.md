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

## Trust classification

Every source has:

```text
trust_class
source_type
owner_scope
authority_rank
```

Example authority ordering is domain-configured, never model-invented.

Authority classification、precedence、outcome semantics、source selection、proof selection、partitioning、predicate/decision-class and supported-logic rules are immutable versioned policy artifacts. Accepted Decisions retain critical provenance to every materially participating policy and exact SourceSetManifest; changing them must trigger normal stale/revalidation semantics.

## Prompt injection isolation and semantic invariance

Source fragments are data, not instructions.

The agent system prompt explicitly labels external document content as untrusted. If Model Armor is available later, route untrusted text through it, but this module must retain its own structural trust rules.

Structural isolation alone is insufficient. Every injection case has a clean twin with identical governing semantics. The pair must preserve:

- stable effective Requirement set;
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

The allowlist is backed by a validated `SourceSetManifest`. `INCOMPLETE | UNKNOWN` coverage or a retrieved subset without versioned completeness semantics yields `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`.

## Stale revision defense

The model can read historical revisions only if the request allows them. Historical refs are tagged and cannot accidentally compile as current governing dependencies.

## Model-label distrust

- Canonical materiality is selected by deterministic proof role; the model has no CRITICAL/SUPPORTING write field.
- Contradiction impact is computed from reachability、proof eligibility and precedence; model severity is advisory.
- `INDETERMINATE` cannot be selected as proof.
- Display proposition text cannot affect semantic identity or DENY proof selection.

## Context and logic fail-closed rules

Contradiction input is deterministically partitioned with receipts and global reduction. Silent truncation is forbidden. Applicable governing logic outside DIRECT_ATOM/ALL_OF produces typed `REJECTED_UNSUPPORTED_LOGIC`; it cannot be approximated.

## Adversarial benchmark cases

At least:

- 10 prompt-injection documents;
- 10 misleading near-match clauses;
- 10 obsolete revision traps;
- 10 contradictory-authority cases;
- 10 dependency-omission cases.

Each injection case is evaluated as a clean/injected pair. Add context-coverage omissions、cross-partition conflicts、ambiguous entailment、policy-revision mutations、semantic paraphrases and unsupported logical forms to the adversarial suite.

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
