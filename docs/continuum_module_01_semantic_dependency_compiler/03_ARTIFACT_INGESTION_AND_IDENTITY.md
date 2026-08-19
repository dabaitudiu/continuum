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
