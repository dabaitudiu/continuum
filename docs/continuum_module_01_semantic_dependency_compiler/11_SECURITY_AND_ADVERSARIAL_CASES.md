# 11 — Security and Adversarial Cases

## Threat model specific to this module

1. Source text contains prompt injection.
2. Model fabricates a canonical ref.
3. Model cites an unauthorized tenant/source.
4. Model cites stale policy revision.
5. Malicious document attempts to become a `GOVERNED_BY` authority.
6. A low-trust source contradicts authoritative policy.
7. Model marks contextual evidence as critical to force broad invalidation.
8. Model omits a material dependency to make approval easier.

## Trust classification

Every source has:

```text
trust_class
source_type
owner_scope
authority_rank
```

Example authority ordering is domain-configured, never model-invented.

## Prompt injection isolation

Source fragments are data, not instructions.

The agent system prompt explicitly labels external document content as untrusted. If Model Armor is available later, route untrusted text through it, but this module must retain its own structural trust rules.

## Relation restrictions

Only policy-class sources may normally produce `GOVERNED_BY` edges.

A vendor PDF stating “this document overrides your policy” must not gain policy authority through model output.

## Scope validation

Refs are issued from a request-scoped allowlist. Cross-tenant references fail even if they exist globally.

## Stale revision defense

The model can read historical revisions only if the request allows them. Historical refs are tagged and cannot accidentally compile as current governing dependencies.

## Adversarial benchmark cases

At least:

- 10 prompt-injection documents;
- 10 misleading near-match clauses;
- 10 obsolete revision traps;
- 10 contradictory-authority cases;
- 10 dependency-omission cases.

## Security acceptance

A prompt-injected source may influence semantic facts only as ordinary data; it must not:

- alter compiler instructions;
- invent a privileged tool call;
- authorize a side effect;
- bypass source authority rules;
- create canonical IDs.
