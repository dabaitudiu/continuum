# 03 — Artifact Ingestion and Stable Identity

## Goal

Later invalidation only works if dependencies point to stable, versioned source identities.

## Source hierarchy

```text
Artifact
  └── Revision
       └── ParsedRepresentation
            └── Fragment
                 └── optional Span
```

## Artifact

Represents the logical object across revisions.

Fields:

```text
artifact_id              stable logical identity
artifact_type            POLICY | DOCUMENT | RECORD | TOOL_SNAPSHOT | HUMAN_APPROVAL | ...
logical_key              domain-facing stable key
owner_scope              tenant/domain/mission scope
created_at
```

Example:

```text
artifact_id = policy:security-policy
```

## Revision

Immutable snapshot.

```text
revision_id              stable unique identity
artifact_id
revision_label           v13 / commit SHA / timestamped version
content_hash
created_at
valid_from
valid_until?
source_uri?
```

Example:

```text
revision_id = policy:security-policy@revision:8fa...
revision_label = v13
```

Business revision identity is independent of content identity and parser identity. Two business labels with identical bytes remain distinct revisions, while one label cannot be silently overwritten with different bytes.

## ParsedRepresentation

Immutable parser output for one source revision.

```text
representation_id
revision_id
parser_version
parser_config_hash
created_at
```

The identity includes `revision_id`, `parser_version`, and canonical parser configuration. Parser v1 and parser v2 of the same source revision may coexist, and old provenance continues to identify its exact representation.

## Fragment

A semantically addressable subsection.

```text
fragment_id
representation_id
fragment_type            SECTION | CLAUSE | FIELD | ROW | TOOL_FIELD | PAGE_BLOCK
logical_path             e.g. section/7.3 or $.handles_customer_pii
heading?
text_hash
ordinal
parent_fragment_id?
```

### Identity rule

`fragment_id` must not depend solely on raw byte offsets because small edits shift offsets. Prefer a stable logical path when the source has structure. Use content hash + parent identity as fallback.

Example:

```text
policy:security-policy@v13!representation-id#section/7.3
vendor-profile@r7!representation-id#$.handles_customer_pii
```

Canonical references are fully representation-qualified:

```text
artifact_id @ revision_label ! representation_id # logical_path
```

Components use canonical UTF-8 percent encoding. Delimiter characters and arbitrary structured-data field names—including `@`, `#`, quotes, Unicode, slash, and `%`—therefore round-trip without ambiguity. Unqualified `artifact@revision#path` is snapshot-relative shorthand only and must not be persisted as canonical provenance.

### Structured array identity

Positional indexes are not stable identities and must not be emitted as critical fragment refs.

- Without explicit configuration, an array is one atomic fragment at its field path.
- A configured keyed array uses a unique scalar field to form selectors such as `$.controls[id="CC6.1"].result`.
- Missing, duplicate, non-scalar, or otherwise invalid stable keys fail ingestion; the parser never falls back to positions.
- The keyed-array configuration contributes to `parser_config_hash`.

## Optional span references

Use spans only for evidence display or verification:

```text
span_id
fragment_id
start_offset
end_offset
span_hash
```

Do not require permanent storage of long quoted text. Store safe excerpts only when useful for UI.

## Supported P0 source types

1. Markdown/text policy documents.
2. JSON/YAML structured records.
3. PDF converted to deterministic text blocks by a controlled parser fixture.
4. Tool snapshots returned as structured JSON.

Do not build a universal ingestion engine in this module.

## P0 normalized governing-rule contract

Reading a policy fragment is not enough to claim support for arbitrary policy logic. A governing fragment may participate in a normal accepted P0 compilation only when its active `ParsedRepresentation` exposes a versioned, trusted normalized-rule record:

```text
NormalizedRule
  obligation_key             stable within the logical policy artifact
  governing_source_ref       exact current fragment
  predicate_code             from the versioned PredicateCatalog
  expected_state
  logic_form                 DIRECT_ATOM | ALL_OF | OR | THRESHOLD |
                             EXCEPTION | QUANTIFIED | UNPARSED | OTHER
  child_obligation_keys[]
  scope_qualifiers
  temporal_qualifiers
  normalized_rule_hash
```

P0 accepts only `DIRECT_ATOM | ALL_OF`. Applicable `OR`、threshold、exception、quantified、unparsed or other unsupported forms produce a typed `REJECTED_UNSUPPORTED_LOGIC` result and no canonical graph. The compiler must never reinterpret them as conjunction. The normalized rule must be source-authored structured policy or produced by a controlled versioned parser and independently approved/signed; unreviewed model normalization is not a trusted acceptance input.

Raw Markdown/PDF prose may still be ingested and shown as context, but if the governing semantics needed for a Decision lack a trusted normalized-rule representation, source coverage is not sufficient for normal acceptance.

## Compiler policy and source-manifest artifacts

Deterministic interpretation inputs use the same immutable identity model as enterprise sources. At minimum the following are versioned artifacts in the world snapshot:

- authority precedence policy;
- authority classification policy;
- outcome semantics policy;
- source-selection policy;
- decision-class contract;
- predicate catalog;
- proof-selection policy;
- context-partition policy;
- supported-logic policy;
- the exact `SourceSetManifest` produced for the compilation.

Their canonical refs and content hashes are not audit-only metadata. Any materially participating policy/manifest ref becomes a validity-bearing Runtime dependency of an accepted Decision, so a revision change enters the ordinary deterministic invalidation path.

Revision 2 extends the artifact/source-type vocabulary with trusted `COMPILER_POLICY` and `SOURCE_SET_MANIFEST` provenance classes. A manifest logical key is derived from scope、decision class、coverage-boundary digest and selection-policy logical key; its revision content hashes the complete selected universe/world snapshot. Relevant universe changes publish a superseding manifest revision so existing Runtime edges can invalidate deterministically.

## Source-universe coverage

Every compilation binds to a content-addressed `SourceSetManifest` containing the selection policy/version, world snapshot, coverage boundary, included artifacts/fragments, excluded artifacts with reason codes, retrieval/index/query versions, contradiction-eligible refs, partition-plan hash, and `DECLARED_COMPLETE | INCOMPLETE | UNKNOWN` status.

Only a trusted source-selection component may declare completeness. A retrieved subset whose completeness cannot be proven for the decision class is `UNKNOWN` and causes `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`. Silent truncation is forbidden.

## Revision semantics

A compiler request is bound to a `world_snapshot_id`. Every referenced revision must be valid in that snapshot, and every current revision is bound to one active parsed representation.

If a model cites an older revision that exists but was not current for the snapshot, validation fails with `STALE_SOURCE_REFERENCE` unless the task explicitly allows historical reasoning.

## Parser versioning

Fragment identity and parsed structure include a `ParsedRepresentation`. If parsing changes materially, re-ingest under a new parser version or parser configuration and never silently reinterpret old provenance.

## Acceptance examples

- Two revisions of the same policy share `artifact_id` but have different `revision_id`.
- Equal-content business revisions with different labels have different `revision_id` values.
- Parser v1 and parser v2 outputs for one revision coexist and resolve exactly.
- Structured JSON field references remain stable if unrelated fields are added.
- Array insertion cannot retarget an existing dependency to a different item.
- A policy edit to §12 does not change the identity of untouched §7.3 when logical headings remain stable.
- The compiler can explain exactly which revision and fragment a dependency uses.
