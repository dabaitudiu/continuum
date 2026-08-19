# 06 — Dependency Validation and Canonicalization

## Validator pipeline

Validation occurs in a fixed order so failures are reproducible.

### V1 Schema validation

Check:

- required fields;
- enum values;
- max lengths;
- confidence range;
- duplicate local claim IDs;
- relation type legality.

### V2 Referential integrity

Every `source_ref` must exist in the request's SourceRegistry snapshot.

Unknown refs are fatal.

### V3 Scope authorization

A valid source may still be outside the current mission/agent scope. Reject cross-tenant or unauthorized refs.

### V4 Temporal validity

Validate that the referenced revision was current or otherwise allowed in `world_snapshot_id`.

### V5 Dependency type rules

Examples:

- `GOVERNED_BY` source must be policy/rule-like.
- `SUPPORTED_BY` cannot target an unrelated action node.
- `AUTHORIZES` should originate from a valid decision in runtime, not raw text.
- `DERIVED_FROM` between claims must form an allowed graph.

### V6 Claim support

Every critical FACT/RULE claim must have source or derived-claim support.

### V7 Decision support

High-risk outcomes must have at least one critical dependency path. “APPROVED with zero critical dependencies” is invalid.

## Canonicalization

### Normalize refs

Resolve aliases to canonical fragment refs before persistence.

### Deduplicate edges

Two identical edges collapse deterministically.

### Stable ordering

Sort by source ref, target local claim/decision identity, relation, then materiality.

### Preserve materiality

`CRITICAL` edges drive later invalidation. `SUPPORTING`/`CONTEXTUAL` edges are provenance-only unless domain policy promotes them.

### Canonical edge creation

Example:

```text
fragment:policy...#section/7.3
    --GOVERNED_BY[CRITICAL]-->
claim:c3

claim:c3
    --REQUIRES[CRITICAL]-->
decision:security-review
```

## Important rule: no broad auto-upgrade

The compiler must not convert every source the model read into a critical dependency. Reading context is not the same as material dependence.

## Important rule: no silent repair

If the model cites:

```text
policy-v13#section7
```

but only:

```text
policy-v13#section/7.3
```

exists, the compiler may return a repair suggestion, but must not silently substitute it in a high-risk decision.

## Compilation hash

Persist a hash over:

- normalized DecisionDraft;
- canonical refs + source hashes;
- compiler version;
- validation policy version.

This lets audit records prove what was compiled.
