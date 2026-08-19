# 01 — Problem and Technical Thesis

## The shallow version of the problem

An agent can return:

```json
{"decision":"APPROVE","dependencies":["policy-v13","soc2-A31"]}
```

This is insufficient because:

- the model may omit a dependency;
- the model may cite an irrelevant dependency;
- IDs may not exist;
- a cited artifact may be an obsolete revision;
- the real dependency may be one section of a large policy, not the whole file;
- two sources may conflict;
- a result may depend on a derived fact rather than a directly cited document;
- broad document-level references cause massive over-invalidation later.

## Full thesis

A usable semantic dependency compiler must produce a **typed, version-aware, fragment-aware provenance graph** whose edges are sufficiently complete to support later invalidation.

The compiler is successful when it can answer:

- What exact claim did the agent make?
- What source fragment supports or governs that claim?
- Which dependencies are material to the final decision?
- Which dependencies are merely contextual?
- Which facts were derived from other claims?
- Which references were valid at decision time?
- Are there conflicting facts or policies?
- Did the model omit an obvious critical source?

## Example

Input sources:

```text
security-policy.pdf / revision 13
  §7.3 AI Vendor Requirements
  §11.2 Customer PII Controls

vendor-profile.json / revision 7
  handles_customer_pii = true

soc2.pdf / revision A31
  CC6.1 ...
```

Decision proposal:

```text
APPROVE vendor security review
```

Expected compiler output conceptually:

```text
Claim C1: vendor is an AI vendor
  DERIVED_FROM vendor-profile-r7#vendor_type

Claim C2: vendor handles customer PII
  SUPPORTED_BY vendor-profile-r7#handles_customer_pii

Claim C3: v13 requires penetration testing for this class of vendor
  GOVERNED_BY security-policy-r13#section-7.3
  REQUIRES C1
  REQUIRES C2

Claim C4: penetration-test evidence is present and acceptable
  SUPPORTED_BY pen-test-r9#finding-summary

Decision SecurityApproved
  REQUIRES C3
  REQUIRES C4
  GOVERNED_BY security-policy-r13#section-11.2
```

If only §11.2 changes later, the runtime should not blindly invalidate every decision that happened to read the whole policy file.

## Core research questions

### RQ1 — Dependency completeness

Can Gemini identify the material dependencies of its own structured decision with high recall?

### RQ2 — Granularity

Can dependency references be narrow enough to avoid excessive invalidation while still being stable across document revisions?

### RQ3 — Robustness

Can the compiler reject unsupported references, obsolete revisions, injected instructions, and contradictory evidence?

### RQ4 — Generality

Does the compiler work across multiple mission domains rather than only vendor onboarding?

## Design stance

We prefer a **hybrid compiler** with explicit semantic stages:

- Model: Requirement Decomposition, Evidence Binding, and dedicated contradiction proposals.
- Deterministic code: identity, access scope, schema, temporal validity, reference integrity, DIRECT/DERIVED_ALL completeness, outcome/justification selection, graph compilation, and invariant enforcement.
- Deterministic acceptance: precedence, outcome/blocking policy, disposition, canonicalization, and Runtime boundary.

The former open-ended second-pass critic is rejected by the product owner after K3 evidence. See `15_REPLACEMENT_ARCHITECTURE.md`; reasoner-only and old-critic pipelines remain ablation baselines, not production candidates.
