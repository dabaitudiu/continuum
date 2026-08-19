# Source Identity Correction Design

## Context

Module 01 Phase A currently combines a business source revision with one parser output. That makes parser upgrades mutually exclusive, makes equal-content business revisions collide, rejects legal structured-data keys containing reference delimiters, and exposes positional array indexes as if they were stable identities.

This correction keeps Phase A's scope: it changes source identity and resolution only. It does not add Decision IR, Gemini, compiler validation, or runtime mutation.

## Identity hierarchy

The canonical hierarchy becomes:

```text
Artifact
  └── SourceRevision
        └── ParsedRepresentation
              └── Fragment
```

`Revision` is the immutable business revision. Its identity is derived from `artifact_id + revision_label`, while `content_hash` remains metadata used to verify the source bytes. Therefore:

- one business label cannot be silently overwritten with new content;
- identical content published as `v12` and `v13` produces two revisions;
- parser changes do not change business revision identity.

`ParsedRepresentation` is an immutable parser output. Its identity is derived from `revision_id + parser_version + parser_config_hash`. Parser v1 and v2 can coexist under one revision and remain independently resolvable.

`Fragment` belongs to a `ParsedRepresentation`, not directly to a source revision.

## Canonical references

A fully qualified canonical reference contains four decoded components:

```text
artifact_id @ revision_label ! representation_id # logical_path
```

Each component is serialized with canonical UTF-8 percent encoding. Delimiters and literal percent signs inside components are encoded, so legal field names containing `@`, `#`, quotes, Unicode, slash, or other punctuation round-trip without ambiguity.

Unqualified `artifact@revision#path` references remain parseable only as snapshot-relative shorthand. Registry-generated fragment IDs and provenance are always representation-qualified so historical provenance resolves exactly.

## Structured arrays

Positional indexes are never emitted as stable fragment identities.

- Default: an array is one atomic fragment at its containing field path. An insertion changes the array fragment's hash but cannot retarget a dependency to another element.
- Explicit keyed strategy: ingestion accepts `array_identity_keys`, keyed by array logical path. Every item must be an object with a unique scalar key. Item paths use a deterministic selector such as `$.controls[id="CC6.1"].result`, so unrelated insertions preserve existing item paths.
- Invalid keyed arrays—missing keys, duplicate keys, non-object items, or non-scalar identities—fail ingestion instead of falling back to positions.

The canonicalized array strategy contributes to `parser_config_hash`; changing it creates a new `ParsedRepresentation`.

## Registry and world snapshot

The registry stores revisions and parsed representations separately:

```text
add_revision(revision)
add_representation(representation, fragments)
```

A `WorldSnapshot` binds:

- each artifact to its current business revision;
- each current revision to its active parsed representation.

Normal resolution accepts only both current bindings. `allow_historical=True` permits an explicitly qualified historical revision or parser representation for audit/revalidation and marks the result as historical. `allowed_refs` returns only fully qualified refs from active representations.

## Compatibility and error behavior

This is a Phase A schema correction before Decision IR or persisted compiler records exist, so internal Phase A APIs may change. Existing stable error categories remain where possible:

- stale revision: `STALE_SOURCE_REFERENCE`;
- non-current representation: `STALE_PARSED_REPRESENTATION`;
- unknown representation: `UNKNOWN_PARSED_REPRESENTATION`;
- malformed snapshot binding: `WORLD_SNAPSHOT_INVALID`.

No migration layer is needed because there is no production source-registry persistence yet.

## Verification

The correction must demonstrate:

1. same source revision with parser v1/v2 coexists and both qualified refs resolve exactly;
2. same content under distinct business labels coexists;
3. arbitrary structured-data field names round-trip through canonical refs;
4. default arrays have no positional fragment refs;
5. keyed-array insertion preserves existing item refs;
6. snapshot-relative refs resolve only through the active representation;
7. all previous scope, validity, stale-source, immutability, determinism, backend, frontend, and build gates remain green.
